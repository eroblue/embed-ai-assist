# S5c port-implementer Skill 需求

> 你现在是一位资深嵌入式开发专家，请帮我编写一个 AI Agent Skill。

## 基本信息

- **Skill 名称**：port-implementer
- **Skill 用途**：实现 S5b 定义的 Port / OSAL / Power 接口，将平台无关的调用翻译为具体 HAL / RTOS / 低功耗操作，扮演 Ports & Adapters 中的 Adapter 角色。`flat` 架构下跳过生成。
- **触发时机**：在 S5a 和 S5b 都完成后触发。
- **执行模型**：三段式（rule prepare → Agent generate → rule validate），与 S5a / S5b 一致。确定性的规则用本地脚本；Port/OSAL/Power 适配代码由 Agent 生成——新增平台/新增 RTOS 无需为本 Skill 编写任何适配脚本。

## 输入

### 从 `state.json` 读取

**S5a 字段**（来源：S5a hardware-initializer）：

- `s5a.init_sources`：S5a 产物源文件列表（`Drivers/BSP/Src/` 下）
- `s5a.init_headers`：S5a 产物头文件列表（`Drivers/BSP/Inc/` 下）
- `s5a.entry_source`：S5a 总入口源文件路径
- `s5a.rtos_hw_init`：RTOS 硬件初始化文件路径（可选）
- `s5a.power_init`：低功耗初始化文件路径（可选）
- `s5a.hardware_capabilities`：硬件能力清单路径
- `s5a.architecture` / `s5a.rtos` / `s5a.power_enabled`：本次使用的架构 / RTOS / 低功耗配置

**S5b 字段**（来源：S5b port-contract-and-app）：

- `s5b.port_manifest`：接口契约路径（`outputs/s5b/port_interface_manifest.json`）
- `s5b.port_headers`：Port 头文件路径列表（`Drivers/Port/Inc/` 下）
- `s5b.osal_header`：OSAL 头文件路径（可选，裸机为 null）
- `s5b.power_header`：Power 头文件路径（可选，未启用低功耗为 null）
- `s5b.architecture` / `s5b.rtos` / `s5b.power_enabled`：本次使用的配置

### 从项目级 `config.json`（与全局 `config.json` 合并后）读取

- `project.target`：MCU 型号
- `project.build_target`：目标工程（`"App"` / `"BootLoader"`，缺省 `"App"`）——`state.json` / 源码目录 / `outputs/` / IDE 工程目录均位于 `<项目根>/<build_target>/`，`docs/` 与 `references/` 为项目根共享
- `project.rtos`：RTOS 类型
- `project.architecture`：架构
- `project.power.enabled`：是否启用低功耗
- `project.inputs.ide_project`：IDE 项目文件路径（可选，缺省按 IDE 工程目录自动发现）
- `s5c.platform`：平台标识（文件命名后缀）
- `s5c.hal_framework`：HAL 框架（用于定位参考材料）

### 可选参考材料

- `references/demos/`：demo 程序（学习 API 写法）
- `references/sdk/`：SDK 源码（确认函数名/枚举名）
- `references/existing_project/`：已有项目（代码风格参考）

### 用户设计输入（`docs/s5c_design_input.md`）

用户向 Agent 传达实现约束的输入通道，**优先级高于自动推断**。文件不存在、内容为空或全部为 `none` 时，改由 Agent 基于 `hardware_capabilities`、接口契约与参考材料自主判断。

```markdown
# s5c设计输入， 告诉 Agent 实现约束.

## 低功耗方案
- 空闲时进入 STOP 模式
- 唤醒源：EXTI0 (PA0)、RTC 闹钟
- 睡眠前：关闭 UART、SPI 时钟

## 已有实现
- 参考 references/existing_project/power_mgmt.c
- 沿用 enter_sleep_before → enter_sleep → wakeup_after_sleep 命名
```

两段分别约束：低功耗策略（唤醒源/时钟门控/恢复流程，仅 `power.enabled` 时生效）、已有实现参考（命名约定与代码风格沿用）。

