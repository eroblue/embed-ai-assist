"""Compile and execute project-owned unit tests selected by S8 prepare."""
from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

from common import SKILL_DIR, compiler, context, digest, inside, now, read_json, rel, schema_validate, write_json


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--run-dir", required=True)
    args = ap.parse_args()
    try:
        config, _, target = context(args.config)
        run_dir = Path(args.run_dir).resolve()
        if not run_dir.is_relative_to((target / "outputs" / "s8").resolve()):
            raise ValueError("run-dir must be under target/outputs/s8")
        selection = read_json(run_dir / "selection.json")
        plan_path = target / "tests" / "unit" / "test_plan.json"
        plan = read_json(plan_path)
        schema_validate(plan, SKILL_DIR / "schemas" / "test_plan.schema.json")
        host_compiler = compiler(config.get("s8", {}).get("host_compiler"))
        timeout = config.get("s8", {}).get("test_timeout_seconds", 60)
        if not isinstance(timeout, int) or timeout < 1:
            raise ValueError("test_timeout_seconds must be a positive integer")
        planned = {u["id"]: u for u in plan["units"]}
        if len(planned) != len(plan["units"]):
            raise ValueError("duplicate unit ID in test plan")
        results = []
        files = {rel(target, plan_path): digest(plan_path)}
        build_lines = []
        test_lines = []
        for unit_id in selection["batch"]:
            unit = planned.get(unit_id)
            if not unit:
                results.append({"unit_id": unit_id, "status": "needs_clarification", "reason": "no reviewed test plan"})
                continue
            if unit["status"] != "ready":
                results.append({"unit_id": unit_id, "status": unit["status"], "reason": unit.get("reason", "")})
                continue
            source = inside(target, unit["source"])
            test_source = inside(target, unit["test_source"])
            if not rel(target, test_source).startswith("tests/unit/"):
                raise ValueError(f"test source must be in tests/unit: {test_source}")
            expected_source = next(u["source"] for u in read_json(run_dir / "unit_inventory.json")["units"] if u["id"] == unit_id)
            if unit["source"] != expected_source:
                raise ValueError(f"plan source mismatch for {unit_id}")
            mock_sources = [inside(target, p) for p in unit.get("mocks", [])]
            includes = [inside(target, p, must_exist=False) for p in unit.get("include_dirs", [])]
            if len({c["id"] for c in unit["cases"]}) != len(unit["cases"]):
                raise ValueError(f"duplicate case ID for {unit_id}")
            for path in [source, test_source, *mock_sources]:
                if path != source and not rel(target, path).startswith("tests/unit/"):
                    raise ValueError(f"test code outside tests/unit: {path}")
                files[rel(target, path)] = digest(path)
            for include_dir in includes:
                if not include_dir.is_dir():
                    raise ValueError(f"include directory missing: {include_dir}")
                for header in include_dir.rglob("*.h"):
                    files[rel(target, header)] = digest(header)
            exe = run_dir / (unit_id.replace("/", "_") + ".exe")
            cmd = [host_compiler, "-std=c99", "-Wall", "-Wextra", "-o", str(exe),
                   str(source), str(test_source), *map(str, mock_sources),
                   *[f"-I{p}" for p in includes], f"-I{target / 'tests' / 'unit' / 'support'}"]
            build_lines.append("$ " + subprocess.list2cmdline(cmd))
            built = subprocess.run(cmd, capture_output=True, text=True, errors="replace", timeout=120)
            build_lines += [built.stdout, built.stderr, f"exit={built.returncode}"]
            if built.returncode:
                results.append({"unit_id": unit_id, "status": "failed", "reason": "test compilation failed", "cases": []})
                continue
            try:
                run = subprocess.run([str(exe)], capture_output=True, text=True, errors="replace", timeout=timeout)
            except subprocess.TimeoutExpired:
                results.append({"unit_id": unit_id, "status": "failed", "reason": "test timeout", "cases": []})
                test_lines.append(f"{unit_id}: timeout after {timeout}s")
                continue
            test_lines += [f"$ {exe}", run.stdout, run.stderr, f"exit={run.returncode}"]
            observed = {}
            for line in run.stdout.splitlines():
                if line.startswith("S8_CASE\t"):
                    fields = line.split("\t", 3)
                    if len(fields) >= 3 and fields[2] in ("PASS", "FAIL"):
                        observed.setdefault(fields[1], []).append(fields[2])
            cases = []
            for case in unit["cases"]:
                hits = observed.get(case["id"], [])
                status = "passed" if hits == ["PASS"] else "failed"
                cases.append({"id": case["id"], "status": status, "observed": hits,
                              "expected_basis": case["expected_basis"]})
            extras = set(observed) - {c["id"] for c in unit["cases"]}
            good = bool(cases) and all(c["status"] == "passed" for c in cases) and not extras and run.returncode == 0
            results.append({"unit_id": unit_id, "status": "passed" if good else "failed",
                            "reason": "" if good else f"exit={run.returncode}; extra cases={sorted(extras)}", "cases": cases})
        version = subprocess.run([host_compiler, "--version"], capture_output=True, text=True, errors="replace", timeout=10)
        manifest = {"created_at": now(), "run_id": run_dir.name, "compiler": host_compiler,
                    "compiler_version": version.stdout.splitlines()[0] if version.stdout else "unknown",
                    "source_hashes": files, "selection_path": "selection.json"}
        write_json(run_dir / "run_manifest.json", manifest)
        (run_dir / "build.log").write_text("\n".join(build_lines), encoding="utf-8")
        (run_dir / "test.log").write_text("\n".join(test_lines), encoding="utf-8")
        result = {"run_id": run_dir.name, "created_at": now(), "units": results,
                  "passed_count": sum(c["status"] == "passed" for u in results for c in u.get("cases", [])),
                  "failed_count": sum(c["status"] == "failed" for u in results for c in u.get("cases", [])),
                  "selection_path": "selection.json", "manifest_path": "run_manifest.json"}
        schema_validate(result, SKILL_DIR / "schemas" / "result.schema.json")
        write_json(run_dir / "result.json", result)
        print(run_dir / "result.json")
        return 1 if any(u["status"] == "failed" for u in results) else 0
    except (ValueError, OSError, ImportError, subprocess.TimeoutExpired, KeyError) as exc:
        print(f"S8 run error: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
