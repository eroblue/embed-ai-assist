# OpenOCD 烧录指南（三期演进项）

> **本指南为演进期占位**——`flash_tool = "openocd"` 当前在本版 prepare 直接报错
> （一期仅支持 jlink 全链路）。三期实装时按本骨架补全并实测校准。
> 适用场景：GD-Link / DAPLink 等 CMSIS-DAP 类探针，以及开源工具链偏好。

## 安装与配置（用户自管理）

- **官方下载渠道**：https://openocd.org/ （xPack OpenOCD 发行版亦可）；
  Windows 下可用 MSYS2 `pacman -S mingw-w64-x86_64-openocd`
- **config.json**：`tool_paths.openocd = <openocd.exe 路径>`（无推导，缺失报错，
  **不自动安装**）

## 命令预告（三期实测校准）

```
openocd -f interface/cmsis-dap.cfg -f target/stm32f1x.cfg \
        -c "program release/Template.hex verify reset exit"
```

- 探针差异由 interface cfg 消化（cmsis-dap / stlink / jlink 均有 cfg），
  无需逐探针适配
- 成功/失败日志特征（`** Programming Started/Finished **`、`Error:` 行族）待三期
  补充至 flash_log_parse_rules.md
