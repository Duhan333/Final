# OpenTCS ↔ ROS2 逻辑仿真运行指南（当前阶段）

本指南只覆盖你现在在做的链路验证：  
**OpenTCS 下单 -> TCP -> ROS2 Action -> 逻辑车辆移动 -> OpenTCS FINISHED**。  
不包含 Gazebo、激光、Nav2。

---

## 0. 先看结论：哪些是必须跑，哪些不是

- **必须跑**
  - `T1`：`evaluation_launch.py`（含 `robot_state_publisher` + `joint_state_publisher` + `logic_sim_robot` + `bridge_node`）
  - `T2`：OpenTCS Kernel
  - `T3`：OpenTCS **初始化**（上传模型、拓扑、绑定 ROS2 适配器、启用车辆——**不是每次都要跑**，见下）
  - `T4`：**下单**（`POST` 运输单 + `dispatcher/trigger`——**每来一张新单跑一次**）
- **可选**
  - OpenTCS **Operations Desk**（连 Kernel 的 Swing 客户端：看车、下运输单等）
  - OpenTCS **Model Editor**（图形编辑 Point/Path/Location，常与 JSON/REST 配合）
  - RViz（只是可视化，不影响订单完成）
  - `nc` 手工发 `GOAL`（这是桥接自测，和 OpenTCS 下单二选一，不是必跑）
  - 一键采证脚本（论文数据采集）

---

## 1. 环境与依赖

```bash
sudo apt update
sudo apt install -y ros-humble-robot-state-publisher ros-humble-joint-state-publisher
```

> `joint_state_publisher` 必须保留：X3 URDF 有 continuous 轮子关节，没有 `/joint_states` 会导致 RViz 车体关节显示不完整。

---

## 2. 一次性编译（首次或代码变更后）

```bash
cd ~/Final/yahboomcar_ws
source /opt/ros/humble/setup.bash
colcon build --packages-select opentcs_ros2_bridge yahboomcar_description --symlink-install
source install/setup.bash
```

---

## 3. 必跑主流程（按顺序）

### T1：启动 ROS2 逻辑仿真链路（常驻）

```bash
cd ~/Final/yahboomcar_ws
source /opt/ros/humble/setup.bash
source install/setup.bash
ros2 launch opentcs_ros2_bridge evaluation_launch.py
```

期望看到：
- `logic_sim_robot`
- `bridge_node`
- `robot_state_publisher`
- `joint_state_publisher`

当前 `evaluation_launch.py` 已是多车版，车辆由 `VEHICLES` 列表驱动（默认两车），与 **`opentcs_plant_model_hub_m.json`** 对齐：
- `vehicle_1`：端口 `9091`，初始位姿 **`E-P0`**（`0.0, 7.5, 0.0` m）
- `vehicle_2`：端口 `9092`，初始位姿 **`W-P0`**（`1.0, 2.5, 0.0` m）

命名空间隔离后，运行时关键接口为：
- action：`/vehicle_1/navigate_to_pose`、`/vehicle_2/navigate_to_pose`
- pose 话题：`/vehicle_1/amcl_pose`、`/vehicle_2/amcl_pose`
- bridge TCP：`9091`（车1）、`9092`（车2）

---

### T2：启动 OpenTCS Kernel（常驻）

```bash
cd ~/Final/opentcs-master
./gradlew :opentcs-kernel:run
```

确认端口可用：

```bash
curl -s http://localhost:55200/v1/kernel/version
```

#### T2b（可选）：打开 OpenTCS 图形客户端

当前指南的 **T3/T4 用 curl** 分别完成初始化与下单；若要在**桌面程序**里连 Kernel、看车辆状态或手工建运输单，另开终端启动 **Operations Desk**（通过 RMI 连 Kernel，默认书签 `localhost:1099`）：

```bash
cd ~/Final/opentcs-master
./gradlew :opentcs-operationsdesk:run
```

若要在**图形界面**里画点、路径、站点（工厂模型），使用 **Model Editor**（多为离线编辑模型，保存后再 `PUT /v1/plantModel` 或导出 JSON 与仓库里的 **`opentcs_plant_model_hub_m.json`** 对齐；旧图 `opentcs_plant_model_test1.json` 仍保留作对照）：

```bash
cd ~/Final/opentcs-master
./gradlew :opentcs-modeleditor:run
```

> **WSL2**：需要图形环境（如 WSLg）；纯无桌面 SSH 会话无法弹出 Swing 窗口。Gradle 的 `run` 工作目录在各自模块的 `build/install/<模块名>/`，一般无需手改。

