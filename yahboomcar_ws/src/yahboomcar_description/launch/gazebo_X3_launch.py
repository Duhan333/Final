# Copyright 2024
# Launch Gazebo with ROSMASTER X3 model (diff_drive + bridge for Nav2)

import os

from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.actions import LogInfo
from launch.actions import OpaqueFunction
from launch.actions import SetEnvironmentVariable
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration

from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource

from launch_ros.actions import Node


def _detect_wsl():
    """WSL1/WSL2：宿主图形栈经 WSLg 转发时 Ogre 常踩 GL 驱动坑，默认开软件光栅 + Qt 修复。"""
    return bool(os.environ.get('WSL_DISTRO_NAME') or os.environ.get('WSL_INTEROP'))


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
    # Humble 的 joint_state_publisher：未传 URDF 路径时会订阅 /robot_description 话题，而 RSP 默认不发该话题 → 永远
    # Waiting...；麦轮 continuous 需 /joint_states 才更新轮子的 TF。
    jsp = Node(
        package='joint_state_publisher',
        executable='joint_state_publisher',
        output='screen',
        arguments=[model_path],
        parameters=[{'use_sim_time': use_sim_time}],
    )
    return [rsp, jsp]


def _gz_parameter_bridge(context, *_args, **_kwargs):
    """Gazebo 传输层激光话题名须与 `ign topic -l` 一致；桥接后仅发布到内部 ROS 话题，对外 /scan 由 gz_laser_scan_relay 写 frame_id 与 stamp。"""
    default_lidar = '/scan'
    topic = LaunchConfiguration('gz_lidar_topic').perform(context).strip()
    if not topic:
        topic = default_lidar
    raw_ros = LaunchConfiguration('ros_gz_laser_raw_topic').perform(context).strip()
    if not raw_ros:
        raw_ros = '/gz_bridge/scan_raw'
    lidar_arg = f'{topic}@sensor_msgs/msg/LaserScan[gz.msgs.LaserScan'
    # 桥接器必须保持 use_sim_time=false：若与 launch 同步为 true，会等 /clock 才推进时间，
    # 而 /clock 又由本进程从 Gazebo 转出 → 死锁，表现为 /clock 永不出现、ros2 topic echo 无输出。
    return [
        Node(
            package='ros_gz_bridge',
            executable='parameter_bridge',
            arguments=[
                '/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock',
                '/model/yahboomcar/cmd_vel@geometry_msgs/msg/Twist@gz.msgs.Twist',
                '/model/yahboomcar/odometry@nav_msgs/msg/Odometry@gz.msgs.Odometry',
                lidar_arg,
            ],
            remappings=[(topic, raw_ros)],
            parameters=[{'use_sim_time': False}],
            output='screen',
        ),
    ]


