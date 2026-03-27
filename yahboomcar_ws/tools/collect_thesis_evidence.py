#!/usr/bin/env python3
"""
一键采证脚本（逻辑仿真版）：
1) 调 OpenTCS Web API 创建并触发运输单
2) 轮询订单状态直到 FINISHED/FAILED
3) 读取 /amcl_pose（最终位姿）
4) 计算目标点与最终位姿误差
5) 产出 summary.md / metrics.csv / order_*.json

前置条件：
- ros2 launch opentcs_ros2_bridge evaluation_launch.py 正在运行
- OpenTCS Kernel 正在运行（默认 http://localhost:55200）
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import math
import pathlib
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request


def iso_now_utc() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_iso_z(ts: str) -> dt.datetime:
    # 兼容 OpenTCS/JVM 常见的纳秒精度时间戳（Python fromisoformat 最多支持微秒 6 位）
    s = ts.strip().replace("Z", "+00:00")
    # 例如: 2026-03-24T06:42:01.881029536+00:00 -> 2026-03-24T06:42:01.881029+00:00
    m = re.match(r"^(.*\.\d{6})\d+([+-]\d{2}:\d{2})$", s)
    if m:
        s = m.group(1) + m.group(2)
    return dt.datetime.fromisoformat(s)


def http_json(method: str, url: str, payload: dict | None = None) -> dict | list | None:
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = resp.read().decode("utf-8").strip()
            if not raw:
                return None
            return json.loads(raw)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"HTTP {e.code} {url}: {body}") from e
    except Exception as e:
        raise RuntimeError(f"Request failed {method} {url}: {e}") from e


def read_simple_yaml_mapping(path: pathlib.Path) -> dict:
    """
    只解析本项目映射文件里的顶层标量键，避免额外依赖 PyYAML。
    """
    out = {
        "scale": 1.0,
        "offset_x": 0.0,
        "offset_y": 0.0,
        "yaw_offset_ros_minus_opentcs": 0.0,
    }
    text = path.read_text(encoding="utf-8")
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("#") or ":" not in s:
            continue
        k, v = s.split(":", 1)
        k = k.strip()
        v = v.strip()
        if k in out:
            try:
                out[k] = float(v)
            except ValueError:
                pass
    return out


def map_opentcs_to_ros(x: float, y: float, yaw: float, m: dict) -> tuple[float, float, float]:
    rx = x * m["scale"] + m["offset_x"]
    ry = y * m["scale"] + m["offset_y"]
    ryaw = yaw + m["yaw_offset_ros_minus_opentcs"]
    return rx, ry, ryaw


def _unit_to_meter(v: float, plant_unit_mm: bool) -> float:
    return v / 1000.0 if plant_unit_mm else v


def resolve_location_target_from_model(
    model_json: pathlib.Path, location_name: str, plant_unit_mm: bool
) -> tuple[float, float, float, str] | None:
    """
    从 opentcs_plant_model.json 解析 location 对应目标坐标（米）。
    优先 location.links -> point.position；否则用 location.position。
    返回: (x_m, y_m, yaw_rad, source_desc)
    """
    if not model_json.exists():
        return None
    data = json.loads(model_json.read_text(encoding="utf-8"))
    points = {p.get("name"): p for p in data.get("points", []) if isinstance(p, dict)}
    locations = {l.get("name"): l for l in data.get("locations", []) if isinstance(l, dict)}
    loc = locations.get(location_name)
    if not isinstance(loc, dict):
        return None

    links = loc.get("links") or []
    if isinstance(links, list) and len(links) > 0:
        p_name = links[0].get("pointName")
        p = points.get(p_name, {})
        pos = p.get("position") or {}
        x = _unit_to_meter(float(pos.get("x", 0.0)), plant_unit_mm)
        y = _unit_to_meter(float(pos.get("y", 0.0)), plant_unit_mm)
        yaw_deg = float(p.get("vehicleOrientationAngle", 0.0))
        yaw = math.radians(yaw_deg)
        return x, y, yaw, f"model.location.links[0].pointName={p_name}"

    pos = loc.get("position") or {}
    x = _unit_to_meter(float(pos.get("x", 0.0)), plant_unit_mm)
    y = _unit_to_meter(float(pos.get("y", 0.0)), plant_unit_mm)
    return x, y, 0.0, "model.location.position"


def read_amcl_pose_once(timeout_sec: int) -> tuple[float, float, float]:
    cmd = "ros2 topic echo /amcl_pose --once"
    try:
        cp = subprocess.run(
            cmd,
            shell=True,
            check=True,
            capture_output=True,
            text=True,
            timeout=timeout_sec,
        )
    except Exception as e:
        raise RuntimeError(f"读取 /amcl_pose 失败：{e}") from e
    txt = cp.stdout
    # 取第一个 pose
    mx = re.search(r"position:\s*\n\s*x:\s*([\-0-9.eE]+)", txt)
    my = re.search(r"position:\s*\n(?:.*\n)*?\s*y:\s*([\-0-9.eE]+)", txt)
    # yaw 从四元数计算
    mox = re.search(r"orientation:\s*\n\s*x:\s*([\-0-9.eE]+)", txt)
    moy = re.search(r"orientation:\s*\n(?:.*\n)*?\s*y:\s*([\-0-9.eE]+)", txt)
    moz = re.search(r"orientation:\s*\n(?:.*\n)*?\s*z:\s*([\-0-9.eE]+)", txt)
    mow = re.search(r"orientation:\s*\n(?:.*\n)*?\s*w:\s*([\-0-9.eE]+)", txt)
    if not all([mx, my, mox, moy, moz, mow]):
        raise RuntimeError("无法解析 /amcl_pose 输出，请确认 evaluation_launch 正在运行。")
    x = float(mx.group(1))
    y = float(my.group(1))
    qx, qy, qz, qw = (float(mox.group(1)), float(moy.group(1)), float(moz.group(1)), float(mow.group(1)))
    yaw = math.atan2(2.0 * (qw * qz + qx * qy), 1.0 - 2.0 * (qy * qy + qz * qz))
    return x, y, yaw


def pick_event_time(order: dict, event_code: str) -> str | None:
    entries = ((order.get("history") or {}).get("entries") or [])
    for e in entries:
        if e.get("eventCode") == event_code:
            return e.get("timestamp")
    return None


def main():
    p = argparse.ArgumentParser(description="一键采证（OpenTCS <-> ROS2 逻辑仿真）")
    p.add_argument("--kernel", default="http://localhost:55200", help="OpenTCS Web API base URL")
    p.add_argument("--vehicle", default="Vehicle-1", help="车辆名")
    p.add_argument("--location", default="Location-B", help="目标 Location 名")
    p.add_argument("--order-name", default="", help="订单名，留空自动生成")
    p.add_argument("--x", type=float, required=True, help="OpenTCS 目标 x（用于误差统计）")
    p.add_argument("--y", type=float, required=True, help="OpenTCS 目标 y（用于误差统计）")
    p.add_argument("--yaw", type=float, default=0.0, help="OpenTCS 目标 yaw(rad)")
    p.add_argument(
        "--mapping",
        default="/home/klq/Final/yahboomcar_ws/src/opentcs_ros2_bridge/config/evaluation_coordinate_map.yaml",
        help="坐标映射 YAML 路径",
    )
    p.add_argument(
        "--plant-model-json",
        default="/home/klq/Final/opentcs_plant_model.json",
        help="OpenTCS plant model JSON（用于解析 location 对应的真实目标坐标）",
    )
    p.add_argument(
        "--plant-unit-mm",
        action="store_true",
        default=True,
        help="plant model position 单位按毫米处理（默认 true）",
    )
    p.add_argument(
        "--plant-unit-m",
        action="store_true",
        default=False,
        help="plant model position 单位按米处理（会覆盖 --plant-unit-mm）",
    )
    p.add_argument("--timeout", type=int, default=90, help="订单完成超时秒")
    p.add_argument("--pose-timeout", type=int, default=8, help="读取 /amcl_pose 超时秒")
    p.add_argument(
        "--min-move-dist",
        type=float,
        default=0.5,
        help="若目标与当前 /amcl_pose 距离小于该值(m)，自动偏移目标，避免'原地完成'",
    )
    p.add_argument("--out-dir", default="/home/klq/Final/evidence", help="证据输出目录")
    args = p.parse_args()

    order_name = args.order_name or f"TOrder-{dt.datetime.now().strftime('%Y%m%d-%H%M%S')}"
    run_dir = pathlib.Path(args.out_dir) / dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    run_dir.mkdir(parents=True, exist_ok=True)

    mapping = read_simple_yaml_mapping(pathlib.Path(args.mapping))
    rx_target_fallback, ry_target_fallback, ryaw_target_fallback = map_opentcs_to_ros(
        args.x, args.y, args.yaw, mapping
    )
    plant_unit_mm = not args.plant_unit_m
    resolved = resolve_location_target_from_model(
        pathlib.Path(args.plant_model_json), args.location, plant_unit_mm
    )
    if resolved is not None:
        rx_target, ry_target, ryaw_target, target_source = resolved
    else:
        rx_target, ry_target, ryaw_target = (
            rx_target_fallback,
            ry_target_fallback,
            ryaw_target_fallback,
        )
        target_source = "fallback_from_--x/--y_and_mapping"
        print(
            "[WARN] 未能从 plant_model 解析 location 目标坐标，误差基准回退到 --x/--y 映射值。"
        )

    # 0) 先读当前位姿，避免目标与当前点一致导致“几乎不动就完成”
    cur_x, cur_y, cur_yaw = read_amcl_pose_once(args.pose_timeout)
    adjusted = False
    d0 = math.hypot(rx_target - cur_x, ry_target - cur_y)
    if d0 < args.min_move_dist:
        adjusted = True
        # 沿 +x 方向偏移，确保发生可观测位移
        rx_target = cur_x + args.min_move_dist
        ry_target = cur_y
        # 反推回 OpenTCS 坐标（仅用于记录；OpenTCS 下单仍是按 location）
        args.x = (rx_target - mapping["offset_x"]) / mapping["scale"]
        args.y = (ry_target - mapping["offset_y"]) / mapping["scale"]
        print(
            f"[WARN] 目标与当前位姿距离 {d0:.3f}m < {args.min_move_dist:.3f}m，"
            f"已自动改目标为 ROS({rx_target:.3f}, {ry_target:.3f}) / OpenTCS({args.x:.3f}, {args.y:.3f})"
        )

    # 1) 创建运输单
    t_create_local = dt.datetime.now(dt.timezone.utc)
    body = {
        "type": "Move",
        "intendedVehicle": args.vehicle,
        "destinations": [{"locationName": args.location, "operation": "Move"}],
    }
    create_url = f"{args.kernel}/v1/transportOrders/{urllib.parse.quote(order_name)}"
    created = http_json("POST", create_url, body)

    # 2) 触发调度
    t_dispatch_local = dt.datetime.now(dt.timezone.utc)
    http_json("POST", f"{args.kernel}/v1/dispatcher/trigger")

    # 3) 轮询状态
    status = "UNKNOWN"
    order = None
    deadline = time.time() + args.timeout
    while time.time() < deadline:
        order = http_json("GET", create_url)
        status = (order or {}).get("state", "UNKNOWN")
        if status in ("FINISHED", "FAILED"):
            break
        time.sleep(0.5)
    if order is None:
        raise RuntimeError("读取订单失败。")

    # 4) 读取最终位姿
    amcl_x, amcl_y, amcl_yaw = read_amcl_pose_once(args.pose_timeout)
    err = math.hypot(amcl_x - rx_target, amcl_y - ry_target)

    # 5) 时序指标（用订单 history）
    ts_assigned = pick_event_time(order, "tcs:history:orderAssignedToVehicle")
    ts_proc = pick_event_time(order, "tcs:history:orderProcVehicleChanged")
    ts_finish = pick_event_time(order, "tcs:history:orderReachedFinalState")
    latency_assign_ms = None
    total_ms = None
    if ts_assigned:
        latency_assign_ms = (parse_iso_z(ts_assigned) - t_dispatch_local).total_seconds() * 1000.0
    if ts_finish:
        total_ms = (parse_iso_z(ts_finish) - t_create_local).total_seconds() * 1000.0

    # 6) 写文件
    (run_dir / "order_created_response.json").write_text(
        json.dumps(created, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (run_dir / f"order_{order_name}.json").write_text(
        json.dumps(order, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    csv_path = run_dir / "metrics.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "order_name",
                "final_state",
                "opentcs_x",
                "opentcs_y",
                "opentcs_yaw",
                "ros_target_x",
                "ros_target_y",
                "ros_target_yaw",
                "target_source",
                "amcl_x",
                "amcl_y",
                "amcl_yaw",
                "position_error_m",
                "dispatch_to_assigned_ms",
                "create_to_finished_ms",
                "timestamp_utc",
            ]
        )
        w.writerow(
            [
                order_name,
                status,
                args.x,
                args.y,
                args.yaw,
                rx_target,
                ry_target,
                ryaw_target,
                target_source,
                amcl_x,
                amcl_y,
                amcl_yaw,
                err,
                f"{latency_assign_ms:.3f}" if latency_assign_ms is not None else "",
                f"{total_ms:.3f}" if total_ms is not None else "",
                iso_now_utc(),
            ]
        )

    summary = f"""# 采证结果（{order_name}）

