---
name: app_oled_display_flow
status: deprecated
version: "1.0"
created_at: 2026-09-24T10:20:00
approved_at: 2026-09-24T10:32:00
approved_by: user
base_version: null
---

<!-- app_oled_display 本地显示（REQ-003）：200ms 周期刷新 4 行（模式/温湿度/光照/告警），
     告警激活时告警行 1Hz 闪烁；OLED 初始化失败（未就绪）时跳过显示（REQ-010 降级）。
     SSD1306 命令协议由 driver_oled 承载，经 i2c_port 写入 -->

```mermaid
flowchart TD
    A[刷新周期到达 /* period_ms=200 */] --> B{OLED 就绪?}
    B -- 否 --> Z([跳过本次刷新])
    B -- 是 --> C[读取共享数据 模式温湿度光照告警]
    C --> D{告警激活?}
    D -- 否 --> E[渲染 4 行完整画面]
    D -- 是 --> F{闪烁相位为亮? /* blink_hz=1 */}
    F -- 是 --> E
    F -- 否 --> G[渲染画面且告警行隐藏]
    E --> H[经 I2C 写入 OLED]
    G --> H
    H --> I{写入成功?}
    I -- 是 --> J([刷新完成])
    I -- 否 --> K[显示失败计数+1]
    K --> J
```
