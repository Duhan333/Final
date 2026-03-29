#!/usr/bin/env python3
"""
Relay Gazebo-bridged LaserScan (often on a long /world/.../scan name) to /scan
and enforce frame_id for Nav2 / costmap.

AMCL / RViz 用 LaserScan.header.stamp 查 TF。gazebo_topic_relay 在 sync_odom_stamp_to_clock 下
只在收到每条 Gazebo 里程计时才发布 /odom 与 odom→base_footprint，且二者 stamp 相同。

若激光用 get_clock().now()，扫描常在**两条里程计之间**到达，stamp 会**晚于** TF 缓存里最新
的 odom→base 变换时间 → tf2 外推/RViz 投影错误，表现为激光与车体不重合、「直角」点云。

因此 align 为真时，默认把 /scan.header.stamp 设为**最近一次 /odom.header.stamp**（与已发布
TF 严格同拍）；多条激光会共用一个 stamp，Cartographer 会报 Ignored subdivision。

align 为假时（推荐 Cartographer）：**不用** 桥接消息里自带的 stamp（常与 /clock、relay 的 odom 不是同一时间基，
会乱序），改为 **get_clock().now()**，并与上一条已发布扫描比较，必要时 +1ns，保证严格单调递增。
scan_stamp_use_sim_time 仅在 align 为真时参与分支。
"""
import copy

import rclpy
from rclpy.clock import Clock, ClockType
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, HistoryPolicy, QoSProfile, ReliabilityPolicy
from nav_msgs.msg import Odometry
from sensor_msgs.msg import LaserScan


class GzLaserScanRelay(Node):
    def __init__(self):
        super().__init__('gz_laser_scan_relay')
        self.declare_parameter(
            'gz_scan_topic',
            '/scan',
        )
        self.declare_parameter('output_topic', '/scan')
        self.declare_parameter('frame_id', 'laser_link')
        self.declare_parameter('odom_topic', '/odom')
        self.declare_parameter('align_scan_stamp_to_odom', True)
        # 仅 align=true：True=用最近一次 /odom.header；False=仍用桥接原 stamp（易与 odom 脱节）。
        self.declare_parameter('scan_stamp_use_sim_time', True)

        gz_topic = self.get_parameter('gz_scan_topic').get_parameter_value().string_value
        self._gz_topic = gz_topic
        out_topic = self.get_parameter('output_topic').get_parameter_value().string_value
        self._frame_id = self.get_parameter('frame_id').get_parameter_value().string_value
        odom_topic = self.get_parameter('odom_topic').get_parameter_value().string_value
        self._align = self.get_parameter('align_scan_stamp_to_odom').get_parameter_value().bool_value
        self._stamp_use_sim_time = self.get_parameter('scan_stamp_use_sim_time').get_parameter_value().bool_value

        self._last_odom_stamp = None  # 仅 odom_header 模式使用；或用于调试
        self._last_scan_stamp_ns = 0  # align=false：保证 Cartographer 见单调 stamp
        self._logged_waiting_for_odom = False
        self._gz_scan_rx_count = 0
        self._diag_fired = False

        # 与 ros_gz parameter_bridge 默认（RELIABLE）对齐；BEST_EFFORT 订阅在部分组合下收不到桥接数据
        _bridge_qos = QoSProfile(
            reliability=ReliabilityPolicy.RELIABLE,
            history=HistoryPolicy.KEEP_LAST,
            durability=DurabilityPolicy.VOLATILE,
            depth=25,
        )
        self.sub = self.create_subscription(LaserScan, gz_topic, self._cb, _bridge_qos)
        # 默认 QoS（RELIABLE）：RViz 等对 /scan 常要求 RELIABLE，BEST_EFFORT 发布会导致
        # 「incompatible QoS / No messages will be sent」。AMCL/costmap 用 best_effort 订阅仍可匹配 RELIABLE 发布。
        self.pub = self.create_publisher(LaserScan, out_topic, 10)
        if self._align:
            self._odom_sub = self.create_subscription(
                Odometry, odom_topic, self._odom_cb, 10
            )
        _stamp_mode = (
            'odom_header' if self._align and self._stamp_use_sim_time
            else ('bridge_header+align' if self._align else 'clock.now_monotonic')
        )
        self.get_logger().info(
            f'GzLaserScanRelay: {gz_topic} -> {out_topic} (frame_id={self._frame_id}, '
            f'align_scan_stamp_to_odom={self._align}, stamp_mode={_stamp_mode})'
        )
        # 勿用仿真时钟定时器：/clock 快进时会在亚秒级误触发「12s」告警
        self._diag_timer = self.create_timer(
            20.0, self._diagnostic_timer_cb, clock=Clock(clock_type=ClockType.SYSTEM_TIME)
        )

    def _diagnostic_timer_cb(self):
        if self._diag_fired:
            return
        self._diag_fired = True
        self._diag_timer.cancel()
        if self._gz_scan_rx_count > 0:
            return
        self.get_logger().warning(
            f'20s（墙上时钟）内未收到任何 Gazebo 激光 ({self._gz_topic!r})，/scan 不会发布。'
            '请确认本 launch 与 ign gz 仍在运行，且 ros_gz_bridge 话题名与模型一致；'
            '另开终端勿忘 source。用 ign topic -l | grep scan 核对 Gazebo 侧话题名，并通过 launch 参数 gz_lidar_topic 传给 parameter_bridge。'
        )

    def _odom_cb(self, msg: Odometry):
        self._last_odom_stamp = copy.deepcopy(msg.header.stamp)

    def _cb(self, msg: LaserScan):
        self._gz_scan_rx_count += 1
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
        else:
            now_ns = self.get_clock().now().nanoseconds
            if now_ns <= self._last_scan_stamp_ns:
                now_ns = self._last_scan_stamp_ns + 1
            self._last_scan_stamp_ns = now_ns
            out.header.stamp.sec = int(now_ns // 1_000_000_000)
            out.header.stamp.nanosec = int(now_ns % 1_000_000_000)
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
