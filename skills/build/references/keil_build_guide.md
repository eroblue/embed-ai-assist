# Keil 命令行编译指南（MDK-ARM / UV4）

## 命令行调用

```text
UV4.exe -b <project.uvprojx> -j0 -o <log_file>     # 增量编译
UV4.exe -r <project.uvprojx> -j0 -o <log_file>     # 全量重编（--rebuild）
```

- `-b` / `-r`：build（增量）/ rebuild（全量），二选一
- `-j0`：不显示 GUI 窗口（后台编译）
- `-o <log_file>`：编译日志输出文件（支持绝对路径；编码见下）
- UV4 会阻塞至编译完成后退出，超时控制由 build.py 的 `--timeout` 负责（缺省 600s）

## 退出码语义（与其他工具链不同，务必区分）

| 退出码 | 含义 |
|---|---|
| 0 | 编译成功，无警告 |
| 1 | 编译成功，有警告 |
| ≥2 | 编译失败（含 fatal error） |

**成功判据 = 退出码 ∈ {0, 1} 且日志解析错误数 = 0**（双条件，缺一不可）。

## 日志编码

Keil 在中文 Windows 上日志常为 **GBK** 编码。build.py 按 UTF-8 → GBK →
`errors='replace'` 顺序解码（见 `log_parse_rules.md`）。

## 日志格式要点

- 编译错误：`../Src/main.c(15): error: #20: identifier "xxx" is undefined`
- 链接错误：`.\Objects\Template.axf: Error: L6218E: Undefined symbol ...`
- 汇总行：`".\Objects\Template.axf" - 0 Error(s), 0 Warning(s).`
  （错误/警告计数优先取汇总行）
- hex 生成行：勾选 "Create HEX file" 时出现 `After Build - User command #1: fromelf.exe --i32 ...`

## 产物目录约定

| 产物 | 路径（相对 MDK-ARM/） |
|---|---|
| 调试产物 `.axf` | `Objects/<target>.axf` |
| 烧录产物 `.hex` | `Objects/<target>.hex`（仅工程勾选 Create HEX 时生成） |
| 合并产物 `.bin` | `Objects/<target>.bin`（S7b 用 fromelf 生成，见 binary_conversion_guide.md） |

target 名来自 `.uvprojx` 的 `<TargetName>`（单 target 自动取用；多 target 必须
显式配置 `project.build_config`，不猜）。

## fromelf 路径推导

`fromelf.exe` **不在 UV4.exe 同目录**：

```text
<Keil 根>/ARM/ARMCLANG/bin/fromelf.exe    # 优先（AC6）
<Keil 根>/ARM/ARMCC/bin/fromelf.exe       # 备选（AC5）
```

`tool_paths.keil_fromelf` 未配置时，build.py 从 `tool_paths.keil`（`UV4/UV4.exe`
的上一级为 Keil 根）按上述两个候选自动探测，多份时取 ARMCLANG 优先。

## 常见问题

- **UV4 弹窗阻塞**：确保 `-j0` 已传（无窗口模式）；License 过期会弹窗，属环境问题
- **日志为空**：`-o` 路径不可写或 UV4 版本过老——检查 outputs/s7b/ 目录存在
- **中文乱码**：解码顺序已处理；`errors='replace'` 后仍有乱码多为日志混编码，不影响错误计数（汇总行 ASCII）
