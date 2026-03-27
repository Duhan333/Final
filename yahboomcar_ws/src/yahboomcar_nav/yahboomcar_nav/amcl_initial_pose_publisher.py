#!/usr/bin/env python3
"""
模拟旧版「T4：初始位姿发布」与 RViz「2D Pose Estimate」：向 /initialpose 发布
PoseWithCovarianceStamped，且带**非零协方差**。

根因说明（为何改坐标仍无 map）：
  Nav2 AMCL 在参数 set_initial_pose:=true 时，on_activate 里构造的初始位姿消息
  **从不填写 pose.covariance**，保持全 0。handleInitialPose 把这些 0 写进粒子滤波的
  初始协方差 → 粒子分布退化 / 数值病态 → 常见现象是激光在跑、位姿也打印了，但
  **长期不发布 map→odom**，global_costmap 一直报 Invalid frame "map"。
  RViz 或独立节点发布的 /initialpose 默认带不确定性，故能跑通。

默认在**首次收到 /scan** 后再延迟 delay_after_scan_sec（**墙上真实秒**，与 use_sim_time 无关）
发布（确保 odom TF 与激光时间对齐已就绪），
若超过 scan_timeout_wall_sec（墙上真实秒）仍无激光则 ERROR（避免静默失败）。

注意：use_sim_time:=true 时 ROS 定时器按 /clock 走；仿真时间往往比真实时间快很多，
若用 create_timer(30) 表示「等 30 秒」，会在零点几秒真实时间内就超时。故超时必须用墙上时钟。
"""
import math
import threading

import rclpy
from rclpy.clock import Clock, ClockType
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from rclpy.time import Time as RosTime
from nav_msgs.msg import Odometry
from geometry_msgs.msg import PoseWithCovarianceStamped
from sensor_msgs.msg import LaserScan


def _yaw_to_quat(yaw: float):
    half = yaw * 0.5
    return 0.0, 0.0, math.sin(half), math.cos(half)


