# Predator TECO ROS 2 工作區

Ubuntu 24.04，ROS 2 Jazzy。工作區使用已安裝的 `ros-jazzy-sick-scan-xd`、
`ros-jazzy-rviz2`、`ros-jazzy-joy` 和 `python3-colcon-common-extensions`。

## 建置與啟動

```bash
cd ~/ros2_ws
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install
source install/setup.bash
ros2 launch predator_bringup robot.launch.py
```

啟動檔會啟動 SICK TiM 光達驅動、RViz2 和硬體盤點節點。NetworkManager 的
`SICK TiM LiDAR` 連線設定透過 `enp0s31f6` 存取 `192.168.0.20:2112`。
RViz2 訂閱 `/scan`，固定座標為 `cloud`。只需要背景節點時可加上
`rviz:=false`，只需要盤點時再加上 `lidar:=false`。

```bash
ros2 topic echo /diagnostics --once
ros2 topic hz /scan
ros2 run joy joy_enumerate_devices
```

偵測到相容手把後，可用 `joy:=true` 啟動 `/joy`。工作區沒有將手把接到馬達控制。

## 待確認的設備

| 設備 | 目前狀態 |
|---|---|
| SICK TiM 5xx | 乙太網路，ROS 2 `/scan` |
| FTDI FT232 ×2、CP210x、CH340 | 自動列入 `/diagnostics`，以 `/dev/serial/by-id/` 追蹤。轉接器另一端的設備尚未確認。 |
| TECO 底盤 | 已在 `/dev/ttyS0`、57600 baud 驗證左右輪回饋。 |
| LPMS-ME1 IMU | 透過 CP210x 接入，發佈 `/imu/data_raw`。 |
| USB 鍵盤、接收器、集線器、Wi‑Fi | 由 Ubuntu 管理，USB 和網路狀態列入 `/diagnostics`。 |
| 手把、攝影機 | 本次未找到可用的遊戲控制器或 V4L2 攝影機節點。 |

盤點節點只檢查設備是否存在及目前使用者的存取權限，不開啟序列埠。


## 移植的 ROS 1 套件

- `my_script_handler` 已轉成 ROS 2 的自訂訊息與服務型別。型別名稱改用 PascalCase，欄位改用 snake_case。舊備份只包含介面，沒有服務實作。
- `odombase` 已移植 TECO 兩輪回饋。ADLINK 的 `/dev/ttyS0`、57600 baud 已收到 ID 1 和 2 的有效回應，節點發佈 `/odom` 與 `odom → base_link`。
- LPMS-ME1 經 CP210x 在 115200 baud 輸出 LP-BUS。節點發佈 `/imu/data_raw` 的角速度與加速度。安裝方向、姿態和底盤座標轉換尚未校正。
- 舊的兩張地圖已移到 `predator_bringup/maps`。舊 ROS 1 `move_base`、AMCL 及其控制參數尚未移植成 Nav2 導航。
- 序列埠存取權限是對目前裝置節點設定的 ACL。重新開機或拔插 IMU 後，如果出現權限錯誤，重新授權：

```bash
sudo setfacl -m "u:$(id -un):rw" /dev/ttyS0 /dev/ttyUSB2
```

## Cartographer 2D 建圖與鍵盤控制

```bash
cd ~/ros2_ws
source setup_mapping.bash
ros2 launch predator_bringup mapping.launch.py
```

建圖使用 `/scan` 和 EKF 的 `/odometry/filtered`。EKF 融合 `/wheel/odom` 的平面輪速與
LPMS-ME1 `/imu/gyro` 的偏航角速度，並由 EKF 單獨發佈 `odom → base_link`。
IMU 的加速度和絕對姿態未納入融合。依舊包直接使用 IMU 的 Z 軸正負方向，預設
`imu_roll:=0.0`，小於或等於 0.01 rad/s 的偏航角速度視為零。原始資料仍可從
`/imu/data_raw` 讀取。可用 `imu_roll`、`imu_pitch`、`imu_yaw`（弧度）調整安裝角。
光達掃描角度為 −1.57 到 +1.57 rad。`robot.launch.py` 會發布 `base_link → cloud`，
預設位置為 X = 0.2、Y = 0、Z = 0.2 公尺，偏航角為 0。建圖沿用同一份設定，可用
`lidar_x`、`lidar_y`、`lidar_z`（公尺）及 `lidar_yaw`（弧度）指定實測值。原有 APT 程序佔用鎖時，建圖環境會使用
工作區 `.mapping-runtime` 內從 APT 下載的 Jazzy 套件。

要控制實體車輪，先停止上述 launch，確認周圍淨空並備妥實體急停，再用
`ros2 launch predator_bringup mapping.launch.py drive:=true` 啟動。
另一個終端機執行：

```bash
cd ~/ros2_ws
source setup_mapping.bash
ros2 run predator_bringup keyboard_teleop
```

按住 WASD 或方向鍵移動，空白鍵停止，Q 離開。終端機顯示是否有底盤訂閱遙控指令。終端機失去按鍵輸入時會停止送移動指令。
底盤驅動另外檢查指令時效和左右輪回饋。實體移動及急停尚未驗證。

地圖還在發佈時，在另一個載入同一工作區的終端機儲存：

```bash
mkdir -p ~/ros2_ws/maps
ros2 run nav2_map_server map_saver_cli -f ~/ros2_ws/maps/teco_new --fmt pgm \
  --ros-args -p map_subscribe_transient_local:=true -p save_map_timeout:=8.0
```

讀取舊地圖前先停止即時建圖，避免兩個節點同時發佈 `/map`。
可用 `ros2 launch predator_bringup map.launch.py` 載入舊地圖。

## Nav2 MPPI 與 RViz2

先停止 Cartographer。第一個終端機啟動光達、TF 和輪速里程計：

```bash
cd ~/ros2_ws
source setup_mapping.bash
ros2 launch predator_bringup robot.launch.py odom:=true drive:=false imu:=false rviz:=false
```

第二個終端機啟動 Nav2 與 RViz2：

```bash
cd ~/ros2_ws
source setup_mapping.bash
ros2 launch nav2_bringup teco_navigation.launch.py
```

預設使用 `maps/teco_20261112_215618.yaml` 與 `config/teco_nav2_mppi.yaml`。
可用 `map:=/完整路徑/地圖.yaml` 選擇其他地圖，或用 `rviz:=False` 只啟動 Nav2。
先在 RViz2 使用 2D Pose Estimate 設定車輛的起始位置及方向。

實車導航時，先取消任何現有目標並停止舊的 Nav2 和底盤程序。確認車身外廓與
成本地圖設定相符、急停可用後，將第一個終端機的底盤啟動指令改為：

```bash
ros2 launch predator_bringup robot.launch.py odom:=true drive:=true drive_source:=nav2 imu:=false rviz:=false
```

Nav2 模式從 `/nav2/cmd_vel_safe` 接收碰撞監控的輸出。鍵盤模式可改用
`drive_source:=keyboard`，切換時需重新啟動底盤。兩種模式各自只訂閱一個來源。
