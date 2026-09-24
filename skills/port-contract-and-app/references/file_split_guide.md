# 文件拆分规范（S5b Agent 产物文件组织）

> 目录落点由任务书给出（PROJECT_LAYOUT.md 解析）：APP 源/头 → `App/Src|Inc/`，
> 设备驱动 → `Drivers/BSP/Src|Inc/`，Port 头 → `Drivers/Port/Inc/`，
> 流程图 → `docs/flow/`，数据产物 → `outputs/s5b/`。

## 一、拆分原则

1. **按功能模块拆**：一个功能模块一对 `.c/.h`（模块名 = 文件基名 = 流程图模块名）；
   状态机/流程图与代码文件一一对应（追踪矩阵依赖此约定）。
2. **未被使用的模块不生成**：S4 硬件事实里有但应用没用的外设不写驱动；
   没有协议需求不写 protocol_*。
3. **职责单一**：`app.c` 只做初始化汇总与主循环/任务创建；
   `main.c` 只调 S5a 总入口（`board_init`/`hal_init`）与 `app_init`/`app_run`；
   业务逻辑一律在 `app_<功能>.c`。
4. **不得把所有 APP 逻辑塞进一个 app.c**（flat 架构除外——flat 允许合并，
   但仍建议至少拆出 `app.c` + 高内聚功能模块）。

## 二、命名规范

| 产物 | 命名 | 示例 |
|---|---|---|
| APP 主入口 | `app.c/h` | `app_init()` / `app_run()` |
| APP 功能模块 | `app_<功能>.c/h` | `app_led.c` / `app_wifi.c` |
| 任务化 APP | `app_<功能>_task.c/h`（仅 RTOS 且非 flat） | `app_wifi_task.c` |
| 协议层 | `protocol_<名称>.c/h` | `protocol_at.c` |
| 设备驱动 | `driver_<设备>.c/h` | `driver_eeprom.c` |
| 主入口 | `main.c` | 不存在时创建 |
| 流程图 | `<模块>_<state\|flow\|sequence>.md` | `app_wifi_state.md` |

- 函数命名：模块前缀 + 动词（`app_led_init` / `protocol_at_send_cmd` / `driver_eeprom_read`）；
  模块对外接口在 `.h` 声明，内部函数 `static`。
- 状态机状态 → 枚举 `<模块>_state_t { <MODULE>_ST_XXX }`；事件 → `<模块>_evt_t`。
- 一模块一流程图：复合逻辑拆子模块（如 `app_wifi_seq`），不允许同模块多张图。

## 三、文件内结构模板

```c
/* app_led.c - LED 指示功能（S5b port-contract-and-app 生成） */
#include "app_led.h"
#include "gpio_port.h"      /* 平台无关 Port 接口 */

/* ---------------- 私有类型/变量 ---------------- */
/* ---------------- 私有函数 ---------------- */
/* ---------------- 公开接口（.h 声明） ---------------- */
```

- 头文件带 include guard（`APP_LED_H`），只 include 自己直接用到的头；
- `.c` 首行注释标注模块用途与来源 skill；
- 不确定的外部行为留 `/* TODO: */` 注释说明，不臆造。

## 四、指针/数据分离（硬规则）

- 代码只进 S5b 产物目录，**不进 `outputs/`**；
- 数据产物（manifest/traceability/flow_diff）只进 `outputs/s5b/`，**不进源码目录**；
- `state.json` 只存指针与清单，不存代码与数据本体。

## 五、IDE 工程

不修改任何 IDE 工程文件（.uvprojx/.ewp 等）——新增源文件与 include 路径
由公共工具 `skills/_shared/scripts/ide_sync.py` 在 validate 段自动同步；
同步失败时输出 `outputs/_shared/ide_sync_manual.md` 手动清单。
