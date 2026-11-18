# S12 参数适配清单（初版）

| Skill | UI/方案参数 | 当前入口 | 说明 |
|---|---|---|---|
| S1 | `eda_tool` | `parse.py` EDA 参数 | `altium`、`kicad`、`pdf`，按 S1 SKILL.md 使用 |
| S3 | `scope` | `extract.py --scope` | 按 S3 允许的范围值校验 |
| S5a/S5b/S5c | `mode` | 各自 SKILL.md 的 full/diff/code-fix 分支 | Agent 按分支执行，不作为通用 CLI 参数 |
| S7b | `rebuild` | `build.py --rebuild` | 未勾选时不传 |
| S8 | `mode` | `prepare.py --mode` | 按 S8 规则提供额外必需参数 |
| S9 | `firmware`、`device` | `prepare.py` / `flash.py` 同名参数 | 固件显式指定时遵守 S9 格式和地址要求 |
| S10 | `port`、`baudrate`、`bytesize`、`parity`、`stopbits`、`encoding` | `capture.py` 同名参数；GUI 可通过 `start_s10.pyw <项目config> --s12-profile <方案>` 预填 | 预填后用户仍在 S10 窗口确认并可修改 |
| S11 | `log_path`、`observation` | `prepare.py` 位置参数 / `--observation` | 可用 S10 产物作输入 |

其他已实现 Skill 首期可勾选并按其自身 `SKILL.md` 默认流程执行。项目共用参数从项目 `config.json` 读取，不复制到方案。尚无可靠适配入口的参数暂不在 UI 提供编辑控件。
