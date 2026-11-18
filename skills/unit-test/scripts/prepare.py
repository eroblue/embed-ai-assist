"""Prepare an S8 run and select a bounded batch of source modules."""
from __future__ import annotations

import argparse
import uuid
from datetime import datetime, timezone
from pathlib import Path

from common import context, inventory, read_json, select, write_json


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--mode", choices=["budget", "ratio", "explicit", "changed", "all"])
    ap.add_argument("--ratio", type=float)
    ap.add_argument("--units", help="comma-separated unit IDs")
    ap.add_argument("--critical-units", help="comma-separated unit IDs")
    ap.add_argument("--max-agent-units", type=int)
    ap.add_argument("--baseline", help="previous unit_inventory.json for changed mode")
    args = ap.parse_args()
    try:
        config, _, target = context(args.config)
        settings = dict(config.get("s8", {}).get("selection", {}))
        for key, value in (("mode", args.mode), ("ratio", args.ratio),
                           ("max_agent_units", args.max_agent_units)):
            if value is not None:
                settings[key] = value
        for key, value in (("units", args.units), ("critical_units", args.critical_units)):
            if value is not None:
                settings[key] = [v.strip() for v in value.split(",") if v.strip()]
        previous = read_json(Path(args.baseline)) if args.baseline else None
        inv = inventory(target)
        selection = select(inv, settings, previous)
        run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
        run_dir = target / "outputs" / "s8" / run_id
        run_dir.mkdir(parents=True, exist_ok=False)
        write_json(run_dir / "unit_inventory.json", inv)
        write_json(run_dir / "selection.json", selection)
        brief = [f"# S8 batch {run_id}", "", "Review only these source modules:", ""]
        brief += [f"- `{item}`" for item in selection["batch"]]
        brief += ["", f"Deferred: {len(selection['deferred'])}; unselected: {len(selection['unselected'])}.",
                  "Inventory is provisional; review source boundaries and expected behavior before writing tests.",
                  "Write tests/unit/test_plan.json plus test C and mock C files, then run run.py --run-dir."]
        (run_dir / "generation_brief.md").write_text("\n".join(brief) + "\n", encoding="utf-8")
        print(run_dir)
        return 0
    except (ValueError, OSError, ImportError) as exc:
        print(f"S8 prepare error: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
