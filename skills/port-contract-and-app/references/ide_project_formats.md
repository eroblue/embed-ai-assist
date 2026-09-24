# IDE 工程文件说明（S5b 视角：Agent 不碰工程文件，只认清单）

> **硬规则：S5b Agent 不得直接编辑任何 IDE 工程文件**（`.uvprojx`/`.ewp`/CMakeLists 等）——
> 工程更新由公共工具 `skills/_shared/scripts/ide_sync.py` 统一完成（谁跑完 validate 谁同步，
> 文件锁防并发覆盖），S5b 只负责"产物落盘到约定目录"。

## 一、S5b 产物的工程归属

`outputs/s5b/ide_pending_files.json`（validate 段自动导出）按组列出本轮产物：

| 组 | 内容 | 目录（按 PROJECT_LAYOUT.md 解析，典型值） |
|---|---|---|
| `App` | `main.c`、`app*.c`、`protocol_*.c`、`*_task.c` | `App/Src/`（include：`App/Inc/`） |
| `Drivers/BSP` | `driver_*.c`（S5b 器件驱动，与 S5a 初始化同层不同名前缀） | `Drivers/BSP/Src/`（include：`Drivers/BSP/Inc/`） |

Port 接口头（`Drivers/Port/Inc/`）是纯头文件，不进源文件组，但会出现在 include_paths 中。
flat 架构无 Port 层，include_paths 相应减少（layout_resolver 自动剔除）。

## 二、同步机制（对 Agent 透明，此处仅说明行为）

1. **validate.py 终验通过后**自动调用 `ide_sync.sync_project(project_root, target)`：扫描 S5a/S5b/S5c 产物目录并集，按工程文件格式增删条目、追加 include 路径。
2. 同步成功 → 工程文件已含 S5b 产物，用户直接编译。
3. 同步失败（工程文件被 IDE 锁定/格式不识别）→ 不中断 S5b 流程：
   - 自动生成手动操作说明 `<target>/outputs/_shared/ide_sync_manual.md`；
   - `ide_pending_files.json` 作为机器可读清单保留（含分组与 include 路径），用户可按清单手动加文件；
   - validate 输出提示，由用户处理后在下一轮 validate 重试同步。

## 三、Agent 注意事项

- 新增/删除源文件后**不需要**手动更新任何工程相关文件或清单——重跑 validate 即可（export 每次全量重写清单）。
- 删除模块代码（流程图 deprecated）时，同时确认该模块文件已从产物目录移除，ide_sync 才能从工程中剔除对应条目；只删工程条目不删文件（或反之）都会造成漂移。
- 若用户自行把工程文件加进 `project.inputs.ide_project`（作为已有工程参考），该文件是**只读参考**（了解分组/include 约定），不是 S5b 的写入对象。
