---
name: app_uart_report_sequence
status: approved
version: 1.0
created_at: 2026-09-24T10:20:00
approved_at: 2026-09-24T10:32:00
approved_by: user
base_version: null
---

<!-- app_uart_report 串口上报（REQ-008/REQ-009）：5s 周期经 uart_port 向上位机上报 JSON 帧
     {"temp":25,"humi":60,"light":75,"mode":"AUTO","alarm":"NORMAL"}\r\n。
     发送失败同周期内重试（retry_max=2），连续 3 个周期失败置上报故障标志（LED1 快闪，由 app.c 呈现）。
     初始化失败时模块置未就绪，跳过上报（REQ-010 降级） -->

```mermaid
sequenceDiagram
    participant APP as app_uart_report（应用）
    participant PORT as uart_port（Port 层）
    APP->>PORT: uart_port_init(UART_PORT_REPORT, cfg)
    PORT-->>APP: PORT_OK / PORT_ERR_xxx（失败则置未就绪并上报初始化故障）
    Note over APP: 5s 上报周期到达 /* period_ms=5000 */
    APP->>APP: 读取共享环境数据并组 JSON 帧
    APP->>PORT: uart_port_write(UART_PORT_REPORT, frame, len)
    PORT-->>APP: PORT_OK（同步拷贝语义）
    Note over APP: 成功 → 清零连续失败周期计数
    APP->>PORT: uart_port_write(UART_PORT_REPORT, frame, len) /* 失败重试 retry_max=2 */
    PORT-->>APP: PORT_ERR_TIMEOUT（重试后仍失败）
    Note over APP: 连续失败周期计数+1 /* fail_threshold=3 */ → 置上报故障标志
```
