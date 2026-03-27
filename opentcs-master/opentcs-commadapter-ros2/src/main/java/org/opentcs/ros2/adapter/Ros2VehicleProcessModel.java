// SPDX-FileCopyrightText: The openTCS Authors
// SPDX-License-Identifier: MIT
package org.opentcs.ros2.adapter;

import jakarta.annotation.Nonnull;
import org.opentcs.common.LoopbackAdapterConstants;
import org.opentcs.data.model.Vehicle;
import org.opentcs.drivers.vehicle.VehicleProcessModel;

/**
 * Minimal process model for the ROS2 adapter: load/unload operation names and operating time,
 * parsed from {@link Vehicle} properties (same keys as the loopback driver).
 */
public class Ros2VehicleProcessModel
    extends
      VehicleProcessModel {

  /**
   * Loading operation prefix.
   */
  private final String loadOperation;
  /**
   * Unloading operation prefix.
   */
  private final String unloadOperation;
  /**
   * Time simulated for load/unload operations (ms).
   */
  private int operatingTime;

  /**
   * Creates a new instance.
   *
   * @param attachedVehicle The vehicle.
   */
  public Ros2VehicleProcessModel(Vehicle attachedVehicle) {
    super(attachedVehicle);
    this.operatingTime = parseOperatingTime(attachedVehicle);
    this.loadOperation = extractLoadOperation(attachedVehicle);
    this.unloadOperation = extractUnloadOperation(attachedVehicle);
  }

  @Nonnull
  public String getLoadOperation() {
    return loadOperation;
  }

  @Nonnull
  public String getUnloadOperation() {
    return unloadOperation;
  }

  public int getOperatingTime() {
    return operatingTime;
  }

  private static int parseOperatingTime(Vehicle vehicle) {
    String opTime = vehicle.getProperty(LoopbackAdapterConstants.PROPKEY_OPERATING_TIME);
    if (opTime == null || opTime.isBlank()) {
      return 5000;
    }
    try {
      return Math.max(Integer.parseInt(opTime.trim()), 1);
    }
    catch (NumberFormatException exc) {
      return 5000;
    }
  }

  private static String extractLoadOperation(Vehicle vehicle) {
    String result = vehicle.getProperty(LoopbackAdapterConstants.PROPKEY_LOAD_OPERATION);
    if (result == null) {
      result = LoopbackAdapterConstants.PROPVAL_LOAD_OPERATION_DEFAULT;
    }
    return result;
  }

  private static String extractUnloadOperation(Vehicle vehicle) {
    String result = vehicle.getProperty(LoopbackAdapterConstants.PROPKEY_UNLOAD_OPERATION);
    if (result == null) {
      result = LoopbackAdapterConstants.PROPVAL_UNLOAD_OPERATION_DEFAULT;
    }
    return result;
  }
}
