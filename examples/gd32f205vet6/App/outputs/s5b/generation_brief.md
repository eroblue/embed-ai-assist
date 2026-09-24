# S5b 代码生成任务书（generation_brief）

> 由 prepare.py 生成（rule 轨）。Agent 按本任务书执行两阶段生成，
> 操作规范见 `skills/port-contract-and-app/SKILL.md` 与 `references/`。
> 流程图未 approved 不生成代码；增量只做定点修改，禁止重写全文件。

## 1. 项目信息

- MCU（仅参考，Port 不得依赖厂商型号）：GD32F205VET6,LQFP100
- 架构：layered；RTOS：none；低功耗：未启用；语言标准：c99
- 数据来源模式：**设计输入驱动（降级模式：S2 spec 缺失）**

## 2. 输入材料清单（Agent 深查用）

- S2 功能规格书：**缺失**——以设计输入与 S4 硬件事实为主，Agent 按经验推荐方案（未指定项输出 outputs/s5b/recommendations.json 供用户确认）
- S4 硬件事实：`E:/skills/EmbedSoftAutomaticProject/embed-ai-assist/examples/gd32f205vet6/App/outputs/circuit_facts.json`（硬件实际连接，Port 实例映射依据；下面第 3 节为摘要）
- 用户设计输入：无（docs/s5b_design_input.md 缺失或全部为 none）——Agent 基于硬件事实与经验自主判断，推荐方案输出 recommendations.json
- （维护期增量：demo/SDK/已有项目学习材料本轮跳过，仅首次全量读取；如变更模块涉及新外设 API，按 config.json 中路径自行查阅）

## 3. 硬件事实摘要（S4 facts，Port 实例定义参考）

- FSMC：PE7（net LCD_DB4，role 并口/LCD 接口）；PE8（net LCD_DB5，role 并口/LCD 接口）；PE9（net LCD_DB6，role 并口/LCD 接口）；PE10（net LCD_DB7，role 并口/LCD 接口）；PD14（net LCD_DB0，role 并口/LCD 接口）；PD15（net LCD_DB1，role 并口/LCD 接口）；PD0（net LCD_DB2，role 并口/LCD 接口）；PD1（net LCD_DB3，role 并口/LCD 接口）；PD7（net LCD_CS，role 并口/LCD 接口）
- GPIO 输入：PA0-WKUP（net NetU1_23，role 唤醒输入）
- NC：PE2（net ?，role -）；PE3（net ?，role -）；PE4（net ?，role -）；PE5（net ?，role -）；PE6（net ?，role -）；VBAT（net ?，role -）；PC13-RTC_AF1（net ?，role -）；PA3（net ?，role -）；PA4（net ?，role -）；PA5（net ?，role -）；PA6（net ?，role -）；PA7（net ?，role -）；PC4（net ?，role -）；PC5（net ?，role -）；PB0（net ?，role -）；PB2（net ?，role -）；PE11（net ?，role -）；PE12（net ?，role -）；PE13（net ?，role -）；PE14（net ?，role -）；PE15（net ?，role -）；PB10（net ?，role -）；PB11（net ?，role -）；PB12（net ?，role -）；PB13（net ?，role -）；PB14（net ?，role -）；PB15（net ?，role -）；PD8/ USART2_TX（net ?，role -）；PD9/USART2_RX（net ?，role -）；PD10（net ?，role -）；PD11（net ?，role -）；PD12（net ?，role -）；PD13（net ?，role -）；PC7/USART5_RX（net ?，role -）；PC8（net ?，role -）；PC9（net ?，role -）；PA9/USART0_TX（net ?，role -）；PA10/USART0_RX（net ?，role -）；PA11（net ?，role -）；PA12（net ?，role -）；NC（net ?，role -）；PD2（net ?，role -）；PD3（net ?，role -）；PD4（net ?，role -）；PD5（net ?，role -）；PD6（net ?，role -）；PB3（net ?，role -）；PB4（net ?，role -）；PB5（net ?，role -）；PB6（net ?，role -）；PB7（net ?，role -）；PB8（net ?，role -）；PB9（net ?，role -）；PE0/UART7_RX（net ?，role -）；PE1/UART7_TX（net ?，role -）；VSS_3（net ?，role -）；VDD_3（net ?，role -）
- SPI：PA15（net SPI-CS，role SPI 通信）；PC10（net SPI-CLK，role SPI 通信）；PC11（net SPI-DO，role SPI 通信）；PC12（net SPI-DI，role SPI 通信）
- TIMER PWM：PA8（net LCD-PWM，role 定时器/脉冲输出）
- USART：PC6/USART5_TX（net DEBUG-TXD，role 串口通信）

