# S10 日志格式

每次采集目录包含 `capture.bin`、`capture.log` 和 `session.json`。

## capture.bin

串口读取到的原始字节拼接，按接收顺序保存，不插入时间戳或换行，不做编码转换。它是字节级事实来源。

## capture.log

UTF-8 JSON Lines。首行是 header，其后每个非空串口读取块一行：

```json
{"record_type":"header","session_id":"20261106T153000-a1b2c3d4","timestamp_semantics":"host_receive_time","encoding":"utf-8","created_at":"2026-11-06T15:30:00.123+08:00"}
{"record_type":"rx","ts_host":"2026-11-06T15:30:01.006+08:00","data_b64":"U3lzdGVtIHJlYWR5XHJcbiA=","text":"System ready\r\n "}
```

- `ts_host` 是主机读取该块时的时间，不代表设备端生成时间。
- `data_b64` 解码后与该块写入 `capture.bin` 的字节一致。
- `text` 用会话串口编码解码，遇到无效序列使用 U+FFFD；JSON 转义负责保留换行和控制字符。
- 若增量解码器在停止时输出尾部替代字符，会追加 `record_type="decode_tail"`，其中 `data_b64` 为空，`text` 记录最后一段解码结果；其原始字节已包含在前面的 RX 记录中。
- S11 可读取 `text` 做常见日志分析；需要精确原始内容时读取 `capture.bin` 并参考 `data_b64`。

## session.json

会话元数据契约见 `schemas/session.schema.json`。路径 `capture_bin`、`capture_log` 是相对会话目录的文件名；状态和计数以该清单为会话记录权威，`state.json.s10` 只保存摘要与指针。