def _gz_odom_scan_relays(context, *_args, **_kwargs):
    """cmd_vel/odom 中继 + 激光：relay 改写 frame_id；scan 时间戳默认保留桥接原值（Cartographer 需单调递增）。"""
    use_sim_time = LaunchConfiguration('use_sim_time').perform(context).lower() in (
        'true', '1', 'yes',
    )
    sync = LaunchConfiguration('sync_odom_stamp_to_clock').perform(context).lower() in (
        'true', '1', 'yes',
    )
    align_scan = LaunchConfiguration('align_scan_stamp_to_odom').perform(context).lower() in (
        'true', '1', 'yes',
    )
    raw_ros = LaunchConfiguration('ros_gz_laser_raw_topic').perform(context).strip()
    if not raw_ros:
        raw_ros = '/gz_bridge/scan_raw'
    scan_frame = LaunchConfiguration('scan_frame_id').perform(context).strip() or 'laser_link'
    relay_odom = Node(
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
    relay_scan = Node(
        package='yahboomcar_description',
        executable='gz_laser_scan_relay',
        parameters=[
            {'use_sim_time': use_sim_time},
            {'gz_scan_topic': raw_ros},
            {'output_topic': '/scan'},
            {'frame_id': scan_frame},
            {'odom_topic': '/odom'},
            {'align_scan_stamp_to_odom': align_scan},
            {'scan_stamp_use_sim_time': True},
        ],
        output='screen',
    )
    return [relay_odom, relay_scan]


def generate_launch_description():
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
    # Gazebo 侧激光话题：以 `ign topic -l | grep scan` 为准；默认 /scan（非 /world/.../sensor/...）
    default_gz_lidar_topic = '/scan'
    gz_lidar_topic = LaunchConfiguration('gz_lidar_topic', default=default_gz_lidar_topic)
    default_model_path = os.path.join(pkg_yahboomcar, 'urdf', 'yahboomcar_X3.urdf')

    _wsl = _detect_wsl()
    _def_libgl = 'true' if _wsl else 'false'
    _def_fix_qt = 'true' if _wsl else 'false'
    libgl_software = LaunchConfiguration('libgl_software', default=_def_libgl)
    fix_qt_x11 = LaunchConfiguration('fix_qt_x11', default=_def_fix_qt)
    default_rviz_config = os.path.join(pkg_yahboomcar, 'rviz', 'yahboomcar.rviz')

    return LaunchDescription([
        LogInfo(
            msg=(
                '\n[gazebo_X3] 本终端请保持运行。另开终端检查话题前必须 source humble + '
                '本工作空间 install，再 ros2 topic list（应含 /clock、/gz_bridge/scan_raw 与 /scan）。\n'
            )
        ),
        DeclareLaunchArgument(
            'headless',
            default_value='false',
            description='true=仅 gz sim -s 无 Gazebo 窗口；默认 false（在 Gazebo 里看仿真、配合建图）。'
                        'WSL 若仍崩可再试 headless:=true + RViz。',
        ),
        DeclareLaunchArgument(
            'headless_rendering',
            default_value='true',
            description='true=在 headless:=true 时追加 ign gazebo --headless-rendering（更稳定但可能影响渲染质量）。'
                        '如果你环境下 headless-rendering 反而更不稳定，可以传 headless_rendering:=false 关闭。',
        ),
        DeclareLaunchArgument(
            'libgl_software',
            default_value=_def_libgl,
            description='true=LIBGL_ALWAYS_SOFTWARE=1（Mesa 软件光栅，缓解 WSL 上 Ogre copyTo 崩溃）。'
                        '检测到 WSL 时默认 true；本机 Linux 独显正常时默认 false。'
                        '若报 EGL “force software rendering” 错误则传 libgl_software:=false。',
        ),
        DeclareLaunchArgument(
            'fix_qt_x11',
            default_value=_def_fix_qt,
            description='true=QT_QPA_PLATFORM=xcb、QT_X11_NO_MITSHM=1。WSLg 下默认 true；原生桌面可传 false。',
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
                        'false：沿用 Gazebo 里程计消息时间戳。',
        ),
        DeclareLaunchArgument(
            'gz_lidar_topic',
            default_value=default_gz_lidar_topic,
            description='Gazebo 传输层 LaserScan（ign topic -l），默认 /scan；经 parameter_bridge→ros_gz_laser_raw_topic，'
                        '再由 gz_laser_scan_relay 发布对外 /scan（header.frame_id=scan_frame_id）。',
        ),
        DeclareLaunchArgument(
            'ros_gz_laser_raw_topic',
            default_value='/gz_bridge/scan_raw',
            description='桥接器在 ROS 侧发布的原始 LaserScan（勿与 /scan 混用）；gz_laser_scan_relay 订阅此话题。',
        ),
        DeclareLaunchArgument(
            'scan_frame_id',
            default_value='laser_link',
            description='写入 /scan.header.frame_id，须与 URDF 雷达 link 一致；多车时可改为命名空间前缀形式。',
        ),
        DeclareLaunchArgument(
            'align_scan_stamp_to_odom',
            default_value='false',
            description='true：/scan.header.stamp 与最近一条 /odom 相同（利于部分 AMCL/RViz）。'
                        'false（默认）：/scan 用 get_clock().now() 单调 stamp，与 sync 后的 odom TF 同基准，供 Cartographer。',
        ),
        DeclareLaunchArgument(
            'model',
            default_value=default_model_path,
            description='X3 URDF 路径（默认 share 下 yahboomcar_X3.urdf；纯 URDF 无需 xacro）。',
        ),
        DeclareLaunchArgument(
            'rviz',
            default_value='false',
            description='true=同时启动 RViz2（默认 false，建图时多用 Gazebo 窗口 + 另开 cartographer/rviz）。',
        ),
        DeclareLaunchArgument(
            'rviz_config',
            default_value=default_rviz_config,
            description='RViz2 配置文件路径（默认 share/rviz/yahboomcar.rviz）。',
        ),
        OpaqueFunction(function=_include_gz_sim),
        OpaqueFunction(function=_gz_parameter_bridge),
        OpaqueFunction(function=_gz_odom_scan_relays),
        # 与 URDF 一致发布 base_footprint→base_link→laser_link…；读文件而非调用 xacro，避免未 source 时找不到 xacro
        OpaqueFunction(function=_robot_state_publisher),
        Node(
            package='rviz2',
            executable='rviz2',
            name='rviz2',
            output='screen',
            arguments=['-d', LaunchConfiguration('rviz_config')],
            parameters=[{'use_sim_time': LaunchConfiguration('use_sim_time')}],
            condition=IfCondition(LaunchConfiguration('rviz')),
        ),
    ])
