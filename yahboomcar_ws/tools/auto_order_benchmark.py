#!/usr/bin/env python3
"""
自动随机下单采样脚本（替代手动 T3）。

功能：
1) 从 OpenTCS 当前 plant model 读取可用 location/point
2) 随机选择目标（支持最小距离约束）
3) 自动创建 transport order + trigger dispatcher
4) 轮询到 FINISHED/FAILED
5) 读取 /amcl_pose，计算终点误差和时延
6) 输出每轮明细和汇总（CSV + Markdown）

前提：
- T1: ros2 launch opentcs_ros2_bridge evaluation_launch.py 正在运行
- T2: opentcs-kernel:run 正在运行
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import math
import pathlib
import random
import re
import statistics
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request


def parse_iso_z(ts: str) -> dt.datetime:
    s = ts.strip().replace("Z", "+00:00")
    m = re.match(r"^(.*\.\d{6})\d+([+-]\d{2}:\d{2})$", s)
    if m:
        s = m.group(1) + m.group(2)
    return dt.datetime.fromisoformat(s)


def http_json(method: str, url: str, payload: dict | None = None):
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


def read_amcl_pose_once(timeout_sec: int) -> tuple[float, float, float]:
    cmd = "ros2 topic echo /amcl_pose --once"
    cp = subprocess.run(
        cmd, shell=True, check=True, capture_output=True, text=True, timeout=timeout_sec
    )
    txt = cp.stdout
    mx = re.search(r"position:\s*\n\s*x:\s*([\-0-9.eE]+)", txt)
    my = re.search(r"position:\s*\n(?:.*\n)*?\s*y:\s*([\-0-9.eE]+)", txt)
    mox = re.search(r"orientation:\s*\n\s*x:\s*([\-0-9.eE]+)", txt)
    moy = re.search(r"orientation:\s*\n(?:.*\n)*?\s*y:\s*([\-0-9.eE]+)", txt)
    moz = re.search(r"orientation:\s*\n(?:.*\n)*?\s*z:\s*([\-0-9.eE]+)", txt)
    mow = re.search(r"orientation:\s*\n(?:.*\n)*?\s*w:\s*([\-0-9.eE]+)", txt)
    if not all([mx, my, mox, moy, moz, mow]):
        raise RuntimeError("无法解析 /amcl_pose 输出，请确认 evaluation_launch 正在运行。")
    x = float(mx.group(1))
    y = float(my.group(1))
    qx, qy, qz, qw = float(mox.group(1)), float(moy.group(1)), float(moz.group(1)), float(mow.group(1))
    yaw = math.atan2(2.0 * (qw * qz + qx * qy), 1.0 - 2.0 * (qy * qy + qz * qz))
    return x, y, yaw


def _unit_to_meter(v: float, mm: bool) -> float:
    return v / 1000.0 if mm else v


def build_location_targets(plant: dict, plant_unit_mm: bool):
    points = {p.get("name"): p for p in plant.get("points", []) if isinstance(p, dict)}
    out = []
    for loc in plant.get("locations", []):
        if not isinstance(loc, dict):
            continue
        name = loc.get("name")
        links = loc.get("links") or []
        if not name or not links:
            continue
        p_name = links[0].get("pointName")
        p = points.get(p_name, {})
        pos = p.get("position") or {}
        x = _unit_to_meter(float(pos.get("x", 0.0)), plant_unit_mm)
        y = _unit_to_meter(float(pos.get("y", 0.0)), plant_unit_mm)
        yaw_deg = float(p.get("vehicleOrientationAngle", 0.0))
        out.append(
            {
                "location": name,
                "point": p_name,
                "x": x,
                "y": y,
                "yaw": math.radians(yaw_deg),
            }
        )
    return out


def pick_event_time(order: dict, event_code: str):
    entries = ((order.get("history") or {}).get("entries") or [])
    for e in entries:
        if e.get("eventCode") == event_code:
            return e.get("timestamp")
    return None


def main():
    ap = argparse.ArgumentParser(description="自动随机下单采样（OpenTCS -> ROS2）")
    ap.add_argument("--kernel", default="http://localhost:55200")
    ap.add_argument("--vehicle", default="Vehicle-1")
    ap.add_argument("--trials", type=int, default=10)
    ap.add_argument("--timeout", type=int, default=90, help="每单超时秒")
    ap.add_argument("--pose-timeout", type=int, default=10)
    ap.add_argument("--min-dist", type=float, default=0.8, help="目标点与当前 /amcl_pose 最小距离(m)")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--plant-unit-mm", action="store_true", default=True)
    ap.add_argument("--plant-unit-m", action="store_true", default=False)
    ap.add_argument("--out-dir", default="/home/klq/Final/evidence")
    args = ap.parse_args()

    random.seed(args.seed)
    plant_unit_mm = not args.plant_unit_m

    plant = http_json("GET", f"{args.kernel}/v1/plantModel")
    if not isinstance(plant, dict):
        raise RuntimeError("无法读取 /v1/plantModel")
    targets = build_location_targets(plant, plant_unit_mm=plant_unit_mm)
    if len(targets) == 0:
        raise RuntimeError("plant model 中未找到可用 location->point 目标。")

    run_dir = pathlib.Path(args.out_dir) / dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    run_dir.mkdir(parents=True, exist_ok=True)

    rows = []
    for i in range(1, args.trials + 1):
        cur_x, cur_y, _ = read_amcl_pose_once(args.pose_timeout)
        candidates = [
            t
            for t in targets
            if math.hypot(t["x"] - cur_x, t["y"] - cur_y) >= args.min_dist
        ]
        if not candidates:
            # 没有足够远的点时，退化为全体随机（并记录）
            candidates = targets[:]
        tgt = random.choice(candidates)
        order_name = f"TOrder-BENCH-{dt.datetime.now().strftime('%Y%m%d-%H%M%S')}-{i}"
        order_url = f"{args.kernel}/v1/transportOrders/{urllib.parse.quote(order_name)}"

        t_create = dt.datetime.now(dt.timezone.utc)
        create_resp = http_json(
            "POST",
            order_url,
            {
                "type": "Move",
                "intendedVehicle": args.vehicle,
                "destinations": [{"locationName": tgt["location"], "operation": "Move"}],
            },
        )
        t_dispatch = dt.datetime.now(dt.timezone.utc)
        http_json("POST", f"{args.kernel}/v1/dispatcher/trigger")

        status = "UNKNOWN"
        order = None
        deadline = time.time() + args.timeout
        last_trigger_ts = 0.0
        tried_immediate = False
        while time.time() < deadline:
            now_ts = time.time()
            # 持续触发调度器，避免订单长期停在 DISPATCHABLE
            if now_ts - last_trigger_ts >= 1.0:
                try:
                    http_json("POST", f"{args.kernel}/v1/dispatcher/trigger")
                except Exception:
                    pass
                last_trigger_ts = now_ts
            order = http_json("GET", order_url)
            status = (order or {}).get("state", "UNKNOWN")
            if status in ("FINISHED", "FAILED"):
                break
            if status == "DISPATCHABLE" and not tried_immediate:
                tried_immediate = True
                try:
                    http_json("POST", f"{order_url}/immediateAssignment")
                except Exception:
                    # DISPATCHABLE 竞争窗口里偶发失败可忽略，下一轮继续靠 dispatcher 触发
                    pass
            time.sleep(0.5)
        if order is None:
            raise RuntimeError(f"[trial {i}] 读取订单失败")
        if status not in ("FINISHED", "FAILED"):
            status = "TIMEOUT"

        ax, ay, ayaw = read_amcl_pose_once(args.pose_timeout)
        err = math.hypot(ax - tgt["x"], ay - tgt["y"])

        ts_assigned = pick_event_time(order, "tcs:history:orderAssignedToVehicle")
        ts_finish = pick_event_time(order, "tcs:history:orderReachedFinalState")
        d_assign_ms = (
            (parse_iso_z(ts_assigned) - t_dispatch).total_seconds() * 1000.0 if ts_assigned else None
        )
        d_total_ms = (
            (parse_iso_z(ts_finish) - t_create).total_seconds() * 1000.0 if ts_finish else None
        )

        rows.append(
            {
                "trial": i,
                "order_name": order_name,
                "location": tgt["location"],
                "point": tgt["point"],
                "target_x": tgt["x"],
                "target_y": tgt["y"],
                "amcl_x": ax,
                "amcl_y": ay,
                "amcl_yaw": ayaw,
                "error_m": err,
                "assign_latency_ms": d_assign_ms,
                "total_ms": d_total_ms,
                "final_state": status,
            }
        )
        (run_dir / f"{order_name}.json").write_text(json.dumps(order, ensure_ascii=False, indent=2), encoding="utf-8")
        (run_dir / f"{order_name}_created.json").write_text(
            json.dumps(create_resp, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    csv_path = run_dir / "benchmark_metrics.csv"
    headers = list(rows[0].keys()) if rows else []
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=headers)
        w.writeheader()
        for r in rows:
            w.writerow(r)

    ok_rows = [r for r in rows if r["final_state"] == "FINISHED"]
    err_vals = [r["error_m"] for r in ok_rows]
    lat_vals = [r["assign_latency_ms"] for r in ok_rows if r["assign_latency_ms"] is not None]
    total_vals = [r["total_ms"] for r in ok_rows if r["total_ms"] is not None]
    summary = {
        "trials": args.trials,
        "finished_count": len(ok_rows),
        "failed_count": len(rows) - len(ok_rows),
        "error_mean_m": statistics.mean(err_vals) if err_vals else None,
        "error_std_m": statistics.pstdev(err_vals) if len(err_vals) > 1 else 0.0 if err_vals else None,
        "assign_latency_mean_ms": statistics.mean(lat_vals) if lat_vals else None,
        "total_duration_mean_ms": statistics.mean(total_vals) if total_vals else None,
    }
    (run_dir / "benchmark_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    err_mean = "" if summary["error_mean_m"] is None else f"{summary['error_mean_m']:.4f} m"
    err_std = "" if summary["error_std_m"] is None else f"{summary['error_std_m']:.4f} m"
    lat_mean = (
        "" if summary["assign_latency_mean_ms"] is None else f"{summary['assign_latency_mean_ms']:.2f} ms"
    )
    total_mean = (
        "" if summary["total_duration_mean_ms"] is None else f"{summary['total_duration_mean_ms']:.2f} ms"
    )
    md = [
        f"# 自动随机下单采样结果（{dt.datetime.now().isoformat()}）",
        "",
        f"- 试验次数：`{args.trials}`",
        f"- 成功(FINISHED)：`{summary['finished_count']}`",
        f"- 失败：`{summary['failed_count']}`",
        f"- 平均误差：`{err_mean}`",
        f"- 误差标准差：`{err_std}`",
        f"- 平均分配延迟：`{lat_mean}`",
        f"- 平均完成时长：`{total_mean}`",
        "",
        "## 产出文件",
        "- benchmark_metrics.csv",
        "- benchmark_summary.json",
        "- 每轮订单 JSON（含 history）",
    ]
    (run_dir / "benchmark_summary.md").write_text("\n".join(md), encoding="utf-8")

    # 默认不在控制台打印，避免干扰批量采样；结果均已写入 run_dir。


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        sys.exit(1)
