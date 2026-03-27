from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def _launch_bridge(context, *args, **kwargs):
    """将 use_sim_time 转为 bool，必须与 Nav2 / Gazebo 一致，否则 NavigateToPose 常被拒绝。"""
    raw = LaunchConfiguration('use_sim_time').perform(context)
    use_sim = str(raw).lower() in ('true', '1', 'yes')

    return [
        Node(
            package='opentcs_ros2_bridge',
            executable='bridge_node',
            name='opentcs_ros2_bridge',
            output='screen',
            parameters=[{
                'tcp_port': 9090,
                'action_name': 'navigate_to_pose',
                'map_frame': 'map',
                # 须为绝对话题名；'amcl_pose' 会变成 /opentcs_ros2_bridge/amcl_pose，收不到 AMCL 数据，
                # OpenTCS 端 TCP read 会每 5s 超时误判失败。
                'pose_topic': '/amcl_pose',
                'send_pose_period_sec': 0.5,
                'use_sim_time': use_sim,
            }],
        ),
    ]


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument(
            'use_sim_time',
            default_value='true',
            description='必须与 navigation_dwa_launch 相同：Gazebo 默认 true；无 /clock 桌面联调传 false',
        ),
        OpaqueFunction(function=_launch_bridge),
    ])
