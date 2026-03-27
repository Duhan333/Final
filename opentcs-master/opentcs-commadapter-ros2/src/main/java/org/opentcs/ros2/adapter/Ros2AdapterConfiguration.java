// SPDX-FileCopyrightText: The openTCS Authors
// SPDX-License-Identifier: MIT
package org.opentcs.ros2.adapter;

import org.opentcs.configuration.ConfigurationEntry;
import org.opentcs.configuration.ConfigurationPrefix;

/**
 * Configuration for the ROS2 / Nav2 TCP bridge vehicle communication adapter.
 */
@ConfigurationPrefix(Ros2AdapterConfiguration.PREFIX)
public interface Ros2AdapterConfiguration {

  /**
   * Configuration prefix for property files.
   */
  String PREFIX = "ros2adapter";

  @ConfigurationEntry(
      type = "Boolean",
      description = "Whether to register the ROS2 bridge communication adapter with the kernel.",
      changesApplied = ConfigurationEntry.ChangesApplied.ON_APPLICATION_START,
      orderKey = "0_enable"
  )
  boolean enable();

  @ConfigurationEntry(
      type = "String",
      description = {
          "Hostname or IP of the machine running the ROS2 bridge (TCP server).",
          "Example: localhost or the robot PC address."
      },
      changesApplied = ConfigurationEntry.ChangesApplied.INSTANTLY,
      orderKey = "1_bridge_1"
  )
  String bridgeHost();

  @ConfigurationEntry(
      type = "Integer",
      description = "TCP port of the ROS2 bridge (default 9090).",
      changesApplied = ConfigurationEntry.ChangesApplied.INSTANTLY,
      orderKey = "1_bridge_2"
  )
  int bridgePort();

  @ConfigurationEntry(
      type = "Boolean",
      description = {
          "If true, keep one TCP connection open between movement commands.",
          "If false, open a new connection per GOAL (simpler for single-client bridges)."
      },
      changesApplied = ConfigurationEntry.ChangesApplied.INSTANTLY,
      orderKey = "1_bridge_3"
  )
  boolean usePersistentConnection();

  @ConfigurationEntry(
      type = "Integer",
      description = "Timeout in milliseconds for establishing a TCP connection to the bridge.",
      changesApplied = ConfigurationEntry.ChangesApplied.INSTANTLY,
      orderKey = "1_bridge_4"
  )
  int connectTimeoutMs();

  @ConfigurationEntry(
      type = "Integer",
      description = {
          "Maximum time in milliseconds to wait for Nav2 to finish after sending a GOAL",
          "(RESULT OK / RESULT FAILED from the bridge)."
      },
      changesApplied = ConfigurationEntry.ChangesApplied.INSTANTLY,
      orderKey = "1_bridge_5"
  )
  int navigationTimeoutMs();

  @ConfigurationEntry(
      type = "Integer",
      description = "The adapter's command queue capacity (same semantics as loopback driver).",
      changesApplied = ConfigurationEntry.ChangesApplied.ON_NEW_PLANT_MODEL,
      orderKey = "2_vehicle_1"
  )
  int commandQueueCapacity();

  @ConfigurationEntry(
      type = "String",
      description = "The string that identifies a recharge operation in transport orders.",
      changesApplied = ConfigurationEntry.ChangesApplied.ON_NEW_PLANT_MODEL,
      orderKey = "2_vehicle_2"
  )
  String rechargeOperation();

  @ConfigurationEntry(
      type = "Double",
      description = {
          "Simulated recharge rate in percent per second.",
          "Used while the vehicle process model state is CHARGING."
      },
      changesApplied = ConfigurationEntry.ChangesApplied.INSTANTLY,
      orderKey = "2_vehicle_3"
  )
  double rechargePercentagePerSecond();

  @ConfigurationEntry(
      type = "Integer",
      description = "Period in milliseconds between simulated recharge ticks.",
      changesApplied = ConfigurationEntry.ChangesApplied.INSTANTLY,
      orderKey = "2_vehicle_4"
  )
  int rechargeSimulationPeriodMs();

  @ConfigurationEntry(
      type = "Double",
      description = {
          "Scale factor from openTCS model coordinates (mm) to ROS map metres.",
          "Use 0.001 when plant model uses millimetres and the ROS map is in metres."
      },
      changesApplied = ConfigurationEntry.ChangesApplied.INSTANTLY,
      orderKey = "3_coords_1"
  )
  double modelUnitToMetres();
}
