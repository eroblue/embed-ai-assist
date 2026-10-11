# GCC Make / CMake 编译指南（arm-none-eabi-gcc）

## Make（gcc_make）

```text
make -j4                 # 增量编译（在 Makefile 所在目录执行）
make clean && make -j4   # --rebuild 全量重编
```

- 无 build_config 概念（build_config = null）
- 日志取 stdout + stderr（UTF-8 为主，多编码解码兜底）

## CMake（gcc_cmake）

```text
cmake --build build [--config <config>] [--clean-first] -- -j4
```

- build_config 缺省推断：优先读 `build/CMakeCache.txt` 的 `CMAKE_BUILD_TYPE`，
  无法确定时缺省 `Debug`
- 首次构建需先配置（`cmake -B build -DCMAKE_TOOLCHAIN_FILE=...`）；未配置过
  build 目录时编译失败，Agent analyze 归为配置问题

## 退出码语义（Make 与 CMake 一致）

| 退出码 | 含义 |
|---|---|
| 0 | 成功 |
| 非 0 | 失败 |

**成功判据 = 退出码 0 且日志解析错误数 = 0。**

`make clean` 允许失败（首次构建无产物可清）。

## 日志格式要点

- 错误：`src/main.c:15:3: error: implicit declaration of function 'xxx'`
- 警告：`src/main.c:20:5: warning: unused variable 'y' [-Wunused-variable]`
- 链接命令 `-o build/app.elf` 用于产物定位（最准确）

## 产物目录约定

| 产物 | 路径 |
|---|---|
| 调试产物 `.elf` | `build/*.elf`（gcc_make）/ `build/<config>/*.elf`（gcc_cmake） |
| 烧录产物 `.hex` | 同目录 `.hex` |
| 合并产物 `.bin` | 同目录 `.bin`（objcopy 生成） |

## bin/hex 生成

```text
arm-none-eabi-objcopy -O binary <name>.elf <name>.bin   # bin（S6 合并必需）
arm-none-eabi-objcopy -O ihex   <name>.elf <name>.hex   # hex（缺失时补生成）
```

`tool_paths.gcc_objcopy` 未配置时从 `tool_paths.gcc` 同目录探测
`arm-none-eabi-objcopy(.exe)`。详见 `binary_conversion_guide.md`。
