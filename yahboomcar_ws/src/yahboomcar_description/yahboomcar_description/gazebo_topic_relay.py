#!/usr/bin/env python3
"""Relay topics between standard ROS2 names and Gazebo model-specific names."""
import copy

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from rclpy.time import Time
from geometry_msgs.msg import Twist, TransformStamped
from nav_msgs.msg import Odometry
from tf2_ros import TransformBroadcaster


class GazeboTopicRelay(Node):
    def __init__(self):
        super().__init__('gazebo_topic_relay')
        self.declare_parameter('publish_odom_tf', True)
        # Ignition 常把里程计 frame 写成「模型名/odom」，Nav2 需要无命名空间的 odom、base_footprint
        self.declare_parameter('strip_frame_prefix', 'yahboomcar/')
        # 与 /clock 的差值过滤：ros_gz 的 odom.header.stamp 常与 /clock 不同步，默认 0=关闭，否则易把所有里程计丢光（无 odom TF → 无 map）
        # 仅当你确认有多套 Gazebo 混进同一 ROS 图时，可设为 2.0～5.0
        self.declare_parameter('max_odom_clock_skew_sec', 0.0)
        # 默认 True：与 gz_laser_scan_relay 的 scan_stamp_use_sim_time 配对（见该节点说明）。
        # 若改为 False，请同时将激光 relay 的 scan_stamp_use_sim_time 设为 false，否则 odom TF 用
        # Gazebo 消息 stamp、/scan 仍可能用 get_clock().now()，反而会混用两套时间基准。
        self.declare_parameter('sync_odom_stamp_to_clock', True)

        self._publish_odom_tf = self.get_parameter('publish_odom_tf').get_parameter_value().bool_value
        self._strip_prefix = self.get_parameter('strip_frame_prefix').get_parameter_value().string_value
        self._max_skew_sec = self.get_parameter('max_odom_clock_skew_sec').get_parameter_value().double_value
        self._sync_stamp = self.get_parameter('sync_odom_stamp_to_clock').get_parameter_value().bool_value
        self._logged_first_odom = False
        self._tf_broadcaster = TransformBroadcaster(self)
        # Gazebo/ros_gz_bridge 有时会按非时间顺序投递里程计，旧 stamp 再发会导致 Nav2 TF_OLD_DATA
        self._last_odom_stamp = None  # type: Time | None
        self._last_skew_warn_ns = 0

        self.cmd_vel_pub = self.create_publisher(Twist, '/model/yahboomcar/cmd_vel', 10)
        self.cmd_vel_sub = self.create_subscription(
            Twist, '/cmd_vel', self.cmd_vel_cb, 10)
        self.odom_pub = self.create_publisher(Odometry, '/odom', 10)
        self.odom_sub = self.create_subscription(
            Odometry,
            '/model/yahboomcar/odometry',
            self.odom_cb,
            qos_profile_sensor_data,
        )
        self.get_logger().info(
            'Gazebo topic relay: /cmd_vel<->/model/yahboomcar/cmd_vel, '
            '/odom<->/model/yahboomcar/odometry, '
            f'publish_odom_tf={self._publish_odom_tf}, strip_frame_prefix={self._strip_prefix!r}, '
            f'max_odom_clock_skew_sec={self._max_skew_sec}, sync_odom_stamp_to_clock={self._sync_stamp}'
        )

    def _normalize_frame(self, frame_id: str, default: str) -> str:
        if not frame_id:
            return default
        p = self._strip_prefix
        if p and frame_id.startswith(p):
            return frame_id[len(p):]
        return frame_id

    def _short_frame(self, frame_id: str) -> str:
        """去掉任意 model/ 前缀，只保留最后一段（兼容 yahboomcar/、yahboomcar_X3/ 等）。"""
        if not frame_id:
            return frame_id
        if '/' in frame_id:
            return frame_id.split('/')[-1]
        return frame_id

    def _ros_odom_child_frame(self, raw: str) -> str:
        """Nav2/静态 TF 以 base_footprint 为底盘；Gazebo 可能发 base_link、chassis 或错位的 canonical link。"""
        s = self._short_frame(self._normalize_frame(raw, 'base_footprint'))
        if s in ('base_link', 'chassis', 'body', 'robot_base'):
            return 'base_footprint'
        return s

    def cmd_vel_cb(self, msg):
        self.cmd_vel_pub.publish(msg)

    def odom_cb(self, msg):
        stamp = Time.from_msg(msg.header.stamp)
        now = self.get_clock().now()
        skew_sec = abs(now.nanoseconds - stamp.nanoseconds) / 1e9
        if not self._logged_first_odom:
            self.get_logger().info(
                f'Received first Gazebo odometry (will publish /odom). child_frame_id={msg.child_frame_id!r}'
            )
            self._logged_first_odom = True
        if self._max_skew_sec > 0.0 and skew_sec > self._max_skew_sec:
            nw = now.nanoseconds
            if nw - self._last_skew_warn_ns > 5_000_000_000:
                self.get_logger().warning(
                    f'Dropping odom: |clock - msg.stamp| = {skew_sec:.2f}s > '
                    f'max_odom_clock_skew_sec={self._max_skew_sec} '
                    f'(msg t={stamp.nanoseconds / 1e9:.3f}s, clock={now.nanoseconds / 1e9:.3f}s). '
                    'Usually: multiple Gazebo/bridge still running — '
                    'run: pkill -f "gz sim"; pkill -f parameter_bridge; '
                    'then restart only one gazebo_X3_launch.'
                )
                self._last_skew_warn_ns = nw
            return

        # 严格单调：时间戳回退一律丢弃。若误判「大幅回退=仿真重置」并接受，会在两条时间线交替时无限刷屏并再次 TF 混乱。
        # 真正重置 Gazebo 世界后请重启本 launch，或单独重启 gazebo_topic_relay。
        if self._last_odom_stamp is not None and stamp.nanoseconds < self._last_odom_stamp.nanoseconds:
            self.get_logger().debug(
                f'Ignoring out-of-order odom: stamp {stamp.nanoseconds} < last {self._last_odom_stamp.nanoseconds}'
            )
            return
        self._last_odom_stamp = stamp

        out = copy.deepcopy(msg)
        # Nav2 / AMCL 固定使用名为 odom 的父坐标系
        out.header.frame_id = 'odom'
        out.child_frame_id = self._ros_odom_child_frame(msg.child_frame_id)
        if self._sync_stamp:
            sync = self.get_clock().now().to_msg()
            out.header.stamp = sync
        self.odom_pub.publish(out)
        if not self._publish_odom_tf:
            return
        t = TransformStamped()
        t.header.stamp = out.header.stamp
        t.header.frame_id = out.header.frame_id
        t.child_frame_id = out.child_frame_id
        p = out.pose.pose.position
        o = out.pose.pose.orientation
        t.transform.translation.x = p.x
        t.transform.translation.y = p.y
        t.transform.translation.z = p.z
        t.transform.rotation = o
        self._tf_broadcaster.sendTransform(t)


def main(args=None):
    rclpy.init(args=args)
    node = GazeboTopicRelay()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        try:
            rclpy.shutdown()
        except Exception:
            pass


if __name__ == '__main__':
    main()
