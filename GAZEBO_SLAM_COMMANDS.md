# Gazebo + Cartographer：每次要跑的命令（备忘）

与 **OpenTCS 逻辑仿真**（`RUN_GUIDE.md` / `DEV_DEBUG_START.md`）是**两条线**：做激光建图时开下面这条；不要同时再开一个 `evaluation_launch.py`，除非你很清楚端口/话题冲突。

**Gazebo 里激光话题**：先在 Gazebo 已起来的终端执行 `ign topic -l | grep -i scan`。你当前环境是 **`/scan`**、**`/scan/points`**；本仓库的 `gazebo_X3_launch.py` 默认按 **`/scan`** 做 `parameter_bridge`，一般**不用再改**。若你机器上名字不同，用 `gz_lidar_topic:=<实际名>` 覆盖。

---

## 0. 依赖（缺包时装一次）

```bash
sudo apt update
sudo apt install -y ros-humble-cartographer-ros ros-humble-cartographer-ros-msgs
```

---

## 1. 改代码后编译（`yahboomcar_description` / `yahboomcar_nav` 有改动时）

**每条单独执行**（不要整段粘成一行）。

```bash
cd ~/Final/yahboomcar_ws
```

```bash
source /opt/ros/humble/setup.bash
```

```bash
colcon build --packages-select yahboomcar_description yahboomcar_nav --symlink-install
```

```bash
source install/setup.bash
```

---

## 2. 终端 A：Gazebo + 车 + 桥接

```bash
cd ~/Final/yahboomcar_ws
```

```bash
source /opt/ros/humble/setup.bash
```

```bash
source install/setup.bash
```

```bash
ros2 launch yahboomcar_description gazebo_X3_launch.py
```

**若 Gazebo 激光话题不是 `/scan`**（以 `ign topic -l` 为准）：

```bash
ros2 launch yahboomcar_description gazebo_X3_launch.py gz_lidar_topic:=/你的话题名
```

---

## 3. 终端 B：Cartographer（`use_sim_time`）

等 Gazebo 和 `/scan_relay` 有数据后再开。

```bash
cd ~/Final/yahboomcar_ws
```

```bash
source /opt/ros/humble/setup.bash
```

```bash
source install/setup.bash
```

```bash
ros2 launch yahboomcar_nav cartographer_launch.py use_sim_time:=true
```

---

## 4. 快速自检（可选）

**仿真时钟 `/clock`**：`parameter_bridge` 固定 **`use_sim_time:=false`**（避免与「自发布 /clock」死锁）。另开终端应先 `source`，再 `ros2 topic list | grep clock` 或 `ros2 topic hz /clock`。若以前 `echo /clock --once` 一直无输出，重启 `gazebo_X3_launch` 后再试。

**Gazebo 侧**（Fortress 用 `ign`，Garden+ 可能是 `gz topic`）：

```bash
ign topic -l | grep -i scan
```

**ROS 侧**（必须先 `source install/setup.bash`）：

```bash
ros2 topic hz /scan_relay
```

```bash
ros2 topic echo /scan_relay --field header.frame_id
```

对外 **`/scan_relay`** 由 `gz_laser_scan_relay` 发布，`header.frame_id` 应为 **`laser_link`**（与 URDF 一致）。桥接器仍会在 ROS 侧发布 **`/scan`**（原样）和 **`/gz_bridge/scan_raw`**（仅供 relay）；Cartographer 默认订阅 `scan_topic:=/scan_relay`，避免重复发布源导致的 `Ignored subdivision…`。默认 **`align_scan_stamp_to_odom:=false`**：relay 会用 **`get_clock().now()`**（与 `gazebo_topic_relay` 的 `/odom`/TF 同一仿真时钟）写时间戳并保证单调递增。

Cartographer 若仍报 `Queue waiting for data: (0, scan)`：先确认 **`ros2 topic hz /scan_relay`** 有频率。若报 `source_frame does not exist`，核对上一行 `frame_id` 是否为 `laser_link`。

---

## 5. 相关文档

- 逻辑仿真 + OpenTCS + `tee` 采证：`DEV_DEBUG_START.md`
- OpenTCS 主流程：`RUN_GUIDE.md`
