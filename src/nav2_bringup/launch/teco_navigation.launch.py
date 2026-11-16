from pathlib import Path

from ament_index_python.packages import get_package_share_path
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration


def generate_launch_description():
    workspace = Path.home() / "ros2_ws"
    launch_dir = get_package_share_path("nav2_bringup") / "launch"

    return LaunchDescription([
        DeclareLaunchArgument(
            "map",
            default_value=str(workspace / "maps" / "teco_20261112_215618.yaml"),
            description="Occupancy map YAML file",
        ),
        DeclareLaunchArgument(
            "params_file",
            default_value=str(workspace / "config" / "teco_nav2_mppi.yaml"),
            description="Nav2 configuration with the TECO MPPI controller",
        ),
        DeclareLaunchArgument("use_sim_time", default_value="False"),
        DeclareLaunchArgument("rviz", default_value="True", description="Start RViz2"),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(str(launch_dir / "bringup_launch.py")),
            launch_arguments={
                "map": LaunchConfiguration("map"),
                "params_file": LaunchConfiguration("params_file"),
                "slam": "False",
                "use_sim_time": LaunchConfiguration("use_sim_time"),
            }.items(),
        ),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(str(launch_dir / "rviz_launch.py")),
            launch_arguments={
                "use_sim_time": LaunchConfiguration("use_sim_time"),
            }.items(),
            condition=IfCondition(LaunchConfiguration("rviz")),
        ),
    ])
