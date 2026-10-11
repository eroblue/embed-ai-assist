# bin/hex 生成与转换指南

## 为什么 bin 是必须产物

BootLoader 合并 App 时 bin 比 hex 方便：bin 是纯二进制镜像（按地址拼接即可：
`boot.bin + pad + app.bin`），hex 含地址/段记录/校验和，合并需解析 Intel HEX
格式易出错。因此 **S7b 必须为所有构建系统生成 bin**，即使 Keil/IAR 默认只输出
hex/axf。

## 各构建系统的 bin 生成命令

| build_system | 命令 |
|---|---|
| `keil` | `fromelf.exe --bin --output=<name>.bin <name>.axf` |
| `iar` | `ielftool.exe --bin <name>.out <name>.bin` |
| `gcc_make` / `gcc_cmake` | `arm-none-eabi-objcopy -O binary <name>.elf <name>.bin` |
| `vendor_ide` | Python `intelhex` 库 hex→bin（工具链无关） |

## hex 补生成规则（S7b 禁止修改工程文件，不能依赖工程内勾选项）

| build_system | 命令 |
|---|---|
| `keil` | `fromelf.exe --i32 --output=<name>.hex <name>.axf` |
| `iar` | `ielftool.exe --ihex <name>.out <name>.hex` |
| `gcc_make` / `gcc_cmake` | `arm-none-eabi-objcopy -O ihex <name>.elf <name>.hex` |
| `vendor_ide` | 厂家 IDE 自身输出 hex，无需补生成 |

## intelhex 兜底（工具链无关）

`intelhex` 同时作为其他构建系统的降级路径：objcopy/fromelf/ielftool 均缺失时，
若 hex 已生成，可用它转 bin（**仅警告不终止**）：

```python
from intelhex import IntelHex
ih = IntelHex("<name>.hex")
ih.tofile("<name>.bin", format="bin")   # 间隙按 0xFF 填充，min~max 地址连续输出
```

安装：`pip install intelhex`

依赖降级语义：intelhex 缺失时——`vendor_ide` 机制在 S7a 检测报错；CLI 机制仅
警告并置 `bin_path = null`（S6 合并时需用户手动提供 bin）。

## 常见错误

| 现象 | 原因与处置 |
|---|---|
| fromelf "invalid file" | 输入不是 axf/elf（编译实际失败或产物路径错）——检查 build.log |
| bin 生成成功但体积异常大 | hex/axf 含分散地址段（如 Boot 占用低地址）——intelhex 按地址区间展开属正常，由 S6 按 bin 基址处理 |
| objcopy "unable to recognise input" | elf 损坏或格式不符——重编译 |
| bin 比 hex 起始地址信息缺失 | bin 本身无地址信息，S6/S9 按 config 的基址配置使用 |
