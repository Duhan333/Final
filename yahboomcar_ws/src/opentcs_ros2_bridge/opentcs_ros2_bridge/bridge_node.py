#!/usr/bin/env python3
"""
OpenTCS–ROS2 桥接节点：多实例兼容版。
"""
import queue
import socket
import threading
import math
import time
import rclpy
import itertools
from typing import Callable, List
from rclpy.node import Node
from rclpy.action import ActionClient
from rclpy.executors import MultiThreadedExecutor
from action_msgs.msg import GoalStatus
from geometry_msgs.msg import PoseStamped, PoseWithCovarianceStamped
from nav2_msgs.action import NavigateToPose

class OpenTCSROS2BridgeNode(Node):
    def __init__(self):
        super().__init__('opentcs_ros2_bridge')
        self.declare_parameter('tcp_port', 9090)
        self.declare_parameter('action_name', 'navigate_to_pose')
        self.declare_parameter('map_frame', 'map')
        
        # 🔴 修改点：去掉默认的 '/'，改用相对名 'amcl_pose'，以便在 namespace 下正确订阅 /vehicle_x/amcl_pose
        self.declare_parameter('pose_topic', 'amcl_pose')
        self.declare_parameter('send_pose_period_sec', 0.5)

        self._port = self.get_parameter('tcp_port').value
        self._action_name = self.get_parameter('action_name').value
        self._map_frame = self.get_parameter('map_frame').value
        self._pose_topic = self.get_parameter('pose_topic').value
        self._send_pose_period = self.get_parameter('send_pose_period_sec').value

        self._current_pose = None
        self._pose_lock = threading.Lock()
        self._client_socket = None
        self._client_lock = threading.Lock()

        self._action_client = ActionClient(self, NavigateToPose, self._action_name)
        self._pose_sub = self.create_subscription(
            PoseWithCovarianceStamped,
            self._pose_topic,
            self._pose_callback,
            10
        )
        self._pose_timer = None
        if self._send_pose_period > 0:
            self._pose_timer = self.create_timer(
                self._send_pose_period,
                self._send_pose_to_client
            )

        self.get_logger().info(
            f'Bridge Ready: TCP port={self._port}, action={self._action_name}, sub={self._pose_topic}'
        )
        self._goal_dispatch_q = queue.Queue()
        self._goal_seq = itertools.count(1)
        self._goal_dispatch_timer = self.create_timer(0.02, self._dispatch_pending_goal)
        self._server_thread = threading.Thread(target=self._run_tcp_server, daemon=True)
        self._server_thread.start()

    def _dispatch_pending_goal(self) -> None:
        try:
            seq, x, y, theta, on_done = self._goal_dispatch_q.get_nowait()
        except queue.Empty:
            return
        self.get_logger().info(
            f'[goal#{seq}] dispatch NavigateToPose x={x:.4f} y={y:.4f} theta={theta:.4f}'
        )
        self._run_nav_goal_async_chain(seq, x, y, theta, on_done)

    def _pose_callback(self, msg: PoseWithCovarianceStamped):
        with self._pose_lock:
            self._current_pose = msg.pose.pose

    def _send_pose_to_client(self):
        with self._pose_lock:
            p = self._current_pose
        if p is None:
            return
        with self._client_lock:
            s = self._client_socket
        if s is None:
            return
        try:
            line = f'POSE {p.position.x} {p.position.y} {_quat_to_yaw(p.orientation)}\n'
            s.sendall(line.encode('utf-8'))
        except Exception:
            pass

    def _run_tcp_server(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(('0.0.0.0', self._port))
        server.listen(1)
        self.get_logger().info(f'TCP server listening on port {self._port}')
        while rclpy.ok():
            client = None
            try:
                client, addr = server.accept()
                self.get_logger().info(f'OpenTCS adapter connected from {addr}')
                with self._client_lock:
                    self._client_socket = client
                self._handle_client(client)
            except Exception as e:
                self.get_logger().warn(f'TCP accept error: {e}')
            finally:
                with self._client_lock:
                    self._client_socket = None
                if client is not None:
                    try:
                        client.close()
                    except Exception:
                        pass

    def _handle_client(self, client: socket.socket):
        buf = b''
        while rclpy.ok():
            try:
                data = client.recv(1024)
                if not data:
                    break
                buf += data
                while b'\n' in buf or b'\r' in buf:
                    line, buf = _split_line(buf)
                    if not line:
                        continue
                    line = line.decode('utf-8').strip()
                    if line.upper().startswith('GOAL '):
                        seq = -1
                        parts = line.split()
                        if len(parts) >= 4:
                            try:
                                x, y, theta = float(parts[1]), float(parts[2]), float(parts[3])
                                seq = next(self._goal_seq)
                                self.get_logger().info(
                                    f'[goal#{seq}] recv GOAL x={x:.4f} y={y:.4f} theta={theta:.4f}'
                                )
                                success = self._send_nav_goal_from_tcp(seq, x, y, theta)
                                reply = 'RESULT OK\n' if success else 'RESULT FAILED\n'
                            except ValueError:
                                reply = 'RESULT FAILED\n'
                        else:
                            reply = 'RESULT FAILED\n'
                        try:
                            client.sendall(reply.encode('utf-8'))
                            if seq > 0:
                                self.get_logger().info(f'[goal#{seq}] send {reply.strip()}')
                            else:
                                self.get_logger().info(f'[goal#invalid] send {reply.strip()}')
                        except Exception:
                            return
            except (ConnectionResetError, BrokenPipeError, OSError):
                break
        self.get_logger().info('OpenTCS adapter disconnected')

    def _send_nav_goal_from_tcp(self, seq: int, x: float, y: float, theta: float) -> bool:
        deadline = time.monotonic() + 5.0
        while rclpy.ok() and time.monotonic() < deadline:
            if self._action_client.server_is_ready():
                break
            time.sleep(0.02)
        else:
            self.get_logger().error(f'[goal#{seq}] NavigateToPose action server not ready (timeout 5s)')
            return False

        done = threading.Event()
        ok_box: List[bool] = [False]

        def finish(success: bool) -> None:
            ok_box[0] = success
            done.set()

        self._goal_dispatch_q.put((seq, x, y, theta, finish))
        done.wait(timeout=650.0)
        if not done.is_set():
            self.get_logger().error(f'[goal#{seq}] timeout waiting nav result (650s)')
        return ok_box[0]

    def _run_nav_goal_async_chain(
        self, seq: int, x: float, y: float, theta: float, on_done: Callable[[bool], None]
    ) -> None:
        if not self._action_client.server_is_ready():
            self.get_logger().error(f'[goal#{seq}] NavigateToPose server not ready when starting async chain')
            on_done(False)
            return

        goal_msg = NavigateToPose.Goal()
        goal_msg.pose = PoseStamped()
        goal_msg.pose.header.stamp = self.get_clock().now().to_msg()
        goal_msg.pose.header.frame_id = self._map_frame
        goal_msg.pose.pose.position.x = x
        goal_msg.pose.pose.position.y = y
        goal_msg.pose.pose.position.z = 0.0
        q = _yaw_to_quat(theta)
        goal_msg.pose.pose.orientation.x = q[0]
        goal_msg.pose.pose.orientation.y = q[1]
        goal_msg.pose.pose.orientation.z = q[2]
        goal_msg.pose.pose.orientation.w = q[3]

        send_future = self._action_client.send_goal_async(goal_msg)

        def on_send_done(fut) -> None:
            try:
                goal_handle = fut.result()
            except Exception as exc:
                self.get_logger().warn(f'[goal#{seq}] send_goal_async failed: {exc}')
                on_done(False)
                return
            if not goal_handle.accepted:
                self.get_logger().warn(f'[goal#{seq}] Goal rejected')
                on_done(False)
                return
            self.get_logger().info(f'[goal#{seq}] Goal accepted by action server')
            result_future = goal_handle.get_result_async()

            def on_result_done(rfut) -> None:
                try:
                    result_response = rfut.result()
                except Exception as exc:
                    self.get_logger().warn(f'[goal#{seq}] get_result failed: {exc}')
                    on_done(False)
                    return
                status = int(result_response.status)
                if status == GoalStatus.STATUS_SUCCEEDED:
                    self.get_logger().info(f'[goal#{seq}] NavigateToPose status=SUCCEEDED')
                    on_done(True)
                    return
                self.get_logger().warn(f'[goal#{seq}] NavigateToPose ended with status={status}')
                on_done(False)

            result_future.add_done_callback(on_result_done)

        send_future.add_done_callback(on_send_done)


def _yaw_to_quat(yaw: float):
    cy, sy = math.cos(yaw * 0.5), math.sin(yaw * 0.5)
    return (0.0, 0.0, sy, cy)


def _quat_to_yaw(q) -> float:
    x, y, z, w = q.x, q.y, q.z, q.w
    siny_cosp = 2 * (w * z + x * y)
    cosy_cosp = 1 - 2 * (y * y + z * z)
    return math.atan2(siny_cosp, cosy_cosp)


def _split_line(buf: bytes):
    for i, b in enumerate(buf):
        if b == ord('\n') or b == ord('\r'):
            return buf[:i], buf[i + 1:]
    return b'', buf


def main(args=None):
    rclpy.init(args=args)
    node = OpenTCSROS2BridgeNode()
    executor = MultiThreadedExecutor(num_threads=4)
    executor.add_node(node)
    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        executor.remove_node(node)
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()