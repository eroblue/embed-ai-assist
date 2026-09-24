"""S2 spec-reader 确定性分析共享模块（rule 轨，prepare/validate 共用）。

职责边界（与 S5a/S5b 同策略：rule 只做确定性契约工作，需求条目内容提取归
Agent/LLM）：
- 分层配置加载、目标工程定位（App/BootLoader 双工程根）、S2 执行上下文组装
- JSON 读写（tmp+replace 原子写）与 schema 校验
- 规格书格式识别（扩展名 → 提取器）

本模块不解析规格书内容、不生成需求条目、不写 state.json（state 写入统一走
state_store，见 prepare/validate）。
"""

from __future__ import annotations

import json
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
ROOT_DIR = SKILL_DIR.parent.parent

SUPPORTED_SUFFIXES = {".md": "markdown", ".txt": "markdown", ".docx": "docx", ".pdf": "pdf"}

# ---------------- JSON / 配置工具（与 S5a/S5b analysis 同模式，skill 间不耦合） ----------------

def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8-sig") as f:
        return json.load(f)


def save_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    tmp.replace(path)


def deep_merge(base: dict, override: dict) -> dict:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def load_layered_config(project_config_path: Path) -> tuple[dict, list[str]]:
    """根目录 config.json → 项目 config.json 深合并（只读，不回写）。"""
    notes: list[str] = []
    root_cfg: dict = {}
    root_config_path = ROOT_DIR / "config.json"
    if root_config_path.is_file():
        root_cfg = load_json(root_config_path)
        notes.append(f"已加载全局配置: {root_config_path}")
    if not project_config_path.is_file():
        raise FileNotFoundError(f"项目配置不存在: {project_config_path}")
    proj_cfg = load_json(project_config_path)
    notes.append(f"已加载项目配置: {project_config_path}")
    return deep_merge(root_cfg, proj_cfg), notes


def validate_schema(instance: dict, schema_path: Path, label: str) -> list[str]:
    """jsonschema 校验，返回错误列表（未安装 jsonschema 时跳过并提示）。"""
    try:
        from jsonschema import Draft202012Validator
    except ImportError:
        return ["jsonschema 未安装，跳过校验: pip install jsonschema"]
    schema = load_json(schema_path)
    errors = sorted(Draft202012Validator(schema).iter_errors(instance), key=lambda e: list(e.path))
    return [f"{label}: {'/'.join(map(str, e.path)) or '<root>'}: {e.message}" for e in errors]


def resolve_target(config: dict | None, project_root: Path) -> Path:
    """目标工程根（App/BootLoader 双工程）：project.build_target 决定（缺省 App）。"""
    target = ((config or {}).get("project") or {}).get("build_target") or "App"
    return project_root / str(target)


# ---------------- S2 执行上下文 ----------------

def load_context(config_path: Path, workspace: Path | None = None) -> dict:
    """加载配置与输入，返回 S2 执行上下文。

    S2 只依赖 S1 建立的工作区（state.json 存在）与 config 的
    project.inputs.functional_spec（必选）。不读其他 Skill 的 state 字段。
    """
    config, _notes = load_layered_config(config_path)
    cfg_errors = validate_schema(config, ROOT_DIR / "schemas" / "config.schema.json", "config")
    if cfg_errors:
        raise RuntimeError("配置契约校验失败: " + "; ".join(cfg_errors))
    if workspace is None:
        workspace = config_path.parent
    project_root = workspace
    workspace = resolve_target(config, project_root)
    state_path = workspace / "state.json"
    if not state_path.exists():
        raise RuntimeError(f"state.json 不存在: {state_path}（先执行 S1 建立工作区）")
    state = load_json(state_path)

    input_errors = validate_schema(state, SKILL_DIR / "schemas" / "input.schema.json", "state")
    if input_errors:
        raise RuntimeError("输入契约校验失败: " + "; ".join(input_errors))

    project_cfg = config.get("project") or {}
    inputs_cfg = project_cfg.get("inputs") or {}
    s2_cfg = config.get("s2") or {}

    # 功能规格书（必选，相对项目根）
    spec_rel = str(inputs_cfg.get("functional_spec") or "").strip()
    if not spec_rel:
        raise RuntimeError(
            "config 缺少 project.inputs.functional_spec（功能规格书路径，相对项目根）"
            "——S2 无输入无法执行")
    spec_abs = (project_root / spec_rel).resolve()
    if not spec_abs.is_file():
        raise RuntimeError(f"功能规格书不存在: {spec_abs}")

    suffix = spec_abs.suffix.lower()
    if suffix not in SUPPORTED_SUFFIXES:
        raise RuntimeError(
            f"不支持的功能规格书格式: '{spec_abs.suffix}'"
            f"（支持 {'/'.join(sorted(set(SUPPORTED_SUFFIXES)))}）")

    # 软件规格书（可选，仅登记指针不解析）
    software_spec = str(inputs_cfg.get("software_spec") or "").strip() or None

    return {
        "config": config,
        "workspace": workspace,          # 目标工程根 <项目根>/<build_target>/
        "project_root": project_root,    # 项目根（docs/ 等共享资源）
        "state_path": state_path,
        "state": state,
        "outputs_dir": workspace / (config.get("output_dir") or "outputs").rstrip("/\\"),
        "spec_file": spec_rel,           # 相对项目根（state.source_file 登记值）
        "spec_abs": spec_abs,            # 绝对路径
        "source_type": SUPPORTED_SUFFIXES[suffix],
        "software_spec": software_spec,
        "language": s2_cfg.get("language") or "zh-CN",
        "strict_mode": bool(s2_cfg.get("strict_mode", False)),
    }
