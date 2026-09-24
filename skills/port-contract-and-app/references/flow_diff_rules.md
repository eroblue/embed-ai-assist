# 流程图 diff 规则（S5b 增量生成的核心机制说明）

> 本文说明 `scripts/flow_differ.py` 的判定逻辑与产物——Agent 理解它才能正确执行增量生成；用户理解它才能正确走"修改流程图 → 重新审核 → version 递增"的循环。
> 没有 diff，每次改动就会重跑整个模块、代码全变，回到 Vibe Coding 的老路——**diff 是 S5b 与"一次性生成"的分水岭**。

## 一、基线与登记

- **基线快照**：`docs/flow/.history/<模块>/<版本>.md`，由 flow_differ 在每次 `full/incremental/skip` 判定后自动写入（不依赖 git；git 提交历史是首选长期保留方案，.history 是本工具的确定性基线）。
- **流程图清单**：`outputs/s5b/flow_index.json`——**只登记 `approved` 与 `deprecated` 流程图**（draft/review/dirty 不登记，避免未定稿内容污染基线）。
- **正文哈希**：front-matter 之后的 mermaid 正文 sha256，用于快速判定"内容是否变过"。

## 二、单模块判定链（按顺序短路）

| # | 前提条件 | 判定 | generation_mode | 说明 |
|---|---|---|---|---|
| 1 | status=deprecated | 废弃 | `deprecated` | 登记保留；**对应代码应由 Agent 移除**（含 IDE 工程引用） |
| 2 | status=draft/review | 未定稿 | `blocked` | 不生成代码、不登记 index |
| 3 | status=dirty | 定稿后被改 | `blocked` | 必须重新审核：用户确认后回 approved 且 version 递增 |
| 4 | approved，index 无记录 | 首次 | `full` | 全量生成模块代码 |
| 5 | approved，index 哈希一致 | 无变更 | `skip` | **不得重跑该模块代码生成**（硬规则） |
| 6 | approved，版本号未递增但内容变了 | 违规修改 | `blocked` | 同 3：重新审核 + version+1 |
| 7 | approved，version 已递增，基线快照存在 | 有基线 | diff 后按变化率定 | 见第三节 |
| 8 | approved，version 已递增，基线快照缺失 | 基线丢失 | `full` | 按 .history/<旧版本>.md 不存在处理，全量生成 |

## 三、diff 粒度与变化率

对状态图/流程图/时序图分别提取节点与边（`analysis.py::parse_mermaid` 的语法子集，超集写法不参与 diff）：

| 图类型 | 节点 | 边 |
|---|---|---|
| stateDiagram-v2 | 状态名 | (from, to, "事件 / 动作") 三元组 |
| flowchart | 节点 id（label 参与重命名检测） | (from, to, 条件) 三元组 |
| sequenceDiagram | 参与者 | (from, to, 消息文本) 三元组 |

**重命名检测（仅 flowchart）**：新图中新增节点与旧图中消失节点若 label 相同 → 判 renamed（节点 id 变了、含义没变），并把重命名映射应用到旧边再比对——避免"挪一下节点 id"被误判成大量删+增。**stateDiagram/sequenceDiagram 节点名即身份**，重命名报为 remove+add（所以状态名要一次定好，改名成本真实存在）。

**modified 边**：起止点相同、标签（条件/事件/消息文本）变化 → modified。改 label 措辞也算 modified——写图时措辞一次到位。

**变化率** = `change_count / max(总节点 + 总边, 1)`，
其中 `change_count = added + removed（节点）+ renamed + added + removed + modified（边）`。

| 变化率 | generation_mode | Agent 行为 |
|---|---|---|
| = 0（内容哈希变了但节点/边无实质变化） | `skip` | 不重跑 |
| ≤ 60% | `incremental` | 只生成变更点对应代码（见 `incremental_generation_rules.md`） |
| > 60% | `full` | 全量生成（**提示工程师确认**） |

## 四、diff 产物

- `outputs/s5b/flow_diffs/<模块>_diff.json`：单模块 diff 结果（schema 约束，含 nodes/edges 明细、change_ratio、generation_mode、change_summary、base_version）。
- `outputs/s5b/flow_index.json`：更新后的流程图清单（模块/文件/版本/状态/哈希/节点边计数）。

## 五、版本管理规则（用户操作向）

1. **修改 approved 流程图**必须：status 置 `dirty`（或改完由校验拦截提醒）→ 用户重新审核 → 确认后 `version` 递增（如 1.0 → 1.1）→ status 回 `approved` → 重跑 `flow_differ.py`。
2. `base_version` 字段记录"基于哪个版本修改"，供追溯；diff 实际基线取 index 中记录的上轮版本快照。
3. **删除模块**：流程图文件删除后，flow_differ 会报告"流程图文件已不存在，对应代码应由 Agent 移除"；正式废弃请保留文件置 `deprecated` 而不是直接删文件（deprecated 路径保留登记，Agent 依此清理代码）。

## 六、Agent 执行要点

- 收到任务后先看 `flow_diffs/*.json` 的 generation_mode：`full` 模块走全量生成、`incremental` 走定点修改（`incremental_generation_rules.md`）、`skip` **绝对不动**、`blocked` 报告用户等待处理、`deprecated` 移除对应代码。
- `full`（>60%）时先向用户说明重构范围，确认后执行。
- flow_differ 写快照的时机是判定完成时——**不要手动编辑 .history/**，快照必须与 index 哈希一致。
