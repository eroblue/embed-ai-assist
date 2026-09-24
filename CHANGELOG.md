# 更新日志（Changelog）

本项目所有显著变更记录于此。格式参考 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)（Skill 契约以 schema `$id` 版本为准）。

## [Unreleased]

### Fixed - 2026-09-23

**S5b port-contract-and-app：缺陷修复第一批（并发安全 / 检测准确性 / 状态完整性）**

- **修复 state.json 并发写丢失**：新增公共工具 `skills/_shared/scripts/state_store.py`
  （O_EXCL 独占文件锁 + 陈旧锁自动清理 + 锁内完成读改写），S5a 4 处与 S5b 5 处
  state 写入点全部接入——与 S5a 并行执行不再互相覆盖丢字段
- **修复能力缺口检测子串误匹配**（`analysis.py`）：引脚/实例匹配由子串包含改为
  精确 token 匹配（大写归一），PA1 不再被 PA10 误判为"可用"，缺口不再漏报
- **修复 diff_range_checker 写 error 时覆盖整个 `state.s5b`**：改为锁内保留
  `rtos/architecture/power_enabled` 等现有字段，仅覆盖 status/error/updated_at，
  prepare 的配置变化检测不再因字段缺失漏检

### Added - 2026-09-23

**S5b port-contract-and-app：守卫增强与维护期优化**

- **flow_differ 守卫增强**：version 回退（如 1.2 → 1.1）同样拦截为 blocked
  （与"同版本内容修改"分别提示）；diff 基线读取前校验 `.history` 快照正文 hash
  与 flow_index 记录一致，不一致输出告警并在 diff 结果标记 `baseline_mismatch`
- **prepare 维护期输入裁剪**：flow_index 已存在时任务书自动跳过 demos/sdk/
  existing_project 学习材料（首轮全量学习，增量轮次按任务书标注路径按需查阅）
- **SKILL.md 新增「执行模式总览」章节**：full/incremental/skip/blocked 为
  flow_differ 逐模块判定（同一轮可混合）；维护操作分支入口原则（独立 Agent 入口，
  不建空壳脚本/参数）

### Changed - 2026-09-23

**S5b requirement.md 与实现对齐（框架收口）**

- 目录树 23 脚本 → 7 个已实现散件 + `functional_decomposer.py`（标注规划中，
  S2 spec.json 就绪后实现）；`task_spec.json` → `generation_brief.md`（9 节）；
  `flow_to_code_mapper.py` / `incremental_generator.py` 改为 Agent 职责
  （按 references 映射规则执行）
- `software_spec.*` 定位明确为 `s5b_design_input.md` 的补充技术输入，冲突时以
  设计输入为准；能力缺口检测由"发现即终止"改为 warning 复核 + error 级 validate
  拦截；`recommendations.json` 增量轮次不重复推荐已确认项；Mock 改可选后处理；
  traceability 粒度放宽至文件级；流程图节点数值参数软约束（参数名旁注当前值）
- 删除配置项 `project.inputs.functional_spec`（功能规格书统一经 S2 接入）；
  功能规格数据统一从 S2 输出的 spec.json 读取
- **四文档一致性修复**：`state.s5b.status` 去除无写入方的 `skipped`；
  flat + RTOS 的 osal.h 生成条件统一为正交论（OSAL 与外设 Port 层正交，
  flat + RTOS 也生成 osal.h，任务化 APP 仍限非 flat）——prepare/validate
  脚本、requirement、SKILL.md 对齐；换平台/换 RTOS"产物哈希不变"补限定
  （仅 layered/full 且硬件连接语义不变，flat 需重跑）；生成模式枚举与
  `flow_diff.schema.json` 对齐（SKILL.md 执行模式总览补 `deprecated`，
  requirement 补 `blocked` / `deprecated`）

### Added - 2026-09-23

**S1 schematic-reader：PDF 原理图支持（schema v1.0 → v1.1，向后兼容）**

- **S1 支持 PDF 原理图输入**：`schematic_path` 支持 `.pdf`（矢量 + 文字层），
  通过扩展名或 `eda_tool: pdf` / `schematic_format: "pdf"` 自动路由到 PDF 适配器；
  `config.json` 修改 `schematic_path` 即可切换输入格式，无需新建示例工程
- **S1 新增置信度分级与人工核对清单**：PDF 输入时每条连接输出
  `confidence` / `method` / `note`（`pin_name_match` 0.95 / `net_label` 0.90 /
  `line_intersection` 0.75 / 邻近推断 0.50），置信度 < 0.7 的连接全部写入
  `outputs/pdf_review.md` 人工核对清单，不得静默丢弃；整体置信度与低置信度
  计数写入 `state.json` 的 `circuit.confidence` / `circuit.low_confidence_count`
- **S1 新增 pdf_adapter 适配器**（`skills/schematic-reader/scripts/adapters/pdf_adapter.py`）：
  pdfplumber 优先 / PyMuPDF 兜底的字符级聚词（字号分层 + 紧排负间隙容差 +
  双层文本去重）、元件框互最近关联、`PI<位号><脚号>` 引脚标注兜底、
  导线并查集连通（端点/T 型/junction 合并）、悬空网络过滤（单端点自动命名
  网络判悬空，引脚保留 `net=null`）、BOM/表格页自动跳过

**Schema 增量扩展（全部可选字段，源文件输入行为与 v1.0 完全一致）**

- `input.schema.json`：新增可选 `schematic_format`
- `output.schema.json`：`circuit` 新增可选 `source_format` / `confidence` /
  `low_confidence_count` / `review_path`
