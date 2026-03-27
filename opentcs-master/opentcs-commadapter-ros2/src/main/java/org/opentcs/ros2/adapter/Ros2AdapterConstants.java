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

  private Ros2AdapterConstants() {
  }
}
