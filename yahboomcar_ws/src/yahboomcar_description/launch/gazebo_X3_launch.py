# Copyright 2024
# Launch Gazebo with ROSMASTER X3 model (diff_drive + bridge for Nav2)

import os

from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.actions import OpaqueFunction
from launch.actions import SetEnvironmentVariable
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration

from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource

from launch_ros.actions import Node


def _include_gz_sim(context):
    """根据 headless 拼接 gz_args：虚拟机 GUI 闪烁时可 -s 只跑服务端。"""
    pkg_yahboomcar = get_package_share_directory('yahboomcar_description')
    world_file = os.path.join(pkg_yahboomcar, 'worlds', 'yahboomcar_empty.world')
    headless = LaunchConfiguration('headless').perform(context).lower() in ('true', '1', 'yes')
    headless_rendering = (
        LaunchConfiguration('headless_rendering').perform(context).lower() in ('true', '1', 'yes')
    )
    # -r 启动即运行；-s 仅仿真服务器，不打开 Gazebo 图形界面（物理与传感器仍工作）
    # --headless-rendering：即使在服务端模式下也显式使用 headless 渲染路径（WSL/部分显卡驱动更稳）
    gz_args = (
        f'-r -s --headless-rendering {world_file}'
        if headless and headless_rendering
        else (f'-r -s {world_file}' if headless else f'-r {world_file}')
    )
    pkg_ros_gz_sim = get_package_share_directory('ros_gz_sim')
    gz_sim_launch = os.path.join(pkg_ros_gz_sim, 'launch', 'gz_sim.launch.py')
    return [
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(gz_sim_launch),
            launch_arguments={'gz_args': gz_args}.items(),
        ),
    ]


def _robot_state_publisher(context, *_args, **_kwargs):
    """直接读 URDF 字符串，避免依赖 PATH 中的 xacro 可执行文件（未 source ROS 时会报 file not found）。"""
    model_path = LaunchConfiguration('model').perform(context)
    if not os.path.isfile(model_path):
        raise FileNotFoundError(
            f'找不到机器人模型文件: {model_path!r}。请确认已 colcon 安装 yahboomcar_description，'
            '或传 model:=<绝对路径>。若使用需宏展开的 .xacro，请先 xacro 生成 URDF 再指向该文件。'
        )
    with open(model_path, 'r', encoding='utf-8') as f:
        robot_description = f.read()
    use_sim_time = LaunchConfiguration('use_sim_time').perform(context).lower() in (
        'true', '1', 'yes',
    )
    rsp = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        output='screen',
        parameters=[
            {'use_sim_time': use_sim_time},
            {'robot_description': robot_description},
        ],
    )
    # 与 rsp 共用 URDF 字符串；麦轮为 continuous，需 /joint_states 才有轮子 TF（默认零位即可消 RViz 报错）
    jsp = Node(
        package='joint_state_publisher',
        executable='joint_state_publisher',
        output='screen',
        parameters=[
            {'use_sim_time': use_sim_time},
            {'robot_description': robot_description},
        ],
    )
    return [rsp, jsp]


def _gz_odom_scan_relays(context, *_args, **_kwargs):
    """gazebo_topic_relay 与 gz_laser_scan_relay 共用一套时间策略，避免 launch 与代码默认值不一致。"""
    world_name = 'yahboomcar_world'
    default_gz_lidar_topic = (
        f'/world/{world_name}/model/yahboomcar/link/laser_link/sensor/lidar/scan'
    )
    use_sim_time = LaunchConfiguration('use_sim_time').perform(context).lower() in (
        'true', '1', 'yes',
    )
    sync = LaunchConfiguration('sync_odom_stamp_to_clock').perform(context).lower() in (
        'true', '1', 'yes',
    )
    gz_lidar_topic = LaunchConfiguration('gz_lidar_topic').perform(context)
    if not (gz_lidar_topic or '').strip():
        gz_lidar_topic = default_gz_lidar_topic

    relay = Node(
        package='yahboomcar_description',
        executable='gazebo_topic_relay',
        parameters=[
            {'use_sim_time': use_sim_time},
            {'publish_odom_tf': True},
            {'max_odom_clock_skew_sec': 0.0},
            {'sync_odom_stamp_to_clock': sync},
        ],
        output='screen',
    )
    scan_relay = Node(
        package='yahboomcar_description',
        executable='gz_laser_scan_relay',
        parameters=[
            {'use_sim_time': use_sim_time},
            {'gz_scan_topic': gz_lidar_topic},
            {'output_topic': '/scan'},
            {'frame_id': 'laser_link'},
            {'odom_topic': '/odom'},
            {'align_scan_stamp_to_odom': True},
            # True：/scan.stamp = 最近 /odom.header（与已发布 odom TF 同拍）；勿用 now() 以免 stamp 晚于 TF
            {'scan_stamp_use_sim_time': True},
        ],
        output='screen',
    )
    return [relay, scan_relay]


