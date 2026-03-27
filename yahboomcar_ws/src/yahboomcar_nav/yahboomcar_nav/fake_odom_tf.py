#!/usr/bin/env python3
"""
在无 Gazebo 时发布 /odom 与 odom->base_footprint TF，替代 RUN_GUIDE 里 T2 + 部分 T1。
与 Gazebo 同时运行会冲突（两套里程计），请勿同时开。
"""
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import TransformStamped
from nav_msgs.msg import Odometry
from tf2_ros import TransformBroadcaster


class FakeOdomTf(Node):
    def __init__(self):
        super().__init__('fake_odom_tf')
        self.declare_parameter('odom_frame', 'odom')
        self.declare_parameter('base_frame', 'base_footprint')
        self.declare_parameter('publish_rate', 20.0)

        self._odom_frame = self.get_parameter('odom_frame').get_parameter_value().string_value
        self._base_frame = self.get_parameter('base_frame').get_parameter_value().string_value
        rate = self.get_parameter('publish_rate').get_parameter_value().double_value
        period = 1.0 / rate if rate > 0.0 else 0.05

        self._pub = self.create_publisher(Odometry, '/odom', 10)
        self._tf_broadcaster = TransformBroadcaster(self)
        self._timer = self.create_timer(period, self._tick)
        self.get_logger().info(
            f'fake_odom_tf: publishing /odom + TF {self._odom_frame} -> {self._base_frame} '
            f'at {rate} Hz (use only when Gazebo is NOT running)'
        )

    def _tick(self):
        now = self.get_clock().now().to_msg()
        msg = Odometry()
        msg.header.stamp = now
        msg.header.frame_id = self._odom_frame
        msg.child_frame_id = self._base_frame
        msg.pose.pose.orientation.w = 1.0
        self._pub.publish(msg)

        t = TransformStamped()
        t.header.stamp = now
        t.header.frame_id = self._odom_frame
        t.child_frame_id = self._base_frame
        t.transform.rotation.w = 1.0
        self._tf_broadcaster.sendTransform(t)


def main(args=None):
    rclpy.init(args=args)
    node = FakeOdomTf()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
