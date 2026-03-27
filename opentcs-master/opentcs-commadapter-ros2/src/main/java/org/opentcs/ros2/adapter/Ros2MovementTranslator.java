// SPDX-FileCopyrightText: The openTCS Authors
// SPDX-License-Identifier: MIT
package org.opentcs.ros2.adapter;

import static java.util.Objects.requireNonNull;

import org.opentcs.data.model.Point;
import org.opentcs.data.model.Pose;
import org.opentcs.data.model.Triple;
import org.opentcs.drivers.vehicle.MovementCommand;

/**
 * Converts openTCS {@link MovementCommand} destinations into ROS map goals (metres, radians).
 */
public final class Ros2MovementTranslator {

  private Ros2MovementTranslator() {
  }

  /**
   * Computes the Nav2 goal pose for the given command.
   *
   * @param cmd The movement command.
   * @param modelUnitToMetres Scale factor (e.g. 0.001 for mm → m).
   * @return array {@code [xMetres, yMetres, thetaRadians]}
   */
  public static double[] goalMetresRadians(MovementCommand cmd, double modelUnitToMetres) {
    requireNonNull(cmd, "cmd");
    Point dest = cmd.getStep().getDestinationPoint();
    Pose pose = dest.getPose();
    Triple pos = pose.getPosition();
    if (pos == null) {
      throw new IllegalArgumentException("Destination point has no position: " + dest.getName());
    }
    double xM = pos.getX() * modelUnitToMetres;
    double yM = pos.getY() * modelUnitToMetres;
    double thetaRad = headingRadians(pose);
    return new double[]{xM, yM, thetaRad};
  }

  private static double headingRadians(Pose pose) {
    double deg = pose.getOrientationAngle();
    if (Double.isNaN(deg)) {
      return 0.0;
    }
    return Math.toRadians(deg);
  }
}
