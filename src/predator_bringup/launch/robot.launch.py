from ament_index_python.packages import get_package_share_path
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, LogInfo, OpaqueFunction
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def base_nodes(context):
    """底盤節點，以及 teleop_safety:=true 時保護鍵盤指令的碰撞監控。

    ekf:=true 時底盤改成餵給 EKF，由 EKF 發佈 /odom 與 odom → base_link。
    """
    def enabled(name):
        return IfCondition(LaunchConfiguration(name)).evaluate(context)

    if enabled("ekf"):
        odom_topic, publish_tf = "/wheel/odom", False
    else:
        odom_topic = LaunchConfiguration("wheel_odom_topic").perform(context)
        publish_tf = enabled("publish_wheel_tf")
    remappings = [("odom", odom_topic)]
    actions = []

    keyboard_drives = (enabled("drive")
                       and LaunchConfiguration("drive_source").perform(context) in ("keyboard", "both"))
    if keyboard_drives and enabled("teleop_safety"):
        # keyboard/cmd_vel → teleop_collision_monitor → keyboard/cmd_vel_safe → odom_control
        remappings.append(("keyboard/cmd_vel", "keyboard/cmd_vel_safe"))
        share = get_package_share_path("predator_bringup")
        actions += [
            Node(
                package="nav2_collision_monitor",
                executable="collision_monitor",
                name="teleop_collision_monitor",
                parameters=[str(share / "config" / "teleop_collision_monitor.yaml")],
                output="screen",
            ),
            Node(
                package="nav2_lifecycle_manager",
                executable="lifecycle_manager",
                name="lifecycle_manager_teleop_safety",
                parameters=[{"autostart": True, "node_names": ["teleop_collision_monitor"]}],
                output="screen",
            ),
        ]
        if not enabled("lidar"):
            actions.append(LogInfo(msg=(
                "[teleop_safety] lidar:=false：碰撞監控收不到 /scan，會擋下所有鍵盤指令。"
                "車輪架高測試時才用 teleop_safety:=false 關閉。")))
    elif keyboard_drives:
        actions.append(LogInfo(msg="[teleop_safety] 已關閉：鍵盤指令不經過碰撞監控，請確認周圍淨空。"))

    actions.insert(0, Node(
        package="odombase",
        executable="odom_control",
        output="screen",
        parameters=[{
            "port": LaunchConfiguration("base_port"),
            "publish_tf": publish_tf,
            "enable_drive": ParameterValue(LaunchConfiguration("drive"), value_type=bool),
            "drive_source": LaunchConfiguration("drive_source"),
        }],
        remappings=remappings,
    ))
    return actions


def generate_launch_description():
    share = get_package_share_path("predator_bringup")
    driver_config = get_package_share_path("sick_scan_xd") / "launch" / "sick_tim_5xx.launch"
    rviz_config = share / "config" / "lidar.rviz"
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
        DeclareLaunchArgument("imu_x", default_value="0.0"),
        DeclareLaunchArgument("imu_y", default_value="-0.1"),
        DeclareLaunchArgument("imu_z", default_value="0.0"),
        DeclareLaunchArgument("imu_roll", default_value="0.0"),
        DeclareLaunchArgument("imu_pitch", default_value="0.0"),
        DeclareLaunchArgument("imu_yaw", default_value="0.0"),
        DeclareLaunchArgument(
            "ekf", default_value="false",
            description="Fuse wheel odometry and IMU yaw rate into /odom with robot_localization"),
        DeclareLaunchArgument("drive", default_value="true"),
        DeclareLaunchArgument("drive_source", default_value="keyboard", choices=["keyboard", "nav2", "both"]),
        DeclareLaunchArgument(
            "teleop_safety", default_value="true",
            description="Route keyboard commands through a collision monitor (needs the lidar)"),
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
                # TiM581 的最小量測距離是 0.05 m；更近的讀數是雜訊（實測在左前方 35° 與 47°）。
                # /scan 的 range_min 跟著變成 0.05，成本地圖、AMCL 與碰撞監控都會忽略更近的點。
                "range_min:=0.05",
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
        OpaqueFunction(
            function=base_nodes,
            condition=IfCondition(LaunchConfiguration("odom")),
        ),
        Node(
            package="predator_bringup",
            executable="lpms_imu",
            output="screen",
            condition=IfCondition(LaunchConfiguration("imu")),
        ),
        Node(
            package="tf2_ros",
            executable="static_transform_publisher",
            name="imu_static_tf",
            arguments=[
                "--x", LaunchConfiguration("imu_x"),
                "--y", LaunchConfiguration("imu_y"),
                "--z", LaunchConfiguration("imu_z"),
                "--roll", LaunchConfiguration("imu_roll"),
                "--pitch", LaunchConfiguration("imu_pitch"),
                "--yaw", LaunchConfiguration("imu_yaw"),
                "--frame-id", "base_link", "--child-frame-id", "imu_link",
            ],
            condition=IfCondition(LaunchConfiguration("imu")),
        ),
        # 與建圖共用 ekf.yaml：融合 /wheel/odom 的平面速度與 /imu/gyro 的偏航角速度。
        # 輸出改名為 /odom，Nav2 與 AMCL 的設定不必更動。
        Node(
            package="robot_localization",
            executable="ekf_node",
            name="ekf_filter_node",
            parameters=[str(share / "config" / "ekf.yaml")],
            remappings=[("odometry/filtered", "/odom")],
            output="screen",
            condition=IfCondition(LaunchConfiguration("ekf")),
        ),
        Node(
            package="joy",
            executable="joy_node",
            output="screen",
            condition=IfCondition(LaunchConfiguration("joy")),
        ),
    ])
