#!/usr/bin/env python3

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
WORKFLOW_DIR = ROOT / "workflows"
WORKFLOW_FILES = sorted(WORKFLOW_DIR.rglob("*.json"))


REDACTED = "<redacted>"
WORKFLOW_LINK = "<link-this-workflow>"
RESOURCE_ID = "<configure-in-your-instance>"


RL_RESOURCE_KEYS = {
    "base",
    "table",
    "channelId",
    "workflowId",
    "folderId",
    "fileId",
}


def sanitize_resource_link(key: str, value: dict[str, Any]) -> dict[str, Any]:
    cleaned = {k: v for k, v in value.items() if k != "cachedResultUrl"}

    if key in RL_RESOURCE_KEYS:
        cleaned["value"] = WORKFLOW_LINK if key == "workflowId" else RESOURCE_ID

    return cleaned


def sanitize_credentials(value: dict[str, Any]) -> dict[str, Any]:
    cleaned: dict[str, Any] = {}
    for credential_type, payload in value.items():
        if isinstance(payload, dict):
            cleaned[credential_type] = {
                "id": REDACTED,
                "name": f"{credential_type} credential",
            }
        else:
            cleaned[credential_type] = REDACTED
    return cleaned


def sanitize(obj: Any, parent_key: str | None = None) -> Any:
    if isinstance(obj, dict):
        if parent_key == "credentials":
            return sanitize_credentials(obj)

        cleaned: dict[str, Any] = {}

        for key, value in obj.items():
            if key == "pinData":
                cleaned[key] = {}
                continue

            if key == "active":
                cleaned[key] = False
                continue

            if key == "meta" and isinstance(value, dict):
                next_meta = dict(value)
                if "instanceId" in next_meta:
                    next_meta["instanceId"] = REDACTED
                cleaned[key] = sanitize(next_meta, key)
                continue

            if key in {"webhookId", "versionId"}:
                cleaned[key] = REDACTED
                continue

            if key == "path" and isinstance(value, str) and "-" in value:
                cleaned[key] = REDACTED
                continue

            if key == "credentials":
                cleaned[key] = sanitize(value, key)
                continue

            if isinstance(value, dict) and value.get("__rl") is True:
                cleaned[key] = sanitize_resource_link(key, value)
                continue

            if key == "cachedResultUrl":
                continue

            cleaned[key] = sanitize(value, key)

        return cleaned

    if isinstance(obj, list):
        return [sanitize(item, parent_key) for item in obj]

    return obj


def main() -> None:
    if not WORKFLOW_FILES:
        raise SystemExit("No workflow exports found.")

    for path in WORKFLOW_FILES:
        with path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)

        sanitized = sanitize(data)

        with path.open("w", encoding="utf-8") as fh:
            json.dump(sanitized, fh, indent=2, ensure_ascii=False)
            fh.write("\n")

    print(f"Sanitized {len(WORKFLOW_FILES)} workflow export(s).")


if __name__ == "__main__":
    main()
