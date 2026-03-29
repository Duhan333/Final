// SPDX-FileCopyrightText: The openTCS Authors
// SPDX-License-Identifier: MIT
package org.opentcs.ros2.adapter;

import static java.util.Objects.requireNonNull;

import java.io.BufferedReader;
import java.io.BufferedWriter;
import java.io.EOFException;
import java.io.IOException;
import java.io.InputStreamReader;
import java.io.OutputStreamWriter;
import java.net.InetSocketAddress;
import java.net.Socket;
import java.net.SocketTimeoutException;
import java.nio.charset.StandardCharsets;
import java.util.function.Consumer;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * TCP client for the ROS2 bridge protocol ({@code GOAL} / {@code RESULT} / {@code POSE}).
 */
public class Ros2TcpBridgeSession {

  /**
   * This class's logger.
   */
  private static final Logger LOG = LoggerFactory.getLogger(Ros2TcpBridgeSession.class);

  /**
   * Synchronizes access to the socket streams.
   */
  private final Object connectionLock = new Object();
  /**
   * Current socket when using a persistent connection.
   */
  private Socket socket;
  /**
   * Writer for the open socket.
   */
  private BufferedWriter writer;
  /**
   * Reader for the open socket.
   */
  private BufferedReader reader;

  /**
   * Creates a new session.
   */
  public Ros2TcpBridgeSession() {
  }

  /**
   * Disconnects and releases resources.
   */
  public void disconnect() {
    synchronized (connectionLock) {
      closeQuietly();
    }
  }

  /**
   * Sends {@code GOAL x y theta} and reads lines until {@code RESULT OK} or {@code RESULT FAILED}.
   *
   * @param configuration bridge connection and timeout settings
   * @param bridgeHost TCP host (often per-vehicle override of {@code configuration.bridgeHost()})
   * @param bridgePort TCP port (often per-vehicle override of {@code configuration.bridgePort()})
   * @param goalMetresRadians goal as {@code [x, y, theta]} in metres and radians
   * @param poseListener optional consumer for {@code POSE x y theta} lines (may be {@code null})
   * @return {@code true} if RESULT OK
   * @throws IOException on I/O errors
   */
  public boolean sendGoalWaitResult(
      Ros2AdapterConfiguration configuration,
      String bridgeHost,
      int bridgePort,
      double[] goalMetresRadians,
      Consumer<double[]> poseListener
  )
      throws IOException {
    requireNonNull(configuration, "configuration");
    requireNonNull(bridgeHost, "bridgeHost");
    requireNonNull(goalMetresRadians, "goalMetresRadians");
    if (goalMetresRadians.length < 3) {
      throw new IllegalArgumentException("goalMetresRadians must contain x, y, theta");
    }

    boolean persistent = configuration.usePersistentConnection();
    if (!persistent) {
      disconnect();
    }
    requireOpenStreams(
        bridgeHost,
        bridgePort,
        configuration.connectTimeoutMs(),
        persistent
    );

    String goalLine = String.format(
        java.util.Locale.US,
        "GOAL %.6f %.6f %.6f%n",
        goalMetresRadians[0],
        goalMetresRadians[1],
        goalMetresRadians[2]
    );
    synchronized (connectionLock) {
      LOG.debug("Sending to ROS2 bridge: {}", goalLine.trim());
      writer.write(goalLine);
      writer.flush();
    }

    int navigationTimeoutMs = configuration.navigationTimeoutMs();
    long deadline = System.currentTimeMillis() + Math.max(1, navigationTimeoutMs);
    while (System.currentTimeMillis() < deadline) {
      String line;
      try {
        synchronized (connectionLock) {
          if (socket == null || socket.isClosed()) {
            throw new IOException("ROS2 bridge connection closed unexpectedly");
          }
          long remaining = deadline - System.currentTimeMillis();
          if (remaining <= 0) {
            throw new SocketTimeoutException("navigation timed out waiting for RESULT");
          }
          int soTimeout = (int) Math.min(remaining, 5_000L);
          socket.setSoTimeout(Math.max(1, soTimeout));
          line = reader.readLine();
        }
      }
      catch (SocketTimeoutException exc) {
        // soTimeout is a per-read slice; no POSE/keepalive in 5s must not abort a long Nav2 run.
        continue;
      }
      if (line == null) {
        throw new EOFException("ROS2 bridge closed connection before RESULT");
      }
      line = line.trim();
      if (line.isEmpty()) {
        continue;
      }
      String upper = line.toUpperCase(java.util.Locale.US);
      if (upper.startsWith("POSE ")) {
        handlePoseLine(line, poseListener);
      }
      else if ("RESULT OK".equalsIgnoreCase(line)) {
        if (!persistent) {
          disconnect();
        }
        return true;
      }
      else if ("RESULT FAILED".equalsIgnoreCase(line)
          || upper.startsWith("RESULT FAILED")) {
            if (!persistent) {
              disconnect();
            }
            return false;
          }
      else {
        LOG.debug("Ignoring bridge line: {}", line);
      }
    }
    throw new SocketTimeoutException("navigation timed out waiting for RESULT");
  }

  private void requireOpenStreams(String host, int port, int connectTimeoutMs, boolean persistent)
      throws IOException {
    synchronized (connectionLock) {
      if (persistent && socket != null && !socket.isClosed() && writer != null && reader != null) {
        return;
      }
      closeQuietly();
      Socket newSocket = new Socket();
      newSocket.connect(new InetSocketAddress(host, port), Math.max(1, connectTimeoutMs));
      newSocket.setTcpNoDelay(true);
      this.socket = newSocket;
      this.writer = new BufferedWriter(
          new OutputStreamWriter(newSocket.getOutputStream(), StandardCharsets.UTF_8)
      );
      this.reader = new BufferedReader(
          new InputStreamReader(newSocket.getInputStream(), StandardCharsets.UTF_8)
      );
    }
  }

  private void handlePoseLine(String line, Consumer<double[]> poseListener) {
    if (poseListener == null) {
      return;
    }
    String[] parts = line.split("\\s+");
    if (parts.length < 4) {
      return;
    }
    try {
      double x = Double.parseDouble(parts[1]);
      double y = Double.parseDouble(parts[2]);
      double theta = Double.parseDouble(parts[3]);
      poseListener.accept(new double[]{x, y, theta});
    }
    catch (NumberFormatException exc) {
      LOG.warn("Malformed POSE line from bridge: {}", line, exc);
    }
  }

  private void closeQuietly() {
    try {
      if (writer != null) {
        writer.close();
      }
    }
    catch (IOException ignored) {
      // ignore
    }
    try {
      if (reader != null) {
        reader.close();
      }
    }
    catch (IOException ignored) {
      // ignore
    }
    try {
      if (socket != null && !socket.isClosed()) {
        socket.close();
      }
    }
    catch (IOException ignored) {
      // ignore
    }
    writer = null;
    reader = null;
    socket = null;
  }

}
