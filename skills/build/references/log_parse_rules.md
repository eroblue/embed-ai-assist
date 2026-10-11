# 日志解析规则

## 编码尝试顺序

`build.log` 统一按 **UTF-8 → GBK → `errors='replace'`** 顺序解码（Keil 在
中文 Windows 上日志常为 GBK；先按 UTF-8 试探失败再 GBK，均失败用 replace 保底，
不中断解析）。

## 错误 / 警告行特征

| build_system | 错误行特征 | 警告行特征 |
|---|---|---|
| `keil` | `*** ERROR` / `error: #...`（编译）/ `Error: L...`（链接） | `warning: #...` |
| `iar` | `Error[` / `Fatal Error[` | `Warning[` |
| `gcc_make` / `gcc_cmake` | `error:` | `warning:` |
| `vendor_ide` | Agent 抄录行含 error/失败 | Agent 抄录行含 warning/警告 |

## 计数规则

1. **优先取日志尾部汇总行**：
   - Keil：`"...\Template.axf" - 0 Error(s), 0 Warning(s).`
   - IAR：`Total number of errors: 0` 类汇总
2. 汇总行与明细行数不一致时**取大者**（防明细漏匹配）。
3. 汇总行本身不计入明细（`- N Error(s)` 模式排除）。

## 错误详情提取

- 文件/行号：`<file>(<line>): ...`（Keil/armcc）、`<file>:<line>:<col>: ...`（GCC）
- 明细条目结构：`{file, line, message}`（file/line 可为 null）

## 产物路径提取（优先级从高到低）

1. **日志解析**（最准确）：GCC 从链接命令 `-o build/app.elf`；Keil/IAR 从输出行
2. **约定路径推断**：`Objects/<target>.axf`（Keil）、`<config>/Exe/*.out`（IAR，
   注意不是 Obj/）、`build[/<config>]/*.elf`（GCC）
3. 推断失败 → `artifact_path = null`（由 S9 flash 阶段再定位）

## GUI 模式（vendor_ide）

- build.log 由 Agent 从 IDE 输出窗口**抄录关键行**（不是完整日志）
- 错误数按抄录行统计；**无法统计时为 -1** 并标注"GUI 模式无法精确计数"
- 抄录格式建议逐行保留原始输出（含文件/行号信息），便于 analyze 阶段四分类
