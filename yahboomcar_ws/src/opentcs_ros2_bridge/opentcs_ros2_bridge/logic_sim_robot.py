#!/usr/bin/env python3
"""
逻辑仿真：多机隔离版。
- 支持 ROS 2 Namespace，话题自动加上前缀
- 接收初始位姿，防止多车出生在同一点
"""
from __future__ import annotations

import math
import threading
import time

import rclpy
from rclpy.action import ActionServer, CancelResponse, GoalResponse
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node

from builtin_interfaces.msg import Duration
from geometry_msgs.msg import PoseStamped, PoseWithCovarianceStamped, TransformStamped
from nav2_msgs.action import NavigateToPose
from std_msgs.msg import Empty
from tf2_ros import TransformBroadcaster


def _quat_to_yaw(q) -> float:
    return math.atan2(
        2.0 * (q.w * q.z + q.x * q.y),
        1.0 - 2.0 * (q.y * q.y + q.z * q.z),
    )

def _yaw_to_quat(yaw: float):
    half = yaw * 0.5
    return 0.0, 0.0, math.sin(half), math.cos(half)

def _shortest_angle_delta(a0: float, a1: float) -> float:
    d = a1 - a0
    while d > math.pi:
        d -= 2.0 * math.pi
    while d < -math.pi:
        d += 2.0 * math.pi
    return d