class AmclInitialPosePublisher(Node):
    def __init__(self):
        super().__init__('amcl_initial_pose_publisher')
        # use_sim_time 仅由 launch 传入，勿在此 declare（否则会与 --params-file 重复 → ParameterAlreadyDeclaredException）
        self.declare_parameter('frame_id', 'map')
        # 本工程 Gazebo 中车体出生点约在世界坐标 (0, 0, 0.08)。
        # 默认把 AMCL 初始位姿也设在 map 坐标 (0, 0)，避免落在 map 外造成 costmap out-of-bounds。
        self.declare_parameter('x', 0.0)
        self.declare_parameter('y', 0.0)
        self.declare_parameter('yaw', 0.0)
        self.declare_parameter('cov_xx', 0.25)
        self.declare_parameter('cov_yy', 0.25)
        self.declare_parameter('cov_yaw', (math.pi / 12.0) ** 2)
        # 降低 burst 频率以减少 CPU/线程开销
        self.declare_parameter('publish_count', 3)
        self.declare_parameter('publish_period_sec', 1.0)
        # 须晚于 AMCL activate 并完成 initPubSub，否则 /initialpose 无订阅会丢包
        # 给 TF cache（base_footprint->odom->map 相关）更充足的“积累窗口”，
        # 避免刚拿到第一帧 /scan 就发布 initialpose，导致 extrapolation into the past/future。
        self.declare_parameter('delay_after_scan_sec', 8.0)
        # 新思路：允许在 T2 启动后不等待 /scan，直接发布 /initialpose。
        self.declare_parameter('wait_for_scan', True)
        self.declare_parameter('delay_after_start_sec', 10.0)
        # /initialpose stamp 来源选择：now/odom/zero
        self.declare_parameter('stamp_mode', 'zero')
        # 墙上真实秒（非仿真秒）；未收到 /scan 时的最长等待
        self.declare_parameter('scan_timeout_wall_sec', 120.0)
        self.declare_parameter('odom_topic', '/odom')

        self._frame_id = self.get_parameter('frame_id').get_parameter_value().string_value
        self._x = self.get_parameter('x').get_parameter_value().double_value
        self._y = self.get_parameter('y').get_parameter_value().double_value
        self._yaw = self.get_parameter('yaw').get_parameter_value().double_value
        cov_xx = self.get_parameter('cov_xx').get_parameter_value().double_value
        cov_yy = self.get_parameter('cov_yy').get_parameter_value().double_value
        cov_yaw = self.get_parameter('cov_yaw').get_parameter_value().double_value
        self._count = max(1, self.get_parameter('publish_count').get_parameter_value().integer_value)
        self._period = float(self.get_parameter('publish_period_sec').get_parameter_value().double_value)
        self._delay_after_scan = float(
            self.get_parameter('delay_after_scan_sec').get_parameter_value().double_value
        )
        scan_timeout_wall = float(
            self.get_parameter('scan_timeout_wall_sec').get_parameter_value().double_value
        )

        self._wait_for_scan = self.get_parameter('wait_for_scan').get_parameter_value().bool_value
        self._delay_after_start = float(
            self.get_parameter('delay_after_start_sec').get_parameter_value().double_value
        )
        self._stamp_mode = self.get_parameter('stamp_mode').get_parameter_value().string_value

        # 延迟与连发间隔按墙上时钟，避免 use_sim_time 下仿真时间过快导致「3 秒」瞬间过完
        self._wall_clock = Clock(clock_type=ClockType.SYSTEM_TIME)

        self._pub = self.create_publisher(PoseWithCovarianceStamped, '/initialpose', 10)
        self._msg = PoseWithCovarianceStamped()
        self._msg.header.frame_id = self._frame_id
        self._msg.pose.pose.position.x = self._x
        self._msg.pose.pose.position.y = self._y
        self._msg.pose.pose.position.z = 0.0
        q = _yaw_to_quat(self._yaw)
        self._msg.pose.pose.orientation.x = q[0]
        self._msg.pose.pose.orientation.y = q[1]
        self._msg.pose.pose.orientation.z = q[2]
        self._msg.pose.pose.orientation.w = q[3]
        c = self._msg.pose.covariance
        c[0] = cov_xx
        c[7] = cov_yy
        c[35] = cov_yaw

        self._scan_seen = False
        self._last_odom_stamp = None
        self._delay_timer = None
        self._burst_timer = None
        self._burst_remaining = 0
        odom_topic = self.get_parameter('odom_topic').get_parameter_value().string_value

        if self._wait_for_scan:
            self._scan_sub = self.create_subscription(
                LaserScan, '/scan', self._on_scan, qos_profile_sensor_data
            )
        else:
            self._scan_sub = None
        # 用于对齐 /initialpose 的 header.stamp，避免 AMCL TF 查询 extrapolation
        self._odom_sub = self.create_subscription(
            Odometry,
            odom_topic,
            self._odom_cb,
            qos_profile_sensor_data,
        )
        self._timeout_fired = False

        def _wall_timeout():
            if self._scan_seen or self._timeout_fired:
                return
            self._timeout_fired = True
            self.get_logger().error(
                f'在约 {scan_timeout_wall:.0f}s 真实时间内未收到任何 /scan，未发布 /initialpose。'
                '请先启动 T1（Gazebo + gz_laser_scan_relay），且与本终端同一 ROS_DOMAIN_ID、'
                '并已 source install；另开终端执行: ros2 topic hz /scan'
            )

        if self._wait_for_scan:
            threading.Timer(scan_timeout_wall, _wall_timeout).start()

        if self._wait_for_scan:
            self.get_logger().info(
                f'等待首帧 /scan（最长 {scan_timeout_wall:.0f}s 真实时间），然后发布 /initialpose '
                f'({self._x}, {self._y}, yaw={self._yaw})。须先启动 T1，否则无 /scan。'
            )
        else:
            # 直接延迟发布：更早进入 AMCL 初始定位流程
            self.get_logger().info(
                f'不等待 /scan；将在 {self._delay_after_start:.1f}s 后发布 /initialpose '
                f'({self._x}, {self._y}, yaw={self._yaw})。'
            )
            self._delay_timer = self.create_timer(
                self._delay_after_start, self._start_burst, clock=self._wall_clock
            )

    def _on_scan(self, _msg: LaserScan):
        if self._scan_seen:
            return
        self._scan_seen = True
        self.destroy_subscription(self._scan_sub)
        self.get_logger().info(
            f'First /scan received; publishing /initialpose in {self._delay_after_scan:.2f}s'
        )
        self._delay_timer = self.create_timer(
            self._delay_after_scan, self._start_burst, clock=self._wall_clock
        )

    def _odom_cb(self, msg: Odometry):
        self._last_odom_stamp = RosTime.from_msg(msg.header.stamp)

    def _start_burst(self):
        if self._delay_timer is not None:
            self._delay_timer.cancel()
            self._delay_timer = None
        self._burst_remaining = self._count
        self._burst_publish_tick()
        if self._burst_remaining > 0:
            self._burst_timer = self.create_timer(
                self._period, self._burst_publish_tick, clock=self._wall_clock
            )

    def _burst_publish_tick(self):
        if self._burst_remaining <= 0:
            if self._burst_timer is not None:
                self._burst_timer.cancel()
                self._burst_timer = None
            return

        # 根据 stamp_mode 选择 /initialpose header.stamp：
        # - now：更容易落在 TF cache 窗口内
        # - odom：用最近一次 /odom stamp
        # - zero：stamp=0（尽量让 TF 查询使用最新）
        if self._stamp_mode == 'odom' and self._last_odom_stamp is not None:
            self._msg.header.stamp = self._last_odom_stamp.to_msg()
        elif self._stamp_mode == 'zero':
            self._msg.header.stamp = RosTime(seconds=0.0).to_msg()
        else:
            self._msg.header.stamp = self.get_clock().now().to_msg()
        self._pub.publish(self._msg)
        self._burst_remaining -= 1
        if self._burst_remaining <= 0 and self._burst_timer is not None:
            self._burst_timer.cancel()
            self._burst_timer = None
            self.get_logger().info('Finished publishing /initialpose burst')


def main(args=None):
    rclpy.init(args=args)
    node = AmclInitialPosePublisher()
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
