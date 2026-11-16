from ament_index_python.packages import get_package_share_path
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    driver_config = get_package_share_path("sick_scan_xd") / "launch" / "sick_tim_5xx.launch"
    rviz_config = get_package_share_path("predator_bringup") / "config" / "lidar.rviz"
    lidar_ip = LaunchConfiguration("lidar_ip")

    return LaunchDescription([
        DeclareLaunchArgument("lidar_ip", default_value="192.168.0.20"),
        DeclareLaunchArgument("lidar", default_value="true"),
        DeclareLaunchArgument("lidar_x", default_value="0.2"),
        DeclareLaunchArgument("lidar_y", default_value="0.0"),
        DeclareLaunchArgument("lidar_z", default_value="0.2"),
        DeclareLaunchArgument("lidar_yaw", default_value="0.0"),
        DeclareLaunchArgument("rviz", default_value="true"),
        DeclareLaunchArgument("joy", default_value="false"),
        DeclareLaunchArgument("odom", default_value="true"),
        DeclareLaunchArgument("imu", default_value="true"),
        DeclareLaunchArgument("drive", default_value="true"),
        DeclareLaunchArgument("drive_source", default_value="keyboard", choices=["keyboard", "nav2"]),
        DeclareLaunchArgument("wheel_odom_topic", default_value="/odom"),
        DeclareLaunchArgument("publish_wheel_tf", default_value="true"),
        DeclareLaunchArgument("base_port", default_value="/dev/ttyS0"),
        Node(
            package="predator_bringup",
            executable="hardware_inventory",
            output="screen",
        ),
        Node(
            package="sick_scan_xd",
            executable="sick_generic_caller",
            arguments=[
                str(driver_config), ["hostname:=", lidar_ip],
                "tf_publish_rate:=0.0", "min_ang:=-1.57", "max_ang:=1.57",
            ],
            output="screen",
            condition=IfCondition(LaunchConfiguration("lidar")),
        ),
        Node(
            package="tf2_ros",
            executable="static_transform_publisher",
            name="lidar_static_tf",
            arguments=[
                "--x", LaunchConfiguration("lidar_x"),
                "--y", LaunchConfiguration("lidar_y"),
                "--z", LaunchConfiguration("lidar_z"),
                "--yaw", LaunchConfiguration("lidar_yaw"),
                "--frame-id", "base_link", "--child-frame-id", "cloud",
            ],
            condition=IfCondition(LaunchConfiguration("lidar")),
        ),
        Node(
            package="rviz2",
            executable="rviz2",
            arguments=["-d", str(rviz_config)],
            output="screen",
            condition=IfCondition(LaunchConfiguration("rviz")),
        ),
        Node(
            package="odombase",
            executable="odom_control",
            output="screen",
            parameters=[{
                "port": LaunchConfiguration("base_port"),
                "publish_tf": ParameterValue(LaunchConfiguration("publish_wheel_tf"), value_type=bool),
                "enable_drive": ParameterValue(LaunchConfiguration("drive"), value_type=bool),
                "drive_source": LaunchConfiguration("drive_source"),
            }],
            remappings=[("odom", LaunchConfiguration("wheel_odom_topic"))],
            condition=IfCondition(LaunchConfiguration("odom")),
        ),
        Node(
            package="predator_bringup",
            executable="lpms_imu",
            output="screen",
            condition=IfCondition(LaunchConfiguration("imu")),
        ),
        Node(
            package="joy",
            executable="joy_node",
            output="screen",
            condition=IfCondition(LaunchConfiguration("joy")),
        ),
    ])
