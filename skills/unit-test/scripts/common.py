"""S8 shared configuration, inventory, selection and artifact helpers."""
from __future__ import annotations

import hashlib
import json
import math
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
ROOT = SKILL_DIR.parent.parent
sys.path.insert(0, str(ROOT / "skills" / "_shared" / "scripts"))
from state_store import update_state  # noqa: E402


def read_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return value


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def deep_merge(a: dict, b: dict) -> dict:
    result = dict(a)
    for key, value in b.items():
        result[key] = deep_merge(result[key], value) if isinstance(value, dict) and isinstance(result.get(key), dict) else value
    return result


def context(config_path: str) -> tuple[dict, Path, Path]:
    cfg_path = Path(config_path).resolve()
    project = cfg_path.parent
    config = deep_merge(read_json(ROOT / "config.json"), read_json(cfg_path))
    schema_validate(config, ROOT / "schemas" / "config.schema.json")
    target = project / config.get("project", {}).get("build_target", "App")
    if not target.is_dir():
        raise ValueError(f"target directory missing: {target}")
    return config, project, target


def schema_validate(value: dict, path: Path) -> None:
    from jsonschema import Draft202012Validator
    errors = sorted(Draft202012Validator(read_json(path)).iter_errors(value), key=lambda e: str(e.path))
    if errors:
        raise ValueError("; ".join(f"{'.'.join(map(str, e.path))}: {e.message}" for e in errors))


def inside(target: Path, rel: str, must_exist: bool = True) -> Path:
    path = (target / rel).resolve()
    if not path.is_relative_to(target.resolve()):
        raise ValueError(f"path escapes target: {rel}")
    if must_exist and not path.is_file():
        raise ValueError(f"file missing: {path}")
    return path


def rel(target: Path, path: Path) -> str:
    return path.resolve().relative_to(target.resolve()).as_posix()


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def inventory(target: Path) -> dict:
    modules = []
    for source_dir in ("App/Src", "Drivers/BSP/Src", "Drivers/Port/Src"):
        folder = target / source_dir
        if not folder.exists():
            continue
        for file in sorted(folder.glob("*.c")):
            if file.name == "main.c":
                continue
            source = rel(target, file)
            text = file.read_text(encoding="utf-8-sig", errors="replace")
            # Function names are hints only; C macros and conditional compilation make
            # a regex scanner unsuitable for declaring a verified testable boundary.
            hints = re.findall(r"(?m)^\s*(?:[\w*]+\s+)+([A-Za-z_]\w*)\s*\([^;]*?\)\s*\{", text)
            modules.append({"id": source.removesuffix(".c"), "source": source,
                            "sha256": digest(file), "function_hints": sorted(set(hints)),
                            "review_status": "unreviewed"})
    return {"generated_at": now(), "candidate_count": len(modules),
            "inventory_uncertain": True, "denominator_kind": "source_module_candidates",
            "units": modules}


def resolve_ids(names: list[str], units: list[dict]) -> list[str]:
    ids = {u["id"] for u in units}
    result = []
    for name in names:
        matches = [u["id"] for u in units if u["id"] == name or u["id"].split("/")[-1] == name]
        if len(matches) != 1:
            raise ValueError(f"unknown or ambiguous unit ID: {name}")
        if matches[0] not in result:
            result.append(matches[0])
    return result


def select(inv: dict, settings: dict, previous: dict | None) -> dict:
    units = inv["units"]
    all_ids = [u["id"] for u in units]
    mode = settings.get("mode", "budget")
    max_agent = settings.get("max_agent_units", 20)
    if not isinstance(max_agent, int) or isinstance(max_agent, bool) or max_agent < 1:
        raise ValueError("max_agent_units must be a positive integer")
    critical = resolve_ids(settings.get("critical_units", []), units)
    explicit = resolve_ids(settings.get("units", []), units)
    previous_hashes = {u["id"]: u["sha256"] for u in previous.get("units", [])} if previous else {}
    changed = [u["id"] for u in units if u["id"] in previous_hashes and u["sha256"] != previous_hashes[u["id"]]]
    if mode == "changed" and not previous:
        raise ValueError("changed mode requires a previous unit_inventory.json baseline")
    ranked = list(dict.fromkeys(critical + changed + sorted(all_ids)))
    if mode == "explicit":
        if not explicit:
            raise ValueError("explicit mode requires units")
        planned = list(dict.fromkeys(critical + explicit))
    elif mode == "changed":
        planned = list(dict.fromkeys(critical + changed))
    elif mode == "ratio":
        ratio = settings.get("ratio")
        if not isinstance(ratio, (float, int)) or isinstance(ratio, bool) or not 0 < ratio <= 1:
            raise ValueError("ratio must be > 0 and <= 1")
        planned = ranked[:max(math.ceil(len(all_ids) * ratio), len(critical))]
    elif mode == "budget":
        planned = ranked[:max(max_agent, len(critical))]
    elif mode == "all":
        planned = ranked
    else:
        raise ValueError(f"unsupported selection mode: {mode}")
    # Prioritize critical units even when only the first batch can be authored.
    batch = planned[:max_agent]
    return {"mode": mode, "settings": settings, "denominator_kind": inv["denominator_kind"],
            "inventory_uncertain": inv["inventory_uncertain"], "candidate_count": len(all_ids),
            "critical": critical, "planned": planned, "batch": batch,
            "deferred": planned[max_agent:], "unselected": [x for x in all_ids if x not in planned],
            "requested_ratio": settings.get("ratio") if mode == "ratio" else None,
            "planned_ratio": len(planned) / len(all_ids) if all_ids else 0,
            "batch_ratio": len(batch) / len(all_ids) if all_ids else 0,
            "max_agent_units": max_agent}


def compiler(name: str | None) -> str:
    if name:
        path = shutil.which(name) or (str(Path(name).resolve()) if Path(name).is_file() else None)
        if not path:
            raise ValueError(f"host compiler not found: {name}")
        return path
    found = [shutil.which(x) for x in ("gcc", "clang", "cc")]
    found = [x for x in found if x]
    if not found:
        raise ValueError("host C compiler not found; set s8.host_compiler")
    return found[0]
