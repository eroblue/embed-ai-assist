# S5c requirement 新增内容摘要

对照原始 requirement，本次增量版共新增 **3 个完整章节、5 个新字段、2 个新 schema、4 个新脚本/文档、若干表格与禁令**。按类别整理如下。

---

## 一、新增完整章节（3 个）

### 1. 生成模式总览

全新章节，位置在“Skill 目录结构”之后。包含：

- **per-peripheral 判定矩阵**：两个正交维度（用户手改 / 接口变化）交叉判定，7 种结果（skip / incremental / full / skip+漂移 / blocked / full 新建 / deprecated）
- **变化率算法**：定义“总字段数”和“变化率”的计算口径，阈值 `>60% → full`、`≤60% → incremental`、`=0 → skip`
- **首次执行规则**：无 snapshot → 全部 full 建基线
- **与 S5b 的一致性**：命名和阈值对标 `flow_differ.py`，便于统一心智模型

### 2. 分支入口：code-fix

全新章节。核心内容：

- **用途**：manifest 未变、hash 未变、实现有 bug 时的定点修复通道
- **设计依据**：引用 S5b 已立下的“分支入口原则”
- **触发条件**：用户显式指定“文件 + 函数 + 症状”
- **执行流程**：6 步（读文件 → 确认方案 → 定点修改 → 最小校验子集 → 更新 file_hashes → 报告）
- **不做事项**：6 条（不跑 prepare、不跑全量 validate、不改 state.status、不覆盖 snapshot 等）
- **与 skip-if-modified 的协同**：修完自动进入“用户维护”状态
- **后续扩展入口**：code-explain / code-refactor / code-add，只描述原则，不预建脚本

### 3. 向后兼容

全新章节。包含：

- **无 snapshot 的老项目**：首次全 full，validate 后写第一份 snapshot
- **无新字段的老 state**：prepare 读时给默认值
- **两个 hash 文件的关系**：明确 `file_hashes.json` 与 `port_manifest_snapshot.json` 是正交维度
- **改造顺序建议**：5 步渐进式落地（先观察、再打开增量、再加 code-fix、再提升共享、最后更新文档）

---

## 二、新增字段（state.json 3 个 + outputs 3 类）

### state.json 新增 3 个字段

| 字段 | 说明 |
|---|---|
| `s5c.port_manifest_snapshot` | 本轮写入的 manifest 快照路径 |
| `s5c.port_diffs` | 本轮每外设 diff 结果文件路径列表 |
| `s5c.generation_modes` | 每外设生成模式映射 `{ "uart": "incremental", ... }` |

### outputs/s5c/ 新增 3 类产物

| 产物 | 说明 |
|---|---|
| `port_manifest_snapshot.json` | 接口变化检测维度 |
| `port_diffs/<外设>_diff.json` | 每外设 diff 结果 |
| `diff_check_result.json` / `diff_anomaly.json` | 增量范围校验结果 |

---

## 三、新增文件（schema 2 个 + scripts 2 个 + references 2 个）

### schemas/

- `port_diff.schema.json` —— per-peripheral diff 结果契约
- `port_manifest_snapshot.schema.json` —— manifest 快照契约

### scripts/

- `port_differ.py` —— per-peripheral 生成模式判定
- `diff_range_checker.py` —— 增量代码范围校验（建议提升到 `_shared`）

### references/

- `port_diff_rules.md` —— 变化率算法 / 版本管理 / blocked 判定
- `incremental_generation_rules.md` —— 定点修改原则 / 范围校验阈值 / 异常处置

---

## 四、新增输入

### 历史产物（增量机制依据）

- `outputs/s5c/port_manifest_snapshot.json`
- `outputs/s5c/file_hashes.json`

---

## 五、修改的执行步骤

### prepare 阶段

- **新增第 7 步**：per-peripheral diff（读 snapshot → 调 port_differ → 产出 port_diffs/）
- **第 8 步（旧文件清理）** 表述补充“未被标记为用户修改”
- **第 9 步（任务书）** 新增“**每外设生成模式表**”（外设 / mode / 原因 / 手改状态 / 接口变化摘要）

### generate 阶段

- **第 15 步重写**：从“逐外设生成”改为“**按任务书的生成模式表逐外设处理**”，明确 5 种 mode 的处置
- **第 12 步** 补充：有 incremental 时加读 `incremental_generation_rules.md`

### validate 阶段

- **新增第 20 步**：增量范围校验（调 `diff_range_checker.py`）
- **新增第 22 步**：写入 manifest 快照
- **第 24 步**：state 收口新增 `port_manifest_snapshot` / `port_diffs` / `generation_modes` 三个字段

---

## 六、新增禁止事项（5 条 Agent 侧）

- `incremental` 模式无权重写整个文件，只做定点修改；diff 范围异常时不得自行修复
- `blocked` 模式必须报告用户（手改 + 上游变更冲突），不自行处理
- `skip` 模式绝对不动文件（含用户手改与接口未变两类）
- 首次执行（无 snapshot）时全部按 full 建基线，不跳过任何文件
- code-fix 分支入口不做全量 validate，只做最小校验子集；不改变 `state.s5c.status`；不动 `port_manifest_snapshot.json`

同时 **rule 脚本侧新增 1 条**：不修改 `port_manifest_snapshot.json` 的历史版本（只追加新版本）。

---

## 七、新增补充说明

### 换平台 / 换 RTOS 表新增 2 行

| 场景 | 重跑范围 |
|---|---|
| manifest 新增外设 | 只跑 S5c；该外设 full，其他按 diff 判定 |
| manifest 改单外设接口 | 只跑 S5c；该外设 incremental（≤60%）或 full（>60%），其他 skip |

### skip-if-modified 章节新增

- **与 code-fix 的协同**：code-fix 修完自动获得“用户维护”状态

### 新增“per-peripheral diff 细则”一节

- snapshot 结构示例（JSON）
- diff 结果结构示例（JSON）

### 新增“演进路径（供实施参考）”一节

5 步渐进式落地清单，每步可回退。

---

## 八、一句话总结

新增内容围绕三条主线：**① per-peripheral 增量机制**（判定矩阵 + 快照 + diff + 范围校验）、**② code-fix 分支入口**（vibe coding 通道）、**③ 向后兼容与演进路径**。原始 requirement 的核心逻辑（文件拆分、命名规范、能力缺口、状态管理、IDE 同步、编译验证边界）**全部保留未动**，新增内容是对“维护期迭代”场景的补充，不改变首轮生成的主流程契约。