# opentcs_ros2_bridge

OpenTCS 与 ROS2 Nav2 之间的通信桥接节点：通过 TCP 接收 OpenTCS 车辆适配器下发的目标点，调用 Nav2 `NavigateToPose`，并将执行结果与位姿回传。

## 协议（TCP）

- **适配器 → 桥接**：一行一条命令  
  - `GOAL <x_m> <y_m> <theta_rad>`  
  例如：`GOAL 1.0 2.0 0.5`

- **桥接 → 适配器**：  
  - 执行结束：`RESULT OK` 或 `RESULT FAILED`  
  - 周期位姿（可选）：`POSE <x_m> <y_m> <theta_rad>`

## 运行前提

- 已启动 Nav2（如 yahboomcar_nav 的导航 launch），且存在 `navigate_to_pose` Action Server。
- 已有定位（如 AMCL）并发布 `amcl_pose`（或可改为 `odom` 等）。

## 编译与运行

```bash
cd ~/Final/yahboomcar_ws
colcon build --packages-select opentcs_ros2_bridge
source install/setup.bash

# 先启动底盘 + 建图/导航（如 yahboomcar 的 bringup + nav），再启动桥接：
ros2 launch opentcs_ros2_bridge bridge_launch.py
```

## 参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| tcp_port | 9090 | TCP 服务端口 |
| action_name | navigate_to_pose | Nav2 Action 名 |
| map_frame | map | 目标点坐标系 |
| pose_topic | amcl_pose | 当前位姿话题 |
| send_pose_period_sec | 0.5 | 向适配器发送 POSE 的周期（0 表示不发送） |

## OpenTCS 侧适配器

Java 侧需实现一个 `VehicleCommAdapter`，在 `sendCommand(MovementCommand cmd)` 中：

1. 从 `cmd.getStep().getDestinationPoint().getPose()` 取得目标（OpenTCS 为 mm、度）。
2. 换算为米、弧度后，通过 TCP 连接本机 9090 端口，发送 `GOAL x y theta\n`。
3. 阻塞或异步读取一行，得到 `RESULT OK` 或 `RESULT FAILED`。
4. 调用 `getProcessModel().commandExecuted(cmd)` 或 `commandFailed(cmd)`。

详见项目根目录的 `OPENTCS_ROS2_ADAPTER_DESIGN.md`。

---

## 逻辑仿真评估（无 Gazebo / 无 Nav2）

用于毕业设计验证 **OpenTCS ↔ ROS2** 链路：`logic_sim_robot` 提供 `NavigateToPose` Action Server，按速度沿直线接近目标后原地转向，到位后 **SUCCEEDED**；同时发布 `/amcl_pose` 与 `map→odom→base_footprint`（`odom` 相对 `map` 为单位阵，与实车 AMCL+里程计语义一致）。

```bash
source install/setup.bash
ros2 launch opentcs_ros2_bridge evaluation_launch.py
```

另开终端：`rviz2`，Fixed Frame 选 `map`，可加 RobotModel（话题 `/robot_description`）、TF。OpenTCS 适配器连 **9090** 发 `GOAL x y theta` 即可。

### 坐标映射（OpenTCS Point → ROS map）

- 配置文件：`share/opentcs_ros2_bridge/config/evaluation_coordinate_map.yaml`
- 工具：`opentcs_map_coord <yaml> <x> <y> [yaw_rad]`
- Python：`opentcs_ros2_bridge.coordinate_mapping` 中 `opentcs_to_ros_xy_yaw(...)`
