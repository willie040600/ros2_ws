from ament_index_python.packages import get_package_share_path
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    map_path = get_package_share_path("predator_navigation") / "maps" / "teco_gmapping.yaml"
    return LaunchDescription([
        DeclareLaunchArgument("map", default_value=str(map_path)),
        Node(
            package="nav2_map_server",
            executable="map_server",
            name="map_server",
            parameters=[{"yaml_filename": LaunchConfiguration("map")}],
            output="screen",
        ),
        Node(
            package="nav2_lifecycle_manager",
            executable="lifecycle_manager",
            name="lifecycle_manager_map",
            parameters=[{"autostart": True, "node_names": ["map_server"]}],
            output="screen",
        ),
    ])
