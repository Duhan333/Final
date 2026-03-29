from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch_ros.actions import Node
from launch.substitutions import LaunchConfiguration


def _occupancy_grid_node(context, *_args, **_kwargs):
    """Humble 上可执行文件名为 cartographer_occupancy_grid_node；参数走 ROS2 parameters。"""
    use_sim = LaunchConfiguration('use_sim_time').perform(context).lower() in (
        'true', '1', 'yes',
    )
    res = float(LaunchConfiguration('resolution').perform(context))
    period = float(LaunchConfiguration('publish_period_sec').perform(context))
    return [
        Node(
            package='cartographer_ros',
            executable='cartographer_occupancy_grid_node',
            name='cartographer_occupancy_grid_node',
            output='screen',
            parameters=[
                {'use_sim_time': use_sim},
                {'resolution': res},
                {'publish_period_sec': period},
            ],
        ),
    ]


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument(
            'resolution',
            default_value='0.05',
            description='Resolution of a grid cell in the published occupancy grid',
        ),
        DeclareLaunchArgument(
            'publish_period_sec',
            default_value='1.0',
            description='OccupancyGrid publishing period',
        ),
        DeclareLaunchArgument(
            'use_sim_time',
            default_value='false',
            description='Use simulation (Gazebo) clock if true',
        ),
        OpaqueFunction(function=_occupancy_grid_node),
    ])
