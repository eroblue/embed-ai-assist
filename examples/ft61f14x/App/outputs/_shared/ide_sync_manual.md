# IDE 手动同步清单

- 生成时间：2026-09-20T12:14:55
- 目标工程：App
- 失败原因：未发现 IDE 工程文件（布局 IDE 目录 Project 下无 .uvprojx / .ewp）；IDE 工程由用户手动创建，请先创建工程后重新运行本工具

> 自动同步未完成，请按以下清单手动处理（完成后可重新运行 `ide_sync.py` 验证）。

## 需要添加到 IDE 工程的源文件（按 group 分组）

### group：Drivers/BSP
- `Drivers/BSP/Src/board_init.c`
- `Drivers/BSP/Src/clock_init.c`
- `Drivers/BSP/Src/nvic_init.c`
- `Drivers/BSP/Src/pwm_init.c`
- `Drivers/BSP/Src/uart_init.c`

## 需要添加的 include 路径

- `App/Inc`
- `Drivers/BSP/Inc`

## 操作指引

- **通用（任何 IDE，含 8 位机 IDE）**：在 IDE 中打开/新建工程后，将上述源文件全部加入工程的编译列表（通常在 Project/Add Files 或工程树右键菜单），并将上述 include 路径加入编译器的头文件搜索路径（编译选项中的 Include Directories / 头文件搜索路径）。
- **Keil**：Project 窗口右键 Target → Add Group → 按上述 group 命名 → 右键该 Group → Add Existing Files to Group → 选择对应源文件；include 路径在 Options for Target → C/C++ → Include Paths 中追加（分号分隔）。
- **IAR**：Workspace 右键 Project → Add → Add Group… → 右键 Group → Add → Add Files…；include 路径在 Project → Options → C/C++ Compiler → Preprocessor → Additional include directories 中追加。
- **工程文件不存在时**：请先在 IDE 中手动创建工程（选芯片、编译器等配置由人工确认更可靠），保存到 `<项目根>/<目标工程>/` 下的 IDE 工程目录（`Project/`，目录结构见 docs/PROJECT_LAYOUT.md），再重新运行 `python skills/_shared/scripts/ide_sync.py --project <项目根> --target <App|BootLoader> --ide <keil|iar>` 即可自动同步（仅 Keil/IAR 支持自动同步，其他 IDE 按本清单手动处理）。
