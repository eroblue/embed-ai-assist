---
name: "spec-reader"
description: "S2 规格书阅读器，三段式执行模型：rule 脚本 prepare.py 检查工作区就绪（仅依赖 S1）、按扩展名调用提取器（md/txt 直读、docx 用 python-docx、pdf 用 pdfplumber，未装依赖报错不降级）把功能规格书转成 Markdown 化原文 raw_text.md，并生成 Agent 任务书 generation_brief.md；Agent（LLM）按任务书把非结构化文本提取成结构化需求 spec.json（REQ-XXX 条目 + F-XXX 功能域 + 业务状态机/时序/错误处理/阈值）+ 需求追溯 spec_trace.json + 未定项清单 uncovered.json；rule 脚本 validate.py 做 schema 校验与引用一致性校验并收口 state.spec（success/partial/failed）。S2 只管'产品要什么'（需求侧），技术实现细节（帧格式/引脚映射/波特率等）归 S5b 设计输入。在 S1 建立工作区后触发，与 S3/S4/S5a 可并行；S5b 消费 spec.json 必须后于 S2 收口。"
---

# spec-reader 规格书阅读器（S2）

## 用途

从原始功能规格书（Markdown / Word / PDF）出发，把非结构化文本转成结构化
需求 JSON（`spec.json`），供 S5b 消费。S2 只管**"产品要什么"**（需求侧），
不管**"技术上怎么实现"**（设计侧）。

**整体流程层级：S2，需求结构化层（平台无关）。**

- 触发时机：S1 建立工作区后即可执行
- 并行关系：与 S3 / S4 / S5a **无数据依赖，可并行**
- 时序约束：**S5b 若需消费 spec.json（spec 驱动模式），必须后于 S2 收口**
  ——若并行，S5b 将因 `state.spec` 缺失走设计输入驱动降级模式（S2 白跑）
- 下游消费：**S5b port-contract-and-app** 读 `requirements[]` /
  `features[]` / `business_*` / `thresholds[]`，结合 `s5b_design_input.md`
  生成模块清单与代码

## 执行模型：rule 准备 → Agent 提取 → rule 校验

**策略（与 S5a/S5b 一致）**：确定性的规则用本地脚本实现；需求条目的
识别、归类、摘要由 Agent（LLM）完成——不同写法的规格书无需任何适配脚本。

```
[rule]  prepare.py    分层配置加载（functional_spec 必选检查）→ 按扩展名
                       选提取器 → outputs/s2/raw_text.md（Markdown 化原文，
                       PDF 带 <!-- page N --> 页码标记）→ 任务书
                       outputs/s2/generation_brief.md → state.spec = running

[agent] Agent 提取    读任务书 + references/（提取要点/分类规范/字段规范）
                       → 逐章节识别需求/状态机/时序/错误处理/阈值
                       → outputs/s2/spec.json（REQ-XXX + F-XXX + 业务结构）
                       + spec_trace.json（每条 REQ 的原文追溯）
                       + uncovered.json（未定项清单，可为空数组）

[rule]  validate.py   三产物 schema 校验 + 引用一致性（REQ 不重复、
                       features/timing/error_handling/thresholds 引用存在、
                       状态机迁移合法、每条 REQ 至少归属一个 feature、
                       spec_trace 恰好覆盖全部 REQ、source_file 与 config
                       一致）→ 统计 spec_summary → state 收口：
                       无未定项 success / 有未定项 partial / 失败 failed
```

- 校验失败（退出码 1）→ 已清理无效产物，Agent 按失败报告修复后重新生成，
  **重跑 validate.py**
- 环境/配置失败（退出码 3）→ state 写 failed + error（spec_path=null，
  不留半成品指针）
- 修改 config 指向新规格书后：重跑 prepare → Agent 重提取 → validate

## 目录结构

