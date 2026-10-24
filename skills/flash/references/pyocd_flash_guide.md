# pyOCD 烧录指南（四期演进项）

> **本指南为演进期占位**——`flash_tool = "pyocd"` 当前在本版 prepare 直接报错
> （一期仅支持 jlink 全链路）。四期实装时按本骨架补全并实测校准。
> 适用场景：Python 生态（pip 安装即用）、CI/自动化脚本偏好。

## 安装与配置（用户自管理）

- **官方渠道**：`pip install pyocd`（https://pyocd.io/ ；含 CMSIS-Pack 设备支持：
  `pyocd pack install <设备名>`）
- **config.json**：`tool_paths.pyocd = <pyocd.exe 路径>`；未配置时以
  `tool_paths.python -m pyocd` 探测（pip 包形态）
- **不自动安装**；缺失报错指向本指南

## 命令预告（四期实测校准）

```
pyocd flash -t stm32f103ze --format hex release/Template.hex
```

- hex 自带地址；bin 需 `--base-address <flash_base+flash_offset>`
- 成功/失败日志特征（`[============] 100%`、`Error:` 行族）待四期补充至
  flash_log_parse_rules.md
