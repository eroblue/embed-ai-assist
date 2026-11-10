# S11 分析任务书

请按 `references/analysis_rules.md` 分析日志。每项 finding 必须引用下列 evidence ID。
只整理日志事实和可说明的归纳；不要读代码、推断根因或选择修复 Skill。

输入来源：1 个；索引证据：6 条。

## SRC01 会话上下文
- session_id: 20261106T101434-0e1b3703
- status: stopped
- started_at: 2026-11-06T10:14:34.549+08:00
- ended_at: 2026-11-06T10:14:53.348+08:00
- duration_sec: 18.791
- stop_reason: user_stop
- bytes_received: 480
- chunks_received: 4
- encoding_errors: 0
- firmware_sha256: 432b33919a2443f73e42a47b53ad84119192476ab07b0a8b73affafa72693249

## 日志证据

- `SRC01-L000001` (记录 2) [2026-11-06T10:14:36.631+08:00]: [LCD] diag code=0003 id=0000 0080 0000 colmod=0005 (0=ok 1=no-resp 2=wrong-id 3=reg-read)
- `SRC01-L000002` (记录 2) [2026-11-06T10:14:36.631+08:00]: {"temp":0,"humi":0,"light":99,"mode":"AUTO","alarm":"SENSOR_FAULT"}
- `SRC01-L000003` (记录 3) [2026-11-06T10:14:42.611+08:00]: [LCD] diag code=0003 id=0000 0080 0000 colmod=0005 (0=ok 1=no-resp 2=wrong-id 3=reg-read)
- `SRC01-L000004` (记录 4) [2026-11-06T10:14:42.828+08:00]: {"temp":0,"humi":0,"light":99,"mode":"AUTO","alarm":"SENSOR_FAULT"}
- `SRC01-L000005` (记录 5) [2026-11-06T10:14:48.791+08:00]: [LCD] diag code=0003 id=0000 0080 0000 colmod=0005 (0=ok 1=no-resp 2=wrong-id 3=reg-read)
- `SRC01-L000006` (记录 5) [2026-11-06T10:14:48.791+08:00]: {"temp":0,"humi":0,"light":99,"mode":"AUTO","alarm":"SENSOR_FAULT"}

## 完全相同记录的重复计数（候选）

- 3 次；代表记录 `SRC01-L000001`；内容：[LCD] diag code=0003 id=0000 0080 0000 colmod=0005 (0=ok 1=no-resp 2=wrong-id 3=reg-read)
- 3 次；代表记录 `SRC01-L000002`；内容：{"temp":0,"humi":0,"light":99,"mode":"AUTO","alarm":"SENSOR_FAULT"}

## Agent 输出

1. 填写 analysis.json。
2. 编写 report.md；无错误时仍报告可确认的运行流程。
3. 运行 validate.py 校验证据引用并收口。
