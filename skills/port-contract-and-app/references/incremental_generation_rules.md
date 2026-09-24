# 增量生成规则（S5b Agent 定点修改代码的行为约束）

> 适用范围：`flow_diffs/<模块>_diff.json` 中 `generation_mode=incremental` 的模块。
> 核心红线（requirement 原文）：**Agent 无权重写整个文件，它只做定点修改。**
> 这一页是防止"每次小改动都全文件重写、代码面目全非"的关键防线。

## 一、输入

| 材料 | 位置 | 用途 |
|---|---|---|
| 现有代码 | `App/Src/<模块>.c` 等（上轮产物） | 修改基底，**原样保留未涉及部分** |
| 变更点 | `outputs/s5b/flow_diffs/<模块>_diff.json` | added/removed/renamed/modified 明细 |
| 映射规则 | `references/flow_to_code_mapping.md` 第五节 | 每类 diff 条目 → 代码动作 |

## 二、定点修改原则

1. **只动映射表要求的对应物**：diff 里没有的状态/节点/函数，一行都不碰（包括"顺手优化"）。
2. **保持节点标记注释**：`/* 节点 A[加载配置] */` 等锚点注释是下一轮 diff 定位与人工对照的依据，修改语句块内容时更新注释、不得删除锚。
3. **重命名走全局替换**：节点/状态 renamed → 同步重命名枚举成员、函数与全部引用点，**不得保留旧名兼容别名**（兼容层是垃圾的温床）。
4. **删除要干净**：removed 节点/迁移 → 删函数/分支后 grep 模块内引用，无引用才收工；跨模块引用（公开 API 被删）→ 更新调用方并登记 traceability 变化。
5. **接口变更同步 manifest**：时序图消息增删导致 Port 接口变化时，`port_interface_manifest.json` 必须同轮更新。
6. **行数自律**：每个变更点预期 ≤ 15 行代码改动（15 行足够放一个 case 分支/一个函数体语句块）；自感要写超 → 先怀疑映射错了，不是"这条改动比较特殊"。

## 三、diff 范围校验（`diff_range_checker.py`，生成后必跑）

| 指标 | 阈值 | 判定 |
|---|---|---|
| 新增行数 | > 变更点数 × 15 × 3 | 异常（added_overflow） |
| 删除行数 | ≥ 基线行数 80% 且预期变更量 < 基线行数 | 异常（rewrite，整文件重写特征） |
| 无关行改动 | 应为 0 | （空行差异不计；异常即越界修改） |
| 模块文件缺失 | incremental 模式找不到 `<模块>.c/h` | 异常（missing，增量要求文件已存在） |

- 基线：prepare 段镜像的 `outputs/s5b/code_baseline/`（上轮产物副本 + sha256 索引）。
- 正常 → `outputs/s5b/diff_check_result.json`；异常 → `outputs/s5b/diff_anomaly.json` + `state.s5b.status=error`，当前文件**保留现状**（不回滚、不覆盖，上轮内容在 code_baseline/ 可对照）。

## 四、异常后的处置流程

1. Agent **不得自行"修复后继续"**——先向用户报告 diff_anomaly.json 内容。
2. 用户二选一：
   - **定点修复**：Agent 对照 code_baseline 恢复越界改动，重新做最小修改；
   - **转全量**：用户确认本次确实是大改动 → 流程图 version 递增、重走 flow_differ 判定（预期落 full）→ 全量生成。
3. 处置完成后重跑 `diff_range_checker.py` 直到通过，再进 validate 终验。

## 五、skip 模块（同样重要）

`skip` 模块的代码文件**一个字符都不改**。重跑 skip 模块的常见借口（"顺便统一格式"、"补个注释"）全部无效——格式化需求应作为独立变更走流程图/设计输入，单独一轮处理。

## 六、自检清单（每个 incremental 模块改完）

- [ ] diff json 里每类条目都有对应代码动作，无遗漏、无多余。
- [ ] 节点标记注释保留/更新。
- [ ] renamed 全局替换干净（grep 旧名 0 命中）。
- [ ] 接口变更已同步 manifest 与 traceability。
- [ ] 预估行数在 变更点 × 15 内；超了先自查映射。