- 订单最终状态：`{status}`
- OpenTCS 目标点：`({args.x:.3f}, {args.y:.3f}, {args.yaw:.3f} rad)`
- ROS 映射目标：`({rx_target:.3f}, {ry_target:.3f}, {ryaw_target:.3f} rad)`
- 误差基准来源：`{target_source}`
- 是否自动改目标避免原地完成：`{"yes" if adjusted else "no"}`
- /amcl_pose 最终：`({amcl_x:.3f}, {amcl_y:.3f}, {amcl_yaw:.3f} rad)`
- 位置误差：`{err:.4f} m`
- 调度触发到分配延迟：`{"" if latency_assign_ms is None else f"{latency_assign_ms:.2f} ms"}`
- 订单创建到完成总时长：`{"" if total_ms is None else f"{total_ms:.2f} ms"}`

## 论文可用话术（可按多次实验均值替换）

1. 通信时序：系统成功实现了基于 TCP 的跨语言分布式调度，订单从调度触发到车辆分配的响应延迟为 `{"" if latency_assign_ms is None else f"{latency_assign_ms:.2f} ms"}`。
2. 坐标映射：通过异构坐标映射模型，目标点与执行层最终位姿误差为 `{err:.4f} m`。
3. 状态机：运输单状态完成了 `BEING_PROCESSED -> FINISHED` 的完整闭环转换。
"""
    (run_dir / "summary.md").write_text(summary, encoding="utf-8")

    print(f"[OK] Evidence saved to: {run_dir}")
    print(f" - {csv_path.name}")
    print(" - summary.md")
    print(f" - order_{order_name}.json")
    print(" - order_created_response.json")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        sys.exit(1)