class LogicSimRobot(Node):
    def __init__(self):
        super().__init__('logic_sim_robot')
        self.declare_parameter('map_frame', 'map')
        self.declare_parameter('odom_frame', 'odom')
        self.declare_parameter('base_frame', 'base_footprint')
        self.declare_parameter('linear_speed', 0.5)
        self.declare_parameter('angular_speed', 0.8)
        self.declare_parameter('position_tolerance', 0.05)
        self.declare_parameter('yaw_tolerance', 0.08)
        self.declare_parameter('action_name', 'navigate_to_pose')
        
        # 🔴 修改点：去掉开头的 '/'，使用相对名称，以便自适应命名空间
        self.declare_parameter('publish_amcl_topic', 'amcl_pose')
        self.declare_parameter('publish_pose_stamped_topic', 'pose')
        
        # 🔴 新增：初始坐标参数，防止多车重叠
        self.declare_parameter('initial_x', 0.0)
        self.declare_parameter('initial_y', 0.0)
        self.declare_parameter('initial_yaw', 0.0)

        self._map = self.get_parameter('map_frame').value
        self._odom = self.get_parameter('odom_frame').value
        self._base = self.get_parameter('base_frame').value
        self._v = float(self.get_parameter('linear_speed').value)
        self._w = float(self.get_parameter('angular_speed').value)
        self._pos_tol = float(self.get_parameter('position_tolerance').value)
        self._yaw_tol = float(self.get_parameter('yaw_tolerance').value)
        
        an = self.get_parameter('action_name').value
        amcl_topic = self.get_parameter('publish_amcl_topic').value
        pose_topic = self.get_parameter('publish_pose_stamped_topic').value

        self._lock = threading.Lock()
        self._nav_lock = threading.Lock()
        self._goal_counter = 0
        
        # 读取初始参数
        self._x = float(self.get_parameter('initial_x').value)
        self._y = float(self.get_parameter('initial_y').value)
        self._yaw = float(self.get_parameter('initial_yaw').value)

        self._tf_broadcaster = TransformBroadcaster(self)
        self._amcl_pub = self.create_publisher(PoseWithCovarianceStamped, amcl_topic, 10)
        self._pose_pub = self.create_publisher(PoseStamped, pose_topic, 10)

        self._cb_group = ReentrantCallbackGroup()
        self._action_server = ActionServer(
            self,
            NavigateToPose,
            an,
            execute_callback=self._execute_navigate,
            goal_callback=self._goal_cb,
            cancel_callback=self._cancel_cb,
            callback_group=self._cb_group,
        )

        # 🔴 修改点：同样去掉 '/'，使其变为 'goal_pose'
        self.create_subscription(PoseStamped, 'goal_pose', self._on_goal_pose, 10)
        self.create_timer(1.0 / 30.0, self._timer_publish_pose_tf)

        self.get_logger().info(
            f'Action {an}, amcl->{amcl_topic}, TF {self._map}->{self._odom}->{self._base}, Spawn at ({self._x}, {self._y})'
        )

    def _goal_cb(self, _goal_request):
        return GoalResponse.ACCEPT

    def _cancel_cb(self, _cancel_request):
        return CancelResponse.ACCEPT

    def _pose_from_nav_goal(self, goal: NavigateToPose.Goal):
        p = goal.pose.pose.position
        yaw = _quat_to_yaw(goal.pose.pose.orientation)
        return float(p.x), float(p.y), float(yaw)

    def _execute_navigate(self, goal_handle):
        gx, gy, gyaw = self._pose_from_nav_goal(goal_handle.request)
        with self._lock:
            self._goal_counter += 1
            goal_id = self._goal_counter
        self.get_logger().info(
            f'[sim-goal#{goal_id}] start x={gx:.4f} y={gy:.4f} yaw={gyaw:.4f}'
        )
        with self._nav_lock:
            ok = self._navigate_blocking(goal_handle, gx, gy, gyaw)
        result = NavigateToPose.Result()
        result.result = Empty()
        if ok:
            self.get_logger().info(f'[sim-goal#{goal_id}] succeeded')
            goal_handle.succeed()
        elif goal_handle.is_cancel_requested:
            self.get_logger().warn(f'[sim-goal#{goal_id}] canceled')
            goal_handle.canceled()
        else:
            self.get_logger().warn(f'[sim-goal#{goal_id}] aborted')
            goal_handle.abort()
        return result

    def _on_goal_pose(self, msg: PoseStamped):
        frame = msg.header.frame_id
        if frame and frame != self._map:
            self.get_logger().warn(
                f'goal_pose frame_id={frame!r} != map_frame={self._map!r}; still using pose'
            )
        gx = float(msg.pose.position.x)
        gy = float(msg.pose.position.y)
        gyaw = _quat_to_yaw(msg.pose.orientation)

        class _Gh:
            @property
            def is_cancel_requested(self):
                return False

        gh = _Gh()
        threading.Thread(
            target=self._goal_pose_worker,
            args=(gh, gx, gy, gyaw),
            daemon=True,
        ).start()

    def _goal_pose_worker(self, gh, gx, gy, gyaw):
        with self._nav_lock:
            self._navigate_blocking(gh, gx, gy, gyaw)

    def _navigate_blocking(self, goal_handle, gx: float, gy: float, gyaw: float) -> bool:
        period = 0.02
        while rclpy.ok():
            if goal_handle.is_cancel_requested:
                return False
            with self._lock:
                x, y, yaw = self._x, self._y, self._yaw
            dx = gx - x
            dy = gy - y
            dist = math.hypot(dx, dy)
            dyaw = _shortest_angle_delta(yaw, gyaw)
            if dist <= self._pos_tol and abs(dyaw) <= self._yaw_tol:
                return True
            step = self._v * period
            if dist > self._pos_tol:
                if dist < step:
                    nx, ny = gx, gy
                else:
                    nx = x + (dx / dist) * step
                    ny = y + (dy / dist) * step
                path_yaw = math.atan2(dy, dx)
                nyaw = path_yaw
            else:
                nx, ny = x, y
                wstep = self._w * period
                if abs(dyaw) < wstep:
                    nyaw = gyaw
                else:
                    nyaw = yaw + math.copysign(wstep, dyaw)
            with self._lock:
                self._x, self._y, self._yaw = nx, ny, nyaw
            time.sleep(period)

    def _timer_publish_pose_tf(self):
        with self._lock:
            x, y, yaw = self._x, self._y, self._yaw
        now = self.get_clock().now().to_msg()

        t_mo = TransformStamped()
        t_mo.header.stamp = now
        t_mo.header.frame_id = self._map
        t_mo.child_frame_id = self._odom
        t_mo.transform.translation.x = 0.0
        t_mo.transform.translation.y = 0.0
        t_mo.transform.translation.z = 0.0
        t_mo.transform.rotation.w = 1.0

        q = _yaw_to_quat(yaw)
        t_ob = TransformStamped()
        t_ob.header.stamp = now
        t_ob.header.frame_id = self._odom
        t_ob.child_frame_id = self._base
        t_ob.transform.translation.x = x
        t_ob.transform.translation.y = y
        t_ob.transform.translation.z = 0.0
        t_ob.transform.rotation.x = q[0]
        t_ob.transform.rotation.y = q[1]
        t_ob.transform.rotation.z = q[2]
        t_ob.transform.rotation.w = q[3]

        self._tf_broadcaster.sendTransform([t_mo, t_ob])

        msg = PoseWithCovarianceStamped()
        msg.header.stamp = now
        msg.header.frame_id = self._map
        msg.pose.pose.position.x = x
        msg.pose.pose.position.y = y
        msg.pose.pose.position.z = 0.0
        msg.pose.pose.orientation.x = q[0]
        msg.pose.pose.orientation.y = q[1]
        msg.pose.pose.orientation.z = q[2]
        msg.pose.pose.orientation.w = q[3]
        c = msg.pose.covariance
        c[0] = 0.02
        c[7] = 0.02
        c[35] = 0.05
        self._amcl_pub.publish(msg)

        ps = PoseStamped()
        ps.header = msg.header
        ps.pose = msg.pose.pose
        self._pose_pub.publish(ps)


def main(args=None):
    rclpy.init(args=args)
    node = LogicSimRobot()
    executor = MultiThreadedExecutor(num_threads=4)
    executor.add_node(node)
    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()