import os

from ament_index_python.packages import get_package_share_path
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    share = get_package_share_path("predator_bringup")
    config_dir = os.environ.get("PREDATOR_CARTOGRAPHER_CONFIG_DIR", str(share / "config"))
    return LaunchDescription([
        DeclareLaunchArgument("drive", default_value="false"),
        DeclareLaunchArgument("imu", default_value="true"),
        DeclareLaunchArgument("mapping_rviz", default_value="true"),
        # imu_x、imu_roll 等安裝位置參數由 robot.launch.py 宣告，在這裡一樣可以指定。
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(str(share / "launch" / "robot.launch.py")),
            launch_arguments={
                "odom": "true", "drive": LaunchConfiguration("drive"), "rviz": "false",
                "imu": LaunchConfiguration("imu"),
                "wheel_odom_topic": "/wheel/odom",
                "publish_wheel_tf": "false",
                "ekf": "false",   # 建圖自己啟動下面那個 EKF，避免兩個 EKF 同時發佈 TF
            }.items(),
        ),
        Node(
            package="robot_localization", executable="ekf_node", name="ekf_filter_node",
            parameters=[str(share / "config" / "ekf.yaml")],
            output="screen",
        ),
        Node(
            package="cartographer_ros", executable="cartographer_node",
            remappings=[("odom", "/odometry/filtered")],
            arguments=["-configuration_directory", config_dir,
                       "-configuration_basename", "cartographer_2d.lua"],
            output="screen",
        ),
        Node(
            package="cartographer_ros", executable="cartographer_occupancy_grid_node",
            arguments=["-resolution", "0.05", "-publish_period_sec", "1.0"],
            output="screen",
        ),
        Node(
            package="rviz2", executable="rviz2",
            arguments=["-d", str(share / "config" / "mapping.rviz")],
            condition=IfCondition(LaunchConfiguration("mapping_rviz")),
        ),
    ])
