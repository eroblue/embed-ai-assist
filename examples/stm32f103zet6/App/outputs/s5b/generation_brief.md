# S5b 代码生成任务书（generation_brief）

> 由 prepare.py 生成（rule 轨）。Agent 按本任务书执行两阶段生成，
> 操作规范见 `skills/port-contract-and-app/SKILL.md` 与 `references/`。
> 流程图未 approved 不生成代码；增量只做定点修改，禁止重写全文件。

## 1. 项目信息

- MCU（仅参考，Port 不得依赖厂商型号）：stm32f103zet6
- 架构：layered；RTOS：none；低功耗：未启用；语言标准：c99
- 数据来源模式：S2 功能规格书驱动

## 2. 输入材料清单（Agent 深查用）

- S2 功能规格书：`outputs/s2/spec.json`（功能需求/外设需求/性能指标的权威来源）
- S4 硬件事实：`E:/skills/EmbedSoftAutomaticProject/embed-ai-assist/examples/stm32f103zet6/App/outputs/circuit_facts.json`（硬件实际连接，Port 实例映射依据；下面第 3 节为摘要）
- 用户设计输入：`docs/s5b_design_input.md`（优先级最高，原文段落见下方）
- （维护期增量：demo/SDK/已有项目学习材料本轮跳过，仅首次全量读取；如变更模块涉及新外设 API，按 config.json 中路径自行查阅）

### 设计输入原文（按段提取）

**功能规格**：

**状态机**：

**时序**：
> | 项目 | 周期 / 时间 |
> |---|---|
> | 主循环 | 10ms |
> | DHT11 采集 | 2s |
> | 光照采集 | 2s |
> | LCD 刷新 | 200ms |
> | 串口上报 | 5s |
> | 按键去抖 | 50ms |
> | 蜂鸣器告警 | 1s 响 / 1s 停 |
> | LED1 心跳 | 1Hz（500ms 亮 / 500ms 灭） |
> | LCD 告警闪烁 | 1Hz |
> ---

**错误处理**：

> spec 数据较大不内嵌，Agent 自行读取上述路径；提取要点见 `references/software_spec_guide.md`。

## 3. 硬件事实摘要（S4 facts，Port 实例定义参考）

- BOOT0：?（net BOOT0，role BOOT0）
- FSMC：?（net LCD_BL，role 并口/LCD 接口）；?（net LCD_BL，role 并口/LCD 接口）；?（net FSMC_D2，role 并口/LCD 接口）；?（net FSMC_NOE，role 并口/LCD 接口）
- FSMC_A18：?（net FSMC_A18，role FSMC_A18）
- FSMC_D0：?（net FSMC_D0，role FSMC_D0）
- FSMC_D1：?（net FSMC_D1，role FSMC_D1）
- FSMC_D14：?（net FSMC_D14，role FSMC_D14）
- FSMC_D15：?（net FSMC_D15，role FSMC_D15）
- FSMC_D2：A（net FSMC_D2，role FSMC_D2）
- GPIO 输入：?（net WK_UP，role 唤醒输入）
- I2C：?（net OV_SCL，role I2C 通信）；?（net IIC_SDA，role I2C 通信）
- NC：VBAT（net ?，role -）；A（net ?，role -）；OSC_IN（net ?，role -）；?（net ?，role -）；?（net ?，role -）；VSSA（net ?，role -）；Vref-（net ?，role -）；?（net ?，role -）；?（net ?，role -）；?（net ?，role -）；?（net ?，role -）；?（net ?，role -）；?（net ?，role -）；?（net ?，role -）；?（net ?，role -）；?（net ?，role -）；?（net ?，role -）；?（net ?，role -）；?（net ?，role -）；NC（net ?，role -）；?（net ?，role -）；A（net ?，role -）；?（net ?，role -）；?（net ?，role -）
- SDIO：?（net SDIO_D1，role SD 卡接口）；?（net SDIO_CMD，role SD 卡接口）
- SDIO_D0：?（net SDIO_D0，role SDIO_D0）
- SDIO_D3：?（net SDIO_D3，role SDIO_D3）
- SPI：A（net SDIO_SCK，role SPI 通信）；?（net VS_SCK，role SPI 通信）；?（net VS_MOSI，role SPI 通信）；?（net SPI2_MISO，role SPI 通信）；?（net T_MISO，role SPI 通信）
- SPI2_SCK：?（net SPI2_SCK，role SPI（SPI2_SCK））
- TIMER PWM：?（net PWM_DAC，role 定时器/脉冲输出）
- USART：?（net USART2_TX，role 串口通信）；?（net USART3_RX，role 串口通信）
- USART1_RX：?（net USART1_RX，role 接收（USART1_RX））
- USART3_TX：?（net USART3_TX，role 发送（USART3_TX））
- USB：?（net USB_D-，role USB 接口）
- VDDA：VDDA（net VDDA，role VDDA）
- VREF+：Vref+（net VREF+，role VREF+）
- 复位：NRST（net RESET，role 复位）；?（net DM9000_RST，role 复位）

## 4. 流程图现状（docs/flow/）

| 模块 | 图类型 | 版本 | 状态 | 本轮是否有修改 |
|---|---|---|---|---|
| app_alarm_control | state | 1.0 | approved | 否 |
| app_env_sensor | flow | 1.0 | approved | 否 |
| app_key_handler | state | 1.0 | approved | 否 |
| app_mode_control | state | 1.0 | approved | 否 |
| app_oled_display | flow | 1.0 | approved | 否 |
| app_uart_report | sequence | 1.0 | approved | 否 |

- 修改已有流程图时**以现有文件为锚点做定点修改**，不重新生成；approved 后修改须将 status 置 dirty，重新审核后 version 递增

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
- 已有 42 个现有产物文件（基线快照 outputs/s5b/code_baseline/）；增量修改后必须运行 diff_range_checker.py（变更行数超预期 3 倍即报错）

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
2. 阶段 A：逐模块写流程图（选对图类型：状态迁移→stateDiagram-v2、顺序流程→flowchart TD、模块交互→sequenceDiagram；骨架在 `assets/flow_skeletons/`）→ 运行 `flow_validator.py` 校验
3. 用户审核流程图（Agent 不得自行批准；用户确认后代改 status=approved 并填 approved_by）
4. 运行 `flow_differ.py` 生成各模块 diff 与生成模式 → 按模式生成/修改模块代码（映射规则 `references/flow_to_code_mapping.md`；增量后运行 `diff_range_checker.py`）
5. 阶段 A 续：生成 Port/OSAL/Power 头文件 + `port_interface_manifest.json`
6. 阶段 B：顶层连接（`app.c`/`main.c`/任务文件）+ `traceability.json`
7. 运行 `validate.py` 终验；失败按报告修复后重跑
