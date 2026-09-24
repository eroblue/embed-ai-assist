---
name: app_alarm_control_state
status: approved
version: 1.0
created_at: 2026-09-24T10:20:00
approved_at: 2026-09-24T10:32:00
approved_by: user
base_version: null
---

<!-- app_alarm_control 告警管理（REQ-005/REQ-006）：四级优先级告警状态机
     HIGH_TEMP(1) > LOW_TEMP(2) > LOW_LIGHT(3) > SENSOR_FAULT(4)，
     多条件同时满足时迁移到优先级最高的告警态。每次环境数据更新/故障事件触发重评估，
     全部条件解除回 NORMAL。迁移动作联动执行器（仅自动模式生效）：
     进 HIGH_TEMP 执行器开、进 LOW_TEMP 执行器关、其他迁移保持（设计输入：高温开低温关其他保持）。
     告警态蜂鸣器 1s 响 1s 停节奏（静音态不响，由模块 poll 按模式/静音门控）。
     手动模式 KEY1 开关执行器走模块公开接口 on_key_switch，不经过本状态机迁移 -->

```mermaid
stateDiagram-v2
    [*] --> NORMAL
    NORMAL --> HIGH_TEMP : on_temp_high / actuator_on
    NORMAL --> LOW_TEMP : on_temp_low / actuator_off
    NORMAL --> LOW_LIGHT : on_light_low
    NORMAL --> SENSOR_FAULT : on_sensor_fault

    HIGH_TEMP --> NORMAL : on_all_clear
    HIGH_TEMP --> LOW_TEMP : on_temp_low / actuator_off
    HIGH_TEMP --> LOW_LIGHT : on_light_low
    HIGH_TEMP --> SENSOR_FAULT : on_sensor_fault

    LOW_TEMP --> HIGH_TEMP : on_temp_high / actuator_on
    LOW_TEMP --> NORMAL : on_all_clear
    LOW_TEMP --> LOW_LIGHT : on_light_low
    LOW_TEMP --> SENSOR_FAULT : on_sensor_fault

    LOW_LIGHT --> HIGH_TEMP : on_temp_high / actuator_on
    LOW_LIGHT --> LOW_TEMP : on_temp_low / actuator_off
    LOW_LIGHT --> NORMAL : on_all_clear
    LOW_LIGHT --> SENSOR_FAULT : on_sensor_fault

    SENSOR_FAULT --> HIGH_TEMP : on_temp_high / actuator_on
    SENSOR_FAULT --> LOW_TEMP : on_temp_low / actuator_off
    SENSOR_FAULT --> LOW_LIGHT : on_light_low
    SENSOR_FAULT --> NORMAL : on_sensor_recovered

    state "正常（无告警）" as NORMAL
    state "高温告警（温度>30°C，优先级1）" as HIGH_TEMP
    state "低温告警（温度<10°C，优先级2）" as LOW_TEMP
    state "低光照告警（光照<20%，优先级3）" as LOW_LIGHT
    state "传感器故障（连续失败5次，优先级4）" as SENSOR_FAULT
    HIGH_TEMP : 执行器开（自动模式），蜂鸣 1s 节奏
    LOW_TEMP : 执行器关（自动模式），蜂鸣 1s 节奏
    LOW_LIGHT : 执行器保持，蜂鸣 1s 节奏
    SENSOR_FAULT : 显示保持上次值，蜂鸣 1s 节奏
```