## 4. 流程图现状（docs/flow/）

- 无流程图：首跑全量模式。按功能拆分逐模块新建（骨架见 `assets/flow_skeletons/`，规范见 `references/mermaid_*_guide.md`）

## 5. 能力缺口（rule 机械比对结果）

- 机械比对无缺口（设计输入引用的外设/引脚均在 S4 事实中）

## 6. 生成要求（两阶段：先模块后连接）

### 目录落点（来自 PROJECT_LAYOUT.md 解析，勿写其他目录）

- APP 源文件（`app*.c` / `protocol_*.c` / `main.c`）：`App/Src/`
- APP 头文件：`App/Inc/`
- 设备驱动（`driver_*.c/h`）：`Drivers/BSP/Src/` + `Drivers/BSP/Inc/`
- Port 接口头文件：`Drivers/Port/Inc/`（模板见 `assets/port_templates/`，裁剪/扩展后生成）
- 流程图：`docs/flow/<模块>_<state|flow|sequence>.md`（front-matter + Mermaid）

### 命名与拆分规范

- 模块名 = 代码文件基名（如 `app_wifi` → `App/Src/app_wifi.c/h` + `docs/flow/app_wifi_state.md`）
- APP 功能模块 `app_<功能>.c/h`；任务化 `app_<功能>_task.c/h`（仅 RTOS 且非 flat）；协议层 `protocol_<名称>.c/h`；驱动 `driver_<设备>.c/h`
- `app.c/h` 只做初始化汇总与主循环/任务创建；`main.c` 不存在时创建（只调 S5a 总入口 `board_init/hal_init` 与 `app_init`，不含业务逻辑）
- 未被使用的模块不生成；文件拆分细则见 `references/file_split_guide.md`

### 数据产物（outputs/s5b/）

- `port_interface_manifest.json`（S5c 实现 Port 的唯一依据，schema 约束，结构见 `assets/port_interface_manifest_example.json`）
- `traceability.json`（需求 → 流程图 → 文件 → 函数追踪矩阵）
- `recommendations.json`（仅当存在 Agent 推荐未定项时）
- `capability_gap.json`（发现缺口时更新；无缺口删除文件）

## 7. 增量模式（本轮生成范围）

- 流程图无变化：对应模块走 skip 分支，不重跑代码生成
- 已有 16 个现有产物文件（基线快照 outputs/s5b/code_baseline/）；增量修改后必须运行 diff_range_checker.py（变更行数超预期 3 倍即报错）

## 8. 禁止事项（硬约束）

- 所有 APP/Driver/协议层源文件不得 include 任何 HAL 头文件与 RTOS 头文件；RTOS 调用必须过 `osal.h`
- Port 接口只使用基本类型（stdint.h）和不透明句柄；厂商实例名/引脚号/网络名只进 manifest 数据，不进代码
- DMA 不暴露给 APP，隐藏在 UART 等实现内
- 不得把所有 APP 逻辑塞进一个 `app.c`（flat 架构除外）
- 不得在流程图未 approved 时生成对应模块代码；不得重新生成已有流程图（只做定点修改）
- 不得在流程图无变更时重跑对应模块代码生成（走 skip）
- 增量生成禁止重写整个文件（diff 范围校验拦截，超 3 倍报警置 error）
- 不修改 config.json / S2/S4 产物 / IDE 工程文件；不依赖 S5a 之外的产物（S5b 与 S5a 并行，Port 实现是 S5c 职责）
- 换平台/换 RTOS 时本 skill 产物内容哈希必须不变（平台无关性）

## 9. 执行步骤（Agent 操作序列，详见 SKILL.md）

1. 功能拆分：从 spec/设计输入/硬件事实提取功能模块清单（module_list，含模块名/来源/依赖/需确认点）
2. 阶段 A：逐模块写流程图（选对图类型：状态迁移→stateDiagram-v2、顺序流程→flowchart LR、模块交互→sequenceDiagram；骨架在 `assets/flow_skeletons/`）→ 运行 `flow_validator.py` 校验
3. 用户审核流程图（Agent 不得自行批准；用户确认后代改 status=approved 并填 approved_by）
4. 运行 `flow_differ.py` 生成各模块 diff 与生成模式 → 按模式生成/修改模块代码（映射规则 `references/flow_to_code_mapping.md`；增量后运行 `diff_range_checker.py`）
5. 阶段 A 续：生成 Port/OSAL/Power 头文件 + `port_interface_manifest.json`
6. 阶段 B：顶层连接（`app.c`/`main.c`/任务文件）+ `traceability.json`
7. 运行 `validate.py` 终验；失败按报告修复后重跑
