# 编译示例（各构建系统命令模板）

## Keil（一期已验证路径）

```bash
# prepare：S5 就绪 + 构建系统/配置判定 + 工具链检测 + 任务书
python skills/build/scripts/prepare.py --config examples/stm32f103zet6/config.json
# 输出示例（state.s7b）：
# { "status": "running", "build_system": "keil", "build_mode": "cli",
#   "build_config": "Template", "build_target": "App", ... }

# build：UV4 增量编译（实际执行）
#   UV4.exe -b <uvprojx> -j0 -o outputs/s7b/build.log
# 成功后：fromelf --bin --output=Objects/Template.bin Objects/Template.axf
python skills/build/scripts/build.py --config examples/stm32f103zet6/config.json

# validate：产物验证 + state 收口（done）
python skills/build/scripts/validate.py --config examples/stm32f103zet6/config.json
```

build_result.json 成功示例（节选）：

```json
{
  "success": true,
  "build_system": "keil", "build_mode": "cli",
  "build_config": "Template", "build_target": "App",
  "artifact_path": "MDK-ARM/Objects/Template.axf", "artifact_format": "axf",
  "hex_path": "MDK-ARM/Objects/Template.hex",
  "bin_path": "MDK-ARM/Objects/Template.bin",
  "error_count": 0, "warning_count": 0
}
```

## IAR

```bash
python skills/build/scripts/prepare.py --config examples/<proj>/config.json
# IarBuild.exe <proj>.ewp -build Debug -log info
python skills/build/scripts/build.py --config examples/<proj>/config.json
# bin: ielftool.exe --bin Exe/<name>.out Exe/<name>.bin
python skills/build/scripts/validate.py --config examples/<proj>/config.json
```

## GCC Make

```bash
python skills/build/scripts/prepare.py --config examples/<proj>/config.json
# make -j4（--rebuild 时 make clean && make -j4）
python skills/build/scripts/build.py --config examples/<proj>/config.json [--rebuild]
# bin: arm-none-eabi-objcopy -O binary build/<name>.elf build/<name>.bin
python skills/build/scripts/validate.py --config examples/<proj>/config.json
```

## GCC CMake

```bash
python skills/build/scripts/prepare.py --config examples/<proj>/config.json
# cmake --build build --config Debug -- -j4（--rebuild 加 --clean-first）
python skills/build/scripts/build.py --config examples/<proj>/config.json [--rebuild]
python skills/build/scripts/validate.py --config examples/<proj>/config.json
```

## vendor_ide（8 位平台 GUI 机制）

```bash
# config 显式：build_system="vendor_ide" + project.vendor_ide + inputs.ide_project
python skills/build/scripts/prepare.py --config examples/ft61f14x/config.json
# Agent 按 generation_brief + references/vendor_ide/<标识>.md 操作 IDE（B1–B6）：
#   启动 IDE → 打开工程 → 编译快捷键 → 轮询输出目录（mtime > T0）→
#   抄录 build.log / gui_build_log.md → 关闭 IDE（不保存工程改动）
python skills/build/scripts/build.py --config examples/ft61f14x/config.json --collect
python skills/build/scripts/validate.py --config examples/ft61f14x/config.json
```

## 编译失败后（Agent analyze 路径）

```text
build.py 退出码 1 → Agent 读 outputs/s7b/build.log + build_result.json
→ 根因四分类（代码/配置/环境/输入）
→ 产出 outputs/s7b/error_analysis.md（只建议不执行）
→ 用户判定后：validate.py 收口；S5 代码问题则用户发起
  "读 outputs/s7b/error_analysis.md，走 S5c code-fix 分支修复 xxx"
```