def generate_launch_description():
    use_sim_time = LaunchConfiguration('use_sim_time', default='true')
    pkg_yahboomcar = get_package_share_directory('yahboomcar_description')
    # 工作机上常见有两套 overlay（~/Final/install 与 ~/Final/yahboomcar_ws/install）；
    # 若 model:// 命中旧 overlay，会导致传感器配置与当前源码不一致。
    # 这里优先固定到本仓库工作空间安装目录，避免加载错模型。
    ws_share = os.path.expanduser('~/Final/yahboomcar_ws/install/yahboomcar_description/share/yahboomcar_description')
    if os.path.isdir(ws_share):
        models_dir = os.path.join(ws_share, 'models')
        worlds_dir = os.path.join(ws_share, 'worlds')
    else:
        models_dir = os.path.join(pkg_yahboomcar, 'models')
        worlds_dir = os.path.join(pkg_yahboomcar, 'worlds')
    # 须与 yahboomcar_empty.world 中 <world name="..."> 一致，供 LiDAR 桥接话题名
    world_name = 'yahboomcar_world'
    default_gz_lidar_topic = f'/world/{world_name}/model/yahboomcar/link/laser_link/sensor/lidar/scan'
    gz_lidar_topic = LaunchConfiguration('gz_lidar_topic', default=default_gz_lidar_topic)
    default_model_path = os.path.join(pkg_yahboomcar, 'urdf', 'yahboomcar_X3.urdf')

    # Bridge: Gazebo <-> ROS2（仿真时钟 / cmd_vel / odom / lidar）
    bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        arguments=[
            # 仿真时间，避免 Nav2 use_sim_time 与 TF 时间戳不一致（TF_OLD_DATA）
            '/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock',
            '/model/yahboomcar/cmd_vel@geometry_msgs/msg/Twist@gz.msgs.Twist',
            '/model/yahboomcar/odometry@nav_msgs/msg/Odometry@gz.msgs.Odometry',
            # GZ -> ROS：长话题名上的 LaserScan，再由 gz_laser_scan_relay 转到 /scan
            [gz_lidar_topic, '@sensor_msgs/msg/LaserScan[gz.msgs.LaserScan'],
        ],
        parameters=[{'use_sim_time': use_sim_time}],
        output='screen',
    )

    libgl_software = LaunchConfiguration('libgl_software', default='false')
    fix_qt_x11 = LaunchConfiguration('fix_qt_x11', default='false')

    return LaunchDescription([
        DeclareLaunchArgument(
            'headless',
            default_value='false',
            description='true=仅启动 Gazebo 仿真服务器（gz sim -s），不打开 3D 窗口。'
                        '虚拟机里 GUI 闪烁、黑屏、看不见模型时推荐；用 RViz 看地图与激光。',
        ),
        DeclareLaunchArgument(
            'headless_rendering',
            default_value='true',
            description='true=在 headless:=true 时追加 ign gazebo --headless-rendering（更稳定但可能影响渲染质量）。'
                        '如果你环境下 headless-rendering 反而更不稳定，可以传 headless_rendering:=false 关闭。',
        ),
        DeclareLaunchArgument(
            'libgl_software',
            default_value='false',
            description='true=设置 LIBGL_ALWAYS_SOFTWARE=1（仅无 3D 的虚拟机需要）。'
                        '已开启虚拟机 3D 加速时必须保持 false，否则 EGL 会报 '
                        '"Not allowed to force software rendering when API selects hardware".',
        ),
        DeclareLaunchArgument(
            'fix_qt_x11',
            default_value='false',
            description='true=设置 QT_QPA_PLATFORM=xcb、QT_X11_NO_MITSHM=1，部分 Wayland/虚拟机下可减轻 Gazebo 窗口闪烁（仍异常时请用 headless:=true）。',
        ),
        SetEnvironmentVariable(
            name='LIBGL_ALWAYS_SOFTWARE',
            value='1',
            condition=IfCondition(libgl_software),
        ),
        SetEnvironmentVariable(
            name='QT_QPA_PLATFORM',
            value='xcb',
            condition=IfCondition(fix_qt_x11),
        ),
        SetEnvironmentVariable(
            name='QT_X11_NO_MITSHM',
            value='1',
            condition=IfCondition(fix_qt_x11),
        ),
        # 显式固定 Gazebo 资源搜索路径，避免 model://yahboomcar_X3 被其它旧安装目录“抢先命中”
        SetEnvironmentVariable(name='IGN_GAZEBO_RESOURCE_PATH', value=f'{models_dir}:{worlds_dir}'),
        SetEnvironmentVariable(name='GZ_SIM_RESOURCE_PATH', value=f'{models_dir}:{worlds_dir}'),
        DeclareLaunchArgument('use_sim_time', default_value='true',
                              description='Use sim time'),
        DeclareLaunchArgument(
            'sync_odom_stamp_to_clock',
            default_value='true',
            description='true：/odom 与 odom→base_footprint TF 使用 get_clock().now()；'
                        'false：沿用 Gazebo 里程计消息时间戳。/scan 始终与最近 /odom.header 对齐。',
        ),
        DeclareLaunchArgument(
            'gz_lidar_topic',
            default_value=default_gz_lidar_topic,
            description='Gazebo LaserScan topic to bridge/relay to /scan (e.g. /lidar).',
        ),
        DeclareLaunchArgument(
            'model',
            default_value=default_model_path,
            description='X3 URDF 路径（默认 share 下 yahboomcar_X3.urdf；纯 URDF 无需 xacro）。',
        ),
        OpaqueFunction(function=_include_gz_sim),
        bridge,
        OpaqueFunction(function=_gz_odom_scan_relays),
        # 与 URDF 一致发布 base_footprint→base_link→laser_link…；读文件而非调用 xacro，避免未 source 时找不到 xacro
        OpaqueFunction(function=_robot_state_publisher),
    ])
