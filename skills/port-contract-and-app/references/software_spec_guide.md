# 软件规格书/设计输入提取要点（S5b Agent 从需求材料到模块拆分的工作方法）

> 本文回答一个问题：拿到任务书（`outputs/s5b/generation_brief.md`）第 2 节列出的输入材料后，**逐份材料读什么、产出什么**。
> 拆分与流程图的质量上限由输入理解深度决定——只扫一眼标题就开始写代码是 S5b 失败模式第一名。

## 一、输入优先级（冲突时取上）

| 优先级 | 材料 | 位置/来源 | 说明 |
|---|---|---|---|
| 1 | 用户设计输入 | `docs/s5b_design_input.md`（或 `project.inputs.s5b_design_input`） | 用户亲笔意图，**逐段原文已内嵌任务书**，冲突时以它为准 |
| 2 | S2 功能规格书 | `state.spec.spec_path`（JSON） | 功能需求/外设需求/性能指标的权威来源 |
| 3 | 软件规格书 | `project.inputs.software_spec` | 用户已有文档（md/doc/pdf），按文件类型读取 |
| 4 | S4 硬件事实 | `state.circuit.facts.facts_path` | 不是需求，是**约束**：硬件实际有什么、接在哪 |
| 5 | demo/SDK/已有项目 | `project.inputs.demos/sdk/existing_project` | 参考实现模式，**不引入厂商 API** |
| 6 | Agent 经验 + 用户对话 | — | 兜底；产生的未定项必须进 `recommendations.json` 让用户拍板 |

缺失降级：S2 spec 缺失 → 设计输入驱动模式（任务书已标注）；设计输入也全 none → **Agent 自主判断模式**——更要把每个假设写进 recommendations.json，并在 traceability 的 requirement 字段标注数据来源（`design_input`/`spec`/`agent_judgment`/`user_dialog`）。

## 二、S2 功能规格书（JSON）提取要点

spec 是 S2 产物、结构以实际文件为准（S2 当前未强制 schema），按下表**语义字段**提取，字段名对不上时按语义就近映射：

| 要找的内容 | 提取产物 |
|---|---|
| 功能/需求清单（编号、描述、优先级） | 模块拆分初稿 + traceability.json 的 requirement 条目（**保留原编号**） |
| 状态/模式类描述（"连接后进入低功耗"、"充电阶段切换"） | `_state.md` 候选模块清单 |
| 步骤/流程类描述（"上电自检→加载配置→..."） | `_flow.md` 候选模块清单 |
| 模块间交互/通信协议描述 | `_sequence.md` 候选 + Port 接口需求 |
| 周期/时延/吞吐指标（"100ms 轮询"、"响应 < 50ms"） | 任务划分依据（RTOS 任务/主循环轮询表）；写进模块头文件注释 |
| 错误处理要求（重试、降级、告警） | 流程图错误分支（review 重点，不得省略） |
| 外设使用需求 | 与 S4 facts 比对（prepare 已做机械比对，Agent 复核 warning 项） |

## 三、设计输入（s5b_design_input.md）已知段用法

任务书已按段内嵌原文。八个已知段 → 产出：

| 段 | 产出 |
|---|---|
| 功能规格 | 模块拆分 + traceability（来源 design_input） |
| 状态机 | 直接转 `_state.md`（该段通常已是状态列表/迁移描述） |
| 时序 | 直接转 `_sequence.md` |
| 错误处理 | 各模块流程图的错误分支 |
| 硬件使用 | 逻辑实例定义（`UART_PORT_WIFI` 等）；prepare 已机械比对 S4 |
| 功能映射 | 功能 → 外设实例的分配，决定 Port 逻辑实例与 hw_instance |
| 协议 | `protocol_<名称>.c/h` 模块 + 协议状态机/解析流程图 |
| 任务划分 | 任务化模块（`app_<功能>_task.c`，仅 RTOS 且非 flat）；冲突时以本段为准 |

非已知段标题的内容也不许丢——通读全文，未覆盖的诉求并入最接近的模块并记 traceability。

## 四、参考材料（demo/SDK/已有项目）的使用边界

- **可取**：任务结构、状态划分思路、协议帧格式、参数默认值、错误处理策略、注释风格。
- **不可取**：厂商 API 直呼（`HAL_UART_Transmit`）、寄存器操作、RTOS 原生接口名、`#include` 依赖、具体引脚号/网络名硬编码（这些属于 S5a/S5c 层，S5b 代码只允许逻辑实例）。
- 参考取材须在 traceability.remark 或模块头注释标注出处（"参考 demo xxx 的状态划分"），方便回溯。

## 五、从需求到模块拆分的判据

1. **每个功能模块必须能画成恰好一张图**（一模块一图）：画不下 → 太大，拆；画出来只有两个节点 → 太小，并。
2. 模块名动词化、可对应一个 `.c` 文件（`app_wifi`、`driver_key`、`protocol_modbus`）。
3. 有独立硬件交互的 → driver（板载器件）；纯逻辑/协议 → app/protocol；只被别人调用的公共算法 → 并入使用方，不单独成"utils"模块（避免垃圾桶模块）。
4. 拆分结果先列清单（模块名 + 一句话职责 + 图类型 + 需求来源编号）给用户过目，**再开始画图**——拆分返工比画图返工贵十倍。

## 六、未定项处理（recommendations.json）

凡输入材料没给答案、Agent 自主拍板的项（默认参数、任务优先级、协议超时值、模块边界取舍），逐条记录：

```json
{
  "topic": "app_wifi 重连间隔",
  "recommendation": "5s 指数退避（上限 60s）",
  "reason": "设计输入未指定；参考 demo_at_modem 的退避策略",
  "impact_if_wrong": "重连风暴或恢复过慢，仅影响参数不改结构"
}
```

结构性假设（模块边界、接口形态）必须等用户确认后再生成对应代码；参数级假设可先生成、但要在最终汇报中列出。
