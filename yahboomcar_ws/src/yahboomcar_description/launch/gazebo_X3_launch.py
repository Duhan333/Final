# Copyright 2024
# Launch Gazebo with ROSMASTER X3 model (diff_drive + bridge for Nav2)

import os

from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.actions import IncludeLaunchDescription
from launch.actions import LogInfo
from launch.actions import OpaqueFunction
from launch.actions import SetEnvironmentVariable
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration

from launch_ros.actions import Node


def _detect_wsl():
    """WSL1/WSL2 defaults for rendering-related stability."""
    return bool(os.environ.get("WSL_DISTRO_NAME") or os.environ.get("WSL_INTEROP"))


def _include_gz_sim(context):
    """Build gz args based on headless options."""
    pkg_yahboomcar = get_package_share_directory("yahboomcar_description")
    world_file = os.path.join(pkg_yahboomcar, "worlds", "yahboomcar_empty.world")
    headless = LaunchConfiguration("headless").perform(context).lower() in ("true", "1", "yes")
    headless_rendering = (
        LaunchConfiguration("headless_rendering").perform(context).lower() in ("true", "1", "yes")
    )
    gz_args = (
        f"-r -s --headless-rendering {world_file}"
        if headless and headless_rendering
        else (f"-r -s {world_file}" if headless else f"-r {world_file}")
    )
    pkg_ros_gz_sim = get_package_share_directory("ros_gz_sim")
    gz_sim_launch = os.path.join(pkg_ros_gz_sim, "launch", "gz_sim.launch.py")
    return [
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(gz_sim_launch),
            launch_arguments={"gz_args": gz_args}.items(),
        ),
    ]


def _robot_state_publisher(context, *_args, **_kwargs):
    """Read URDF text directly to avoid xacro binary dependency."""
    model_path = LaunchConfiguration("model").perform(context)
    if not os.path.isfile(model_path):
        raise FileNotFoundError(
            f"Cannot find robot model file: {model_path!r}. "
            "Check yahboomcar_description install, or pass model:=<absolute_path>."
        )
    with open(model_path, "r", encoding="utf-8") as f:
        robot_description = f.read()

    use_sim_time = LaunchConfiguration("use_sim_time").perform(context).lower() in ("true", "1", "yes")
    rsp = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        output="screen",
        parameters=[
            {"use_sim_time": use_sim_time},
            {"robot_description": robot_description},
        ],
    )
    jsp = Node(
        package="joint_state_publisher",
        executable="joint_state_publisher",
        output="screen",
        arguments=[model_path],
        parameters=[{"use_sim_time": use_sim_time}],
    )
    return [rsp, jsp]


def _gz_parameter_bridge(context, *_args, **_kwargs):
    """Bridge Gazebo transport topics; publish scan to internal ROS raw topic."""
    default_lidar = "/scan"
    topic = LaunchConfiguration("gz_lidar_topic").perform(context).strip()
    if not topic:
        topic = default_lidar
    raw_ros = LaunchConfiguration("ros_gz_laser_raw_topic").perform(context).strip()
    if not raw_ros:
        raw_ros = "/gz_bridge/scan_raw"
    lidar_arg = f"{topic}@sensor_msgs/msg/LaserScan[gz.msgs.LaserScan"
    # Keep bridge on wall/ROS time; avoid /clock self-dependency deadlock.
    return [
        Node(
            package="ros_gz_bridge",
            executable="parameter_bridge",
            arguments=[
                "/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock",
                "/model/yahboomcar/cmd_vel@geometry_msgs/msg/Twist@gz.msgs.Twist",
                "/model/yahboomcar/odometry@nav_msgs/msg/Odometry@gz.msgs.Odometry",
                lidar_arg,
            ],
            remappings=[(topic, raw_ros)],
            parameters=[{"use_sim_time": False}],
            output="screen",
        ),
    ]


def _gz_odom_scan_relays(context, *_args, **_kwargs):
    """cmd_vel/odom relay + laser relay with frame_id normalization."""
    use_sim_time = LaunchConfiguration("use_sim_time").perform(context).lower() in ("true", "1", "yes")
    sync = LaunchConfiguration("sync_odom_stamp_to_clock").perform(context).lower() in ("true", "1", "yes")
    align_scan = LaunchConfiguration("align_scan_stamp_to_odom").perform(context).lower() in ("true", "1", "yes")
    raw_ros = LaunchConfiguration("ros_gz_laser_raw_topic").perform(context).strip()
    if not raw_ros:
        raw_ros = "/gz_bridge/scan_raw"
    scan_frame = LaunchConfiguration("scan_frame_id").perform(context).strip() or "laser_link"
    scan_out_topic = LaunchConfiguration("scan_output_topic").perform(context).strip() or "/scan_relay"
    relay_odom = Node(
        package="yahboomcar_description",
        executable="gazebo_topic_relay",
        parameters=[
            {"use_sim_time": use_sim_time},
            {"publish_odom_tf": True},
            {"max_odom_clock_skew_sec": 0.0},
            {"sync_odom_stamp_to_clock": sync},
        ],
        output="screen",
    )
    relay_scan = Node(
        package="yahboomcar_description",
        executable="gz_laser_scan_relay",
        parameters=[
            {"use_sim_time": use_sim_time},
            {"gz_scan_topic": raw_ros},
            {"output_topic": scan_out_topic},
            {"frame_id": scan_frame},
            {"odom_topic": "/odom"},
            {"align_scan_stamp_to_odom": align_scan},
            {"scan_stamp_use_sim_time": True},
        ],
        output="screen",
    )
    return [relay_odom, relay_scan]


