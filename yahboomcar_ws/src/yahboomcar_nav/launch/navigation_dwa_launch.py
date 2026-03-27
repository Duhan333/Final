import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.actions import IncludeLaunchDescription
from launch.actions import OpaqueFunction
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration

from launch_ros.actions import Node


def _amcl_initial_pose_node(context, *args, **kwargs):
    """仿真下用 /initialpose 带协方差初始化 AMCL（避免 Nav2 内置 set_initial_pose 全 0 协方差）。"""
    raw_auto = LaunchConfiguration('auto_initial_pose').perform(context)
    if str(raw_auto).lower() not in ('true', '1', 'yes'):
        return []
    use_sim = str(LaunchConfiguration('use_sim_time').perform(context)).lower() in ('true', '1', 'yes')
    return [
        Node(
            package='yahboomcar_nav',
            executable='amcl_initial_pose_publisher',
            name='amcl_initial_pose_publisher',
            output='screen',
            # 只传 use_sim_time，避免与节点内 declare_parameter 重复（曾导致 ParameterAlreadyDeclaredException）
            parameters=[
                {'use_sim_time': use_sim},
                # 必须等 /scan：无激光时发 /initialpose，AMCL 往往仍不发布 map→odom，global_costmap
                # 会永久报「Invalid frame map」。先 T1 再 T2 或 T2 先于 T1 稍后起激光均可恢复。
                {'wait_for_scan': True},
                {'delay_after_scan_sec': 8.0},
                # now：与仿真时钟一致，减轻 AMCL 对 base_footprint→odom 的 extrapolation 告警
                {'stamp_mode': 'now'},
                {'publish_count': 3},
                {'publish_period_sec': 1.0},
            ],
        ),
    ]


def generate_launch_description():
    package_path = get_package_share_directory('yahboomcar_nav')
    nav2_bringup_dir = get_package_share_directory('nav2_bringup')

    use_sim_time = LaunchConfiguration('use_sim_time', default='true')
    # 须与 nav2_bringup 一致用大写 True/False：其 localization/navigation 里用
    # PythonExpression(['not ', use_composition])，小写 'true' 会变成非法 Python「not true」。
    use_composition = LaunchConfiguration('use_composition', default='True')
    map_yaml_path = LaunchConfiguration(
        'map', default=os.path.join(package_path, 'maps', 'yahboomcar.yaml'))
    nav2_param_path = LaunchConfiguration('params_file', default=os.path.join(
        package_path, 'params', 'dwa_nav_params.yaml'))

    return LaunchDescription([
        DeclareLaunchArgument(
            'use_sim_time',
            default_value='true',
            description='须与 T1/RViz/桥接一致：Gazebo 仿真默认 true；真车无 /clock 时传 false'),
        DeclareLaunchArgument(
            'use_composition',
            default_value='True',
            description='Nav2 默认 True（单进程 component_container）。若 AMCL 始终不发布 map→odom、'
                        'global_costmap 报 map 不存在，可改为 False（首字母大写）让 amcl/map_server 独立进程运行；'
                        '勿用小写 true/false，否则 Nav2 的 PythonExpression 会报 name true/false is not defined。'),
        DeclareLaunchArgument(
            'launch_fake_odom',
            default_value='false',
            description='If true, publish /odom + odom->base_footprint TF (for Nav2 without Gazebo). '
                        'Set false when using gazebo_X3_launch.py (Gazebo already publishes odom TF).',
        ),
        DeclareLaunchArgument('map', default_value=map_yaml_path,
                              description='Full path to map file to load'),
        DeclareLaunchArgument('params_file', default_value=nav2_param_path,
                              description='Full path to param file to load'),
        DeclareLaunchArgument(
            'auto_initial_pose',
            default_value='true',
            description='true：启动 amcl_initial_pose_publisher，在收到 /scan 后发布带协方差的 '
                        '/initialpose（替代 Nav2 内置 set_initial_pose 的零协方差问题）。'
                        '纯 RViz 手动给位姿时可设 false。',
        ),

        OpaqueFunction(function=_amcl_initial_pose_node),

        Node(
            package='yahboomcar_nav',
            executable='fake_odom_tf',
            name='fake_odom_tf',
            condition=IfCondition(LaunchConfiguration('launch_fake_odom')),
            parameters=[{'use_sim_time': use_sim_time}],
            output='screen',
        ),

        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                [nav2_bringup_dir, '/launch', '/bringup_launch.py']),
            launch_arguments={
                'map': map_yaml_path,
                'use_sim_time': use_sim_time,
                'params_file': nav2_param_path,
                'use_composition': use_composition,
            }.items(),
        ),
    ])
