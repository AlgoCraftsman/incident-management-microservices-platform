from __future__ import annotations

import argparse
import importlib
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OPENAPI_DIR = ROOT / "docs" / "openapi"
PLATFORM_COMMON = ROOT / "libs" / "platform_common"


@dataclass(frozen=True)
class ServiceSpec:
    name: str
    service_dir: Path
    output_file: Path


SERVICES = [
    ServiceSpec(
        name="incidents-service",
        service_dir=ROOT / "services" / "incidents-service",
        output_file=OPENAPI_DIR / "incidents-service.openapi.json",
    ),
    ServiceSpec(
        name="alerts-service",
        service_dir=ROOT / "services" / "alerts-service",
        output_file=OPENAPI_DIR / "alerts-service.openapi.json",
    ),
    ServiceSpec(
        name="oncall-service",
        service_dir=ROOT / "services" / "oncall-service",
        output_file=OPENAPI_DIR / "oncall-service.openapi.json",
    ),
    ServiceSpec(
        name="status-page-service",
        service_dir=ROOT / "services" / "status-page-service",
        output_file=OPENAPI_DIR / "status-page-service.openapi.json",
    ),
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Export FastAPI OpenAPI contracts for all platform services.")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail if checked-in OpenAPI contracts differ from generated output.",
    )
    args = parser.parse_args()

    OPENAPI_DIR.mkdir(parents=True, exist_ok=True)
    changed: list[Path] = []
    for service in SERVICES:
        document = generate_contract(service)
        rendered = render_json(document)
        if args.check:
            current = service.output_file.read_text(encoding="utf-8") if service.output_file.exists() else ""
            if current != rendered:
                changed.append(service.output_file)
        else:
            service.output_file.write_text(rendered, encoding="utf-8")
            print(f"wrote {service.output_file.relative_to(ROOT)}")

    if changed:
        print("OpenAPI contracts are out of date. Run: python scripts/export_openapi.py", file=sys.stderr)
        for path in changed:
            print(f"changed: {path.relative_to(ROOT)}", file=sys.stderr)
        return 1
    return 0


def generate_contract(service: ServiceSpec) -> dict[str, Any]:
    service_path = str(service.service_dir)
    common_path = str(PLATFORM_COMMON)
    sys.path.insert(0, common_path)
    sys.path.insert(0, service_path)
    try:
        module = importlib.import_module("app.main")
        document = module.app.openapi()
        document["info"]["x-service-name"] = service.name
        return document
    finally:
        sys.path.remove(service_path)
        sys.path.remove(common_path)
        clear_service_modules()


def clear_service_modules() -> None:
    for module_name in list(sys.modules):
        if module_name == "app" or module_name.startswith("app."):
            del sys.modules[module_name]


def render_json(document: dict[str, Any]) -> str:
    return json.dumps(document, indent=2, sort_keys=True) + "\n"


if __name__ == "__main__":
    raise SystemExit(main())