---

### T3：OpenTCS 初始化（不必每次跑）

在 **Kernel 已启动（T2）** 的前提下执行。**典型只做一次**（或在下述情况再跑一遍）：

- 第一次联调、或 **重启了 Kernel**（内存模型清空）  
- 换了 **`opentcs_plant_model_hub_m.json`**（点/路径/站点变更）  
- 车辆 **通信适配器被卸掉/禁用**，需要重新绑定 ROS2 适配器并启用  

**推荐**：一键执行。仅初始化（T3）不加单：

```bash
bash /home/klq/Final/curl_hub_m.sh --init-only
```

初始化 + 双车示例单 + 一次 `trigger`（T3+T4）：

```bash
bash /home/klq/Final/curl_hub_m.sh
```

或**手动**（便于对照 API）：

```bash
curl -s -X PUT http://localhost:55200/v1/plantModel \
  -H "Content-Type: application/json" \
  --data-binary @/home/klq/Final/opentcs_plant_model_hub_m.json

curl -s -X POST http://localhost:55200/v1/plantModel/topologyUpdateRequest \
  -H "Content-Type: application/json" \
  -d '{"paths":["E-P0 --- E-P1","E-P1 --- E-P2","E-P2 --- M","M --- E-P3","M --- W-P3","W-P0 --- W-P1","W-P1 --- W-P2","W-P2 --- M"]}'

curl -s -X PUT "http://localhost:55200/v1/vehicles/Vehicle-0001/commAdapter/attachment?newValue=org.opentcs.ros2.adapter.Ros2CommunicationAdapterDescription"
curl -s -X PUT "http://localhost:55200/v1/vehicles/Vehicle-0001/commAdapter/enabled?newValue=true"
curl -s -X PUT "http://localhost:55200/v1/vehicles/Vehicle-0001/integrationLevel?newValue=TO_BE_UTILIZED"
curl -s -X PUT "http://localhost:55200/v1/vehicles/Vehicle-0001/acceptableOrderTypes" \
  -H "Content-Type: application/json" \
  -d '{"acceptableOrderTypes":[{"name":"Move","priority":0}]}'

curl -s -X PUT "http://localhost:55200/v1/vehicles/Vehicle-0002/commAdapter/attachment?newValue=org.opentcs.ros2.adapter.Ros2CommunicationAdapterDescription"
curl -s -X PUT "http://localhost:55200/v1/vehicles/Vehicle-0002/commAdapter/enabled?newValue=true"
curl -s -X PUT "http://localhost:55200/v1/vehicles/Vehicle-0002/integrationLevel?newValue=TO_BE_UTILIZED"
curl -s -X PUT "http://localhost:55200/v1/vehicles/Vehicle-0002/acceptableOrderTypes" \
  -H "Content-Type: application/json" \
  -d '{"acceptableOrderTypes":[{"name":"Move","priority":0}]}'
```

T3 **不包含**创建运输单；模型与车辆就绪后执行 **T4**。用脚本时：`curl_hub_m.sh --init-only` 只做 T3；无参数则连 T4 一并执行。

> **`opentcs_plant_model_hub_m.json`**：东/西走廊经共用点 **M** 分流至 **E-P3** / **W-P3**；两车 bridge 端口 **`Vehicle-0001 -> 9091`**、**`Vehicle-0002 -> 9092`**。  
> 多车评估时 Kernel 建议使用 **`kernelapp.vehicleResourceManagementType = LENGTH_IGNORED`**（见 `opentcs-kernel` 分发配置）。  
> ROS2 适配器对 **`Move`** 在导航结束后会 **立即** `commandExecuted`，装卸仍用 `operatingTime`。两车可 **一起下单、一次 trigger**；若在 **M** 点互斥排队属正常调度行为。  
> **路由**：每条 Path 的 **`maxReverseVelocity` 必须大于 0**，否则含「远端卸货再回起点 **CHARGE**」的整单会在 `dispatcher/trigger` 后被标成 **`UNROUTABLE`**（内核会校验整条 drive-order 链是否连通）。当前 hub_m 已按此设置。  
> **重跑**：若订单已是 `UNROUTABLE`，请改用**新订单名**再 `POST`，或在内核里撤掉旧单后再下单。  
> **curl**：T3 里**每辆车**必须各有一条**完整**的 `acceptableOrderTypes` 请求；勿把多行粘贴连成一行（否则第二辆车可能未写入 `Move`，表现为异常）。

---

### T4：下单（可重复；每张新单跑一次）