## 输出

### 文件拆分原则

S5c 生成的 Port 实现**必须按外设拆分成多个文件**，输出目录由 `docs/PROJECT_LAYOUT.md` 解析确定（32 位 layered 典型值为 `Drivers/Port/Src/`——与 S5b 的 Port 接口头目录 `Drivers/Port/Inc/` 对称）。

| 产物 | 生成条件 |
|---|---|
| `port_impl_uart_<平台>.c` | manifest 中存在 UART Port |
| `port_impl_i2c_<平台>.c` | manifest 中存在 I2C Port |
| `port_impl_spi_<平台>.c` | manifest 中存在 SPI Port |
| `port_impl_gpio_<平台>.c` | manifest 中存在 GPIO Port |
| `port_impl_adc_<平台>.c` | manifest 中存在 ADC Port |
| `port_impl_timer_<平台>.c` | manifest 中存在 Timer Port |
| `port_impl_pwm_<平台>.c` | manifest 中存在 PWM Port |
| `port_impl_osal_<rtos>.c` | `project.rtos != "none"`（含 flat 架构） |
| `port_impl_power_<平台>.c` | `project.power.enabled == true` 且非 flat |

**命名规范**：

- `<平台>`：小写字母，来自 `s5c.platform`（如 `gd32f205` / `stm32f103` / `ft61f14x`）
- `<rtos>`：全小写、连字符转下划线（如 `freertos` / `rtthread` / `zephyr`）
- `<外设>`：小写（uart / i2c / spi / gpio / adc / timer / pwm）

未被使用的外设不生成。每个实现文件 include S5b 的 Port 头文件，只实现对应接口。

### 写入 `state.json`（仅 `s5c` 字段）

| 字段 | 类型 | 说明 |
|---|---|---|
| `s5c.status` | string | `pending` / `running` / `done` / `error` / `skipped` |
| `s5c.rtos` | string | 本次生成使用的 RTOS 配置 |
| `s5c.architecture` | string | 本次使用的架构 |
| `s5c.power_enabled` | bool | 是否启用低功耗 |
| `s5c.generation_brief` | string | 任务书路径（`outputs/s5c/generation_brief.md`） |
| `s5c.port_impl_sources` | array | Port 实现源文件相对路径列表 |
| `s5c.osal_impl` | string/null | OSAL 实现源文件相对路径，裸机时为 null |
| `s5c.power_impl` | string/null | Power 实现源文件相对路径，未启用低功耗时为 null |
| `s5c.skipped_files` | array | 因用户已修改而跳过的文件列表（skip-if-modified） |
| `s5c.error` | string/null | 错误信息 |
| `s5c.updated_at` | string | ISO 时间戳 |

契约由 `schemas/output.schema.json` 约束。

### 写入 S5c 产物目录（Agent 生成的代码）

目录由 `docs/PROJECT_LAYOUT.md` 解析（prepare 段已幂等创建骨架），任务书给出确切路径。

### 写入 `outputs/s5c/`（数据）

| 产物 | 内容说明 |
|---|---|
| `generation_brief.md` | Agent 任务书（prepare 段）：manifest 接口清单 / 能力供给 / 映射要点 / ISR 规范 / 禁止事项 |
| `capability_gap.json` | 可选，prepare 阶段检测到 S5b 需要的硬件能力在 S5a 能力清单中不存在时输出，并**终止执行** |
| `file_hashes.json` | 生成文件哈希（skip-if-modified 依据） |

### 指针 / 数据分离规则

- 代码放 S5c 产物目录（`Drivers/Port/Src/`，由布局解析确定）
- 数据产物放 `outputs/s5c/`
- `state.json` 只存指针与统计，不存数据本体，不存代码本体

## Skill 目录结构（标准结构）

