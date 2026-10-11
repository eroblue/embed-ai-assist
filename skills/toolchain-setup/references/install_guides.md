# 各工具官方安装方式（install_guides）

> Agent 在 install 阶段只使用本文件列出的官方来源，不使用来源不明的安装包。

## ARM GNU Toolchain（arm-none-eabi-gcc + objcopy）

| 平台 | 命令 / 方式 |
|---|---|
| Windows（winget） | `winget install Arm.GnuArmEmbeddedToolchain` |
| Windows（官网） | https://developer.arm.com/downloads/-/gnu-rm 下载 `.exe` 安装 |
| Linux | `sudo apt install gcc-arm-none-eabi binutils-arm-none-eabi` |
| macOS | `brew install arm-none-eabi-gcc arm-none-eabi-binutils` |

- 目标路径默认建议 `C:/gcc-arm/`（避免空格与用户目录权限；**须先检测可写性**）
- 安装后回填：`tool_paths.gcc` = `<路径>/bin/arm-none-eabi-gcc.exe`；
  `tool_paths.gcc_objcopy` 同目录（未配置时 S7a/S7b 自动推导）

## GNU Make

| 平台 | 命令 / 方式 |
|---|---|
| Windows（MSYS2） | `winget install MSYS2.MSYS2` 后 `C:/msys64/usr/bin/pacman -S make` |
| Linux | `sudo apt install make` |
| macOS | `brew install make` |

- Windows 下 make 位于 `C:/msys64/usr/bin/make.exe`；回填 `tool_paths.make`

## CMake

| 平台 | 命令 / 方式 |
|---|---|
| Windows（winget） | `winget install KitWare.CMake` |
| Linux | `sudo apt install cmake` |
| macOS | `brew install cmake` |

- 目标路径默认建议 `C:/cmake/`；回填 `tool_paths.cmake`

## Python intelhex 包

```bash
pip install intelhex
```

（vendor_ide 机制的 hex→bin 依赖；其他构建系统 bin 工具缺失时的兜底。）

## 商业工具（不自动安装，仅指引）

| 工具 | 官网 | 说明 |
|---|---|---|
| Keil MDK | https://www.keil.com/download/ | 商业授权；安装后回填 `tool_paths.keil`（UV4/UV4.exe）；fromelf 随 Keil 安装（ARM/ARMCLANG|ARMCC/bin/），可自动推导 |
| IAR EWARM | https://www.iar.com/downloads/ | 商业授权；安装后回填 `tool_paths.iar`（IarBuild.exe）；ielftool 同目录 common/bin/，可自动推导 |
| 厂家 IDE | 各厂家官网 | 商业/免费但无 CLI；安装后回填 `tool_paths.vendor_ide` |

## 回填 config.json 的约束（全项目唯一例外）

- 只允许追加/更新全局 config.json 的 `tool_paths` 段工具路径键
- **写入前在对话中展示将要写入的键值对（diff），经用户确认**
- 不覆盖已有配置键，除非该键指向的路径已失效
- 禁止修改任何其他字段
