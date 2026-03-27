#!/usr/bin/env python3
"""
Relay Gazebo-bridged LaserScan (often on a long /world/.../scan name) to /scan
and enforce frame_id for Nav2 / costmap.

AMCL / RViz 用 LaserScan.header.stamp 查 TF。gazebo_topic_relay 在 sync_odom_stamp_to_clock 下
只在收到每条 Gazebo 里程计时才发布 /odom 与 odom→base_footprint，且二者 stamp 相同。

若激光用 get_clock().now()，扫描常在**两条里程计之间**到达，stamp 会**晚于** TF 缓存里最新
的 odom→base 变换时间 → tf2 外推/RViz 投影错误，表现为激光与车体不重合、「直角」点云。

因此 align 为真时，默认把 /scan.header.stamp 设为**最近一次 /odom.header.stamp**（与已发布
TF 严格同拍）。scan_stamp_use_sim_time:=false 时改为保留 Gazebo 桥接消息头时间（仅特殊调试）。
"""
import copy

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from nav_msgs.msg import Odometry
from sensor_msgs.msg import LaserScan


class GzLaserScanRelay(Node):
    def __init__(self):
        super().__init__('gz_laser_scan_relay')
        self.declare_parameter(
            'gz_scan_topic',
            '/world/yahboomcar_world/model/yahboomcar/link/laser_link/sensor/lidar/scan',
        )
        self.declare_parameter('output_topic', '/scan')
        self.declare_parameter('frame_id', 'laser_link')
        self.declare_parameter('odom_topic', '/odom')
        self.declare_parameter('align_scan_stamp_to_odom', True)
        # True：stamp=最近一次 /odom.header（与 odom TF 同拍，推荐）。False：保留桥接 LaserScan 原 header.stamp。
        self.declare_parameter('scan_stamp_use_sim_time', True)

        gz_topic = self.get_parameter('gz_scan_topic').get_parameter_value().string_value
        out_topic = self.get_parameter('output_topic').get_parameter_value().string_value
        self._frame_id = self.get_parameter('frame_id').get_parameter_value().string_value
        odom_topic = self.get_parameter('odom_topic').get_parameter_value().string_value
        self._align = self.get_parameter('align_scan_stamp_to_odom').get_parameter_value().bool_value
        self._stamp_use_sim_time = self.get_parameter('scan_stamp_use_sim_time').get_parameter_value().bool_value

        self._last_odom_stamp = None  # 仅 odom_header 模式使用；或用于调试
        self._logged_waiting_for_odom = False

        self.sub = self.create_subscription(LaserScan, gz_topic, self._cb, qos_profile_sensor_data)
        # 默认 QoS（RELIABLE）：RViz 等对 /scan 常要求 RELIABLE，BEST_EFFORT 发布会导致
        # 「incompatible QoS / No messages will be sent」。AMCL/costmap 用 best_effort 订阅仍可匹配 RELIABLE 发布。
        self.pub = self.create_publisher(LaserScan, out_topic, 10)
        if self._align:
            self._odom_sub = self.create_subscription(
                Odometry, odom_topic, self._odom_cb, 10
            )
        self.get_logger().info(
            f'GzLaserScanRelay: {gz_topic} -> {out_topic} (frame_id={self._frame_id}, '
            f'align_scan_stamp_to_odom={self._align}, scan_stamp_use_sim_time={self._stamp_use_sim_time})'
        )

    def _odom_cb(self, msg: Odometry):
        self._last_odom_stamp = copy.deepcopy(msg.header.stamp)

    def _cb(self, msg: LaserScan):
        if self._align and self._last_odom_stamp is None:
            if not self._logged_waiting_for_odom:
                self.get_logger().info(
                    'align_scan_stamp_to_odom: waiting for first /odom before publishing /scan '
                    '(avoids AMCL MessageFilter / map frame deadlock).'
                )
                self._logged_waiting_for_odom = True
            return
        out = copy.deepcopy(msg)
        out.header.frame_id = self._frame_id
        if self._align:
            if self._stamp_use_sim_time:
                out.header.stamp = copy.deepcopy(self._last_odom_stamp)
            else:
                out.header.stamp = copy.deepcopy(msg.header.stamp)
        self.pub.publish(out)


def main(args=None):
    rclpy.init(args=args)
    node = GzLaserScanRelay()
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