运输单在 API 路径里的 **名称必须唯一**。Hub-M 模型下示例单为 **`TOrder-HubM-E-1`** / **`TOrder-HubM-W-1`**（各自走廊：装 → 卸 → 回起点充电，经共用点 **M**）。若已用无参 `curl_hub_m.sh`，本节可跳过。

#### 4.1 创建并确认订单（车 1，东走廊）

```bash
curl -s -X POST "http://localhost:55200/v1/transportOrders/TOrder-HubM-E-1" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "Move",
    "intendedVehicle": "Vehicle-0001",
    "destinations": [
      { "locationName": "Location-E-Load", "operation": "Load" },
      { "locationName": "Location-E-Unload", "operation": "Unload" },
      { "locationName": "Location-E-Charge", "operation": "CHARGE" }
    ]
  }'

curl -s "http://localhost:55200/v1/transportOrders/TOrder-HubM-E-1" | head -n 120
```

#### 4.2 创建并确认订单（车 2，西走廊）

```bash
curl -s -X POST "http://localhost:55200/v1/transportOrders/TOrder-HubM-W-1" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "Move",
    "intendedVehicle": "Vehicle-0002",
    "destinations": [
      { "locationName": "Location-W-Load", "operation": "Load" },
      { "locationName": "Location-W-Unload", "operation": "Unload" },
      { "locationName": "Location-W-Charge", "operation": "CHARGE" }
    ]
  }'
curl -s "http://localhost:55200/v1/transportOrders/TOrder-HubM-W-1" | head -n 120
```

#### 4.3 触发调度（两车单都创建后执行一次）

```bash
curl -s -X POST "http://localhost:55200/v1/dispatcher/trigger"
curl -s "http://localhost:55200/v1/transportOrders/TOrder-HubM-E-1" | head -n 80
curl -s "http://localhost:55200/v1/transportOrders/TOrder-HubM-W-1" | head -n 80
```

#### 4.4 查询订单状态（可重复执行）

```bash
curl -s "http://localhost:55200/v1/transportOrders/TOrder-HubM-E-1" | rg '"state"|"intendedVehicle"|"name"'
curl -s "http://localhost:55200/v1/transportOrders/TOrder-HubM-W-1" | rg '"state"|"intendedVehicle"|"name"'
```

最终期望：两张单状态到 `FINISHED`。

> 旧图 **`opentcs_plant_model_test1.json`** 下的 `TOrder-BCDA-A-1` / `TOrder-BCDA-A-2` 示例仍可用于三角拓扑对照，但与当前默认 launch 位姿不一致，需改回旧 plant 与 `evaluation_launch.py` 坐标后再用。

> `immediateAssignment` 不是必需；订单已在执行/完成时再调会报 `TRANSPORT_ORDER_STATE_INVALID`，属于正常行为。

---

## 4. 可选验证（不是必跑）

### A) RViz 可视化

```bash
cd ~/Final/yahboomcar_ws
source /opt/ros/humble/setup.bash
source install/setup.bash
rviz2 -d ~/Final/yahboomcar_ws/src/yahboomcar_description/rviz/yahboomcar.rviz
```

- Fixed Frame 选 `map`
- 看 `RobotModel` + `TF`

---

### B) `nc` 手动桥接测试（与 OpenTCS 下单二选一）

```bash
# 车1：目标接近 E-P1（4.0m, 7.5m），与 hub_m 东线一致
printf 'GOAL 4.0 7.5 0.0\n' | nc -q 2 127.0.0.1 9091
```

期望：`RESULT OK`。  
用途：快速判断 TCP + Action 链路是否通，不依赖 OpenTCS 调度。

第二台车：

```bash
# 车2：目标接近 W-P1（2.8m, 2.5m）
printf 'GOAL 2.8 2.5 0.0\n' | nc -q 2 127.0.0.1 9092
```

---

## 5. 论文采证（一键脚本）

脚本路径：
`~/Final/yahboomcar_ws/tools/collect_thesis_evidence.py`

运行：

```bash
cd ~/Final/yahboomcar_ws
source /opt/ros/humble/setup.bash
source install/setup.bash
python3 tools/collect_thesis_evidence.py \
  --x 4.0 --y 7.5 --yaw 0.0 \
  --vehicle Vehicle-0001 \
  --location Location-E-Load \
  --pose-timeout 30
```

> 默认 `--plant-model-json` 已指向 `opentcs_plant_model_hub_m.json`；若改用极简 `opentcs_plant_model.json`，请显式传入该参数。

