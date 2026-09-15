# PDF 提取策略（datasheet-extractor）

> 适配器：`scripts/adapters/stm32_adapter.py`。策略适用于 ST 手册风格
> （GD32 手册结构相近，接入样本后可复用本策略）。
>
> **数据源优先级：SVD > SDK 头文件 > 参考手册 PDF**。PDF 解析是最后兜底路径；
> 有 SVD 时走 `svd_source.py`（一次 XML 解析），无 SVD 有头文件时走
> `sdk_source.py`（CMSIS 设备头解析），均无需本策略。

## 单手册模式（国产 MCU / 8 位机）

ST 系手册分 datasheet（引脚/电气特性）与 reference manual（寄存器/外设）两本；
多数国产 MCU 特别是 8 位机（STC、辉芒微、中颖等）**只有一本手册**，
寄存器描述直接写在 datasheet 中。适配器统一接口
`extract(datasheet, secondary, scope, svd, sdk_header)` 中 `svd` / `sdk_header`
/ `secondary` 为 None 时由**适配器自行决定**：

- 有 SVD（GD32、沁恒、华大等多数国产 ARM 核厂商提供）：走 `svd_source.py`
  通用解析，寄存器数据权威完整
- 无 SVD 有 SDK 头文件（厂商必然提供）：走 `sdk_source.py`
- STM32 适配器：三者全无时降级 partial（ST 的 datasheet 确实不含寄存器章节）
- 8 位机适配器：直接从 datasheet 提取寄存器/外设/时钟（单手册模式），
  产物 `source.reference_manual` 为 null

## 中文手册关键词

国产手册多为中文，章节定位关键词需中英双语匹配（在适配器内维护）：

| 目标 | 英文关键词 | 中文关键词 |
|------|-----------|-----------|
| 引脚定义 | `pin definitions` | `引脚定义` / `管脚定义` / `引脚功能` |
| 寄存器描述 | `register map` / `register boundary` | `寄存器` / `寄存器列表` / `特殊功能寄存器` / `SFR` |
| 中断向量 | `vector table` / `interrupt` | `中断向量` / `中断源` |
| 封装信息 | `ordering information` / `package` | `封装` / `订货须知` |

注意：中文 PDF 依赖内嵌字体可提取（多数国产手册可，扫描版不可——
扫描版手册本 Skill 无法处理，需人工或 OCR）。

## 总体原则

- **尽力而为（best effort）**：单个章节解析失败记入 warnings，不中断其他范围提取，
  最终由主入口汇总为 `partial` 状态
- **启发式页面选择（两阶段扫描）**：参考手册上千页，先低成本定位再深扫——
  - 阶段 1（毫秒级）：`pypdf` 读 PDF 书签（outline），按关键词
    （register / memory map / vector table / interrupt / nvic / rcc / clock）
    匹配章节标题，得到目标章节页码集合（RM0008 实测 576/1136 页，跳过 49%）
  - 阶段 2：仅对目标页做 `extract_text` 预筛 + 命中页 `extract_tables` 深解析
  - 书签不可用 / 无匹配时退化为全页文本预筛（兼容无书签 PDF）
- **先定位再解析**：先按关键词定位目标表格所在页，再对该页做表格提取，
  避免全文档逐页解析大表的开销
- **写入前校验**：提取结果先在内存中通过 schema 校验，全部通过才落盘（不留半成品）

## datasheet：引脚定义表

1. **定位**：页文本含 `pin definitions`（高密度手册为 "Table 5. High-density
   STM32F103xx pin definitions"，跨 9 页，每页 "continued"）
2. **取表**：`page.extract_tables()` 中取行数最多的表（引脚表是页内主表，
   12 列布局）
3. **识别封装列**（关键步骤）：
   - 封装名是**竖排文本**，直接反转得到：`441PFQL` → `LQFP144`、
     `46PSCLW` → `WLCSP64`、`441AGBFL` → `LFBGA144`
   - 优先取与 platform 命名解析一致的列（`stm32f103zet6` → Z=144 脚 + T=LQFP
     → `LQFP144`）；匹配不到时回退第一个 LQFP 列
4. **行解析**：跳过 2 行表头；列布局 `[0-5]=封装引脚位, 6=pin name,
   7=type, 8=I/O level, 9=main function, 10=alt default, 11=alt remap`
5. **清洗**：单元格内换行去除（`V\nREF-` → `VREF-`）；复用功能按 `/` 拆分；
   引脚号必须为纯数字（自然过滤表尾注释行）
6. **分类**：type 列 `S`→POWER，`I/O`→IO，`I`→INPUT，`O`→OUTPUT；
   名称特判 `BOOT*`→BOOT、`NRST`→NRST

## platform 命名解析（交叉验证）

ST 命名规则：`STM32F103` + `Z`(144 脚) + `E`(512K Flash) + `T`(LQFP) + `6`(温度)。

- mcu_family：`stm32f103xxx` → `STM32F1`
- package：脚数代码（Z=144 / V=100 / R=64 / C=48…）+ 封装代码（T=LQFP /
  H=LFBGA / Y=WLCSP…）→ `LQFP144`
- PDF 列头识别结果**优先**于命名解析（实际以手册为准），识别失败才用解析值

## reference manual：寄存器/外设/时钟树

| 目标 | 定位关键词 | 输出 |
|------|-----------|------|
| 外设边界 | `register boundary addresses` | peripherals.json（基地址/边界/总线推断） |
| 中断向量 | `vector table` / `interrupt` | peripherals.json 的 irqs（按名关联外设） |
| 寄存器偏移 | `xxx register map` | registers.json（offset+名称，基地址合成绝对地址） |
| RCC 位域 | 表内 `RCC_xxx` 表头 + `xxxEN` 位段名 | clock_tree.json（使能位/分频位） |

- 总线归属按地址段推断：APB1=0x40000000-0x4000FFFF、
  APB2=0x40010000-0x40013FFF、AHB=0x40018000-0x5003FFFF
- 位域提取仅覆盖 RCC（时钟树需要）；其他外设位域留空，
  完整位域建议后续接入 SVD 文件源（见 SKILL.md 已知限制）

## partial 判定标准

- 请求范围与完成范围（成功写出的产物集合）不一致 → `partial`，
  `chip.error` 记录未完成范围与 warnings
- 只提供 datasheet 未提供参考手册：registers/clocks/peripherals 无法提取，
  scope 退化为 pins，状态 partial（需求定义的标准降级路径）
- 全部产物校验失败或未提取到任何数据 → `failed`

## 已知限制

1. RM 位域表格式多变，非 RCC 外设的 bitfields 可能为空数组
   （SVD 路径无此问题：449 寄存器位域全覆盖）
2. 启发式页面选择按书签关键词选择深扫页，个别寄存器章节标题不含关键词时
   会漏提（实测 208 vs 全页扫 210，可接受误差）
3. GD32/FM32 适配器为占位，待接入真实手册样本后实现
