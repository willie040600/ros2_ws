# Predator TECO ROS 2 工作區

TECO 兩輪差速底盤的 ROS 2 Jazzy 工作區，執行在 Ubuntu 24.04 的車載電腦上。
內容包含底盤與感測器驅動、Cartographer 2D 建圖、Nav2 MPPI 導航，以及鍵盤遙控。

| 功能 | 使用的元件 |
|---|---|
| 底盤驅動與輪速里程計 | `odombase`（TECO 馬達驅動器，RS-232） |
| 光達 | SICK TiM 5xx，`sick_scan_xd` |
| IMU | LPMS-ME1，`predator_bringup/lpms_imu` |
| 建圖 | Cartographer 2D，里程計由 EKF 融合輪速與陀螺儀 |
| 導航 | Nav2，控制器為 MPPI，輸出經過碰撞監控 |
| 手動控制 | `predator_bringup/keyboard_teleop` |

> **實車移動與急停尚未完整驗證。** 讓輪子轉動之前，請確認周圍淨空並備妥實體急停。

## 目錄

- [環境需求](#環境需求)
- [安裝與建置](#安裝與建置)
- [快速開始](#快速開始)
- [鍵盤控制](#鍵盤控制)
- [建圖](#建圖)
- [導航](#導航)
- [鍵盤與 Nav2 共用底盤](#鍵盤與-nav2-共用底盤)
- [啟動參數](#啟動參數)
- [話題與座標](#話題與座標)
- [硬體](#硬體)
- [工作區結構](#工作區結構)
- [疑難排解](#疑難排解)
- [已知限制](#已知限制)
- [授權](#授權)

## 環境需求

- Ubuntu 24.04，ROS 2 Jazzy
- 工作區可以放在任何位置。下面的指令以 `~/ros2_ws` 為例。

安裝相依套件：

```bash
sudo apt install ros-jazzy-desktop ros-jazzy-navigation2 ros-jazzy-nav2-bringup \
  ros-jazzy-cartographer-ros ros-jazzy-robot-localization ros-jazzy-sick-scan-xd \
  ros-jazzy-joy python3-serial python3-colcon-common-extensions \
  libxtensor-dev libxsimd-dev libomp-dev libbenchmark-dev
```

最後一行的四個函式庫是編譯 `src/nav2_mppi_controller` 需要的。車載電腦的 CPU
（Celeron G3900TE）不支援 AVX，所以 MPPI 控制器要從原始碼以關閉 AVX 的選項自行編譯，
不能直接使用 APT 的版本。

## 安裝與建置

```bash
git clone https://github.com/willie040600/ros2_ws.git ~/ros2_ws
```

```bash
cd ~/ros2_ws && source /opt/ros/jazzy/setup.bash && colcon build --symlink-install
```

使用 `--symlink-install` 時，修改 `scripts/`、`launch/` 和 `config/` 內的檔案不需要重新建置。

之後每個新的終端機都要先載入工作區：

```bash
cd ~/ros2_ws && source setup_mapping.bash
```

`setup_mapping.bash` 會載入 `install/setup.bash`。系統缺少 Cartographer、
`robot_localization` 或 `nav2_map_server` 時，它會改用工作區內的 `.mapping-runtime`
備援環境。這個資料夾沒有放進版本庫，用上面的 `apt install` 裝好套件就不需要它。

## 快速開始

啟動光達、TF、輪速里程計、IMU、硬體盤點和 RViz2：

```bash
ros2 launch predator_bringup robot.launch.py drive:=false
```

`drive:=false` 表示只讀取輪速，不送出馬達指令。確認感測器有資料：

```bash
ros2 topic hz /scan
```

```bash
ros2 topic echo /odom --once
```

```bash
ros2 topic echo /diagnostics --once
```

RViz2 訂閱 `/scan`，固定座標為 `cloud`。只需要背景節點時加上 `rviz:=false`。

## 鍵盤控制

第一個終端機啟動底盤。`drive` 預設為 `true`，`drive_source` 預設為 `keyboard`：

```bash
ros2 launch predator_bringup robot.launch.py
```

第二個終端機啟動鍵盤節點：

```bash
ros2 run predator_bringup keyboard_teleop
```

| 按鍵 | 動作 |
|---|---|
| `W` / `↑` | 前進 0.10 m/s |
| `S` / `↓` | 後退 0.08 m/s |
| `A` / `←` | 左轉 0.30 rad/s |
| `D` / `→` | 右轉 0.30 rad/s |
| 空白鍵 | 停車，持續送 3 秒零速 |
| `Q` / `Esc` | 離開 |

要按住按鍵才會持續移動，放開後車子會停。畫面第二行顯示底盤是否有訂閱鍵盤指令，
第三行顯示鍵盤目前是 `driving`、`holding stop` 還是 `idle`。

鍵盤指令預設會先經過碰撞監控（`teleop_safety:=true`）：以 40×40 cm 的車體外形模擬車子沿指令前進或旋轉，
預計 1.2 秒內會撞到光達看到的障礙物時降速，貼近時停車。碰撞監控需要光達資料，所以
`lidar:=false` 時鍵盤指令會全部被擋下。車輪架高、沒有光達的測試才用 `teleop_safety:=false`
關閉。光達只看得到前方，**按 `S` 倒車時沒有任何保護**。

## 建圖

Cartographer 2D 使用 `/scan` 和 EKF 輸出的 `/odometry/filtered`：

```bash
ros2 launch predator_bringup mapping.launch.py
```

要邊開邊建圖，加上 `drive:=true`，再到另一個終端機執行 `keyboard_teleop`：

```bash
ros2 launch predator_bringup mapping.launch.py drive:=true
```

地圖還在發佈時，在另一個終端機儲存：

```bash
ros2 run nav2_map_server map_saver_cli -f ~/ros2_ws/src/predator_navigation/maps/teco_new --fmt pgm --ros-args -p map_subscribe_transient_local:=true -p save_map_timeout:=8.0
```

新地圖要重新建置 `predator_navigation` 才會安裝；在那之前可以用 `map:=` 指定完整路徑：

```bash
cd ~/ros2_ws && colcon build --symlink-install --packages-select predator_navigation
```

載入既有地圖（預設為 `predator_navigation/maps/teco_gmapping.yaml`）：

```bash
ros2 launch predator_navigation map.launch.py
```

載入地圖前先停止即時建圖，避免兩個節點同時發佈 `/map`。

EKF 融合 `/wheel/odom` 的平面輪速與 `/imu/gyro` 的偏航角速度，並單獨發佈
`odom → base_link`。IMU 的加速度和絕對姿態沒有納入融合。小於或等於 0.01 rad/s
的偏航角速度視為零。

## 導航

先停止 Cartographer。第一個終端機啟動光達、TF 和底盤：

```bash
ros2 launch predator_bringup robot.launch.py odom:=true drive:=true drive_source:=nav2 imu:=false rviz:=false
```

想先測試 Nav2 而不讓車子移動，把 `drive:=true` 改成 `drive:=false`。

Nav2 不會讓車子倒車，因為光達只看得到前方 180°，後方沒有感測器：

- MPPI 的 `vx_min` 與速度平滑器的線速度下限都是 0。
- 恢復行為不載入 `backup`，行為樹使用 `predator_navigation/behavior_trees` 內拿掉 BackUp 的版本。
  卡住時依序清除成本地圖、原地旋轉、等待。

這個指令只用輪速里程計，所以關掉 IMU。要用 IMU 修正轉向（例如輪子打滑時），
改用 `ekf:=true` 並開啟 IMU：

```bash
ros2 launch predator_bringup robot.launch.py odom:=true drive:=true drive_source:=nav2 imu:=true ekf:=true rviz:=false
```

`ekf:=true` 時，底盤節點改發佈 `/wheel/odom` 且不發佈 TF。EKF 融合 `/wheel/odom`
的平面速度與 `/imu/gyro` 的偏航角速度，輸出到 `/odom` 並發佈 `odom → base_link`，
所以 Nav2 與 AMCL 的設定不用改。EKF 與建圖共用 `predator_bringup/config/ekf.yaml`。
第一次使用前，先照[確認 IMU 轉向方向](#確認-imu-轉向方向)檢查正負號。

第二個終端機啟動 Nav2 與 RViz2：

```bash
ros2 launch predator_navigation navigation.launch.py
```

啟動後的步驟：

1. 在 RViz2 用 **2D Pose Estimate** 設定車子的起始位置與方向。
2. 確認光達掃描與地圖重合。
3. 用 **Nav2 Goal** 指定目標。

預設使用 `predator_navigation` 套件內的 `maps/teco_20261112_215618.yaml` 與
`config/teco_nav2_mppi.yaml`。指定其他地圖或設定：

```bash
ros2 launch predator_navigation navigation.launch.py map:=/完整路徑/地圖.yaml params_file:=/完整路徑/設定.yaml
```

`predator_navigation/config/teco_nav2.yaml` 是使用 DWB 控制器的原地測試設定。它的碰撞監控輸出到
`cmd_vel` 而不是 `/nav2/cmd_vel_safe`，底盤不會收到指令，車子不會移動。

實車導航前，先取消任何現有目標，並停止舊的 Nav2 和底盤程序。同時只能有一組底盤在跑：
底盤程式會獨佔 `/dev/ttyS0`，後啟動的那組打不開序列埠，送給它的指令馬達收不到。

成本地圖和兩個碰撞監控都使用 40×40 cm 的方形車體外形（`footprint`），輪軸在正中央。
車子原地旋轉時，四個角會掃過直徑約 0.57 m 的圓。

### 確認 IMU 轉向方向

EKF 直接採用 IMU 的 Z 軸角速度。IMU 的正負號若與輪速相反，兩者會互相抵消，
轉向估計就會出錯。要讓車子在地面上實際轉動才看得出來，架高車輪時 IMU 量不到轉動，
所以請在空曠處進行並備妥急停。用鍵盤模式啟動底盤：

```bash
ros2 launch predator_bringup robot.launch.py drive:=true drive_source:=keyboard imu:=true ekf:=true rviz:=false
```

另外兩個終端機分別觀察輪速與 IMU 的偏航角速度：

```bash
ros2 topic echo /wheel/odom --field twist.twist.angular.z
```

```bash
ros2 topic echo /imu/gyro --field angular_velocity.z
```

再用 `keyboard_teleop` 按住 `A` 左轉。兩個數值都應該是正的，而且大小相近（約 0.3）。
IMU 是負的代表它的 Z 軸朝下，啟動時加上 `imu_roll:=3.14159` 翻轉 IMU 座標，再確認
`/odom` 的 `twist.twist.angular.z` 與 `/wheel/odom` 同號。建圖時也要用同一個 `imu_roll`。

## 鍵盤與 Nav2 共用底盤

`drive_source:=both` 讓底盤同時接受兩個來源，鍵盤優先：

```bash
ros2 launch predator_bringup robot.launch.py odom:=true drive:=true drive_source:=both imu:=false rviz:=false
```

Nav2 和 `keyboard_teleop` 照前面的方式各自啟動。

| 鍵盤狀態 | 底盤執行的指令 |
|---|---|
| 按住方向鍵 | 鍵盤 |
| 剛放開方向鍵（0.5 秒內） | 鍵盤的零速，車子停下 |
| 按下空白鍵（3 秒內） | 鍵盤的零速，按住可一直停著 |
| 沒有按鍵 | Nav2 |

使用時要注意：

- 兩個來源各自經過碰撞監控後才進入底盤仲裁，鍵盤接手時一樣會在障礙物前降速。
- Nav2 不知道被鍵盤接手，放開按鍵後會繼續往原目標前進。要完全接管，先在 RViz2 取消目標。
- `keyboard` 與 `nav2` 兩種模式各自只訂閱一個來源，切換模式要重新啟動底盤。

## 啟動參數

### `robot.launch.py`

| 參數 | 預設值 | 說明 |
|---|---|---|
| `lidar` | `true` | 啟動 SICK 光達驅動與 `base_link → cloud` |
| `lidar_ip` | `192.168.0.20` | 光達的 IP |
| `lidar_x` / `lidar_y` / `lidar_z` | `0.2` / `0.0` / `0.2` | 光達相對 `base_link` 的位置（公尺） |
| `lidar_yaw` | `0.0` | 光達的偏航角（弧度） |
| `odom` | `true` | 啟動底盤節點 `odom_control` |
| `drive` | `true` | 允許送出馬達指令。`false` 時只讀輪速 |
| `drive_source` | `keyboard` | 速度指令來源：`keyboard`、`nav2` 或 `both` |
| `teleop_safety` | `true` | 鍵盤指令先經過碰撞監控。需要光達；`false` 時鍵盤直接進底盤 |
| `base_port` | `/dev/ttyS0` | 底盤序列埠 |
| `wheel_odom_topic` | `/odom` | 輪速里程計的話題名稱。`ekf:=true` 時固定為 `/wheel/odom` |
| `publish_wheel_tf` | `true` | 由底盤節點發佈 `odom → base_link`。`ekf:=true` 時固定為 `false` |
| `imu` | `true` | 啟動 LPMS-ME1 驅動與 `base_link → imu_link` |
| `imu_x` / `imu_y` / `imu_z` | `0.0` / `-0.1` / `0.0` | IMU 相對 `base_link` 的位置（公尺） |
| `imu_roll` / `imu_pitch` / `imu_yaw` | `0.0` | IMU 的安裝角（弧度） |
| `ekf` | `false` | 用 EKF 融合輪速與 IMU，輸出到 `/odom`。需要搭配 `imu:=true` |
| `rviz` | `true` | 啟動 RViz2 |
| `joy` | `false` | 啟動 `joy_node`。手把沒有接到馬達控制 |

### `mapping.launch.py`

| 參數 | 預設值 | 說明 |
|---|---|---|
| `drive` | `false` | 允許送出馬達指令 |
| `imu` | `true` | 啟動 IMU 並納入 EKF |
| `mapping_rviz` | `true` | 啟動建圖用的 RViz2 |

建圖時底盤節點改發佈 `/wheel/odom` 且不發佈 TF，`odom → base_link` 由建圖自己的 EKF
負責，輸出到 `/odometry/filtered`。`robot.launch.py` 的 `imu_x`、`imu_roll`、`lidar_x`
等安裝位置參數也可以在這個啟動檔使用。`ekf` 參數在建圖時無效。

### `predator_navigation` 的 `navigation.launch.py`

| 參數 | 預設值 | 說明 |
|---|---|---|
| `map` | 套件內 `maps/teco_20261112_215618.yaml` | 地圖 YAML |
| `params_file` | 套件內 `config/teco_nav2_mppi.yaml` | Nav2 設定 |
| `rviz` | `True` | 啟動 RViz2 |
| `use_sim_time` | `False` | 使用模擬時間 |

## 話題與座標

| 話題 | 發佈者 | 說明 |
|---|---|---|
| `/scan` | `sick_scan_xd` | 光達掃描，角度 −1.57 到 +1.57 rad，`range_min` 0.05 m |
| `/odom` | `odom_control`，或 `ekf:=true` 時的 `ekf_filter_node` | Nav2 與 AMCL 使用的里程計 |
| `/wheel/odom` | `odom_control` | 輪速里程計，只在 `ekf:=true` 或建圖時使用 |
| `/odometry/filtered` | `ekf_filter_node` | 建圖時融合後的里程計 |
| `/imu/data_raw` | `lpms_imu` | 角速度與加速度 |
| `/imu/gyro` | `lpms_imu` | 給 EKF 使用的偏航角速度 |
| `/diagnostics` | `hardware_inventory` | 設備是否存在與存取權限 |
| `keyboard/cmd_vel` | `keyboard_teleop` | 鍵盤速度指令 |
| `keyboard/cmd_vel_safe` | `teleop_collision_monitor` | 經過碰撞監控的鍵盤指令 |
| `/nav2/cmd_vel_safe` | Nav2 碰撞監控 | 導航速度指令 |

兩個來源各自經過碰撞監控，再由底盤節點依優先序選用（鍵盤優先）：

```text
controller ─ cmd_vel_nav ─▶ velocity_smoother ─ cmd_vel_smoothed ─▶ collision_monitor ─ /nav2/cmd_vel_safe ─▶ odom_control
keyboard_teleop ─ keyboard/cmd_vel ─▶ teleop_collision_monitor ─ keyboard/cmd_vel_safe ──────────────────▶ odom_control
```

`teleop_safety:=false` 時鍵盤指令跳過 `teleop_collision_monitor`，直接送到 `odom_control`。

座標關係為 `map → odom → base_link`，`base_link` 底下有 `cloud`（光達）與 `imu_link`（IMU）。
`odom → base_link` 預設由 `odom_control` 發佈，`ekf:=true` 或建圖時改由 EKF 發佈，
同一時間只有一個來源。

底盤節點對所有來源套用相同的保護：

- 線速度限制在 ±0.12 m/s，角速度限制在 ±0.35 rad/s（`odom_control` 的 `max_linear_velocity`、
  `max_angular_velocity` 參數）。Nav2 的 MPPI、速度平滑器與旋轉恢復行為都設成相同的上限，
  改上限時要一起改 `predator_navigation/config/teco_nav2_mppi.yaml`。
- 超過 0.35 秒沒收到新指令就送零速。
- 停車時連續送出多個零速框，避免單一框遺失造成車子繼續移動。

## 硬體

| 設備 | 連接方式 | 狀態 |
|---|---|---|
| SICK TiM 5xx | 乙太網路 `enp0s31f6`，`192.168.0.20:2112` | 已發佈 `/scan` |
| TECO 底盤 | `/dev/ttyS0`，57600 baud | 已驗證 ID 1、2 的左右輪回饋 |
| LPMS-ME1 IMU | CP210x，115200 baud | 已發佈 `/imu/data_raw`。安裝方向與姿態尚未校正 |
| FTDI FT232 ×2、CP210x、CH340 | USB | 列入 `/diagnostics`。轉接器另一端的設備尚未確認 |
| 手把、攝影機 | — | 未找到可用的裝置 |

光達的網路由 NetworkManager 的 `SICK TiM LiDAR` 連線設定管理。
底盤參數：輪距 0.33 m、輪徑 0.1524 m、減速比 33。車體長、寬、高都是 40 cm，驅動輪軸
（`base_link`）在車體正中央，光達中心在車頭前緣、離地 20 cm（`lidar_x:=0.2`、`lidar_z:=0.2`）。

## 工作區結構

```text
ros2_ws/
├── setup_mapping.bash         每個終端機都要 source 的環境設定
└── src/
    ├── predator_bringup/      硬體啟動、建圖、鍵盤遙控、IMU 驅動、硬體盤點、EKF 與 Cartographer 設定
    ├── predator_navigation/   地圖、Nav2 設定、行為樹、導航與地圖伺服器啟動檔
    ├── odombase/              TECO 底盤驅動與輪速里程計
    ├── my_script_handler/     由 ROS 1 移植的訊息與服務型別
    └── nav2_mppi_controller/  Nav2 MPPI 控制器原始碼，編譯選項關閉 AVX
```

`nav2_bringup` 使用 apt 安裝的版本。`predator_navigation/maps` 內的 `0121` 和
`teco_gmapping` 是從 ROS 1 帶過來的舊地圖。

`my_script_handler` 只有介面定義，沒有服務實作。型別名稱使用 PascalCase，欄位使用
snake_case。舊 ROS 1 的 `move_base` 與 AMCL 參數沒有移植，導航改用 Nav2。

## 疑難排解

**序列埠出現權限錯誤。** 序列埠屬於 `dialout` 群組。確認目前使用者在群組內：

```bash
id -nG | grep -w dialout
```

沒有輸出的話加入群組，登出再登入後生效：

```bash
sudo usermod -aG dialout "$(id -un)"
```

IMU 的 `/dev/ttyUSB*` 編號會隨插拔順序改變，`lpms_imu` 用 `/dev/serial/by-id/` 底下的固定路徑開啟。

**`keyboard_teleop` 顯示 `Drive disabled or offline`。** 底盤沒有訂閱鍵盤指令。
確認底盤是用 `drive:=true` 啟動，而且 `drive_source` 是 `keyboard` 或 `both`。

**鍵盤顯示 `Drive connected` 但車子不動或很慢。** 鍵盤指令會經過碰撞監控：光達沒在跑時全部擋下，
前方有障礙物時降速或停車。先確認光達有資料：

```bash
ros2 topic hz /scan
```

再按住 `W`，看碰撞監控輸出的速度。`linear.x` 比鍵盤的 0.10 小，代表正在因障礙物降速：

```bash
ros2 topic echo /keyboard/cmd_vel_safe --field linear.x
```

**Nav2 有規劃路徑但車子不動。** 確認底盤的 `drive_source` 是 `nav2` 或 `both`，
並檢查碰撞監控是否有輸出：

```bash
ros2 topic hz /nav2/cmd_vel_safe
```

**收不到 `/scan`。** 確認 `SICK TiM LiDAR` 連線已啟用，而且 ping 得到光達：

```bash
ping -c 3 192.168.0.20
```

**兩個節點同時發佈 `/map`。** 即時建圖、`map.launch.py` 和 Nav2 一次只啟動一個。

## 已知限制

- 實車移動、急停，以及 `drive_source:=both` 的鍵盤與 Nav2 共用，都還沒在實車上驗證。
- 導航用的 `ekf:=true` 已在實車上確認接線與原地轉向，還沒實際跑過 Nav2 導航。
- IMU 的偏航角速度已確認與輪速同號（2026-11-16，`imu_roll:=0.0`，原地左右轉各約 300°，
  兩者相差 2% 以內）。IMU 的姿態、加速度和安裝位置尚未校正。
- 光達在車頭前緣、只看前方 180°，車身兩側與後方都看不到。鍵盤倒車（`S`）沒有保護；
  緊貼側邊障礙物原地旋轉時，碰撞監控也看不到車身旁邊的東西。
- 鍵盤碰撞監控與 Nav2 不倒車的設定，只用模擬底盤與假光達測過，還沒在實車上驗證。
- Nav2 速度平滑器與 MPPI 的加速度限制仍是原本的值，要等量到底盤實際加減速後再調。
- 手把只會發佈 `/joy`，沒有接到馬達控制。

## 授權

- `nav2_mppi_controller`：MIT，見 `src/nav2_mppi_controller/LICENSE.md`。
- `predator_navigation/behavior_trees`：修改自 Nav2 的行為樹，Apache-2.0。
- `predator_bringup`、`predator_navigation`、`odombase`、`my_script_handler`：尚未指定授權。
