// SPDX-FileCopyrightText: The openTCS Authors
// SPDX-License-Identifier: MIT
package org.opentcs.ros2.adapter;

import com.google.inject.assistedinject.FactoryModuleBuilder;
import org.opentcs.customizations.kernel.KernelInjectionModule;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Configures the ROS2 bridge communication adapter for the openTCS kernel.
 */
public class Ros2CommAdapterModule
    extends
      KernelInjectionModule {

  /**
   * This class's logger.
   */
  private static final Logger LOG = LoggerFactory.getLogger(Ros2CommAdapterModule.class);

  /**
   * Creates a new instance.
   */
  public Ros2CommAdapterModule() {
  }

  @Override
  protected void configure() {
    Ros2AdapterConfiguration configuration
        = getConfigBindingProvider().get(
            Ros2AdapterConfiguration.PREFIX,
            Ros2AdapterConfiguration.class
        );

    if (!configuration.enable()) {
      LOG.info("ROS2 bridge communication adapter disabled by configuration.");
      return;
    }

    bind(Ros2AdapterConfiguration.class).toInstance(configuration);

    install(new FactoryModuleBuilder().build(Ros2AdapterComponentsFactory.class));

    vehicleCommAdaptersBinder().addBinding().to(Ros2CommunicationAdapterFactory.class);
  }
}
