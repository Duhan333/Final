#!/usr/bin/env python3
"""
OpenTCS 平面坐标 → ROS map 平面坐标（米、与 map 原点一致）。

用法:
  from opentcs_ros2_bridge.coordinate_mapping import load_mapping, opentcs_to_ros_xy_yaw
  cfg = load_mapping('.../evaluation_coordinate_map.yaml')
  rx, ry = opentcs_to_ros_xy(1.0, 2.0, cfg)
"""
from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Dict, Tuple, Union

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None  # type: ignore


def load_mapping(path: Union[str, Path]) -> Dict[str, Any]:
    path = Path(path)
    text = path.read_text(encoding='utf-8')
    if yaml is None:
        raise RuntimeError('需要 PyYAML: pip install pyyaml 或 apt install python3-yaml')
    data = yaml.safe_load(text)
    if not isinstance(data, dict):
        raise ValueError('mapping YAML 根节点须为 dict')
    return data


def opentcs_to_ros_xy(opentcs_x: float, opentcs_y: float, cfg: Dict[str, Any]) -> Tuple[float, float]:
    s = float(cfg.get('scale', 1.0))
    ox = float(cfg.get('offset_x', 0.0))
    oy = float(cfg.get('offset_y', 0.0))
    return opentcs_x * s + ox, opentcs_y * s + oy


def opentcs_to_ros_yaw(yaw_opentcs: float, cfg: Dict[str, Any]) -> float:
    """ROS map 下绕 z 正向角 = OpenTCS yaw + yaw_offset_ros_minus_opentcs（弧度）。"""
    off = float(cfg.get('yaw_offset_ros_minus_opentcs', 0.0))
    return yaw_opentcs + off


def opentcs_to_ros_xy_yaw(
    opentcs_x: float, opentcs_y: float, yaw_opentcs: float, cfg: Dict[str, Any]
) -> Tuple[float, float, float]:
    rx, ry = opentcs_to_ros_xy(opentcs_x, opentcs_y, cfg)
    ryaw = opentcs_to_ros_yaw(yaw_opentcs, cfg)
    return rx, ry, ryaw


# 无 YAML 时的默认（1:1，无旋转平移）
DEFAULT_MAPPING: Dict[str, Any] = {
    'scale': 1.0,
    'offset_x': 0.0,
    'offset_y': 0.0,
    'yaw_offset_ros_minus_opentcs': 0.0,
}


def main_cli():
    """python3 -m opentcs_ros2_bridge.coordinate_mapping <yaml> x y [yaw]"""
    import sys

    if len(sys.argv) < 4:
        print('Usage: coordinate_mapping.py <yaml> x y [yaw_rad]', file=sys.stderr)
        sys.exit(1)
    cfg = load_mapping(sys.argv[1])
    x, y = float(sys.argv[2]), float(sys.argv[3])
    yaw = float(sys.argv[4]) if len(sys.argv) > 4 else 0.0
    rx, ry, ryaw = opentcs_to_ros_xy_yaw(x, y, yaw, cfg)
    print(f'ROS map: x={rx:.6f} y={ry:.6f} yaw={ryaw:.6f} rad ({math.degrees(ryaw):.3f} deg)')


if __name__ == '__main__':
    main_cli()