def generate_launch_description():
    pkg_yahboomcar = get_package_share_directory("yahboomcar_description")
    # Prefer this workspace install path when present.
    ws_share = os.path.expanduser("~/Final/yahboomcar_ws/install/yahboomcar_description/share/yahboomcar_description")
    if os.path.isdir(ws_share):
        models_dir = os.path.join(ws_share, "models")
        worlds_dir = os.path.join(ws_share, "worlds")
        pkg_dir = ws_share
        pkg_parent = os.path.dirname(ws_share)
    else:
        models_dir = os.path.join(pkg_yahboomcar, "models")
        worlds_dir = os.path.join(pkg_yahboomcar, "worlds")
        pkg_dir = pkg_yahboomcar
        pkg_parent = os.path.dirname(pkg_yahboomcar)

    # Keep multiple lookup roots:
    # - models_dir/worlds_dir for model://yahboomcar_X3 and world assets
    # - pkg_parent for model://yahboomcar_description/meshes/...
    resource_paths = ":".join([models_dir, worlds_dir, pkg_dir, pkg_parent])

    default_gz_lidar_topic = "/scan"
    default_model_path = os.path.join(pkg_yahboomcar, "urdf", "yahboomcar_X3.urdf")
    _wsl = _detect_wsl()
    _def_libgl = "true" if _wsl else "false"
    _def_fix_qt = "true" if _wsl else "false"
    libgl_software = LaunchConfiguration("libgl_software", default=_def_libgl)
    fix_qt_x11 = LaunchConfiguration("fix_qt_x11", default=_def_fix_qt)
    default_rviz_config = os.path.join(pkg_yahboomcar, "rviz", "yahboomcar.rviz")

    return LaunchDescription(
        [
            LogInfo(
                msg=(
                    "\n[gazebo_X3] Keep this terminal running. In a new terminal, source humble + workspace "
                    "install, then check topics (/clock, /gz_bridge/scan_raw, /scan_relay).\n"
                )
            ),
            DeclareLaunchArgument("headless", default_value="false"),
            DeclareLaunchArgument("headless_rendering", default_value="true"),
            DeclareLaunchArgument("libgl_software", default_value=_def_libgl),
            DeclareLaunchArgument("fix_qt_x11", default_value=_def_fix_qt),
            SetEnvironmentVariable(name="LIBGL_ALWAYS_SOFTWARE", value="1", condition=IfCondition(libgl_software)),
            SetEnvironmentVariable(name="QT_QPA_PLATFORM", value="xcb", condition=IfCondition(fix_qt_x11)),
            SetEnvironmentVariable(name="QT_X11_NO_MITSHM", value="1", condition=IfCondition(fix_qt_x11)),
            SetEnvironmentVariable(name="IGN_GAZEBO_RESOURCE_PATH", value=resource_paths),
            SetEnvironmentVariable(name="GZ_SIM_RESOURCE_PATH", value=resource_paths),
            DeclareLaunchArgument("use_sim_time", default_value="true"),
            DeclareLaunchArgument("sync_odom_stamp_to_clock", default_value="true"),
            DeclareLaunchArgument("gz_lidar_topic", default_value=default_gz_lidar_topic),
            DeclareLaunchArgument("ros_gz_laser_raw_topic", default_value="/gz_bridge/scan_raw"),
            DeclareLaunchArgument("scan_output_topic", default_value="/scan_relay"),
            DeclareLaunchArgument("scan_frame_id", default_value="laser_link"),
            DeclareLaunchArgument("align_scan_stamp_to_odom", default_value="false"),
            DeclareLaunchArgument("model", default_value=default_model_path),
            DeclareLaunchArgument("rviz", default_value="false"),
            DeclareLaunchArgument("rviz_config", default_value=default_rviz_config),
            OpaqueFunction(function=_include_gz_sim),
            OpaqueFunction(function=_gz_parameter_bridge),
            OpaqueFunction(function=_gz_odom_scan_relays),
            OpaqueFunction(function=_robot_state_publisher),
            Node(
                package="rviz2",
                executable="rviz2",
                name="rviz2",
                output="screen",
                arguments=["-d", LaunchConfiguration("rviz_config")],
                parameters=[{"use_sim_time": LaunchConfiguration("use_sim_time")}],
                condition=IfCondition(LaunchConfiguration("rviz")),
            ),
        ]
    )
