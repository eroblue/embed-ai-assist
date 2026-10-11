#!/usr/bin/env python
"""S7b build 第 1 段：prepare（rule 轨）。

四段式执行模型（与 S5 系列不同：CLI 编译是确定性操作不需要 Agent）：
  1. [rule]  prepare.py    → S5 系列就绪检查 + 平台/编译机制判定 + 构建系统/配置判定
                            （显式优先，智能推断；多候选/零候选报错）
                            → 工具链就绪检查（编译工具缺失报错提示 S7a；bin 工具缺失仅警告）
                            → outputs/s7b/generation_brief.md（CLI 与 GUI 两种任务书）
                            → state.s7b = running
  2. [rule/agent] build.py → CLI 机制纯 rule 编译；GUI 机制（vendor_ide）Agent 按
                            vendor 指南操作 IDE，build.py --collect 收口
  3. [agent] analyze       → 仅编译失败时产出 error_analysis.md（不自动修复）
  4. [rule]  validate.py   → 产物验证 + state 收口

本脚本不生成任何 C 代码，不修改工程文件。

退出码：0 就绪检查通过；2 配置错误 / S5 未完成 / 工具链缺失 / 工程文件缺失。
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

if sys.version_info < (3, 10):  # 版本守卫：本框架需 3.10+
    print("[错误] 本框架需要 Python 3.10+，当前解释器为 "
          f"{sys.version.split()[0]}", file=sys.stderr)
    sys.exit(2)

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
ROOT_DIR = SKILL_DIR.parent.parent
sys.path.insert(0, str(SCRIPT_DIR))
sys.path.insert(0, str(SKILL_DIR.parent / "_shared" / "scripts"))

import analysis  # noqa: E402
import makefile_gen  # noqa: E402
import state_store  # noqa: E402

EXIT_OK = 0
EXIT_CONFIG_ERROR = 2


def _log(msg: str) -> None:
    print(f"[s7b-prepare] {msg}", file=sys.stderr)


def _generate_makefile(ctx: dict, target_root: Path) -> dict:
    """阶段 A'：Makefile 自动生成分支入口（makefile_gen 抛错由调用方转 fail）。"""
    config = ctx["config"]
    platform = config.get("platform") or ""
    platforms_root = Path(config.get("platforms_root") or "platforms/")
    platform_dir = (platforms_root if platforms_root.is_absolute()
                    else ROOT_DIR / platforms_root) / platform
    mcu_family = (ctx["state"].get("chip") or {}).get("mcu_family") or ""
    ide_project = ((target_root / ctx["ide_project"]).resolve()
                   if ctx["ide_project"] else None)
    flash_offset = int((ctx["config"].get("project") or {})
                       .get("flash_offset") or 0)
    return makefile_gen.generate_build_files(
        target_root,
        platform_dir if platform_dir.is_dir() else None,
        mcu_family, None, ide_project, flash_offset)


def _write_error_state(ctx_or_path, error: str) -> dict:
    """prepare 失败时写 state.s7b = error（退出码 2）。"""
    payload = {"status": "error", "error": error,
               "updated_at": datetime.now().isoformat(timespec="seconds")}
    state_path = None
    if isinstance(ctx_or_path, dict):
        state_path = ctx_or_path.get("state_path")
        payload.update({
            "build_system": ctx_or_path.get("build_system_resolved") or ctx_or_path.get("build_system_cfg") or "",
            "build_mode": ("gui" if ctx_or_path.get("build_system_resolved") == "vendor_ide" else "cli"),
            "build_target": ctx_or_path.get("build_target") or "App",
            "error_count": 0, "warning_count": 0,
            "build_log": "", "build_result": "",
        })
    else:
        try:
            cfg = analysis.load_layered_config(Path(ctx_or_path))[0]
            state_path = analysis.resolve_target(cfg, Path(ctx_or_path).parent) / "state.json"
        except Exception:
            state_path = None
    try:
        if state_path is not None:
            state_store.update_state(state_path, {"s7b": payload})
    except (OSError, state_store.StateLockTimeout):
        pass
    return payload


# ---------------- 任务书 ----------------

