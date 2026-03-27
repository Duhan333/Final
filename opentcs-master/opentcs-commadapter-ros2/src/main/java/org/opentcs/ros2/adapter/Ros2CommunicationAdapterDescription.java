// SPDX-FileCopyrightText: The openTCS Authors
// SPDX-License-Identifier: MIT
package org.opentcs.ros2.adapter;

import org.opentcs.drivers.vehicle.VehicleCommAdapterDescription;

/**
 * Description for the ROS2 / Nav2 bridge communication adapter.
 */
public class Ros2CommunicationAdapterDescription
    extends
      VehicleCommAdapterDescription {

  /**
   * Creates a new instance.
   */
  public Ros2CommunicationAdapterDescription() {
  }

  @Override
  public String getDescription() {
    return "ROS2 Nav2 bridge (TCP)";
  }

  @Override
  public boolean isSimVehicleCommAdapter() {
    return false;
  }
}
