// SPDX-FileCopyrightText: The openTCS Authors
// SPDX-License-Identifier: MIT
package org.opentcs.ros2.adapter;

/**
 * Property keys for the ROS2 vehicle communication adapter.
 */
public final class Ros2AdapterConstants {

  /**
   * Vehicle property: name of the plant model {@link org.opentcs.data.model.Point} where the
   * vehicle is initially located (e.g. {@code Point-A}). Required for dispatching/routing before
   * the first movement completes, because the adapter otherwise only updates position after
   * navigation.
   */
  public static final String PROPKEY_INITIAL_POINT = "org.opentcs.ros2.initialPoint";

  /**
   * Vehicle property: TCP host of this vehicle's ROS2 bridge (overrides kernel
   * {@code ros2adapter.bridgeHost} when set).
   */
  public static final String PROPKEY_BRIDGE_HOST = "org.opentcs.ros2.bridgeHost";

  /**
   * Vehicle property: TCP port of this vehicle's ROS2 bridge (overrides kernel
   * {@code ros2adapter.bridgePort} when set). Required for multi-vehicle setups with one bridge
   * instance per port.
   */
  public static final String PROPKEY_BRIDGE_PORT = "org.opentcs.ros2.bridgePort";

  private Ros2AdapterConstants() {
  }
}