```text
port-implementer/
├── SKILL.md
├── schemas/
│   ├── input.schema.json              # 输入契约（S5a/S5b 就绪性 + 一致性检查）
│   ├── output.schema.json             # 输出契约（state.json 的 s5c 字段）
│   └── capability_gap.schema.json     # 能力缺口报告契约
├── scripts/                            # rule 轨（仅确定性契约工作，无代码生成）
│   ├── analysis.py                     # 共享分析（配置加载/manifest 解析/能力缺口/残留检测/哈希）
│   ├── prepare.py                      # 阶段 1：就绪检查 + 一致性检查 + 残留清理 + 任务书
│   └── validate.py                     # 阶段 3：产物校验 + IDE 同步调用
├── references/
│   ├── hal_mapping_guide.md            # HAL 映射指南（厂商 API ↔ Port 接口）
│   ├── rtos_mapping_guide.md           # RTOS 映射指南（RTOS API ↔ OSAL 接口）
│   ├── port_impl_pattern.md            # 实现模式（环形缓冲 / DMA 骨架 / 错误码映射）
│   └── isr_safety_rules.md             # 中断安全规范（回调判空 / 临界区 / ISR 上下文约束）
└── assets/
    └── port_impl_example.c             # 实现示例
```

> IDE 工程同步公共工具位于 `skills/_shared/scripts/ide_sync.py`（跨 Skill 共享，S5a/S5b/S5c 各自 validate 段调用）。

## 执行步骤

### 阶段 A：prepare（rule）

1. 从 `state.json` 读取 `s5a.*` 和 `s5b.*` 字段，确认 S5a 和 S5b 均已成功执行。
2. 读取项目级 `config.json`，与全局 `config.json` 深合并。
3. **配置一致性检查**（防漂移）：比对 `s5a.rtos/architecture/power_enabled` 与 `s5b.*` 对应字段，不一致 → 写 error（提示重跑其中一方使配置对齐）并终止（退出码 2）。
4. **能力缺口前置检测**：遍历 manifest 需要的硬件能力，在 `hardware_capabilities.json` 中查找；不存在 → 输出 `capability_gap.json` 并终止（退出码 2）。
5. **flat 判定**：`architecture == "flat"` → 跳过生成（S5b 已直接对接厂商库），`s5c.status` 置 `skipped`，终止。
6. **旧文件清理**：
   - 先执行"用户修改检测"（比对 `file_hashes.json`）标记哪些文件被用户改过
   - 再删除 S5c 产物目录下 **非当前平台/非当前 RTOS 的 `port_impl_*.c` 且未被标记为用户修改**的文件（换平台/换 RTOS 残留文件会导致编译失败）
   - 首跑（`file_hashes.json` 不存在）→ 所有文件视为"未改过"，正常清理
7. **生成任务书** `outputs/s5c/generation_brief.md`，内含：
   - 项目信息（平台、RTOS、架构、低功耗）
   - S5a 能力清单摘要（硬件实例、引脚、中断号）
   - S5b manifest 接口清单（每个外设的逻辑实例、接口签名、回调约定）
   - 映射要点（HAL API → Port 接口的对应关系）
   - ISR 安全规范引用
   - 用户修改文件清单（跳过重写）
   - 禁止事项
8. **生成推荐清单**（如有未指定项）：输出 `recommendations.json`（可选）。
9. 更新 `state.s5c.status = running`。

### 阶段 B：generate（agent）

10. 读任务书 + `SKILL.md` + `references/hal_mapping_guide.md` + `references/rtos_mapping_guide.md` + `references/port_impl_pattern.md` + `references/isr_safety_rules.md`。
11. 读 `docs/s5c_design_input.md`：存在且非空时以其为准；空/缺失时基于 `hardware_capabilities` 与参考材料自主判断。
12. 读 manifest + capabilities + 标准外设库头文件，**核对将要用到的 API 函数名/枚举名/时钟使能宏**——不确定的留 `/* TODO: */` 注释，不臆造 API。
13. 遍历 manifest 接口，按外设逐个生成实现文件到 S5c 产物目录：
    - 每个外设一个 `.c` 文件
    - 每个文件只实现对应外设的 Port 接口
    - **跳过任务书标注"用户已修改"的文件**
