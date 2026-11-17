cmake_minimum_required(VERSION 3.16)
project(predator_bringup)

find_package(ament_cmake REQUIRED)
install(DIRECTORY launch config DESTINATION share/${PROJECT_NAME})
install(PROGRAMS scripts/hardware_inventory scripts/keyboard_teleop scripts/lpms_imu DESTINATION lib/${PROJECT_NAME})
ament_package()
