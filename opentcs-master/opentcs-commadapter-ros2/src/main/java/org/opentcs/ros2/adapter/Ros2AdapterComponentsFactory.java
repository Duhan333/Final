// SPDX-FileCopyrightText: The openTCS Authors
// SPDX-License-Identifier: MIT
package org.opentcs.ros2.adapter;

import org.opentcs.data.model.Vehicle;

/**
 * Assisted-inject factory for {@link Ros2CommunicationAdapter} instances.
 */
public interface Ros2AdapterComponentsFactory {

  /**
   * Creates a new adapter for the given vehicle.
   *
   * @param vehicle The vehicle.
   * @return A new adapter instance.
   */
  Ros2CommunicationAdapter createRos2CommAdapter(Vehicle vehicle);
}
