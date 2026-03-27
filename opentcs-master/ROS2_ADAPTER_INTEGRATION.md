# OpenTCS 侧 ROS2 通信适配器集成说明

本说明描述如何在 OpenTCS 中新增一个“ROS2 车辆通信适配器”，与 `opentcs_ros2_bridge`（ROS2 节点）通过 TCP 配合，把调度下发的 `MovementCommand` 转为 Nav2 导航目标，并回写执行结果与位姿。

## 1. 参考实现

完整参考：**opentcs-commadapter-loopback** 模块。

- 入口类：`LoopbackCommunicationAdapter` 继承 `BasicVehicleCommAdapter`。
- 关键方法：
  - `sendCommand(MovementCommand cmd)`：把指令发给“车辆”（本项目中改为通过 TCP 发给桥接节点）。
  - 在收到“执行完成”后调用 `getProcessModel().commandExecuted(cmd)`，失败则 `commandFailed(cmd)`。
  - 需要更新位姿时：`getProcessModel().setPosition(String pointName)` 或 `setPrecisePosition(x, y, z)`（单位：mm），以及 `setState(Vehicle.State.XXX)`。

## 2. 新建 Gradle 子项目（建议名称：opentcs-commadapter-ros2）

- 在 `settings.gradle` 中增加：`include 'opentcs-commadapter-ros2'`。
- 新建目录 `opentcs-commadapter-ros2`，仿照 `opentcs-commadapter-loopback` 的 `build.gradle` 和包结构。
- 依赖：`opentcs-api-base`、`opentcs-common` 等（与 loopback 一致即可，无需 ROS 库）。

## 3. 协议（与桥接节点一致）

- **连接**：TCP 客户端，连接桥接节点监听的地址（如 `localhost`）和端口（默认 `9090`）。
- **发送**：一行一条命令，以 `\n` 结尾：  
  `GOAL <x_m> <y_m> <theta_rad>`
- **接收**：  
  - 执行结果：一行 `RESULT OK` 或 `RESULT FAILED`。  
  - 可选：周期接收 `POSE <x_m> <y_m> <theta_rad>`，用于更新 ProcessModel 的精确位姿。

单位：**米、弧度**。OpenTCS 模型为 **mm、度** 时，在发送前换算：

- `x_m = point.getPose().getPosition().getX() / 1000.0`
- `y_m = point.getPose().getPosition().getY() / 1000.0`
- `theta_rad = Math.toRadians(point.getPose().getOrientationAngle())`

## 4. 在 sendCommand 中的推荐流程

1. 从 `cmd.getStep().getDestinationPoint()` 得到 `Point`，再取 `point.getPose()`。
2. 将位置与朝向换算为米和弧度。
3. 建立 TCP 连接（或复用长连接），发送 `GOAL x y theta\n`。
4. 阻塞读取一行（或异步 + 回调），解析 `RESULT OK` / `RESULT FAILED`。
5. 根据结果调用 `getProcessModel().commandExecuted(cmd)` 或 `commandFailed(cmd)`。
6. 若需更新当前点：可根据当前最近已知的 POSE 或目标点名称调用 `setPosition(...)`。

注意：`sendCommand` 在 Kernel 的 executor 线程中执行，若阻塞过久可能影响其他车辆；可改为“异步发送 + 在单独线程中等待结果并回调更新 ProcessModel”。

## 5. 注册适配器

- 实现 `VehicleCommAdapterFactory`，在工厂中为对应车辆类型创建本适配器实例。
- 通过 Guice 或 OpenTCS 的扩展机制注册该工厂，使 Kernel 在加载车辆驱动时使用“ROS2 适配器”。具体注册方式与 loopback 适配器的注册方式一致（参见 loopback 模块及 Kernel 的 `VehicleCommAdapterRegistry` / 配置）。

## 6. 与 ROS2 桥接的联合调试

1. 先启动 ROS2 侧：底盘 + 定位 + Nav2 + 桥接节点（`ros2 launch opentcs_ros2_bridge bridge_launch.py`）。
2. 再启动 OpenTCS Kernel，并为测试车辆选择“ROS2”通信适配器。
3. 在 OpenTCS 中下发运输单，观察适配器是否连上桥接、是否发送 GOAL、是否收到 RESULT 并正确调用 `commandExecuted` / `commandFailed`。

以上完成后，即可实现“OpenTCS 调度 ↔ 通信适配器 ↔ ROS2 桥接 ↔ Nav2”的完整链路；建图算法仍由 yahboomcar_nav 的 launch 独立使用，无需修改适配器。