```
spec-reader/
├── SKILL.md                          ← 本文件（Agent 操作手册）
├── schemas/
│   ├── input.schema.json             ← 输入契约（state.json 就绪性检查）
│   ├── output.schema.json            ← 输出契约（state.json 的 spec 字段）
│   ├── spec.schema.json              ← spec.json 结构契约（核心）
│   ├── spec_trace.schema.json        ← 追溯矩阵契约
│   └── uncovered.schema.json         ← 未定项清单契约
├── scripts/
│   ├── analysis.py                   ← 共享分析（配置加载/格式识别/上下文）
│   ├── prepare.py                    ← 阶段 1：提取原文 + 生成任务书
│   ├── validate.py                   ← 阶段 3：校验 + state 收口
│   └── extractors/                   ← 各格式文本提取器（适配器模式）
│       ├── __init__.py               ← 提取器注册（按 source_type 分发）
│       ├── markdown_extractor.py     ← .md/.txt 直读
│       ├── docx_extractor.py         ← .docx（python-docx，段落+表格有序提取）
│       └── pdf_extractor.py          ← .pdf（pdfplumber，逐页+页码标记）
├── references/
│   ├── spec_extraction_guide.md      ← 规格书提取要点（Agent 依据）
│   ├── requirement_taxonomy.md       ← 需求分类与优先级规范
│   └── spec_json_format.md           ← spec.json 字段规范
└── assets/
    ├── spec_example.json             ← spec.json 示例（SmartEnvGuard）
    └── spec_trace_example.json       ← spec_trace.json 示例
```

## 输入 / 输出

### 输入

| 来源 | 字段 | 说明 |
|---|---|---|
| state.json | 无 | S2 是流水线早期 Skill，只依赖工作区存在（state.json 存在） |
| config.json | `project.build_target` | 目标工程（App/BootLoader，缺省 App），决定 state/outputs 位置 |
| config.json | `project.inputs.functional_spec` | **必选**，功能规格书路径（相对项目根） |
| config.json | `project.inputs.software_spec` | 可选，软件规格书路径（**仅登记指针，不解析**） |
| config.json | `s2.language` | 可选，输出语言（默认 zh-CN，仅影响描述字段） |
| config.json | `s2.strict_mode` | 可选，严格模式（默认 false；启用后模糊描述只进 uncovered 不臆断） |

### 输出

**state.json（仅 `spec` 字段，经 state_store 文件锁原子写入）**：

| 字段 | 说明 |
|---|---|
| `spec.status` | running / success / partial / failed |
| `spec.spec_path` | `outputs/s2/spec.json` 相对路径（success/partial 必填；failed 为 null，不留半成品指针） |
| `spec.software_spec_path` | 软件规格书路径指针（config 指定时登记；S5b 实际以 config 为准） |
| `spec.spec_summary` | `{total_requirements, feature_count, uncovered_count}` |
| `spec.source_file` | 原始规格书路径（相对项目根） |
| `spec.updated_at` / `spec.error` | ISO 时间戳 / 失败原因 |

