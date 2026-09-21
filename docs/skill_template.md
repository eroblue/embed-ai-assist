# embed-ai-assist Skill 通用模板

> 后续 14 个 skill 均按本模板生成。第一个 skill（schematic-reader）为本模板的参考实现，
> 位于 `skills/schematic-reader/`。

## 一、标准目录结构

每个 skill 统一采用以下目录结构：

```
skills/<skill-name>/
├── SKILL.md                     ← 技能说明（给 Agent 看，必选）
├── schemas/
│   ├── input.schema.json        ← 输入契约（必选）
│   ├── output.schema.json       ← 输出契约（必选：state.json 对应字段，仅指针+统计）
│   └── <产物名>.schema.json     ← 产物数据契约（可选：数据量大的 outputs/ 产物结构约束）
├── scripts/                     ← 可执行脚本（必选）
│   ├── <main>.py                ← 主入口（读配置 → 分发 → 产出 → 更新 state）
│   └── adapters/                ← 按工具类型分发的适配器（可选，有多种工具时使用）
│       ├── <tool_a>_adapter.py
│       └── <tool_b>_adapter.py
├── references/                  ← 参考文档（可选：格式规范、领域知识、协议说明）
│   └── <topic>.md
└── assets/                      ← 资源文件（可选：示例输出、样例数据、模板文件）
    └── <sample>.xlsx
```

说明：

- `references/` 与 `assets/` 为 2026-09 新增标准目录，所有 skill 均需创建（可为空或按需填充）
- 适配器模式：同一功能支持多种外部工具（EDA/烧录器/编译器/串口工具）时，主入口只做
  配置读取与分发，具体工具逻辑写入 `adapters/`，避免主入口膨胀
- 大块数据（网表、芯片手册提取结果、日志等）一律写入 `outputs/`，不放 skill 目录内

## 二、需求描述模板（写新 skill 需求时使用）

向 AI 提需求时，按以下格式描述（以 schematic-reader 为参考范例）：

```
你现在是一位资深嵌入式开发专家，请帮我编写一个AI Agent Skill。

Skill名称：<skill-name>
Skill用途：<一句话说明做什么、处理什么文件/数据、产出什么>。
当<触发场景>时触发。

输入：
- 从config.json读取<配置字段>（<含义>）
- 从config.json读取project.workspace（输出目录）
- 可选参数<参数名>：<可选值枚举>（默认<默认值>）

输出：
写入state.json（仅<state字段名>字段）：
- <state字段名>.<key1>：<含义>
- <state字段名>.<key2>：<含义>
- <state字段名>.status：success / partial / failed

写入outputs/：
- outputs/<产物文件1>：<内容说明>
- outputs/<产物文件2>：<内容说明（如有 Excel/报告类产物，注明列定义与格式规范）>

（数据量大的产物需同步定义schemas/<产物名>.schema.json，写入前校验；
state.json只存产物路径指针与统计，不存数据本体）

Skill目录结构（标准结构，所有skill统一）：
<skill-name>/
├── SKILL.md / schemas/ / scripts/ / references/ / assets/
（详见 embed-ai-assist/docs/skill_template.md）

执行步骤：
1. 从config.json读取<输入>，检查<前置条件>
2. 根据<分发参数>选择适配器或执行分支
3. <核心处理逻辑>
4. 将<产物>写入outputs/
5. 将<状态/路径/统计信息>写入state.json

依赖：Python 3.10+，<第三方库清单>
禁止事项：不要修改config.json，不要读写其他Skill的字段
```

## 三、SKILL.md 标准结构

```markdown
---
name: "<skill-name>"
description: "<做什么 + 何时触发，200字符以内>"
---

# <skill-name> <中文名>

## 用途
<功能描述，以及在整体流程中的层级（S1~Sx）和上下游依赖>

## 目录结构
<标准目录树及各文件职责>

## 输入
<参数表格：参数 / 来源 / 类型 / 必填 / 说明>

## 输出
### 写入 state.json（仅 <state字段名> 字段）
<字段表格：字段 / 类型 / 说明>

### 写入 outputs/
<产物文件结构说明（JSON 示例或格式规范引用）>

## 执行步骤
<编号步骤列表>

## 使用方法
<bash 命令示例 + 参数说明>

## 依赖
<Python 版本、第三方库及安装命令>

## 禁止事项
<状态隔离等红线规则>
```

## 四、统一规则

1. **配置分层加载**：第 1 步加载根目录 `config.json`（全局默认：tool_paths、
   platforms_root、skills_root），第 2 步加载项目/示例 `config.json`（覆盖或补充），
   第 3 步深合并得到最终配置。项目相对路径（schematic_path、output_dir 等）相对
   项目 config.json 所在目录解析；以 `platforms/` 开头的路径相对根目录解析。
   工作区 = 项目目录（state.json 与 outputs/ 均在此）
2. **状态隔离**：每个 skill 只读写 `state.json` 中属于自己的字段
   （如 schematic-reader 只写 `circuit`），禁止触碰其他 skill 的字段
3. **指针/数据分离**：数据量大的产物（网表、芯片手册提取结果、串口日志等）
   真实数据放 `outputs/`，结构由 `schemas/<产物名>.schema.json` 约束并在写入前校验；
   `state.json` 中对应字段只存指针（产物路径）与统计计数，不存数据本体
4. **config.json 只读**：任何 skill 不得修改 `config.json`；命令行覆盖参数仅本次生效
5. **契约校验**：输出前用 `jsonschema` 依据 `schemas/output.schema.json` 校验
   state 字段，依据 `schemas/<产物名>.schema.json` 校验产物数据文件
6. **失败处理**：解析失败时写 `status: failed` 与错误信息到 state.json，不留半成品产物文件
7. **退出码**：0=成功（含 partial），1=失败，2=配置错误
8. **依赖降级**：非核心依赖（如 openpyxl）缺失时告警跳过对应功能，不影响主流程
9. **Excel/报告类产物**：格式规范写在 `references/`，示例放在 `assets/`，
   产物输出到 `outputs/`
10. **路径风格**：state.json 中的产物路径用工作区内相对 POSIX 路径
   （如 `outputs/pin_table.xlsx`），工作区外用绝对路径

## 五、新建 skill 检查清单

- [ ] 目录结构完整（SKILL.md / schemas / scripts / references / assets）
- [ ] input.schema.json 与 output.schema.json 已定义并通过 jsonschema 校验
- [ ] 数据量大的产物已定义 <产物名>.schema.json 并在写入前校验（指针/数据分离）
- [ ] state.json 字段隔离（只写自己的字段）
- [ ] config.json 只读
- [ ] 失败路径（文件不存在/依赖缺失/解析异常）正确写 failed 状态并返回对应退出码
- [ ] SKILL.md 含目录结构、输入输出、执行步骤、使用方法、依赖、禁止事项
- [ ] 有 Excel/报告产物时：references/ 有格式规范，assets/ 有示例
- [ ] 用 test_assets/ 样本完成正常 + 错误路径测试
