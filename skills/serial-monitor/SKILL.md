---
name: serial-monitor
description: "S10 串口日志采集技能。Windows 普通用户通过 Tkinter GUI 选择项目 config、串口和参数，实时查看设备输出并保存采集会话；CLI 是高级备用入口。只做 RX-only 采集，不发送命令、不分析日志。用户停止或关闭窗口时有序保存已收到的数据。"
---

# S10 serial-monitor

为嵌入式目标采集串口输出并保存可追溯的日志会话。S10 的职责是**连接、观察、保存**；日志诊断由 S11 完成。

## 普通用户入口（Windows）

双击 `scripts/start_s10.pyw` 打开界面。首次使用时选择项目 `config.json`，刷新并选择串口，确认串口参数后点击“开始采集”。界面显示连接状态、实时日志、已接收字节数和输出目录；点击“停止采集”或关闭窗口会先保存已收到的数据，再结束会话。

连接失败会在界面显示端口、参数、操作系统错误和检查建议。用户可以调整参数后重试。S10 不要求先烧录，也不由 S9 自动启动。

## 执行边界

- GUI 与 CLI 共用 `capture_service.py`；GUI 事件线程不执行阻塞串口读写。
- 只监听 RX；不发送串口数据、不控制 DTR/RTS、不复位设备。
- 连接成功后才创建会话目录；打开端口失败不会产生空日志。
- 用户停止和自动时长结束是正常收口；断连或写盘失败时尽量保留部分日志并记录错误。
- 原始字节写入 `capture.bin`；`capture.log` 为 JSON Lines，包含主机接收时间、原始块 Base64 和解码文本；`session.json` 记录会话参数、状态和统计。
- 每次会话写入 `<项目根>/<build_target>/outputs/s10/<session_id>/`。state 存在时只更新 `s10` 字段；state 不存在时会话仍可独立使用。
- S10 不解释日志、不调用 Agent、不自动触发 S11。用户可以把 `capture.log` 或其他来源的文本日志交给 S11。

## GUI 操作要求

1. 选择项目配置并显示当前配置路径；最近项目记录保存在用户级设置中，不写进仓库。
2. 串口列表可刷新；不自动猜端口。串口默认值来自 `project.serial`，GUI 临时修改不写回配置。
3. 只有用户明确勾选“保存本次参数为项目默认值”并确认后才更新项目配置。
4. 采集开始后显示实际参数、状态、运行时长、字节数和会话目录；实时显示暂停只影响屏幕，不影响采集和落盘。
5. 日志显示缓冲有界；UI 过载时允许丢弃屏幕旧行并提示，绝不丢弃文件数据。
6. 点击停止或关闭窗口时请求幂等停止，等待串口关闭、文件 flush 和 session 收口；窗口保持响应并显示保存状态。

## 高级 CLI 用法

```powershell
# 枚举串口
python skills/serial-monitor/scripts/prepare.py --config examples/stm32f103zet6/config.json --list-ports

# 单条命令采集 60 秒；Ctrl+C 也可正常停止
python skills/serial-monitor/scripts/capture.py --config examples/stm32f103zet6/config.json --port COM5 --baudrate 115200 --duration 60

# 校验并收口最近生成的会话目录
python skills/serial-monitor/scripts/validate.py --config examples/stm32f103zet6/config.json --session-dir examples/stm32f103zet6/App/outputs/s10/<session_id>
```

CLI 不回写项目配置。更多参数见 `scripts/capture.py --help`。

## 契约与实现文件

- 串口配置：根 `schemas/config.schema.json` 的 `project.serial`。
- 可选输入：`schemas/input.schema.json`（S9 状态投影，不构成前置依赖）。
- state 输出：`schemas/output.schema.json`（`state.json.s10`）。
- 会话清单：`schemas/session.schema.json`。
- 采集文件约定：`references/log_format.md`。
- 目录和状态约定：`docs/skill_requirements/S10 requirement.md`。
