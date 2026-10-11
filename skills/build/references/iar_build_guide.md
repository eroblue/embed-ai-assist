# IAR 命令行编译指南（IarBuild / ielftool）

## 命令行调用

```text
IarBuild.exe <project.ewp> -build <config> -log info
```

- `-build <config>`：构建指定 configuration（如 Debug / Release）
- `-log info`：输出详细日志（stdout，build.py 收集为 build.log）
- `--rebuild` 场景用 `-make` 全量：实际以 IarBuild 的 rebuild 参数为准
  （`IarBuild <ewp> -build <config>` 自身即全量链路检查）

## 退出码语义

| 退出码 | 含义 |
|---|---|
| 0 | 成功 |
| 非 0 | 失败 |

**成功判据 = 退出码 0 且日志解析错误数 = 0。**

## 日志格式要点

- 错误：`Error[Pe020]: identifier "xxx" is undefined`、`Fatal Error[Lc019]`
- 警告：`Warning[Pe223]: ...`
- 完成行：`Total number of errors: 0` / `Build complete`（产物路径见 Exe 输出行）

## 产物目录约定（注意 Exe 与 Obj 的区分）

**`.out` 最终产物在 `Exe/` 目录**，`Obj/` 只有 `.o` 中间文件：

| 产物 | 路径 |
|---|---|
| 调试产物 `.out` | `<IAR 工程>/<config>/Exe/<name>.out` |
| 烧录产物 `.hex` | `<IAR 工程>/<config>/Exe/<name>.hex`（仅工程配置开启时生成） |
| 合并产物 `.bin` | `<IAR 工程>/<config>/Exe/<name>.bin`（S7b 用 ielftool 生成） |

## ielftool 路径推导

`tool_paths.iar_ielftool` 未配置时，从 `tool_paths.iar`（IarBuild.exe）同目录
探测 `common/bin/ielftool.exe`。

## bin/hex 生成

```text
ielftool.exe --bin  <name>.out <name>.bin    # bin（S6 合并必需）
ielftool.exe --ihex <name>.out <name>.hex    # hex（工程未开启时补生成）
```

详见 `binary_conversion_guide.md`。
