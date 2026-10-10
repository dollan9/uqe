#!/usr/bin/env python3
"""validate_evidence.py — UQE evidence-report validator (zero-dependency).

Checks a JSON evidence report against evidence.schema.json using a built-in
subset validator (type/enum/required/minLength/minItems/additionalProperties),
plus semantic gates the schema cannot express:

  * file-typed evidence (screenshot/frame/render/test_output/diff/measurement/
    audit_log/command_output) must point at an artifact that EXISTS on disk,
    unless --no-file-check is passed;
  * citation-type evidence paths must be http(s) URLs.

Exit codes: 0 valid · 1 invalid · 2 usage/environment error.
Usage: python3 scripts/validate_evidence.py report.json [--schema path] [--root dir] [--no-file-check]
"""
import argparse
import json
import os
import sys

FILE_REQUIRED_TYPES = {
    "screenshot", "frame", "render", "test_output", "diff",
    "measurement", "audit_log", "command_output",
}

def fail(msg):
    print(f"[evidence][INVALID] {msg}")
    return False

def check_type(value, expected):
    mapping = {
        "object": dict, "array": list, "string": str,
        "integer": int, "number": (int, float), "boolean": bool,
    }
    t = mapping.get(expected)
    if t is None:
        return True
    if expected == "integer" and isinstance(value, bool):
        return False
    return isinstance(value, t)

def validate(node, schema, path, errors):
    """Minimal draft-2020 subset: type, enum, required, properties,
    additionalProperties (bool or subschema), items, minLength, minItems,
    minimum, maximum, minProperties."""
    t = schema.get("type")
    if t and not check_type(node, t):
        errors.append(f"{path}: expected type {t}, got {type(node).__name__}")
        return
    if "enum" in schema and node not in schema["enum"]:
        errors.append(f"{path}: {node!r} not in enum {schema['enum']}")
    if isinstance(node, dict):
        for req in schema.get("required", []):
            if req not in node:
                errors.append(f"{path}: missing required key '{req}'")
        props = schema.get("properties", {})
        ap = schema.get("additionalProperties", True)
        for k, v in node.items():
            if k in props:
                validate(v, props[k], f"{path}.{k}", errors)
            elif ap is False:
                errors.append(f"{path}: unexpected key '{k}' (additionalProperties: false)")
            elif isinstance(ap, dict):
                validate(v, ap, f"{path}.{k}", errors)
        if "minProperties" in schema and len(node) < schema["minProperties"]:
            errors.append(f"{path}: needs >= {schema['minProperties']} properties")
    if isinstance(node, list):
        if "minItems" in schema and len(node) < schema["minItems"]:
            errors.append(f"{path}: needs >= {schema['minItems']} items")
        items = schema.get("items")
        if isinstance(items, dict):
            for i, el in enumerate(node):
                validate(el, items, f"{path}[{i}]", errors)
    if isinstance(node, str):
        if "minLength" in schema and len(node) < schema["minLength"]:
            errors.append(f"{path}: string shorter than {schema['minLength']} chars")
    if isinstance(node, (int, float)) and not isinstance(node, bool):
        if "minimum" in schema and node < schema["minimum"]:
            errors.append(f"{path}: {node} < minimum {schema['minimum']}")
        if "maximum" in schema and node > schema["maximum"]:
            errors.append(f"{path}: {node} > maximum {schema['maximum']}")

def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    elif len(argv) > 0 and argv[0].endswith(".py"):
        argv = argv[1:]

    here = os.path.dirname(os.path.abspath(__file__))
    default_schema = os.path.join(here, os.pardir, "evidence.schema.json")

    parser = argparse.ArgumentParser(
        description="validate_evidence.py — UQE evidence-report validator (zero-dependency).",
    )
    parser.add_argument("report", help="Path to evidence report JSON")
    parser.add_argument("--schema", default=default_schema, help="Path to evidence.schema.json")
    parser.add_argument("--root", default=os.getcwd(), help="Root directory for workspace artifact paths")
    parser.add_argument("--no-file-check", action="store_true", help="Skip checking that referenced artifact files exist on disk")

    try:
        parsed = parser.parse_args(argv)
    except SystemExit as exc:
        return exc.code

    report_path = parsed.report
    schema_path = parsed.schema
    root = parsed.root
    no_file_check = parsed.no_file_check

    try:
        with open(schema_path, encoding="utf-8") as f:
            schema = json.load(f)
    except OSError as e:
        print(f"[evidence][ERROR] cannot read schema {schema_path}: {e}", file=sys.stderr)
        return 2
    try:
        with open(report_path, encoding="utf-8") as f:
            report = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        print(f"[evidence][INVALID] cannot parse report {report_path}: {e}")
        return 1

    errors = []
    validate(report, schema, "$", errors)

    if not no_file_check:
        for i, ev in enumerate(report.get("evidence", []) if isinstance(report.get("evidence"), list) else []):
            if not isinstance(ev, dict):
                continue
            etype, epath = ev.get("type", ""), ev.get("path", "")
            if etype in FILE_REQUIRED_TYPES and epath and not epath.startswith(("http://", "https://")):
                full = epath if os.path.isabs(epath) else os.path.join(root, epath)
                if not os.path.exists(full):
                    errors.append(f"$.evidence[{i}]: file-backed evidence '{etype}' points to nonexistent artifact: {epath}")
            if etype == "citation" and not str(epath).startswith(("http://", "https://", "doi:", "isbn:")):
                errors.append(f"$.evidence[{i}]: citation path must be a URL/DOI/ISBN, got: {epath}")

    if errors:
        for e in errors:
            fail(e)
        print(f"[evidence] {len(errors)} problem(s). Fix or mark claims UNVERIFIED (SKILL.md Section 5).")
        return 1

    n = len(report.get("evidence", []))
    d = len(report.get("defects", []))
    print(f"[evidence] VALID: {n} evidence item(s), {d} defect(s) recorded. Report: {report_path}")
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv))
