# Source this file from Bash after building ~/ros2_ws.
_predator_ws="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
source "${_predator_ws}/install/setup.bash"
if [[ -d "${_predator_ws}/.mapping-runtime/root" ]] &&
   [[ ! -d /opt/ros/jazzy/share/cartographer_ros ||
      ! -d /opt/ros/jazzy/share/robot_localization ||
      ! -d /opt/ros/jazzy/share/nav2_map_server ]]; then
    _predator_root="${_predator_ws}/.mapping-runtime/root"
    _predator_prefix="${_predator_root}/opt/ros/jazzy"
    export AMENT_PREFIX_PATH="${_predator_prefix}${AMENT_PREFIX_PATH:+:${AMENT_PREFIX_PATH}}"
    export LD_LIBRARY_PATH="${_predator_prefix}/lib:${_predator_root}/usr/lib/x86_64-linux-gnu:${_predator_root}/usr/lib${LD_LIBRARY_PATH:+:${LD_LIBRARY_PATH}}"
    export PREDATOR_CARTOGRAPHER_CONFIG_DIR="${_predator_ws}/.mapping-runtime/config"
    unset _predator_root _predator_prefix
else
    unset PREDATOR_CARTOGRAPHER_CONFIG_DIR
fi
unset _predator_ws
