# per-peripheral diff 规则（S5c 增量生成的核心机制说明）

> 本文说明 `scripts/port_differ.py` 的判定逻辑与产物——Agent 理解它才能正确执行
> per-peripheral 增量生成；用户理解它才能判断某次 manifest 改动会触发哪些文件重生成。
> 没有 diff，manifest 每动一处就会重跑整个 S5c、所有实现文件全变——**diff 是 S5c
> 与"一次性生成"的分水岭**（判定机制对标 S5b `flow_differ.py`，命名与阈值一致）。

## 一、基线与登记（三个判定维度）

| 维度 | 基线文件 | 检测什么 |
|---|---|---|
| **用户手改** | `outputs/s5c/file_hashes.json`（整文件 sha256） | 文件是否被用户/人工改过 |
| **接口变化** | `outputs/s5c/port_manifest_snapshot.json`（per-peripheral 签名摘要） | 上游 manifest 该单元的接口是否变了 |
| **设计输入变化** | 快照内的 `design_input_hash` | `docs/s5c_design_input.md` 是否变了（**仅提示，不自动改文件**） |

- 前两个维度**正交**，交叉判定生成模式（见第二节）；第三个维度只做提示。
- **设计输入变化为何只提示**：它是全局约束（不分单元），无法机械映射到具体实现文件；
  且变化未必需要改码（可能是补充说明）。任务书会标注"设计输入已变化"，
  由用户核对第 2 节原文后决定：删除受影响文件（下轮判 `full`）或走 `code-fix`。
  `port_diffs/*.json` 的 `design_input_changed` 字段承载该标记。
- 快照由 **validate 成功后写入**（本轮 manifest 签名摘要 + 设计输入哈希，作为下轮基线）；
  旧版本追加到 `port_manifest_snapshot_history/`，保留回溯（不修改历史版本）。
- `file_hashes.json` 的"用户手改过的文件保留旧基线"逻辑保持不变。

## 二、单单元判定链（按顺序短路）

一个"单元" = 一个 port_impl 文件 = 一次判定（外设取 slug(peripheral)；
OSAL/Power 取同名键，用 `kind` 区分）。

| # | 前提 | 判定 | generation_mode |
|---|---|---|---|
| 1 | 实现文件不存在（新单元） | 首次生成 | `full` |
| 2 | **用户手改** + 无签名基线（首次执行/新增单元） | 保护手改 | `skip`（+漂移标注） |
| 3 | **用户手改** + 接口变化 | 冲突 | `blocked`（报告用户） |
| 4 | **用户手改** + 接口未变 | 保护手改 | `skip`（+漂移标注） |
| 5 | 未手改 + 无签名基线（快照缺失 / 该单元无记录） | 建立/重建基线 | `full` |
| 6 | 未手改 + 接口未变 | 无变更 | `skip` |
| 7 | 未手改 + 变化率 > 60% | 大改 | `full` |
| 8 | 未手改 + 变化率 ≤ 60% | 定点修改 | `incremental` |
| 9 | manifest 已删除该单元（仅存于快照） | 外设删除 | `deprecated`（移除文件） |

**用户手改保护优先于"首次执行全 full"**：`skip-if-modified` 是硬约束——用户改过的
文件不得被自动重写（第 2 条）。"首次执行全部 full"只适用于未手改的文件。

## 三、diff 粒度与变化率

对每个单元把 manifest 条目规范化成**原子字段集**（`analysis.unit_fields`）：

```
instance:<名>|<描述>          # 逻辑实例
hw:<名>|<hw_instance>          # 硬件实例映射
config:<名>.<键>=<值>          # 实例配置属性
iface:<函数名>|<签名>          # 接口签名
iface_isr / iface_cb / iface_desc:<函数名>|<属性>
callback / callback_ctx / callback_desc:<回调名>|<属性>
note:<文本>
```

- **变化率** = `有增/删/改的字段数 ÷ 当前字段总数`（字段=原子属性）。
- **变更点数** `change_count` = 配对后的变更条目数（同类别同名的 added+removed
  合并为 `*_modified`，避免"改一个属性"被算成两个变更点）；供任务书展示与
  增量范围校验的预期基数。

| 变化率 | generation_mode | Agent 行为 |
|---|---|---|
| = 0（签名未变） | `skip` | 绝不动该文件 |
| ≤ 60% | `incremental` | 只做定点修改（`incremental_generation_rules.md`） |
| > 60% | `full` | 全量重生成该文件（大改，建议向用户说明范围） |

## 四、diff 产物

- `outputs/s5c/port_diffs/<单元>_diff.json`：单单元判定结果（schema 约束，
  含 `generation_mode` / `signature_changed` / `change_rate` / `change_count` /
  `file_hash_changed` / `changes` 明细 / `reason` / `drift_warning`）。
- `outputs/s5c/port_manifest_snapshot.json`：本轮签名快照（validate 写）。
- `state.s5c.generation_modes`：`{ "uart": "incremental", ... }` 汇总。

## 五、版本管理（用户操作向）

1. **改 manifest 即改契约**：S5b 侧修改 `port_interface_manifest.json` 后重跑 S5c，
   `port_differ` 自动按签名变化率判定该单元 full / incremental。
2. **快照不需要手工维护**：由 validate 在通过后自动写入；不要手工编辑
   `port_manifest_snapshot.json`（下轮 diff 会基于错误基线）。
3. **删除外设**：从 manifest 移除该外设条目后重跑，`port_differ` 判 `deprecated`，
   Agent 移除对应实现文件（IDE 引用由 `ide_sync.py` 收口）。
4. **换平台 / 换 RTOS**：文件名 token 变化 → 旧文件被残留清理（stale），
   新文件判 `full`（附 `hardware_capabilities` 差异重跑）。

## 六、Agent 执行要点

- 先看任务书"生成模式表"或 `port_diffs/*.json` 的 `generation_mode`：
  `full` 全量重生成、`incremental` 定点修改、`skip` **绝对不动**、
  `blocked` **报告用户**、`deprecated` 移除文件。
- `blocked` 不得自行处理——它是"用户手改 vs 上游变更"的冲突，须用户裁决。
- `skip` 含两类：接口未变（正常）与用户手改（漂移标注）；两者都不得重写。
- `full` 且变化率 > 60% 时先向用户说明重构范围，确认后执行。