- `netlist.schema.json`：引脚/端点新增可选 `confidence` / `method` / `note`
  （`$id` 保持 `embedaiassist.netlist.v1` 不变）
- 根目录 `config.schema.json`：`eda_tool` 枚举新增 `pdf`，新增可选 `schematic_format`

**文档与资源**

- 新增 `skills/schematic-reader/references/pdf_extraction_guide.md`（PDF 提取
  原理、关键算法、置信度模型、已知精度边界、降级策略）
- 新增 `skills/schematic-reader/assets/pdf_review_example.md`（核对清单格式示例）
- 更新 `skills/schematic-reader/SKILL.md`（PDF 输入输出说明、依赖、禁止事项）

**验证**

- SchDoc 回归：stm32f103zet6 示例输出与 v1.0 逐字段一致（仅时间戳差异），
  原有工作流不受影响
- PDF E2E：正点原子战舰板 5 页原理图（233 元件 / 290 网络 / 660 连接，
  整体置信度 0.808），关键元件引脚识别正确（U2 120/144、U6 4/4、U8 3/3、
  U9 8/8、U12 4/4），已知精度损失（MCU 电源脚无引脚号文字、少量层叠词
  噪声网络名）均记录于提取指南并进核对清单

### Added - 2026-09-23

**S2 spec-reader：功能规格书阅读器（新 Skill，三段式）**

- **S2 新 Skill**：功能规格书（md / docx / pdf）→ 结构化需求 `spec.json`
  （S5b 消费）。执行模型与 S5a/S5b 一致：rule prepare（提取文本 +
  `raw_text.md` 存档 + 生成 `generation_brief.md` 任务书）→ Agent 生成
  （`spec.json` / `spec_trace.json` / `uncovered.json`）→ rule validate
  （结构校验 + 交叉引用校验 + 收口）；`state.json` 新增 `spec` 字段
  （running / success / partial / failed，指针/数据分离，写入走
  `state_store` 文件锁）；失败收口清理 Agent 半成品、保留 rule 产物
- **5 个 schema 契约**：`requirements[].category` 枚举
  functional / interface / performance / constraint（interface 承载
  功能级外设需求，波特率/引脚等技术细节仍归 S5b 设计输入）；
  `spec_trace` 恰好覆盖全部 REQ-ID（missing / extra / dupes 三查）；
  每条 REQ 至少归属一个 feature；状态机 from/to ∈ states
- **3 个格式提取器**（适配器模式，按扩展名分发）：markdown
  （utf-8-sig 容错 + gbk 回退）、docx（python-docx 段落/表格按文档
  顺序迭代，标题层级含中文样式与 Title）、pdf（pdfplumber 逐页提取
  + `<!-- page N -->` 页码标记 + 表格转 Markdown）；缺依赖明确报错
  不降级；扫描件 PDF 提示需 OCR 不支持
- **references / assets**：spec_extraction_guide（六类信息识别模式 +
  自检清单）、requirement_taxonomy（category/priority 判定 + 越界示例）、
  spec_json_format（逐字段规范）3 个指南；spec_example（12 REQ /
  9 feature）、spec_trace_example 2 个示例（均通过 schema 校验）

**配置与示例**

- 根 `config.schema.json`：project 下新增可选 `inputs` 对象
  （`functional_spec` 为 S2 必选输入，另有 software_spec /
  s5b_design_input / demos / sdk / existing_project / ide_project）
- gd32f205vet6 示例：新增 `docs/functional_spec.md`（SmartEnvGuard
  规格）与 `project.inputs.functional_spec` 配置；`App/outputs/s2/`
  含完整 E2E 产物（12 REQ / 9 feature / 0 uncovered → success）

**跨 Skill 兼容（Fixed）**

- S5b `input.schema.json`：`spec.status` 枚举补 `running`、`spec_path`
  与 `software_spec_path` 改可空——S2 running 期间并行执行 S5b 不再
  触发输入契约报错，而是按设计走设计输入驱动降级模式

**验证**

- 12 项测试矩阵全过：md E2E 正路径、坏引用拦截（exit 1 + failed +
  产物清理）、修复恢复、state.json 完整性（仅增 spec 字段）、缺
  functional_spec（exit 3）、非法 build_target（schema 拦截）、缺
  state.json（提示先执行 S1）、docx 缺依赖、pdf/docx 提取、缺三产物
  （exit 1）、partial 收口（uncovered 非空）
- 与 S3/S4/S5a 可并行；S5b 消费 spec 须后于 S2 收口（gd32 success 态
  S5b 正确解析 `spec_path`）

### Fixed - 2026-09-24

**S4 circuit-investigator：主控识别支持 PDF 提取网表**

- **修复 PDF 网表下主控识别失败**：S1 PDF 适配器输出的网表元件 `value`
  常为空（PDF 中型号文字未关联进 value 字段），S4 仅按 value 匹配平台名
  导致 `网表中未找到主控元件` 直接 failed。`_find_mcu_component` 增加
  回退策略：value 未命中时按引脚数最多的 U* 元件识别（主控通常是引脚
  最多的 U 位号元件），回退命中计入 warning 提示人工复核
- 战舰板 PDF E2E 验证：U2（120 脚）正确识别为 STM32F103ZET6 主控，
  交叉验证 97 脚 / 4 冲突 / 64 警告 / 23 NC；SchDoc 网表（value 齐全）
  仍走 value 匹配路径，行为不变