def _brief_cli(ctx: dict, system: str, build_config: str | None, project_file: Path,
               tools: dict, warnings: list[str]) -> list[str]:
    """CLI 机制任务书（编译由 build.py 纯 rule 执行，任务书为失败分析路径准备）。"""
    target_root = ctx["workspace"]
    lines: list[str] = []
    add = lines.append
    add("# S7b build 任务书（CLI 机制）")
    add("")
    add("> 由 prepare.py 生成（rule 轨）。编译由 `build.py` 纯 rule 执行；")
    add("> 本任务书为**编译失败后的 Agent 分析路径**准备。")
    add("")
    add("## 1. 编译参数")
    add("")
    add(f"- 构建系统：`{system}`（build_mode=cli）")
    add(f"- 构建配置：{build_config!r}")
    add(f"- 目标工程：`{ctx['build_target']}`（工程根 `{analysis.rel_posix(target_root, ctx['project_root'])}`）")
    add(f"- 工程文件：`{analysis.rel_posix(project_file, target_root)}`")
    add(f"- 编译命令：见 `references/{'keil' if system == 'keil' else ('iar' if system == 'iar' else 'gcc')}_build_guide.md`"
        "（--rebuild 开关与超时参数见 build.py --help）")
    add("")
    add("## 2. 工具链")
    add("")
    add("| 工具 | 路径 | 来源 |")
    add("|---|---|---|")
    for name, info in tools.items():
        if info["path"]:
            add(f"| {name} | `{info['path']}` | {'显式配置' if info['configured'] else '自动推导'} |")
        else:
            add(f"| {name} | **缺失** | - |")
    for w in warnings:
        add(f"- ⚠️ {w}")
    add("")
    add("## 3. 产物约定（编译成功后必须产出 bin）")
    add("")
    add("- 主调试产物 / hex / bin 的生成与转换规则：`references/binary_conversion_guide.md`")
    add("- 日志解析规则（错误/警告提取、多编码解码）：`references/log_parse_rules.md`")
    add("")
    add("## 4. 编译失败时的 Agent 分析路径（阶段 C）")
    add("")
    add("1. 读 `outputs/s7b/build.log` + `outputs/s7b/build_result.json` + 本 SKILL.md + `references/`")
    add("2. 按**代码问题 / 配置问题 / 环境问题 / 输入问题**四类根因归类（不简单归为 S5 代码问题）")
    add("3. 产出 `outputs/s7b/error_analysis.md`：错误摘要 / 每条错误详细分析 / 修复建议（**只建议不执行**）")
    add("4. 判定为 S5 代码问题时明确写出\"建议走 S5c code-fix 分支\"——由用户显式发起，不自动触发")
    add("")
    add("## 5. 禁止事项")
    add("")
    add("- 不自动修复代码、不修改任何源文件与配置文件、不修改工程文件")
    add("- 不自动触发 S5c code-fix 与任何下游 Skill")
    add("- 不臆造错误原因——分析必须基于 build.log 与 build_result.json 的实际内容")
    add("")
    return lines


def _brief_gui(ctx: dict, vendor: str, guide_path: Path, ide_project: Path,
               output_dir: Path, t0_iso: str) -> list[str]:
    """GUI 机制任务书（vendor_ide：Agent 按 vendor 指南操作厂家 IDE 编译）。"""
    target_root = ctx["workspace"]
    lines: list[str] = []
    add = lines.append
    add("# S7b build 任务书（GUI 机制，vendor_ide）")
    add("")
    add("> 由 prepare.py 生成（rule 轨）。厂家 IDE 无 CLI 支持，编译由 Agent")
    add("> 按 vendor 指南操作 IDE 完成，`build.py --collect` 收口。")
    add("")
    add("## 1. 编译参数")
    add("")
    add(f"- 构建系统：`vendor_ide`（build_mode=gui），厂家 IDE 标识：`{vendor}`")
    add(f"- 目标工程：`{ctx['build_target']}`")
    add(f"- IDE 可执行文件：`{ctx['tools'].get('vendor_ide', {}).get('path', '')}`")
    add(f"- 工程文件：`{analysis.rel_posix(ide_project, target_root)}`")
    add(f"- 编译输出目录：`{analysis.rel_posix(output_dir, target_root)}`")
    add(f"- **编译开始时刻 T0：`{t0_iso}`**（产物新旧判定基准，mtime ≤ T0 的产物不算本次产物）")
    add(f"- 超时：同 CLI `--timeout`（缺省 600 秒），超时按失败处理")
    add("")
    add("## 2. 操作指南（必须严格遵循）")
    add("")
    add(f"- vendor 指南：`references/vendor_ide/{vendor}.md`（启动方式 / 打开工程参数 /")
    add("  编译快捷键（菜单路径）/ 输出目录约定 / 编译完成判定特征 / 常见错误输出窗口特征）")
    add("- **只执行指南中列出的快捷键 / 菜单操作**——不点击任何未在指南中的控件，")
    add("  不打开工程配置 / 选项对话框")
    add("- **不保存任何工程文件改动**——关闭工程与 IDE 时遇到保存提示一律选\"否\"")
    add("- 不在 IDE 中编辑任何源代码（编译归编译，修复走 S5c code-fix）")
    add("- GUI 操作失败（快捷键未生效 / IDE 未响应）不得反复盲试超过 2 次——记录现象，")
    add("  归为环境问题进入 analyze")
    add("")
    add("## 3. 执行步骤（B1–B6）")
    add("")
    add("1. **B2** 启动厂家 IDE，打开上述工程文件，等待 IDE 就绪（按指南窗口特征判定）")
    add("2. **B3** 按 vendor 指南发送编译快捷键 / 菜单操作触发编译")
    add("3. **B4** 轮询输出目录文件 mtime 与 IDE 窗口状态判断编译完成（超时按失败处理）")
    add("4. **B5** 编译结束后从 IDE 输出窗口抄录错误/警告关键行写入 `outputs/s7b/build.log`；")
    add("   GUI 操作全过程（启动 / 快捷键 / 完成判定依据 / 观察到的输出）记录到")
    add("   `outputs/s7b/gui_build_log.md`")
    add("5. **B6** 关闭工程与 IDE（不保存任何工程文件改动，保存提示一律选\"否\"）")
    add("6. **B7** 运行 `build.py --collect` 收口（产物检测 mtime > T0 / intelhex 转 bin /")
    add("   build_result.json）")
    add("")
    return lines


