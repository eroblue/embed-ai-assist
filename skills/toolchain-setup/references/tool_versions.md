# 最低版本要求与版本探测命令

## 开源工具白名单最低版本

| 工具 | tool_paths 键 | 最低版本 | 版本探测命令 |
|---|---|---|---|
| arm-none-eabi-gcc | `gcc` | 10.0+ | `arm-none-eabi-gcc --version` |
| arm-none-eabi-objcopy | `gcc_objcopy` | 10.0+ | `arm-none-eabi-objcopy --version` |
| GNU Make | `make` | 4.0+ | `make --version` |
| CMake | `cmake` | 3.20+ | `cmake --version` |
| Python intelhex | -（pip 包） | 任意可用 | `python -c "import intelhex"` |

- 版本低于最低要求：**警告不终止**（提示升级），不阻断 S7b
- 版本探测失败（命令不可执行）：开源工具视为未就绪；商业工具版本不作判据

## 版本字符串解析

探测输出中取首个 `主版本.次版本[.修订]`：

```text
arm-none-eabi-gcc (Arm GNU Toolchain 13.2.Rel1) 13.2.1 20231009   → 13.2.1
GNU Make 4.3                                                      → 4.3
cmake version 3.28.0                                              → 3.28.0
```

## 商业工具（不探测版本，只检测存在性）

| 工具 | tool_paths 键 | 说明 |
|---|---|---|
| Keil UV4 | `keil` | UV4 无安全的 --version 参数（会拉起 GUI），只做路径存在性检测 |
| Keil fromelf | `keil_fromelf` | 未配置时从 Keil 根推导（ARMCLANG 优先于 ARMCC） |
| IAR IarBuild | `iar` | 同上，只检测存在性 |
| IAR ielftool | `iar_ielftool` | 未配置时从 IarBuild 同目录 common/bin/ 推导 |
| 厂家 IDE | `vendor_ide` | 只检测存在性 |
