// SPDX-FileCopyrightText: The openTCS Authors
// SPDX-License-Identifier: MIT
package org.opentcs.ros2.adapter;

import static java.util.Objects.requireNonNull;

import com.google.inject.assistedinject.Assisted;
import jakarta.inject.Inject;
import java.io.IOException;
import java.util.Iterator;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicLong;
import java.util.stream.Collectors;
import org.opentcs.customizations.kernel.KernelExecutor;
import org.opentcs.data.model.Pose;
import org.opentcs.data.model.Triple;
import org.opentcs.data.model.Vehicle;
import org.opentcs.data.order.TransportOrder;
import org.opentcs.drivers.vehicle.BasicVehicleCommAdapter;
import org.opentcs.drivers.vehicle.LoadHandlingDevice;
import org.opentcs.drivers.vehicle.MovementCommand;
import org.opentcs.drivers.vehicle.management.VehicleProcessModelTO;
import org.opentcs.util.ExplainedBoolean;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Vehicle communication adapter that forwards movement to a ROS2 Nav2 bridge over TCP.
 *
 * <p>
 * Behaviour:
 * </p>
 * <ul>
 * <li>Movement to a point: sends {@code GOAL x y theta} (metres, radians) to the bridge.
 * </li>
 * <li>Waits for {@code RESULT OK} or {@code RESULT FAILED} on a background I/O thread.</li>
 * <li>Invokes {@code commandExecuted} or {@code commandFailed} on the kernel executor, and removes
 * the command from {@link #getSentCommands()} so {@link #canAcceptNextCommand()} can admit further
 * legs (required whenever {@code commandQueueCapacity} is finite).</li>
 * <li>Optional {@code POSE} lines update
 * {@link org.opentcs.drivers.vehicle.VehicleProcessModel#setPose}.</li>
 * <li>Load/unload operations run after navigation with configurable operating time.</li>
 * <li>Recharge operations complete navigation first, then simulate charging like the loopback
 * driver.</li>
 * </ul>
 */
public class Ros2CommunicationAdapter
    extends
      BasicVehicleCommAdapter {

  /**
   * Default load handling device name (aligned with loopback driver).
   */
  public static final String LHD_NAME = "default";
  /**
   * Error code when already loaded.
   */
  private static final String LOAD_OPERATION_CONFLICT = "cannotLoadWhenLoaded";
  /**
   * Error code when not loaded.
   */
  private static final String UNLOAD_OPERATION_CONFLICT = "cannotUnloadWhenNotLoaded";

  /**
   * Logger.
   */
  private static final Logger LOG = LoggerFactory.getLogger(Ros2CommunicationAdapter.class);

  /**
   * Vehicle reference (properties, name).
   */
  private final Vehicle vehicle;
  /**
   * Kernel / configuration.
   */
  private final Ros2AdapterConfiguration configuration;
  /**
   * Typed process model.
   */
  private final Ros2VehicleProcessModel rosModel;
  /**
   * Blocking TCP runs here so the single-threaded kernel executor is not stalled.
   */
  private ExecutorService ioExecutor;
  /**
   * TCP session (may be persistent).
   */
  private final Ros2TcpBridgeSession tcpSession = new Ros2TcpBridgeSession();
  /**
   * Monotonic command sequence for cross-process log correlation.
   */
  private final AtomicLong commandSeq = new AtomicLong(0);
  /**
   * Tracks load state for {@link #canProcess(TransportOrder)}.
   */
  private LoadState loadState = LoadState.EMPTY;

  /**
   * Guice entry point: creates the typed process model then delegates to the private constructor.
   *
   * @param vehicle the vehicle model instance
   * @param configuration adapter configuration
   * @param kernelExecutor kernel executor for scheduling adapter callbacks
   */
  @Inject
  public Ros2CommunicationAdapter(
      @Assisted
      Vehicle vehicle,
      Ros2AdapterConfiguration configuration,
      @KernelExecutor
      java.util.concurrent.ScheduledExecutorService kernelExecutor
  ) {
    this(vehicle, configuration, kernelExecutor, new Ros2VehicleProcessModel(vehicle));
  }

  private Ros2CommunicationAdapter(
      Vehicle vehicle,
      Ros2AdapterConfiguration configuration,
      java.util.concurrent.ScheduledExecutorService kernelExecutor,
      Ros2VehicleProcessModel rosModel
  ) {
    super(
        rosModel,
        configuration.commandQueueCapacity(),
        configuration.rechargeOperation(),
        kernelExecutor
    );
    this.vehicle = requireNonNull(vehicle, "vehicle");
    this.configuration = requireNonNull(configuration, "configuration");
    this.rosModel = requireNonNull(rosModel, "rosModel");
  }

  @Override
  public void initialize() {
    if (isInitialized()) {
      return;
    }
    super.initialize();
    String initialPoint = vehicle.getProperty(Ros2AdapterConstants.PROPKEY_INITIAL_POINT);
    if (initialPoint != null && !initialPoint.isBlank()) {
      String trimmed = initialPoint.trim();
      getProcessModel().setPosition(trimmed);
      LOG.info(
          "{}: Initial kernel position set from vehicle property {}={}",
          getName(),
          Ros2AdapterConstants.PROPKEY_INITIAL_POINT,
          trimmed
      );
    }
    else {
      LOG.warn(
          "{}: Vehicle property {} is not set; OpenTCS cannot route until a point is known "
              + "(dispatch will fail with VEHICLE_CURRENT_POSITION_UNKNOWN). "
              + "Set it on the vehicle in the plant model, e.g. Point-A.",
          getName(),
          Ros2AdapterConstants.PROPKEY_INITIAL_POINT
      );
    }
    this.ioExecutor = Executors.newSingleThreadExecutor(
        runnable -> {
          Thread thread = new Thread(runnable, "ros2-bridge-io-" + vehicle.getName());
          thread.setDaemon(true);
          return thread;
        }
    );
    getProcessModel().setState(Vehicle.State.IDLE);
    getProcessModel().setLoadHandlingDevices(
        java.util.List.of(new LoadHandlingDevice(LHD_NAME, false))
    );
  }

  @Override
  public void terminate() {
    if (!isInitialized()) {
      return;
    }
    tcpSession.disconnect();
    if (ioExecutor != null) {
      ioExecutor.shutdownNow();
      ioExecutor = null;
    }
    super.terminate();
  }

  @Override
  public void onVehiclePaused(boolean paused) {
    // Nav2 pause could be added later (cancel goal, etc.).
  }

  @Override
  public synchronized ExplainedBoolean canProcess(TransportOrder order) {
    requireNonNull(order, "order");
    return canProcess(
        order.getFutureDriveOrders().stream()
            .map(driveOrder -> driveOrder.getDestination().getOperation())
            .collect(Collectors.toList())
    );
  }

  private ExplainedBoolean canProcess(java.util.List<String> operations) {
    requireNonNull(operations, "operations");
    LOG.debug("{}: Checking processability of {}...", getName(), operations);
    boolean can = true;
    String reason = "";
    boolean loaded = loadState == LoadState.FULL;
    Iterator<String> opIter = operations.iterator();
    while (can && opIter.hasNext()) {
      final String nextOp = opIter.next();
      if (loaded) {
        if (nextOp.startsWith(rosModel.getLoadOperation())) {
          can = false;
          reason = LOAD_OPERATION_CONFLICT;
        }
        else if (nextOp.startsWith(rosModel.getUnloadOperation())) {
          loaded = false;
        }
      }
      else if (nextOp.startsWith(rosModel.getLoadOperation())) {
        loaded = true;
      }
      else if (nextOp.startsWith(rosModel.getUnloadOperation())) {
        can = false;
        reason = UNLOAD_OPERATION_CONFLICT;
      }
    }
    if (!can) {
      LOG.debug("{}: Cannot process {}, reason: '{}'", getName(), operations, reason);
    }
    return new ExplainedBoolean(can, reason.isEmpty() ? "" : reason);
  }

  @Override
  protected synchronized void connectVehicle() {
    getProcessModel().setCommAdapterConnected(true);
  }

  @Override
  protected synchronized void disconnectVehicle() {
    tcpSession.disconnect();
    getProcessModel().setCommAdapterConnected(false);
  }

  @Override
  protected synchronized boolean isVehicleConnected() {
    return getProcessModel().isCommAdapterConnected();
  }

  @Override
  protected VehicleProcessModelTO createCustomTransferableProcessModel() {
    return new VehicleProcessModelTO();
  }

  @Override
  public synchronized void sendCommand(MovementCommand cmd)
      throws IllegalArgumentException {
    requireNonNull(cmd, "cmd");
    requireNonNull(ioExecutor, "ioExecutor");

    final double[] goal;
    final long seq = commandSeq.incrementAndGet();
    try {
      goal = Ros2MovementTranslator.goalMetresRadians(cmd, configuration.modelUnitToMetres());
    }
    catch (IllegalArgumentException | NullPointerException exc) {
      throw new IllegalArgumentException("Invalid movement goal: " + exc.getMessage(), exc);
    }

    LOG.info(
        "{} [seq={}]: sendCommand start, {} -> GOAL({:.3f},{:.3f},{:.3f})",
        getName(),
        seq,
        describeCommand(cmd),
        goal[0],
        goal[1],
        goal[2]
    );

    getExecutor().execute(() -> getProcessModel().setState(Vehicle.State.EXECUTING));

    ioExecutor.execute(() -> runNavigationPipeline(seq, cmd, goal));
  }

  private void runNavigationPipeline(long seq, MovementCommand cmd, double[] goal) {
    try {
      boolean ok = tcpSession.sendGoalWaitResult(
          configuration,
          goal,
          pose -> getExecutor().execute(() -> applyPoseFromRos(pose))
      );
      LOG.info(
          "{} [seq={}]: bridge RESULT={}, {}",
          getName(),
          seq,
          ok ? "OK" : "FAILED",
          describeCommand(cmd)
      );
      if (!ok) {
        getExecutor().execute(() -> {
          getProcessModel().setState(Vehicle.State.IDLE);
          markCommandFailed(cmd);
        });
        return;
      }

      getExecutor().execute(() -> afterNavigationSuccess(seq, cmd));
    }
    catch (IOException exc) {
      LOG.warn("{} [seq={}]: ROS2 bridge communication failed, {}", getName(), seq, describeCommand(cmd), exc);
      tcpSession.disconnect();
      getExecutor().execute(() -> {
        getProcessModel().setState(Vehicle.State.IDLE);
        markCommandFailed(cmd);
      });
    }
  }

  /**
   * Notifies the kernel and frees adapter queue capacity for the next movement command.
   */
  private void markCommandExecuted(MovementCommand cmd) {
    synchronized (this) {
      if (!getSentCommands().remove(cmd)) {
        LOG.warn("{}: commandExecuted but command not in sent queue: {}", getName(), cmd);
      }
    }
    LOG.info("{}: commandExecuted, {}", getName(), describeCommand(cmd));
    getProcessModel().commandExecuted(cmd);
  }

  /**
   * Notifies the kernel of failure and frees adapter queue capacity.
   */
  private void markCommandFailed(MovementCommand cmd) {
    synchronized (this) {
      if (!getSentCommands().remove(cmd)) {
        LOG.warn("{}: commandFailed but command not in sent queue: {}", getName(), cmd);
      }
    }
    LOG.warn("{}: commandFailed, {}", getName(), describeCommand(cmd));
    getProcessModel().commandFailed(cmd);
  }

  private void applyPoseFromRos(double[] poseMetersRad) {
    double scale = configuration.modelUnitToMetres();
    if (scale < 1e-12) {
      scale = 0.001;
    }
    long xMm = Math.round(poseMetersRad[0] / scale);
    long yMm = Math.round(poseMetersRad[1] / scale);
    double deg = Math.toDegrees(poseMetersRad[2]);
    getProcessModel().setPose(new Pose(new Triple(xMm, yMm, 0L), deg));
  }

  private void afterNavigationSuccess(long seq, MovementCommand cmd) {
    updatePositionAndPoseFromPlantModel(cmd);
    if (cmd.hasEmptyOperation()) {
      LOG.info("{} [seq={}]: reached routing point (empty operation), {}", getName(), seq, describeCommand(cmd));
      getProcessModel().setState(Vehicle.State.IDLE);
      markCommandExecuted(cmd);
      return;
    }

    String op = cmd.getOperation();
    LOG.info("{} [seq={}]: post-nav operation='{}', {}", getName(), seq, op, describeCommand(cmd));
    if (op.equals(configuration.rechargeOperation())) {
      markCommandExecuted(cmd);
      getProcessModel().setState(Vehicle.State.CHARGING);
      float energy = getProcessModel().getEnergyLevel();
      getExecutor().schedule(
          () -> chargingSimulation(energy),
          configuration.rechargeSimulationPeriodMs(),
          TimeUnit.MILLISECONDS
      );
      return;
    }

    int delay = Math.max(1, rosModel.getOperatingTime());
    getExecutor().schedule(() -> applyLoadUnloadAndFinish(cmd), delay, TimeUnit.MILLISECONDS);
  }

  private void updatePositionAndPoseFromPlantModel(MovementCommand cmd) {
    String pointName = cmd.getStep().getDestinationPoint().getName();
    getProcessModel().setPosition(pointName);
    Pose p = cmd.getStep().getDestinationPoint().getPose();
    if (p.getPosition() != null) {
      getProcessModel().setPose(p);
    }
  }

  private void applyLoadUnloadAndFinish(MovementCommand cmd) {
    String op = cmd.getOperation();
    if (op.startsWith(rosModel.getLoadOperation())) {
      loadState = LoadState.FULL;
      getProcessModel().setLoadHandlingDevices(
          java.util.List.of(new LoadHandlingDevice(LHD_NAME, true))
      );
    }
    else if (op.startsWith(rosModel.getUnloadOperation())) {
      loadState = LoadState.EMPTY;
      getProcessModel().setLoadHandlingDevices(
          java.util.List.of(new LoadHandlingDevice(LHD_NAME, false))
      );
    }
    getProcessModel().setState(Vehicle.State.IDLE);
    markCommandExecuted(cmd);
  }

  private void chargingSimulation(float energyPercentage) {
    if (!getSentCommands().isEmpty()) {
      LOG.debug("{}: Aborting recharge simulation (new commands pending).", getName());
      getProcessModel().setState(Vehicle.State.IDLE);
      return;
    }
    if (getProcessModel().getState() != Vehicle.State.CHARGING) {
      return;
    }
    int period = Math.max(1, configuration.rechargeSimulationPeriodMs());
    float delta = (float) (configuration.rechargePercentagePerSecond() / 1000.0 * period);
    float next = energyPercentage + delta;
    if (next < 100.0f) {
      getProcessModel().setEnergyLevel((int) next);
      getExecutor().schedule(
          () -> chargingSimulation(next),
          period,
          TimeUnit.MILLISECONDS
      );
    }
    else {
      getProcessModel().setEnergyLevel(100);
      getProcessModel().setState(Vehicle.State.IDLE);
      LOG.debug("{}: Recharge simulation finished.", getName());
    }
  }

  private enum LoadState {
    EMPTY,
    FULL
  }

  private String describeCommand(MovementCommand cmd) {
    String dest = cmd.getStep().getDestinationPoint().getName();
    String op = cmd.hasEmptyOperation() ? "EMPTY" : cmd.getOperation();
    return "destPoint=" + dest + ", op=" + op;
  }
}
