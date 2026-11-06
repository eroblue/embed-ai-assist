# S10 使用示例

1. 双击 `skills/serial-monitor/scripts/start_s10.pyw`。
2. 选择示例工程 `examples/stm32f103zet6/config.json`。
3. 刷新端口，选择开发板对应的 USB-UART 端口，确认与固件一致的波特率（例如 115200、8N1）。
4. 点击“开始采集”。连接成功后窗口实时显示输出，并显示会话目录。
5. 点击“停止采集”。已接收内容保存在 `App/outputs/s10/<session_id>/`。
6. 将 `capture.log` 交给 S11 分析，或直接查看 `capture.bin` / `session.json`。

如果串口连接失败，检查端口占用和设备管理器中的端口号，刷新列表后重试。S10 不会替用户猜测波特率或更换端口。