> 多车场景请注意：默认采证脚本读取 `/amcl_pose`。若你的位姿发布在命名空间（如 `/vehicle_1/amcl_pose`），请按脚本参数或代码配置改到对应话题。  
> 脚本会先读取当前位姿；若你给的目标与当前位姿距离小于 `--min-move-dist`（默认 0.5m），会自动偏移目标，避免“原地完成导致车几乎不动”。

输出目录：
`/home/klq/Final/evidence/<timestamp>/`

包含：
- `summary.md`（可直接贴论文）
- `metrics.csv`（误差与时延）
- `order_*.json`（状态机证据）

---

## 6. 坐标映射（OpenTCS -> ROS）

配置文件：
`yahboomcar_ws/src/opentcs_ros2_bridge/config/evaluation_coordinate_map.yaml`

默认是 1:1：
- `scale: 1.0`
- `offset_x: 0.0`
- `offset_y: 0.0`
- `yaw_offset_ros_minus_opentcs: 0.0`

命令行检查：

```bash
ros2 run opentcs_ros2_bridge opentcs_map_coord \
  $(ros2 pkg prefix opentcs_ros2_bridge)/share/opentcs_ros2_bridge/config/evaluation_coordinate_map.yaml \
  4.0 7.5 0.0
```

---

## 7. 最短故障排查

### 7.1 采证脚本报 `/amcl_pose` 超时

先确认 T1 在跑，然后在同一终端执行：

```bash
cd ~/Final/yahboomcar_ws
source /opt/ros/humble/setup.bash
source install/setup.bash
ros2 topic hz /vehicle_1/amcl_pose
ros2 topic hz /vehicle_2/amcl_pose
```

应看到约 30Hz。

### 7.2 采证脚本报连接 Kernel 失败

```bash
curl -v --max-time 5 http://localhost:55200/v1/kernel/version
ss -ltnp | rg 55200
```

若端口不在监听，先重启 T2（Kernel）。

### 7.3 `Package 'opentcs_ros2_bridge' not found`

说明当前终端未 source 工作空间，重来：

```bash
cd ~/Final/yahboomcar_ws
source /opt/ros/humble/setup.bash
colcon build --packages-select opentcs_ros2_bridge --symlink-install
source install/setup.bash
```

---

### 7.4 死锁/卡点诊断日志（建议必抓）

这版代码已加三端关联日志：
- Java 适配器：`[seq=<n>] sendCommand / RESULT / empty operation`
- Python bridge：`[goal#<n>] recv GOAL / dispatch / Goal accepted / status / send RESULT`
- Python logic sim：`[sim-goal#<n>] start / succeeded / aborted`

抓日志建议：

1) 终端 A（ROS）先清屏再启动：
```bash
cd ~/Final/yahboomcar_ws
source /opt/ros/humble/setup.bash
source install/setup.bash
ros2 launch opentcs_ros2_bridge evaluation_launch.py 2>&1 | tee /tmp/ros_multi.log
```

2) 终端 B（Kernel）先清屏再启动：
```bash
cd ~/Final/opentcs-master
./gradlew :opentcs-kernel:run 2>&1 | tee /tmp/kernel_multi.log
```

3) 复现导航/调度问题后，提取关键行：
```bash
rg "\[goal#|\[sim-goal#|RESULT|NavigateToPose" /tmp/ros_multi.log
rg "\[seq=|sendCommand|commandExecuted|commandFailed|empty operation|ROS2 bridge" /tmp/kernel_multi.log
```

把这两段输出贴回即可做精确定位（是命令未下发、未送达、未执行，还是未回执）。

---

## 8. 相关文件

- `opentcs_plant_model_hub_m.json`（默认工厂模型）
- `curl_hub_m.sh`（Hub-M 初始化 / 一键下单）
- `opentcs_plant_model_test1.json`（旧三角拓扑对照，非默认）
- `yahboomcar_ws/src/opentcs_ros2_bridge/launch/evaluation_launch.py`
- `yahboomcar_ws/src/opentcs_ros2_bridge/opentcs_ros2_bridge/logic_sim_robot.py`
- `yahboomcar_ws/src/opentcs_ros2_bridge/opentcs_ros2_bridge/bridge_node.py`
- `yahboomcar_ws/src/opentcs_ros2_bridge/config/evaluation_coordinate_map.yaml`
- `yahboomcar_ws/tools/collect_thesis_evidence.py`
- `yahboomcar_ws/src/yahboomcar_description/urdf/yahboomcar_X3.urdf`

---

*文档版本：逻辑仿真链路版（当前毕业设计阶段）。*
