#!/usr/bin/env python3
"""
逻辑仿真评估启动文件（多机隔离版）。
配置 VEHICLES 列表，一键拉起所有车辆的 RSP, JSP, Logic Sim 和 Bridge 节点。
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

# ==========================================
# 🚀 核心配置：在这里定义你要同时跑的车辆 
# ==========================================
VEHICLES = [
    # 车1：端口 9091，出生在 (0.0, 0.0)
    {'name': 'vehicle_1', 'port': 9091, 'init_x': 0.0, 'init_y': 0.0, 'init_yaw': 0.0},
    # 车2：端口 9092，出生在 (0.0, 1.5) 以防止重叠
    {'name': 'vehicle_2', 'port': 9092, 'init_x': 0.0, 'init_y': 1.5, 'init_yaw': 0.0},
    # 车3：如果有需要，解开下面这行的注释即可
    # {'name': 'vehicle_3', 'port': 9093, 'init_x': 0.0, 'init_y': -1.5, 'init_yaw': 0.0},
]


def _build_multi_robot_nodes(context, *args, **kwargs):
    pkg_desc = get_package_share_directory('yahboomcar_description')
    model_path = LaunchConfiguration('model').perform(context)
    if not os.path.isfile(model_path):
        raise FileNotFoundError(f'找不到 URDF: {model_path}')
        
    with open(model_path, 'r', encoding='utf-8') as f:
        robot_description = f.read()
        
    use_sim = LaunchConfiguration('use_sim_time').perform(context).lower() in ('true', '1', 'yes')
    
    nodes_to_start = []

    # 循环遍历每一辆车，分配专属节点与命名空间
    for v in VEHICLES:
        v_name = v['name']
        v_port = v['port']
        v_prefix = v_name + '/' # 用于 TF 的隔离前缀

        # 1. Robot State Publisher (TF 发布)
        rsp = Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            namespace=v_name,
            output='screen',
            parameters=[
                {'use_sim_time': use_sim},
                {'robot_description': robot_description},
                {'frame_prefix': v_prefix}  # 关键：让 base_link 变成 vehicle_x/base_link
            ],
        )
        
        # 2. Joint State Publisher
        jsp = Node(
            package='joint_state_publisher',
            executable='joint_state_publisher',
            namespace=v_name,
            output='screen',
            parameters=[
                {'use_sim_time': use_sim},
                {'robot_description': robot_description},
            ],
        )

        # 3. 逻辑仿真小车节点
        sim_node = Node(
            package='opentcs_ros2_bridge',
            executable='logic_sim_robot',
            name='logic_sim_robot',
            namespace=v_name,
            output='screen',
            parameters=[
                {'use_sim_time': use_sim},
                {'linear_speed': 0.5},
                {'angular_speed': 0.9},
                {'map_frame': 'map'},                        # map 是大家共用的全局坐标系
                {'odom_frame': v_prefix + 'odom'},           # 里程计独立隔离
                {'base_frame': v_prefix + 'base_footprint'}, # 底盘独立隔离
                {'action_name': 'navigate_to_pose'},         # 相对命名，结合 namespace 会变成 /vehicle_x/navigate_to_pose
                {'publish_amcl_topic': 'amcl_pose'},         # 相对命名
                {'publish_pose_stamped_topic': 'pose'},
                {'initial_x': v['init_x']},                  # 错开出生点
                {'initial_y': v['init_y']},
                {'initial_yaw': v['init_yaw']},
            ],
        )

        # 4. OpenTCS TCP 通信桥接节点
        bridge_node = Node(
            package='opentcs_ros2_bridge',
            executable='bridge_node',
            name='opentcs_ros2_bridge',
            namespace=v_name,
            output='screen',
            parameters=[
                {'use_sim_time': use_sim},
                {'tcp_port': v_port},                        # 各车用自己的端口监听
                {'action_name': 'navigate_to_pose'},
                {'map_frame': 'map'},
                {'pose_topic': 'amcl_pose'},                 # 相对命名
                {'send_pose_period_sec': 0.5},
            ],
        )

        nodes_to_start.extend([rsp, jsp, sim_node, bridge_node])

    return nodes_to_start


def generate_launch_description():
    pkg_desc = get_package_share_directory('yahboomcar_description')
    default_model = os.path.join(pkg_desc, 'urdf', 'yahboomcar_X3.urdf')

    return LaunchDescription([
        DeclareLaunchArgument('use_sim_time', default_value='false'),
        DeclareLaunchArgument('model', default_value=default_model),
        # 集中生成所有车辆节点的 OpaqueFunction
        OpaqueFunction(function=_build_multi_robot_nodes),
    ])