# ---------------- 主流程 ----------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="S7b prepare: S5 就绪检查 + 构建系统/配置判定 + 工具链检测 + 任务书")
    parser.add_argument("--config", default="config.json", help="项目 config.json 路径")
    parser.add_argument("--workspace", default=None, help="覆盖项目目录（默认 --config 所在目录）")
    args = parser.parse_args(argv)

    config_path = Path(args.config).resolve()
    workspace = Path(args.workspace or ".").expanduser()
    if not workspace.is_absolute():
        workspace = (config_path.parent / workspace).resolve()

    # ---- 1. 上下文：配置加载 + S5 就绪检查 ----
    try:
        ctx = analysis.load_build_context(config_path, workspace)
    except (RuntimeError, FileNotFoundError, json.JSONDecodeError, OSError) as exc:
        payload = _write_error_state(config_path, str(exc))
        _log(str(exc))
        print(json.dumps({"s7b": payload}, ensure_ascii=False, indent=2))
        return EXIT_CONFIG_ERROR

    target_root = ctx["workspace"]
    s7b_out = ctx["s7b_outputs"]
    s7b_out.mkdir(parents=True, exist_ok=True)

    # ---- 2. 平台与编译机制判定 ----
    arch_family = ctx["arch_family"]
    system_cfg = ctx["build_system_cfg"]
    vendor = ctx["vendor_ide"]
    ide_project_cfg = ctx["ide_project"]

    def fail(msg: str) -> int:
        payload = _write_error_state(ctx, msg)
        _log(msg)
        print(json.dumps({"s7b": payload}, ensure_ascii=False, indent=2))
        return EXIT_CONFIG_ERROR

    if system_cfg == "vendor_ide":
        if arch_family == "cortex_m":
            return fail("build_system=vendor_ide 仅用于厂家自研 IDE 无 CLI 的 8 位平台；"
                        "Cortex-M 的 Keil/IAR/GCC 均有 CLI，请改用对应构建系统")
        if not vendor:
            return fail("build_system=vendor_ide 时 project.vendor_ide 必填"
                        "（用于定位 references/vendor_ide/<标识>.md 操作指南）")
        if not ide_project_cfg:
            return fail("build_system=vendor_ide 时 project.inputs.ide_project 必填"
                        "（GUI 打开的目标）")
        guide = SKILL_DIR / "references" / "vendor_ide" / f"{vendor}.md"
        if not guide.is_file():
            return fail(f"厂家 IDE 操作指南不存在: references/vendor_ide/{vendor}.md"
                        "——请先为该厂家 IDE 编写指南（模板见 references/vendor_ide/_template.md）")
    else:
        if arch_family == "mcu8" and not system_cfg:
            return fail("8 位平台（arch_family=mcu8）不自动推断构建系统（厂家工程文件格式"
                        "各异）——请显式配置 project.build_system（vendor_ide 或厂家 IDE "
                        "对应的 CLI 值）")

    # ---- 3. 构建系统判定（显式优先，否则推断） ----
    build_system = system_cfg
    project_file: Path | None = None
    makefile_gen_result: dict | None = None  # 阶段 A' 生成结果（仅显式 gcc_make 触发）
    if build_system == "vendor_ide":
        project_file = (target_root / ide_project_cfg).resolve()
        if not project_file.is_file():
            return fail(f"IDE 工程文件不存在: {ide_project_cfg}（project.inputs.ide_project）")
    else:
        try:
            inferred, found = analysis.infer_build_system(
                target_root, ide_project_cfg) if not build_system else (build_system, None)
        except analysis.BuildDetectError as exc:
            return fail(str(exc))
        if not build_system:
            build_system = inferred
            project_file = found
            _log(f"构建系统推断: {build_system}（依据 {project_file.name}）")
        else:
            # 显式配置：定位对应工程文件
            if ide_project_cfg:
                project_file = (target_root / ide_project_cfg).resolve()
            if project_file is None or not project_file.is_file():
                evidence = analysis.scan_build_evidence(target_root)
                files = evidence.get(build_system, [])
                if len(files) == 1 and not (build_system == "gcc_make"
                                            and makefile_gen.is_generated_file(files[0])):
                    project_file = files[0]
                elif build_system == "gcc_make" and files and all(
                        makefile_gen.is_generated_file(f) for f in files):
                    # 阶段 A'（重新生成）：现有 Makefile 全部为本 skill 生成（含标记）
                    # → 重新生成（拾取模板修正等）；用户自维护文件（无标记）不进入此分支
                    try:
                        makefile_gen_result = _generate_makefile(ctx, target_root)
                    except makefile_gen.MakefileGenError as exc:
                        return fail(f"Makefile 自动生成失败: {exc}"
                                    "——请手写 Makefile 或改用 keil/iar")
                    for w in makefile_gen_result["warnings"]:
                        _log(f"阶段 A': {w}")
                    project_file = target_root / "Makefile"
                    if not project_file.is_file():
                        return fail("Makefile 自动生成被跳过（用户自维护文件存在）"
                                    "——如需自动生成请删除现有 Makefile")
                elif not files:
                    if build_system == "gcc_make":
                        # 阶段 A'（首次生成）：无任何 Makefile → 自动生成
                        try:
                            makefile_gen_result = _generate_makefile(ctx, target_root)
                        except makefile_gen.MakefileGenError as exc:
                            return fail(f"Makefile 自动生成失败: {exc}"
                                        "——请手写 Makefile 或改用 keil/iar")
                        for w in makefile_gen_result["warnings"]:
                            _log(f"阶段 A': {w}")
                        mk = target_root / "Makefile"
                        if mk.is_file():
                            project_file = mk
                        else:
                            return fail("Makefile 自动生成被跳过（用户自维护文件存在）"
                                        "——如需自动生成请删除现有 Makefile")
                    else:
                        return fail(f"未发现 {build_system} 的工程文件（目标工程根 {target_root}）"
                                    "——请创建工程文件或检查 project.build_system 配置")
                elif len(files) > 1 and project_file is None:
                    if build_system == "gcc_make":
                        # 混合场景：存在用户自维护 Makefile（无标记）→ 用之，不覆盖
                        user_mks = [f for f in files
                                    if not makefile_gen.is_generated_file(f)]
                        if len(user_mks) == 1:
                            project_file = user_mks[0]
                            _log(f"使用用户自维护的 Makefile: {user_mks[0].name}（不覆盖）")
                        else:
                            names = "、".join(str(f.relative_to(target_root)) for f in user_mks)
                            return fail(f"发现多个 Makefile（{names}）——"
                                        "请在 project.inputs.ide_project 指定其一")
                    else:
                        names = "、".join(str(f.relative_to(target_root)) for f in files)
                        return fail(f"发现多个 {build_system} 工程文件（{names}）——"
                                    "请在 project.inputs.ide_project 指定其一")
        if project_file is None or not project_file.is_file():
            return fail(f"工程文件不存在: {project_file}")

    # ---- 4. 构建配置判定（显式优先；多候选报错；vendor_ide 无 config 概念） ----
    build_config = ctx["build_config_cfg"]
    if build_system != "vendor_ide" and not build_config:
        try:
            build_config = analysis.infer_build_config(build_system, project_file)
        except analysis.BuildDetectError as exc:
            return fail(str(exc))
        if build_config:
            _log(f"构建配置推断: {build_config}")
    if build_system == "vendor_ide":
        build_config = None

    # ---- 5. 工具链就绪检查 ----
    tools = analysis.resolve_tool_paths(ctx["config"], build_system)
    ctx["tools"] = tools
    warnings: list[str] = []
    missing_compile = [t for t in analysis.compile_tools_required(build_system)
                       if not tools.get(t, {}).get("path")]
    if missing_compile:
        return fail(f"编译工具缺失: {', '.join(missing_compile)}"
                    "——先运行 S7a toolchain-setup 或手动配置全局 config.json 的 tool_paths"
                    "（S7b 不自动触发 S7a）")
    missing_bin = [t for t in analysis.bin_tools(build_system)
                   if not tools.get(t, {}).get("path")]
    if missing_bin:
        if analysis.intelhex_available():
            warnings.append(f"bin/hex 转换工具缺失: {', '.join(missing_bin)}"
                            "——编译成功后降级用 Python intelhex 从 hex 转 bin（仅警告不终止）")
        else:
            warnings.append(f"bin/hex 转换工具缺失: {', '.join(missing_bin)}，且 intelhex "
                            "未安装（pip install intelhex）——bin_path 将为 null，"
                            "S6 合并时需用户手动提供 bin")
    if makefile_gen_result is not None:
        warnings.extend(makefile_gen_result["warnings"])

    # ---- 6. 任务书 + state ----
    t0_iso = datetime.now().isoformat(timespec="seconds")
    brief_rel = "outputs/s7b/generation_brief.md"
    brief_path = s7b_out / "generation_brief.md"
    if build_system == "vendor_ide":
        out_dir_rel = ctx["vendor_ide_output_dir"] or "Project/Output/"
        out_dir = target_root / out_dir_rel
        brief_path.write_text("\n".join(_brief_gui(
            ctx, vendor, SKILL_DIR / "references" / "vendor_ide" / f"{vendor}.md",
            project_file, out_dir, t0_iso)) + "\n", encoding="utf-8", newline="\n")
        # GUI 机制：T0 落盘供 build.py --collect 机械读取（同时写入任务书）
        analysis.save_json(s7b_out / "gui_session.json", {
            "t0": t0_iso,
            "vendor_ide": vendor,
            "ide_project": analysis.rel_posix(project_file, target_root),
            "output_dir": out_dir_rel.replace("\\", "/"),
        })
    else:
        brief_path.write_text("\n".join(_brief_cli(
            ctx, build_system, build_config, project_file, tools, warnings)) + "\n",
            encoding="utf-8", newline="\n")

    payload = {
        "status": "running",
        "build_system": build_system,
        "build_mode": "gui" if build_system == "vendor_ide" else "cli",
        "build_config": build_config,
        "build_target": ctx["build_target"],
        "artifact_path": None, "artifact_format": None,
        "hex_path": None, "bin_path": None,
        "error_count": 0, "warning_count": 0,
        "build_log": "outputs/s7b/build.log",
        "build_result": "outputs/s7b/build_result.json",
        "makefile_generated": bool(makefile_gen_result
                                    and makefile_gen_result["makefile_generated"]),
        "linker_script_generated": bool(makefile_gen_result
                                         and makefile_gen_result["linker_script_generated"]),
        "error_analysis": None,
        "gui_build_log": "outputs/s7b/gui_build_log.md"
                          if build_system == "vendor_ide" else None,
        "bin_warning": ("; ".join(warnings) if warnings else None),
        "error": None,
        "updated_at": t0_iso,
    }
    schema_errors = analysis.validate_schema(
        payload, SKILL_DIR / "schemas" / "output.schema.json", "s7b")
    if schema_errors:
        payload = _write_error_state(ctx, "; ".join(schema_errors))
        _log("s7b 状态契约校验失败: " + "; ".join(schema_errors))
        print(json.dumps({"s7b": payload}, ensure_ascii=False, indent=2))
        return EXIT_CONFIG_ERROR
    state_store.update_state(ctx["state_path"], {"s7b": payload})

    _log(f"任务书已生成: {brief_path}")
    for w in warnings:
        _log(f"警告: {w}")
    _log("下一步：CLI 机制运行 build.py 编译；GUI 机制按任务书操作厂家 IDE 后运行 "
         "build.py --collect；完成后 validate.py 收口")
    print(json.dumps({"s7b": payload}, ensure_ascii=False, indent=2))
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
