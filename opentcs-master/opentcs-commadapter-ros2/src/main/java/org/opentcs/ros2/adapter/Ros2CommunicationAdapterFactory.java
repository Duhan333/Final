// SPDX-FileCopyrightText: The openTCS Authors
// SPDX-License-Identifier: MIT
package org.opentcs.ros2.adapter;

import static java.util.Objects.requireNonNull;

import jakarta.inject.Inject;
import org.opentcs.data.model.Vehicle;
import org.opentcs.drivers.vehicle.VehicleCommAdapterDescription;
import org.opentcs.drivers.vehicle.VehicleCommAdapterFactory;

/**
 * Factory for {@link Ros2CommunicationAdapter} instances.
 */
public class Ros2CommunicationAdapterFactory
    implements
      VehicleCommAdapterFactory {

  /**
   * Creates components (adapters) for vehicles.
   */
  private final Ros2AdapterComponentsFactory componentsFactory;
  /**
   * Whether this factory has been initialized.
   */
  private boolean initialized;

  /**
   * Creates a new instance.
   *
   * @param componentsFactory The assisted-inject factory.
   */
  @Inject
  public Ros2CommunicationAdapterFactory(Ros2AdapterComponentsFactory componentsFactory) {
    this.componentsFactory = requireNonNull(componentsFactory, "componentsFactory");
  }

  @Override
  public void initialize() {
    if (isInitialized()) {
      return;
    }
    initialized = true;
  }

  @Override
  public boolean isInitialized() {
    return initialized;
  }

  @Override
  public void terminate() {
    if (!isInitialized()) {
      return;
    }
    initialized = false;
  }

  @Override
  public VehicleCommAdapterDescription getDescription() {
    return new Ros2CommunicationAdapterDescription();
  }

  @Override
  public boolean providesAdapterFor(Vehicle vehicle) {
    requireNonNull(vehicle, "vehicle");
    return true;
  }

  @Override
  public Ros2CommunicationAdapter getAdapterFor(Vehicle vehicle) {
    requireNonNull(vehicle, "vehicle");
    return componentsFactory.createRos2CommAdapter(vehicle);
  }
}