14. 若 `project.rtos != "none"`，生成 `port_impl_osal_<rtos>.c`。
15. 若 `project.power.enabled == true`，生成 `port_impl_power_<平台>.c`。
16. 遵守中断安全规范：ISR 内调用回调前**必须判断函数指针非 NULL**（回调未注册时清除中断标志直接返回，不得裸调）；DMA 隐藏在 Port 实现内。

### 阶段 C：validate（rule）

17. 产物校验：
    - manifest 中每个接口在对应实现文件中都有定义
    - 禁止 include 应用头文件（`app*.h` / `protocol_*.h`）
    - ISR 回调判空抽查（grep 回调调用点，检查前置判空）
18. 记录文件哈希到 `outputs/s5c/file_hashes.json`（validate 成功后写入）。
19. 调用公共工具 `skills/_shared/scripts/ide_sync.py` 同步 IDE 工程：
    - 扫描**目标工程根的源码目录**（`App/Src` + `Drivers/BSP/Src` + `Drivers/Port/Src` 等，由布局解析确定）
    - 差异同步（新增/删除/改 include 路径）
    - 失败不中断，输出 `outputs/_shared/ide_sync_manual.md` 手动清单
20. 更新 `state.s5c` 字段：
    - 成功 → `status: done`
    - flat → `status: skipped`
    - 校验失败 → `status: running`（保持，Agent 修复后重跑 validate）
    - 环境/契约失败 → `status: error`

> **编译验证由 S12 workflow-runner 在 S5c 之后编排 S7 build 执行，S5c 自身不调用工具链。**

## 使用方法

```bash
# 前置：S2、S3、S4、S5a、S5b 已在同一项目执行
python skills/port-implementer/scripts/prepare.py --config examples/gd32f205vet6/config.json
# → Agent 按 outputs/s5c/generation_brief.md 生成代码 →
python skills/port-implementer/scripts/validate.py --config examples/gd32f205vet6/config.json
```

## 依赖

- Python 3.10+
- `jsonschema`（契约校验）
- `xml.etree`（IDE 工程同步公共工具使用）
- **不需要交叉编译工具链**（编译验证移交 S7 build）

## 退出码

| 退出码 | 含义 |
|---|---|
| 0 | 成功（含 skipped） |
| 1 | 产物校验失败（state 保持 running，Agent 修复后重跑） |
| 2 | 配置错误 / 就绪失败 / 能力缺口 / 一致性冲突（state 写 error） |

## 禁止事项

- 不要修改 `config.json`，不要读写其他 Skill 的字段。
- 不要修改 S5a / S5b 产出的文件（含所有 `<外设>_port.h`、`osal.h`、`power_port.h` 接口定义）。
- 不得写任何应用业务逻辑。
- 不得生成 HAL 初始化代码（S5a 职责）。
- 必须优先读取 `port_interface_manifest.json`，不得硬解析 C 头文件。
- 硬件只依据 `hardware_capabilities.json`，**禁止直接读取 S3/S4 数据**。
- 能力缺口必须报 `capability_gap` 终止（prepare 阶段），不得偷偷改接口或降级实现。
- **ISR 内回调调用前必须判空**，不得裸调未注册的回调。
- 不得把所有 Port 实现塞进一个文件，必须按外设拆分。
- 不得把代码放在 `outputs/` 中，必须放在 S5c 产物目录（布局解析确定）。
- **不重写任务书标注"用户已修改"的文件**（skip-if-modified）。
- 不直接修改 IDE 工程文件——同步统一由公共工具 `skills/_shared/scripts/ide_sync.py` 完成。

## 补充说明

### 换平台 / 换 RTOS 的重跑规则

| 场景 | 重跑范围 |
|---|---|
| 换 MCU | S3 → S4 → S5a → S5c（触发旧文件清理 + 重新生成 port_impl）；S5b 产物不变（layered/full） |
| 换 RTOS | S5a（rtos_hw_init）→ S5c（OSAL 实现替换 + 清理旧 RTOS 残留）；S5b 产物不变 |
| flat 架构换平台 | S5c 跳过生成；需重跑 S5b（其产物平台相关） |