**outputs/s2/**（指针/数据分离：state 只存指针与统计）：

| 产物 | 说明 |
|---|---|
| `raw_text.md` | 原文 Markdown 化提取（保留标题层级；PDF 插 `<!-- page N -->` 页码；表格转 Markdown） |
| `generation_brief.md` | Agent 任务书（prepare 生成） |
| `spec.json` | 结构化需求（**核心产物**，S5b 消费） |
| `spec_trace.json` | 需求追溯（REQ-ID → 章节/页码/原文引用），恰好覆盖全部 REQ |
| `uncovered.json` | 未定项清单（模糊描述/缺失项，供用户确认；无未定项时 items=[]） |

## 执行步骤

### 阶段 A：prepare（rule）

```bash
python skills/spec-reader/scripts/prepare.py --config <项目>/config.json
```

1. 分层加载配置（根 config.json → 项目 config.json 深合并），校验
   `project.inputs.functional_spec` 存在且文件可读（缺失 → failed 退出）。
2. 按扩展名选提取器，提取原文到 `outputs/s2/raw_text.md`。
3. 生成任务书 `outputs/s2/generation_brief.md`（项目信息/原文摘要/输出
   要求/条目化规范/未定项原则/原文全文）。
4. `state.spec.status = running`。

### 阶段 B：generate（agent）

5. 读任务书 + `references/spec_extraction_guide.md` +
   `references/spec_json_format.md`（分类判定见
   `references/requirement_taxonomy.md`）。
6. 逐章节扫描识别需求条目：`REQ-XXX` 顺序编号不跳号，`source.section` /
   `source.page` 可定位原文，`acceptance` 提取验收标准。
7. 归类功能域 `features[]`（`F-XXX`），提取 `business_states[]` /
   `business_timing[]` / `error_handling[]` / `thresholds[]`。
8. 写 `spec.json` + `spec_trace.json` + `uncovered.json`（写前逐个过
   schema 自检；结构参考 `assets/` 示例）。

### 阶段 C：validate（rule）

```bash
python skills/spec-reader/scripts/validate.py --config <项目>/config.json
```

9. 三产物 schema 校验 + 引用一致性（见执行模型图）+ 统计。
10. state 收口：无未定项 `success`；有未定项 `partial`（用户确认
    uncovered 后修订 spec 并重跑）；失败 `failed` + error（清理无效产物）。

## 使用方法

```bash
# 前置：S1 已建立工作区（state.json 存在）；项目 config.json 配置：
#   "project": {"inputs": {"functional_spec": "docs/functional_spec.md"}}

# 1. 运行 prepare 提取原始文本 + 生成任务书
python skills/spec-reader/scripts/prepare.py --config examples/gd32f205vet6/config.json
# → Agent 按 outputs/s2/generation_brief.md 生成三个产物

# 2. 运行 validate 终验
python skills/spec-reader/scripts/validate.py --config examples/gd32f205vet6/config.json

# 3. 查看结果
#    examples/gd32f205vet6/App/state.json      -> spec 字段
#    examples/gd32f205vet6/App/outputs/s2/     -> raw_text.md + spec.json
#                                                 + spec_trace.json + uncovered.json
```

## 依赖

- Python 3.10+
- `jsonschema`（契约校验，必装）
- `python-docx`（可选，.docx 提取；未装时 .docx 报错退出，不降级）
- `pdfplumber`（可选，.pdf 提取；未装时 .pdf 报错退出，不降级）

## 禁止事项

- 不修改 `config.json`，不读写其他 Skill 的 state 字段。
- **不提取技术实现细节**：帧格式、命令码、波特率、校验方式、引脚映射、
  DMA、外设选择、消抖/调度/心跳实现方式——这些归 S5b 从
  `s5b_design_input.md` 读取。
- **不生成 `module_list.json`**（S5b 产物）、**不做 feature → module 映射**
  （S5b 职责），S2 只输出功能域标签 `features[]`。
- **不解析 `software_spec` 内容**——只登记路径到 state。
- `spec.json` 中不内联"如何实现"的描述，只写"要什么"。
- 数据量大的产物放 `outputs/s2/`，`state.json` 只存指针与统计。
- `spec.status=failed` 时不留半成品产物文件（prepare 失败清空 outputs/s2/，
  validate 失败清理三个 Agent 产物）。

## 与 S5b 的职责边界

| 内容 | 提取方 |
|---|---|
| 功能清单、业务状态、业务时序、错误策略、数据项、阈值范围 | **S2**（规格书里明确写的，业务级） |
| 帧格式、命令码、波特率、校验方式、引脚映射、DMA、外设选择 | **S5b**（技术细节，来自 `s5b_design_input.md`） |
| 模块拆分（`module_list.json`）、流程图、Port 接口、C 代码 | **S5b**（技术决策与产物） |

关键区分：`spec.json`（S2）= 需求条目清单 + 业务域标签；
`module_list.json`（S5b）= 功能模块清单（可映射到 `.c/.h`）。两者是不同
层的东西，不要混。
