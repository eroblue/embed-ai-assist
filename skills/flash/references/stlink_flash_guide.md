# STM32CubeProgrammer CLI（stlink）烧录指南（三期演进项）

> **本指南为演进期占位**——`flash_tool = "stlink"` 当前在本版 prepare 直接报错
> （一期仅支持 jlink 全链路）。三期实装时按本骨架补全并实测校准。
> 适用场景：ST-Link 探针 + ST 系芯片（STM32 优先惯例工具）。

## 安装与配置（用户自管理）

- **官方下载渠道**：https://www.st.com/en/development-tools/stm32cubeprog.html
  （STM32CubeProgrammer，含 CLI；仅 ST-Link 探针适用）
- **config.json**：`tool_paths.stlink_cli = <STM32_Programmer_CLI.exe 路径>`
  （无推导，缺失报错指向本指南，**不自动安装**）

## 命令预告（三期实测校准）

```
STM32_Programmer_CLI -c port=SWD mode=Normal -d <固件> <地址> -v -rst
```

- hex 自带地址可不传 `<地址>`；bin 必须显式传（flash_base + flash_offset）
- 成功/失败日志特征（含 `Error: CubeProgrammer` 行族、读保护提示行）待三期
  补充至 flash_log_parse_rules.md