### 能力缺口处理

如果 S5b 定义的 Port 接口需要某硬件能力，但 S5a 的 `hardware_capabilities.json` 中没有提供，S5c 在 **prepare 阶段**输出 `capability_gap.json` 并终止（退出码 2）。**不得尝试修改接口或降级实现**——缺口是契约层问题，修复要回 S5a/S5b。

### skip-if-modified（用户修改检测）

与 S5b 相同的整文件级哈希比对：

1. validate 成功后把本轮生成文件哈希记入 `outputs/s5c/file_hashes.json`
2. prepare 重跑时逐文件比对：
   - 不一致 = 用户改过 → 任务书标注"跳过重写"
   - 一致 = 正常重生成
3. 被跳过的文件不接收上游变化；**删除该文件即恢复自动生成**
4. 跳过清单写入 `state.s5c.skipped_files`

**风险提示**：跳过的文件与上游 manifest 会逐渐漂移——接口变了、实现没跟上。任务书会在"用户修改文件清单"处标注 **⚠️ 接口漂移风险**，用户需自行判断是保留手改还是恢复自动生成。

### Port 实现的状态管理

每个 Port 实例（如 UART 的两个逻辑实例 wifi/debug）需要保存自己的状态（接收缓冲、回调函数指针等）。**建议实现约定**：

- 文件内 `static` 数组，按 instance id 索引（如 `static uart_impl_ctx_t s_uart_ctx[UART_PORT_COUNT];`）
- 不动态分配（符合"不用动态内存"约束）
- 上下文结构体声明在实现文件内（`static` 类型），不进头文件

### IDE 工程同步

IDE 工程文件（`.uvprojx` / `.ewp`）由公共工具 `skills/_shared/scripts/ide_sync.py` 同步：

- **扫描范围**：目标工程根下的**源码目录**（`App/Src` + `Drivers/BSP/Src` + `Drivers/Port/Src` 等，由 `PROJECT_LAYOUT.md` 解析确定），不是硬编码 `src/`
- **差异同步**：新增/删除/改 include 路径，保留原工程配置
- **并发安全**：全局文件锁
- **幂等**：重复调用不产生重复条目；无变化不写盘
- **备份/回滚**：修改前备份 `.bak`，写入失败自动恢复
- **失败不中断**：输出 `outputs/_shared/ide_sync_manual.md` 手动清单
- IDE 工程由用户手动创建，工具只做增量同步

### 文件拆分示例

一个使用 UART、I2C、GPIO、FSMC（LCD）、ADC 的 GD32F205 项目：

```text
Drivers/Port/
├── Inc/                       # S5b 产出（接口头）
│   ├── uart_port.h
│   ├── i2c_port.h
│   ├── gpio_port.h
│   ├── adc_port.h
│   ├── timer_port.h
│   └── osal.h                 # RTOS 时
└── Src/                       # S5c 产出（实现）
    ├── port_impl_uart_gd32f205.c
    ├── port_impl_i2c_gd32f205.c
    ├── port_impl_gpio_gd32f205.c
    ├── port_impl_adc_gd32f205.c
    ├── port_impl_timer_gd32f205.c
    └── port_impl_osal_freertos.c
```

### 接口语义约定来源

接口语义（错误码、超时、线程安全）按 **S5b 的 `references/port_design_principle.md`** 同一约定实现。S5c 的 `references/hal_mapping_guide.md` 会引用该约定，不重复定义。

### 编译验证边界

S5c **不做编译验证**。编译（含链接）由 S12 workflow-runner 在 S5c 完成后编排 S7 build 执行。原因：

- S5c 执行时 IDE 工程可能尚未创建（用户手工建工程）
- 完整编译需要工具链就绪，属于 build 阶段职责
- 保持职责单一：S5c 管"代码写对"，S7 管"编译通过"