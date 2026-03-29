# 开发调试：带 tee 的启动与采证流程

本文是 **[RUN_GUIDE.md](./RUN_GUIDE.md)** 的配套文档，专门约定 **联调 / 排障** 时如何用 **`tee` 落盘日志**，保证 `/tmp` 里的文件与**当前这一轮**进程一致。

- **日常跑通**：仍以 `RUN_GUIDE.md` 为主。  
- **要对照 kernel / ROS 时间线、发给别人看日志**：按本文执行。

---

## 1. 代码有改动时（先做一次）

**Java（ROS2 适配器 / kernel）**

```bash
cd ~/Final/opentcs-master
./gradlew :opentcs-kernel:installDist
```

**ROS 包（`opentcs_ros2_bridge` 等）**

```bash
cd ~/Final/yahboomcar_ws
source /opt/ros/humble/setup.bash
colcon build --packages-select opentcs_ros2_bridge yahboomcar_description --symlink-install
```

---

## 2. 终端分工（建议固定三个）

| 终端 | 内容 |
|------|------|
| **A** | ROS2 `evaluation_launch.py`，**必须 `tee`** |
| **B** | OpenTCS Kernel，`**必须 `tee`**` |
| **C** | `curl`（T3/T4）+ `rg` 查日志 |

旧进程在对应窗口 **Ctrl+C** 停掉后再开新一轮。

---

## 3. 清空或轮换日志（每轮调试前执行）

固定文件名（简单，但**每轮前先删**，否则会混进上一轮）：

```bash
rm -f /tmp/ros_multi.log /tmp/kernel_multi.log
```

或按时间戳分开存（推荐多人/多轮对比）：

```bash
STAMP=$(date +%Y%m%d_%H%M%S)
export ROS_LOG="/tmp/ros_multi_${STAMP}.log"
export KERNEL_LOG="/tmp/kernel_multi_${STAMP}.log"
```

下文默认使用 **`/tmp/ros_multi.log`** 与 **`/tmp/kernel_multi.log`**；若用了 `ROS_LOG`/`KERNEL_LOG`，后面所有 `tee` / `rg` 路径改成这两个变量。

---

## 4. 终端 A：ROS2（带 tee）

```bash
cd ~/Final/yahboomcar_ws
source /opt/ros/humble/setup.bash
source install/setup.bash
ros2 launch opentcs_ros2_bridge evaluation_launch.py 2>&1 | tee /tmp/ros_multi.log
```

**期望**：两车 `TCP server listening on port 9091` / `9092`。

---

## 5. 终端 B：OpenTCS Kernel（带 tee）

```bash
cd ~/Final/opentcs-master
./gradlew :opentcs-kernel:run 2>&1 | tee /tmp/kernel_multi.log
```

**期望**：`Listening on http://0.0.0.0:55200/`。

**快速自检**（终端 C）：

```bash
curl -s http://localhost:55200/v1/kernel/version
```

---

## 6. 终端 C：T3 初始化（每重启一次 Kernel 执行一整块）

**整段复制执行**（与 [RUN_GUIDE.md §T3](./RUN_GUIDE.md) 一致；或 `bash /home/klq/Final/curl_hub_m.sh --init-only`）：

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

---

## 7. 终端 C：T4 下单与触发（与 RUN_GUIDE 一致）

**新建订单时 URL 中订单名须唯一**；若沿用下例名称，需保证内核里没有同名未完成单。两车单都 `POST` 后 **执行一次** `dispatcher/trigger`（见 [RUN_GUIDE.md §T4](./RUN_GUIDE.md)）。也可直接 `bash /home/klq/Final/curl_hub_m.sh`（含 T3+T4）。

### 7.1 车 1 下单（东走廊 Hub-M）

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

### 7.2 车 2 下单（西走廊 Hub-M）

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

### 7.3 触发调度（单独一行，注意引号成对）

```bash
curl -s -X POST "http://localhost:55200/v1/dispatcher/trigger"
```

### 7.4 查订单（可反复执行）

```bash
curl -s "http://localhost:55200/v1/transportOrders/TOrder-HubM-E-1" | rg '"state"|"intendedVehicle"|"name"'
curl -s "http://localhost:55200/v1/transportOrders/TOrder-HubM-W-1" | rg '"state"|"intendedVehicle"|"name"'
```

更多说明见 [RUN_GUIDE.md §T4](./RUN_GUIDE.md)。

---

## 8. 本轮采证：对 tee 出来的文件 `rg`

**Kernel**

```bash
rg -n "Vehicle-0001|Vehicle-0002|seq=|sendCommand|commandExecuted|commandFailed|bridge RESULT|stranded|9091|9092" /tmp/kernel_multi.log
```

**ROS**

```bash
rg -n "vehicle_1|vehicle_2|9091|9092|\[goal#|recv GOAL|send RESULT|NavigateToPose|connected from" /tmp/ros_multi.log
```

---

## 9. 再开一轮时

1. 终端 A/B **Ctrl+C**。  
2. **§3** 再执行一次（`rm` 或换新的 `STAMP` 日志名）。  
3. 从 **§4** 起重复。

---

## 10. 注意

- **没有 `tee` 时**，终端里的输出**不会**自动进 `/tmp/ros_multi.log`；不要用旧文件冒充当前轮。  
- **路径**：若仓库不在 `/home/klq/Final`，请替换 `plantModel` 的 `--data-binary @...` 路径。  
- **依赖与 RViz 等**：仍以 [RUN_GUIDE.md](./RUN_GUIDE.md) 为准。  
- **Hub-M `UNROUTABLE`**：多为旧版 plant 路径不可倒车，或订单名已失败过；见 RUN_GUIDE 中「路由 / 重跑」说明。T3 的 curl **逐条执行**，避免两行粘成一行导致 `acceptableOrderTypes` 未发到第二辆车。
