cmake_minimum_required(VERSION 3.16)
project(my_script_handler)
find_package(ament_cmake REQUIRED)
find_package(rosidl_default_generators REQUIRED)
rosidl_generate_interfaces(${PROJECT_NAME}
  "msg/ActionItem.msg"
  "msg/ActionList.msg"
  "msg/PeripheralCmd.msg"
  "msg/ShowItem.msg"
  "msg/ShowList.msg"
  "srv/DeleteScriptService.srv"
  "srv/ListScriptService.srv"
)
ament_export_dependencies(rosidl_default_runtime)
ament_package()
