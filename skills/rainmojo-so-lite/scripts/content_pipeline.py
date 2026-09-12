#!/usr/bin/env python3
"""Create, track, and validate client-neutral SEO content production packages."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import uuid
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from string import Formatter
from typing import Any
from urllib.parse import urljoin, urlparse, urlsplit, urlunsplit

import client_workspace


SCRIPT_DIR = Path(__file__).resolve().parent
RAINMOJO_ROOT = SCRIPT_DIR.parent
DEFAULTS_PATH = RAINMOJO_ROOT / "reference" / "content-production" / "defaults.json"

STATUSES = [
    "planned",
    "outline_ready",
    "research_ready",
    "draft_ready",
    "content_qa_passed",
    "image_specs_ready",
    "images_technical_ready",
    "images_qa_passed",
    "publish_ready",
    "draft_uploaded",
    "verified",
]

SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
MARKDOWN_LINK_RE = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)", re.I)
RAW_LINK_RE = re.compile(r"""href=["']([^"']+)["']""", re.I)
H1_RE = re.compile(r"^#\s+\S", re.M)
INLINE_PLACEHOLDER_RE = re.compile(r"\{\{INLINE_IMAGE_(\d+)\}\}")
ADAPTER_OPERATION_RE = re.compile(r"^[a-z][a-z0-9_]*$")
ADAPTER_PARAMETER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
SHELL_META_RE = re.compile(r"[;&|<>`\r\n\x00]")
PATH_SUFFIXES = {
    ".py",
    ".json",
    ".csv",
    ".md",
    ".html",
    ".yaml",
    ".yml",
}
INTERPRETER_COMMANDS = {"python", "python.exe", "py", "py.exe"}
CLIENT_NATIVE_BASE_OPERATIONS = {
    "prepare",
    "status",
    "self_test",
}
CAPABILITY_KEYS = {
    "scope",
    "content",
    "images",
    "wordpress_draft",
    "content_review",
    "image_source_review",
    "image_visual_review",
    "verify_only",
    "draft_only",
}
CAPABILITY_BOOLEAN_KEYS = CAPABILITY_KEYS - {"scope"}
CAPABILITY_SCOPES = {"end_to_end", "image_only", "partial"}
END_TO_END_CAPABILITIES = {
    "content",
    "images",
    "wordpress_draft",
    "content_review",
    "image_source_review",
    "image_visual_review",
    "verify_only",
    "draft_only",
}
IMAGE_CAPABILITIES = {
    "images",
    "image_source_review",
    "image_visual_review",
}
OPERATION_CAPABILITIES = {
    "init_article": "content",
    "approve_outline": "content",
    "validate_content": "content",
    "review_content": "content_review",
    "image_spec": "images",
    "optimize_images": "images",
    "review_image_sources": "image_source_review",
    "review_images": "image_visual_review",
    "validate_publish": "wordpress_draft",
    "preflight": "wordpress_draft",
    "publish_draft": "wordpress_draft",
    "verify_only": "verify_only",
}
CONTENT_REVIEW_FILE = "reports/content-review.json"
IMAGE_PROVENANCE_SNAPSHOT_FIELDS = (
    "source_type",
    "provider",
    "source_url",
    "rights_record",
    "license_record",
    "generation_notes",
)
PRODUCTION_PLACEHOLDER_VALUES = {
    "client_defined",
    "define-for-client",
    "define_for_client",
    "placeholder",
    "replace-me",
    "replace_me",
    "todo",
    "tbd",
}

STATUS_INDEX = {status: index for index, status in enumerate(STATUSES)}
STATUS_TRANSITIONS = {
    current: {STATUSES[index + 1]} if index + 1 < len(STATUSES) else set()
    for index, current in enumerate(STATUSES)
}


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8-sig") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise RuntimeError(f"Expected a JSON object: {path}")
    return data


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except Exception:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise


def write_text_atomic(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(value)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except Exception:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(base)
    for key, value in override.items():
        if (
            key in result
            and isinstance(result[key], dict)
            and isinstance(value, dict)
        ):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = deepcopy(value)
    return result


def canonical_json_sha256(data: Any) -> str:
    payload = json.dumps(
        data,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def declared_capabilities(config: dict[str, Any]) -> dict[str, Any]:
    engine = config.get("engine", {})
    capabilities = engine.get("capabilities", {})
    return capabilities if isinstance(capabilities, dict) else {}


def capability_summary(config: dict[str, Any]) -> dict[str, Any]:
    capabilities = declared_capabilities(config)
    enabled = {
        key: capabilities.get(key) is True
        for key in CAPABILITY_BOOLEAN_KEYS
    }
    return {
        "scope": capabilities.get("scope"),
        **enabled,
        "end_to_end": all(enabled.get(key, False) for key in END_TO_END_CAPABILITIES),
        "images_ready": all(enabled.get(key, False) for key in IMAGE_CAPABILITIES),
    }


def required_native_operations(config: dict[str, Any]) -> set[str]:
    capabilities = capability_summary(config)
    required = set(CLIENT_NATIVE_BASE_OPERATIONS)
    if capabilities["content"]:
        required.update({"init_article", "approve_outline", "validate_content"})
    if capabilities["content_review"]:
        required.add("review_content")
    if capabilities["images"]:
        required.update({"image_spec", "optimize_images"})
    if capabilities["image_source_review"]:
        required.add("review_image_sources")
    if capabilities["image_visual_review"]:
        required.add("review_images")
    if capabilities["wordpress_draft"]:
        required.update({"validate_publish", "preflight", "publish_draft"})
    if capabilities["verify_only"]:
        required.add("verify_only")
    return required


def require_config_capabilities(
    config: dict[str, Any],
    required: list[str] | tuple[str, ...] | set[str],
) -> dict[str, Any]:
    summary = capability_summary(config)
    missing: list[str] = []
    for capability in required:
        if capability == "end_to_end":
            available = summary["end_to_end"]
        elif capability == "images":
            available = summary["images_ready"]
        elif capability == "wordpress_draft":
            available = (
                summary["wordpress_draft"]
                and summary["verify_only"]
                and summary["draft_only"]
            )
        else:
            raise RuntimeError(f"Unknown required capability: {capability}")
        if not available:
            missing.append(capability)
    if missing:
        raise RuntimeError(
            "Client pipeline does not declare the required capability: "
            + ", ".join(missing)
            + f". Declared scope is {summary.get('scope') or 'missing'}."
        )
    return summary


def is_production_placeholder(value: Any) -> bool:
    text = str(value or "").strip().casefold()
    if not text:
        return False
    if text in PRODUCTION_PLACEHOLDER_VALUES:
        return True
    return any(
        marker in text
        for marker in (
            "<domain>",
            "<client",
            "{domain}",
            "{client_name}",
            "your-domain",
            "your-site",
        )
    )


def is_placeholder_domain(value: Any) -> bool:
    raw = str(value or "").strip()
    hostname = normalize_domain(urlparse(raw).hostname or raw)
    return (
        hostname in {"example.com", "example.test", "localhost"}
        or hostname.endswith(
            (".example.com", ".example.test", ".example", ".test", ".invalid")
        )
    )


def resolve_client(client: str | Path) -> Path:
    try:
        path = client_workspace.resolve_plain_root(client)
        client_workspace.assert_plain_tree(path)
        return path
    except client_workspace.WorkspaceError as exc:
        raise RuntimeError(str(exc)) from exc


def safe_path(base: Path, value: str | Path) -> Path:
    raw = Path(value)
    candidate = raw.resolve() if raw.is_absolute() else (base / raw).resolve()
    allowed = base.resolve()
    if candidate != allowed and allowed not in candidate.parents:
        raise RuntimeError(f"Path escapes allowed root {allowed}: {candidate}")
    return candidate


def parse_adapter_command(value: Any) -> list[str]:
    if isinstance(value, str):
        try:
            command = shlex.split(value, posix=True)
        except ValueError as exc:
            raise RuntimeError(f"Invalid adapter command string: {exc}") from exc
    elif isinstance(value, list) and all(isinstance(item, str) for item in value):
        command = list(value)
    else:
        raise RuntimeError("Adapter commands must be strings or string arrays.")
    if not command or not command[0].strip():
        raise RuntimeError("Adapter command must not be empty.")
    return command


def command_placeholders(command: list[str]) -> set[str]:
    placeholders: set[str] = set()
    for token in command:
        try:
            parsed = list(Formatter().parse(token))
        except ValueError as exc:
            raise RuntimeError(f"Invalid adapter placeholder syntax: {token}") from exc
        for _, field_name, format_spec, conversion in parsed:
            if field_name is None:
                continue
            if not ADAPTER_PARAMETER_RE.fullmatch(field_name):
                raise RuntimeError(
                    f"Adapter placeholder must be a simple name: {field_name}"
                )
            if format_spec or conversion:
                raise RuntimeError(
                    f"Adapter placeholder formatting is not allowed: {field_name}"
                )
            placeholders.add(field_name)
    return placeholders


def _looks_like_path(token: str) -> bool:
    if token.startswith(("http://", "https://", "//")):
        return False
    if token.startswith(("./", "../", ".\\", "..\\")):
        return True
    raw = Path(token)
    return (
        raw.is_absolute()
        or "/" in token
        or "\\" in token
        or raw.suffix.lower() in PATH_SUFFIXES
    )


def validate_adapter_argv(
    client: Path,
    command: list[str],
    allowed_commands: list[str],
    *,
    allow_placeholders: bool,
) -> None:
    if any(SHELL_META_RE.search(token) for token in command):
        raise RuntimeError("Adapter commands may not contain shell metacharacters.")

    placeholders = command_placeholders(command)
    if placeholders and not allow_placeholders:
        raise RuntimeError(
            "Adapter command still contains unresolved placeholders: "
            + ", ".join(sorted(placeholders))
        )

    allowed = {item.casefold() for item in allowed_commands if item.strip()}
    executable = command[0]
    if executable.casefold() not in allowed:
        raise RuntimeError(
            f"Adapter executable is not explicitly allowlisted: {executable}"
        )

    executable_name = Path(executable).name.casefold()
    if executable_name in INTERPRETER_COMMANDS:
        if any(token in {"-c", "-m"} for token in command[1:]):
            raise RuntimeError("Adapter interpreters may not use -c or -m.")
        script_tokens = [
            token
            for token in command[1:]
            if "{" not in token and Path(token).suffix.lower() == ".py"
        ]
        if not script_tokens:
            raise RuntimeError(
                "Allowlisted Python adapters must name a client-root Python script."
            )
        script = safe_path(client, script_tokens[0])
        if not script.is_file():
            raise RuntimeError(f"Adapter script not found: {script}")

    for token in command[1:]:
        if "{" in token or not _looks_like_path(token):
            continue
        safe_path(client, token)


def validate_config(
    config: dict[str, Any],
    client: Path,
    *,
    declared_config: dict[str, Any] | None = None,
) -> None:
    errors: list[str] = []

    def require_dict(parent: dict[str, Any], key: str) -> dict[str, Any]:
        value = parent.get(key)
        if not isinstance(value, dict):
            errors.append(f"{key} must be an object.")
            return {}
        return value

    policy = require_dict(config, "config_policy")
    profile = policy.get("profile")
    if profile not in {"production", "demo", "test"}:
        errors.append("config_policy.profile must be production, demo, or test.")
    if policy.get("require_client_file") is not True:
        errors.append("config_policy.require_client_file must be true.")
    explicit_profiles = policy.get("explicit_defaults_profiles", [])
    if not isinstance(explicit_profiles, list) or any(
        item not in {"demo", "test"} for item in explicit_profiles
    ):
        errors.append(
            "config_policy.explicit_defaults_profiles may only contain demo and test."
        )

    site = require_dict(config, "site")
    site_domain = str(site.get("domain", "")).strip()
    if not site_domain:
        errors.append("site.domain is required.")
    base_value = str(site.get("url") or site.get("base_url") or "").strip()
    if base_value and site_domain:
        base_host = normalize_domain(urlparse(base_value).hostname or "")
        if not base_host or not domain_matches(
            base_host,
            normalize_domain(site_domain),
        ):
            errors.append("site.url/base_url must belong to site.domain.")

    engine = require_dict(config, "engine")
    mode = engine.get("mode")
    if mode not in {"generic", "client_native"}:
        errors.append("engine.mode must be generic or client_native.")
    source_of_truth = str(engine.get("source_of_truth", "")).strip()
    if not source_of_truth:
        errors.append("engine.source_of_truth is required.")
    elif Path(source_of_truth).is_absolute():
        errors.append("engine.source_of_truth must be relative to the client root.")
    else:
        try:
            source_path = safe_path(client, source_of_truth)
            if mode == "generic" and source_path != safe_path(
                client,
                "content/production",
            ):
                errors.append(
                    "Generic engine.source_of_truth must be content/production."
                )
            if mode == "client_native" and not source_path.exists():
                errors.append(
                    f"engine.source_of_truth does not exist: {source_path}"
                )
        except RuntimeError as exc:
            errors.append(str(exc))

    capabilities = engine.get("capabilities")
    if not isinstance(capabilities, dict):
        errors.append("engine.capabilities must be an object.")
        capabilities = {}
    missing_capability_keys = sorted(CAPABILITY_KEYS - set(capabilities))
    if missing_capability_keys:
        errors.append(
            "engine.capabilities is missing keys: "
            + ", ".join(missing_capability_keys)
        )
    extra_capability_keys = sorted(set(capabilities) - CAPABILITY_KEYS)
    if extra_capability_keys:
        errors.append(
            "engine.capabilities has unknown keys: "
            + ", ".join(extra_capability_keys)
        )
    scope = capabilities.get("scope")
    if scope not in CAPABILITY_SCOPES:
        errors.append(
            "engine.capabilities.scope must be end_to_end, image_only, or partial."
        )
    for key in sorted(CAPABILITY_BOOLEAN_KEYS):
        if not isinstance(capabilities.get(key), bool):
            errors.append(f"engine.capabilities.{key} must be boolean.")
    if capabilities.get("draft_only") is not True:
        errors.append(
            "engine.capabilities.draft_only must be true for every production scope."
        )
    if capabilities.get("content_review") is True and capabilities.get("content") is not True:
        errors.append(
            "engine.capabilities.content_review requires content=true."
        )
    for key in ("image_source_review", "image_visual_review"):
        if capabilities.get(key) is True and capabilities.get("images") is not True:
            errors.append(f"engine.capabilities.{key} requires images=true.")
    if capabilities.get("verify_only") is True and capabilities.get(
        "wordpress_draft"
    ) is not True:
        errors.append(
            "engine.capabilities.verify_only requires wordpress_draft=true."
        )

    capability_state = capability_summary(config)
    if scope == "end_to_end" and not capability_state["end_to_end"]:
        missing = sorted(
            key
            for key in END_TO_END_CAPABILITIES
            if capabilities.get(key) is not True
        )
        errors.append(
            "end_to_end scope requires all production capabilities: "
            + ", ".join(missing)
        )
    if scope == "image_only":
        required_image = {
            "images",
            "image_source_review",
            "image_visual_review",
            "draft_only",
        }
        forbidden_image = {
            "content",
            "wordpress_draft",
            "content_review",
            "verify_only",
        }
        missing = sorted(
            key for key in required_image if capabilities.get(key) is not True
        )
        forbidden = sorted(
            key for key in forbidden_image if capabilities.get(key) is not False
        )
        if missing:
            errors.append(
                "image_only scope requires capabilities: " + ", ".join(missing)
            )
        if forbidden:
            errors.append(
                "image_only scope must disable capabilities: "
                + ", ".join(forbidden)
            )
    if scope == "partial" and (
        capability_state["end_to_end"]
        or (
            capability_state["images_ready"]
            and capabilities.get("content") is False
            and capabilities.get("wordpress_draft") is False
            and capabilities.get("content_review") is False
            and capabilities.get("verify_only") is False
        )
    ):
        errors.append(
            "engine.capabilities.scope must use end_to_end or image_only when "
            "the declared booleans match that complete scope."
        )
    if mode == "generic" and not capability_state["end_to_end"]:
        errors.append(
            "generic engine mode must declare the complete end_to_end capability set."
        )
    if (
        mode == "client_native"
        and profile == "production"
        and declared_config is not None
    ):
        declared_engine = declared_config.get("engine")
        declared_caps = (
            declared_engine.get("capabilities")
            if isinstance(declared_engine, dict)
            else None
        )
        if not isinstance(declared_caps, dict):
            errors.append(
                "Production client_native configuration must explicitly declare "
                "engine.capabilities in the client file."
            )
        else:
            missing_declared = sorted(CAPABILITY_KEYS - set(declared_caps))
            if missing_declared:
                errors.append(
                    "Production client_native engine.capabilities must explicitly "
                    "declare every key: " + ", ".join(missing_declared)
                )

    adapter = require_dict(engine, "adapter")
    allowed_commands = adapter.get("allowed_commands", [])
    operations = adapter.get("operations", {})
    if not isinstance(allowed_commands, list) or not all(
        isinstance(item, str) and item.strip() for item in allowed_commands
    ):
        errors.append("engine.adapter.allowed_commands must be a string array.")
        allowed_commands = []
    if not isinstance(operations, dict):
        errors.append("engine.adapter.operations must be an object.")
        operations = {}
    if mode == "generic" and operations:
        errors.append("generic engine mode must not define native adapter operations.")
    if mode == "client_native" and not operations:
        errors.append("client_native engine mode requires adapter operations.")
    if mode == "client_native" and isinstance(operations, dict):
        missing_operations = sorted(
            required_native_operations(config) - set(operations)
        )
        if missing_operations:
            errors.append(
                "client_native adapter is missing required operations: "
                + ", ".join(missing_operations)
            )
        disabled_operations = sorted(
            operation
            for operation, capability in OPERATION_CAPABILITIES.items()
            if operation in operations and capabilities.get(capability) is not True
        )
        if disabled_operations:
            errors.append(
                "client_native adapter declares operations outside its capability "
                "scope: " + ", ".join(disabled_operations)
            )
    for operation, command_value in operations.items():
        if not ADAPTER_OPERATION_RE.fullmatch(str(operation)):
            errors.append(f"Invalid adapter operation name: {operation}")
            continue
        try:
            command = parse_adapter_command(command_value)
            validate_adapter_argv(
                client,
                command,
                list(allowed_commands),
                allow_placeholders=True,
            )
        except RuntimeError as exc:
            errors.append(f"engine.adapter.operations.{operation}: {exc}")

    content = require_dict(config, "content")
    inline_counts = content.get("inline_image_counts", {})
    minimum_links = content.get("minimum_internal_links", {})
    if not isinstance(inline_counts, dict) or not inline_counts:
        errors.append("content.inline_image_counts must be a non-empty object.")
    if not isinstance(minimum_links, dict) or not minimum_links:
        errors.append("content.minimum_internal_links must be a non-empty object.")
    if isinstance(inline_counts, dict) and isinstance(minimum_links, dict):
        missing_minimums = sorted(set(inline_counts) - set(minimum_links))
        if missing_minimums:
            errors.append(
                "content.minimum_internal_links is missing article types: "
                + ", ".join(missing_minimums)
            )
        default_type = content.get("default_article_type")
        if default_type not in inline_counts:
            errors.append(
                "content.default_article_type must exist in inline_image_counts."
            )
    for label, mapping in (
        ("content.inline_image_counts", inline_counts),
        ("content.minimum_internal_links", minimum_links),
    ):
        if isinstance(mapping, dict):
            for article_type, value in mapping.items():
                if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                    errors.append(f"{label}.{article_type} must be a non-negative integer.")

    external = content.get("external_links", {})
    if not isinstance(external, dict):
        errors.append("content.external_links must be an object.")
    else:
        minimum = external.get("minimum", 0)
        maximum = external.get("maximum", 0)
        if not isinstance(minimum, int) or minimum < 0:
            errors.append("content.external_links.minimum must be non-negative.")
        if not isinstance(maximum, int) or maximum < 0:
            errors.append("content.external_links.maximum must be non-negative.")
        if (
            isinstance(minimum, int)
            and isinstance(maximum, int)
            and maximum
            and minimum > maximum
        ):
            errors.append("External link minimum may not exceed maximum.")
        for key in ("allowed_domains", "blocked_domains"):
            values = external.get(key, [])
            if not isinstance(values, list) or not all(
                isinstance(item, str) for item in values
            ):
                errors.append(f"content.external_links.{key} must be a string array.")

    links = require_dict(config, "links")
    target_groups = links.get("required_target_groups", {})
    if not isinstance(target_groups, dict):
        errors.append("links.required_target_groups must be an object.")
    else:
        allowed_groups = {
            "product_targets",
            "pillar_targets",
            "related_targets",
        }
        for article_type, groups in target_groups.items():
            if not isinstance(groups, list) or not groups:
                errors.append(
                    f"links.required_target_groups.{article_type} must be a non-empty array."
                )
                continue
            unknown = [item for item in groups if item not in allowed_groups]
            if unknown:
                errors.append(
                    f"links.required_target_groups.{article_type} has unknown groups: "
                    + ", ".join(unknown)
                )
        if isinstance(inline_counts, dict):
            missing_groups = sorted(set(inline_counts) - set(target_groups))
            if missing_groups:
                errors.append(
                    "links.required_target_groups is missing article types: "
                    + ", ".join(missing_groups)
                )

    provenance = require_dict(config, "provenance")
    for key in ("external_required_fields", "image_required_fields"):
        fields = provenance.get(key, [])
        if not isinstance(fields, list) or not fields or not all(
            isinstance(item, str) and item.strip() for item in fields
        ):
            errors.append(f"provenance.{key} must be a non-empty string array.")

    seo = require_dict(config, "seo")
    meta_fields = seo.get("meta_fields", {})
    if not isinstance(meta_fields, dict):
        errors.append("seo.meta_fields must be an object.")
    else:
        for field in ("title", "description", "focus_keyword", "canonical"):
            value = str(meta_fields.get(field, "")).strip()
            if not value:
                errors.append(f"seo.meta_fields.{field} is required.")
            if seo.get("plugin") == "yoast" and value and not value.startswith(
                "_yoast_wpseo_"
            ):
                errors.append(
                    f"seo.meta_fields.{field} must use the _yoast_wpseo_ key."
                )

    images = require_dict(config, "images")
    for role in ("featured", "inline"):
        dimensions = images.get(role, {})
        if not isinstance(dimensions, dict):
            errors.append(f"images.{role} must be an object.")
            continue
        for field in ("width", "height"):
            value = dimensions.get(field)
            if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
                errors.append(f"images.{role}.{field} must be a positive integer.")
    logo = images.get("logo", {})
    if isinstance(logo, dict) and logo.get("required"):
        asset_path = str(logo.get("asset_path", "")).strip()
        if not asset_path:
            errors.append("images.logo.asset_path is required when logo.required is true.")
        else:
            try:
                logo_path = safe_path(client, asset_path)
                if not logo_path.is_file():
                    errors.append(f"Required logo asset not found: {logo_path}")
            except RuntimeError as exc:
                errors.append(str(exc))
    style = images.get("style", {})
    if not isinstance(style, dict):
        errors.append("images.style must be an object.")
    else:
        checklist = style.get("review_checklist", [])
        if not isinstance(checklist, list) or not checklist or not all(
            isinstance(item, str) and item.strip() for item in checklist
        ):
            errors.append("images.style.review_checklist must be a non-empty string array.")
    infographic = images.get("infographic", {})
    if not isinstance(infographic, dict):
        errors.append("images.infographic must be an object.")
    else:
        if not isinstance(infographic.get("allowed"), bool):
            errors.append("images.infographic.allowed must be boolean.")
        if not str(infographic.get("language", "")).strip():
            errors.append("images.infographic.language is required.")

    if profile == "production":
        if is_production_placeholder(site_domain) or is_placeholder_domain(site_domain):
            errors.append(
                "Production site.domain contains a placeholder or example value."
            )
        if is_production_placeholder(base_value) or (
            base_value and is_placeholder_domain(base_value)
        ):
            errors.append(
                "Production site.url/base_url contains a placeholder or example value."
            )
        if is_production_placeholder(source_of_truth):
            errors.append(
                "Production engine.source_of_truth contains a placeholder value."
            )
        style_mode = style.get("mode") if isinstance(style, dict) else ""
        if is_production_placeholder(style_mode):
            errors.append(
                "Production images.style.mode must name the approved client style, "
                "not a placeholder."
            )

    wordpress = require_dict(config, "wordpress")
    if wordpress.get("default_status") != "draft":
        errors.append("wordpress.default_status must be draft.")
    interval = wordpress.get("write_interval_seconds")
    if not isinstance(interval, (int, float)) or isinstance(interval, bool) or interval < 0:
        errors.append("wordpress.write_interval_seconds must be non-negative.")
    category_id = wordpress.get("default_category_id")
    if category_id is not None and (
        not isinstance(category_id, int)
        or isinstance(category_id, bool)
        or category_id <= 0
    ):
        errors.append("wordpress.default_category_id must be null or a positive integer.")
    category_name = wordpress.get("default_category_name", "")
    if not isinstance(category_name, str):
        errors.append("wordpress.default_category_name must be a string.")
    if not isinstance(wordpress.get("create_missing_categories"), bool):
        errors.append("wordpress.create_missing_categories must be boolean.")
    external_attributes = wordpress.get("external_link_attributes", {})
    if not isinstance(external_attributes, dict):
        errors.append("wordpress.external_link_attributes must be an object.")
    else:
        if not isinstance(external_attributes.get("target_blank"), bool):
            errors.append(
                "wordpress.external_link_attributes.target_blank must be boolean."
            )
        rel_values = external_attributes.get("rel", [])
        if not isinstance(rel_values, list) or not all(
            isinstance(item, str) and item.strip() for item in rel_values
        ):
            errors.append(
                "wordpress.external_link_attributes.rel must be a string array."
            )
    lock_timeout = wordpress.get("lock_timeout_seconds")
    if not isinstance(lock_timeout, (int, float)) or isinstance(
        lock_timeout,
        bool,
    ) or lock_timeout <= 0:
        errors.append("wordpress.lock_timeout_seconds must be positive.")
    env_aliases = wordpress.get("env_aliases", {})
    if not isinstance(env_aliases, dict):
        errors.append("wordpress.env_aliases must be an object.")
    else:
        for key, value in env_aliases.items():
            values = [value] if isinstance(value, str) else value
            if not isinstance(values, list) or not all(
                isinstance(item, str) and item.strip() for item in values
            ):
                errors.append(
                    f"wordpress.env_aliases.{key} must be a string or string array."
                )
    state_paths = wordpress.get("state_paths", {})
    if not isinstance(state_paths, dict):
        errors.append("wordpress.state_paths must be an object.")
    else:
        for key in ("operation_lock", "write_lock", "write_state"):
            value = str(state_paths.get(key, "")).strip()
            if not value:
                errors.append(f"wordpress.state_paths.{key} is required.")
                continue
            try:
                safe_path(client, value)
            except RuntimeError as exc:
                errors.append(str(exc))

    gates = require_dict(config, "quality_gates")
    if gates.get("draft_only") is not True:
        errors.append("quality_gates.draft_only must be true.")
    content_review_checklist = gates.get("content_review_checklist", [])
    if gates.get("content_review_required") is True and (
        not isinstance(content_review_checklist, list)
        or not content_review_checklist
        or not all(
            isinstance(item, str) and item.strip()
            for item in content_review_checklist
        )
    ):
        errors.append(
            "quality_gates.content_review_checklist must be a non-empty string "
            "array when content review is required."
        )
    image_source_checklist = gates.get("image_source_review_checklist", [])
    if capabilities.get("image_source_review") is True and gates.get(
        "image_source_review_required"
    ) is not True:
        errors.append(
            "quality_gates.image_source_review_required must be true when the "
            "engine declares image_source_review."
        )
    if gates.get("image_source_review_required") is True and (
        not isinstance(image_source_checklist, list)
        or not image_source_checklist
        or not all(
            isinstance(item, str) and item.strip()
            for item in image_source_checklist
        )
    ):
        errors.append(
            "quality_gates.image_source_review_checklist must be a non-empty "
            "string array when image source review is required."
        )

    if errors:
        raise RuntimeError("Invalid content-pipeline configuration:\n- " + "\n- ".join(errors))


def load_client_config(
    client: str | Path,
    *,
    defaults_profile: str | None = None,
) -> dict[str, Any]:
    client_path = resolve_client(client)
    config = load_json(DEFAULTS_PATH)
    client_config_path = client_path / "content-pipeline.json"
    declared_config: dict[str, Any] | None = None
    if client_config_path.exists():
        declared_config = load_json(client_config_path)
        config = deep_merge(config, declared_config)
    else:
        profiles = config.get("config_policy", {}).get(
            "explicit_defaults_profiles",
            [],
        )
        if defaults_profile not in profiles:
            raise RuntimeError(
                "Client content-pipeline.json is required. Defaults may only be "
                "used explicitly with a demo or test profile."
            )
        config["config_policy"]["profile"] = defaults_profile
        configured_domain = client_path.name
        config["site"] = {"domain": configured_domain}
    validate_config(
        config,
        client_path,
        declared_config=declared_config,
    )
    return config


def article_package(client: str | Path, slug: str) -> Path:
    if not SLUG_RE.fullmatch(slug):
        raise RuntimeError(
            "Slug must be lowercase ASCII with hyphens only: " + slug
        )
    client_path = resolve_client(client)
    workspace = client_workspace.validate_workspace(client_path)
    if not workspace["passed"]:
        raise RuntimeError(
            "Client workspace routing validation failed: "
            + "; ".join(workspace["errors"])
        )
    try:
        routed = client_workspace.route_output(
            client_path,
            "content-production",
            slug,
        )
    except client_workspace.WorkspaceError as exc:
        raise RuntimeError(f"Cannot resolve content production route: {exc}") from exc
    return Path(routed["target"])


def read_package(client: str | Path, slug: str) -> tuple[Path, dict[str, Any]]:
    package = article_package(client, slug)
    article_path = package / "article.json"
    if not article_path.exists():
        raise RuntimeError(f"Article package not initialized: {package}")
    return package, load_json(article_path)


def load_effective_config(
    client: str | Path,
    package: Path | None = None,
    article: dict[str, Any] | None = None,
) -> dict[str, Any]:
    client_path = resolve_client(client)
    if package is None or article is None:
        return load_client_config(client_path)

    snapshot_path = package / "resolved-config.json"
    if not snapshot_path.is_file():
        raise RuntimeError(f"Frozen package configuration is missing: {snapshot_path}")
    snapshot = load_json(snapshot_path)
    expected_hash = str(
        article.get("config_snapshot", {}).get("sha256", "")
    ).strip()
    actual_hash = canonical_json_sha256(snapshot)
    if expected_hash and actual_hash != expected_hash:
        raise RuntimeError(
            "Frozen resolved-config.json was modified after package initialization. "
            "Create an article config_overrides entry or initialize a new package."
        )

    overrides = article.get("config_overrides", {})
    if not isinstance(overrides, dict):
        raise RuntimeError("article.config_overrides must be an object.")
    forbidden = sorted(
        key
        for key in overrides
        if key in {"config_policy", "engine", "site"}
    )
    if forbidden:
        raise RuntimeError(
            "Article config overrides may not alter security or routing keys: "
            + ", ".join(forbidden)
        )
    effective = deep_merge(snapshot, overrides)
    validate_config(effective, client_path)
    return effective


def image_item(
    slug: str,
    role: str,
    dimensions: dict[str, Any],
    index: int | None = None,
) -> dict[str, Any]:
    is_featured = role == "featured"
    image_id = "featured" if is_featured else f"inline-{index:02d}"
    filename = (
        f"{slug}-featured.webp"
        if is_featured
        else f"{slug}-inline-{index:02d}.webp"
    )
    return {
        "id": image_id,
        "role": role,
        "placeholder": None if is_featured else f"{{{{INLINE_IMAGE_{index}}}}}",
        "source": "",
        "output": f"images/optimized/{filename}",
        "width": int(dimensions["width"]),
        "height": int(dimensions["height"]),
        "concept": "",
        "prompt": "",
        "negative_prompt": "",
        "alt": "",
        "title": "",
        "caption": "",
        "credit": "",
        "provenance": {
            "source_type": "",
            "provider": "",
            "source_url": "",
            "rights_record": "",
            "license_record": "",
            "generation_notes": ""
        },
        "source_review": {
            "status": "pending",
            "reviewer": "",
            "reviewed_at": None,
            "evidence_file": "",
            "source_sha256": "",
            "source_width": None,
            "source_height": None,
            "provenance_sha256": "",
        },
        "technical_status": "pending",
        "qa_status": "pending",
        "qa_notes": ""
    }


def initialize_package(
    client: str | Path,
    slug: str,
    title: str,
    primary_keyword: str,
    article_type: str = "cluster",
    language: str | None = None,
    defaults_profile: str | None = None,
) -> Path:
    client_path = resolve_client(client)
    title = title.strip()
    primary_keyword = primary_keyword.strip()
    if not title:
        raise RuntimeError("Article title is required.")
    if not primary_keyword:
        raise RuntimeError("Primary keyword is required.")
    package = article_package(client_path, slug)
    if package.exists():
        raise RuntimeError(f"Article package already exists: {package}")

    config = load_client_config(
        client_path,
        defaults_profile=defaults_profile,
    )
    if config["engine"]["mode"] != "generic":
        raise RuntimeError(
            "Generic package initialization is disabled for client_native mode. "
            "Use adapter-run --operation init_article."
        )
    inline_counts = config["content"]["inline_image_counts"]
    if article_type not in inline_counts:
        raise RuntimeError(
            f"Unknown article type {article_type}; expected one of "
            + ", ".join(sorted(inline_counts))
        )
    inline_count = int(inline_counts[article_type])
    timestamp = now_iso()

    for relative in ("images/raw", "images/optimized", "reports"):
        (package / relative).mkdir(parents=True, exist_ok=True)

    client_config_path = client_path / "content-pipeline.json"
    resolved_config = deepcopy(config)
    resolved_config["_resolution"] = {
        "frozen_at": timestamp,
        "defaults_file": str(DEFAULTS_PATH),
        "defaults_sha256": file_sha256(DEFAULTS_PATH),
        "client_config_file": (
            "content-pipeline.json" if client_config_path.exists() else None
        ),
        "client_config_sha256": (
            file_sha256(client_config_path)
            if client_config_path.exists()
            else None
        ),
        "precedence": [
            "plugin_defaults",
            "client_content_pipeline",
            "article_config_overrides",
        ],
    }
    resolved_hash = canonical_json_sha256(resolved_config)

    article = {
        "version": "1.0.0",
        "slug": slug,
        "title": title,
        "article_type": article_type,
        "language": language or config["content"]["default_language"],
        "primary_keyword": primary_keyword,
        "secondary_keywords": [],
        "search_intent": "",
        "status": "planned",
        "config_snapshot": {
            "file": "resolved-config.json",
            "sha256": resolved_hash,
            "frozen_at": timestamp,
        },
        "config_overrides": {},
        "content_file": "article.md",
        "images_file": "image-manifest.json",
        "sources_file": "sources.json",
        "content_review": {
            "file": CONTENT_REVIEW_FILE,
            "status": "pending",
            "reviewer": "",
            "article_sha256": "",
            "reviewed_at": None,
        },
        "seo": {
            "title": "",
            "description": "",
            "focus_keyword": primary_keyword,
            "canonical": ""
        },
        "links": {
            "product_targets": [],
            "pillar_targets": [],
            "related_targets": [],
            "external_sources": []
        },
        "wordpress": {
            "post_type": config["wordpress"]["post_type"],
            "category_ids": [],
            "tag_ids": [],
            "post_id": None,
            "media_ids": {}
        },
        "history": [
            {
                "at": timestamp,
                "status": "planned",
                "notes": "Article package initialized"
            }
        ],
        "created_at": timestamp,
        "updated_at": timestamp
    }
    images = {
        "version": "1.0.0",
        "slug": slug,
        "items": [
            image_item(slug, "featured", config["images"]["featured"])
        ]
        + [
            image_item(slug, "inline", config["images"]["inline"], index)
            for index in range(1, inline_count + 1)
        ]
    }
    sources = {
        "version": "1.0.0",
        "slug": slug,
        "internal": [],
        "external": []
    }

    write_json(package / "resolved-config.json", resolved_config)
    write_json(package / "article.json", article)
    write_json(package / "image-manifest.json", images)
    write_json(package / "sources.json", sources)
    (package / "article.md").write_text(
        "<!-- Write the approved article body here. -->\n",
        encoding="utf-8",
        newline="\n",
    )
    return package


def review_evidence_path(package: Path, article: dict[str, Any]) -> Path:
    review = article.get("content_review", {})
    value = (
        review.get("file")
        if isinstance(review, dict)
        else CONTENT_REVIEW_FILE
    )
    return safe_path(package, str(value or CONTENT_REVIEW_FILE))


def content_review_validation(
    package: Path,
    article: dict[str, Any],
    config: dict[str, Any],
) -> tuple[list[str], dict[str, Any]]:
    article_path = safe_path(package, article["content_file"])
    current_sha = file_sha256(article_path) if article_path.is_file() else ""
    required = config.get("quality_gates", {}).get(
        "content_review_required",
        True,
    )
    evidence_path = review_evidence_path(package, article)
    result: dict[str, Any] = {
        "required": required,
        "file": str(evidence_path.relative_to(package)).replace("\\", "/"),
        "current_article_sha256": current_sha,
        "reviewed_article_sha256": "",
        "reviewer": "",
        "passed": not required,
    }
    if not required:
        return [], result

    errors: list[str] = []
    if not evidence_path.is_file():
        errors.append(
            "Structured content review evidence is missing: "
            + result["file"]
        )
        return errors, result
    review = load_json(evidence_path)
    reviewer = str(review.get("reviewer", "")).strip()
    reviewed_sha = str(review.get("article_sha256", "")).strip().lower()
    checklist = review.get("checklist")
    result["reviewer"] = reviewer
    result["reviewed_article_sha256"] = reviewed_sha
    if not reviewer:
        errors.append("Content review evidence is missing reviewer.")
    if not reviewed_sha:
        errors.append("Content review evidence is missing article_sha256.")
    elif reviewed_sha != current_sha:
        errors.append(
            "article.md changed after content review; current SHA-256 does not "
            "match the reviewed article SHA-256."
        )
    if not isinstance(checklist, dict):
        errors.append("Content review checklist must be an object.")
        checklist = {}
    required_checks = config.get("quality_gates", {}).get(
        "content_review_checklist",
        [],
    )
    missing_checks = [
        key for key in required_checks if key not in checklist
    ]
    failed_checks = [
        key
        for key in required_checks
        if str(checklist.get(key, "")).strip().casefold() != "passed"
    ]
    if missing_checks:
        errors.append(
            "Content review checklist is missing required items: "
            + ", ".join(missing_checks)
        )
    if failed_checks:
        errors.append(
            "Content review checklist items have not passed: "
            + ", ".join(failed_checks)
        )
    result["passed"] = not errors
    return errors, result


def record_content_review(
    client: str | Path,
    slug: str,
    review: dict[str, Any],
) -> dict[str, Any]:
    package, article = read_package(client, slug)
    if article.get("status") != "draft_ready":
        raise RuntimeError(
            "Content review may only be recorded while article status is draft_ready. "
            "Invalidate later states before re-reviewing changed content."
        )
    config = load_effective_config(client, package, article)
    reviewer = str(review.get("reviewer", "")).strip()
    submitted_sha = str(review.get("article_sha256", "")).strip().lower()
    checklist = review.get("checklist")
    if not reviewer:
        raise RuntimeError("Content review requires a reviewer.")
    if not submitted_sha:
        raise RuntimeError("Content review requires article_sha256 evidence.")
    article_path = safe_path(package, article["content_file"])
    if not article_path.is_file():
        raise RuntimeError(f"Article body is missing: {article_path}")
    current_sha = file_sha256(article_path)
    if submitted_sha != current_sha:
        raise RuntimeError(
            "Content review article_sha256 does not match the current article.md."
        )
    if not isinstance(checklist, dict):
        raise RuntimeError("Content review checklist must be an object.")
    required_checks = config.get("quality_gates", {}).get(
        "content_review_checklist",
        [],
    )
    missing = [key for key in required_checks if key not in checklist]
    failed = [
        key
        for key in required_checks
        if str(checklist.get(key, "")).strip().casefold() != "passed"
    ]
    if missing:
        raise RuntimeError(
            "Content review checklist is missing required items: "
            + ", ".join(missing)
        )
    if failed:
        raise RuntimeError(
            "Content review checklist items have not passed: "
            + ", ".join(failed)
        )

    timestamp = now_iso()
    evidence = {
        "version": "1.0.0",
        "slug": slug,
        "reviewer": reviewer,
        "reviewed_at": timestamp,
        "article_file": article["content_file"],
        "article_sha256": current_sha,
        "checklist": {
            key: str(checklist[key]).strip().casefold()
            for key in required_checks
        },
        "notes": str(review.get("notes", "")).strip(),
    }
    evidence_path = review_evidence_path(package, article)
    write_json(evidence_path, evidence)
    article["content_review"] = {
        "file": str(evidence_path.relative_to(package)).replace("\\", "/"),
        "status": "passed",
        "reviewer": reviewer,
        "article_sha256": current_sha,
        "reviewed_at": timestamp,
    }
    article["updated_at"] = timestamp
    write_json(package / "article.json", article)
    return evidence


def image_source_review_errors(
    package: Path,
    item: dict[str, Any],
    config: dict[str, Any],
) -> list[str]:
    if not config.get("quality_gates", {}).get(
        "image_source_review_required",
        True,
    ):
        return []
    image_id = str(item.get("id", "unknown"))
    errors: list[str] = []
    review = item.get("source_review")
    if not isinstance(review, dict) or review.get("status") != "passed":
        return [f"{image_id}: structured image source review has not passed."]
    evidence_value = str(review.get("evidence_file", "")).strip()
    if not evidence_value:
        return [f"{image_id}: source review evidence_file is missing."]
    try:
        evidence_path = safe_path(package, evidence_value)
    except RuntimeError as exc:
        return [str(exc)]
    if not evidence_path.is_file():
        return [f"{image_id}: source review evidence is missing: {evidence_path}"]
    evidence = load_json(evidence_path)
    if not str(evidence.get("reviewer", "")).strip():
        errors.append(f"{image_id}: source review evidence is missing reviewer.")

    source_value = str(item.get("source", "")).strip()
    if not source_value:
        return errors + [f"{image_id}: source image path is missing."]
    try:
        source_path = safe_path(package, source_value)
    except RuntimeError as exc:
        return errors + [str(exc)]
    if not source_path.is_file():
        return errors + [f"{image_id}: source image is missing: {source_path}"]
    identity = evidence.get("source_identity")
    if not isinstance(identity, dict):
        errors.append(f"{image_id}: source review identity must be an object.")
    else:
        current_identity: dict[str, Any] = {
            "path": str(source_path.relative_to(package)).replace("\\", "/"),
            "sha256": file_sha256(source_path),
            "bytes": source_path.stat().st_size,
        }
        try:
            from PIL import Image

            with Image.open(source_path) as source_image:
                source_image.load()
                current_identity.update(
                    {
                        "width": source_image.width,
                        "height": source_image.height,
                        "format": source_image.format or "",
                    }
                )
        except (ImportError, OSError) as exc:
            errors.append(
                f"{image_id}: source dimensions could not be verified: {exc}"
            )
        for key, value in current_identity.items():
            if identity.get(key) != value:
                errors.append(
                    f"{image_id}: source {key} changed after source review."
                )

    provenance = item.get("provenance")
    if not isinstance(provenance, dict):
        errors.append(f"{image_id}: provenance must be an object.")
        provenance = {}
    current_provenance = {
        key: str(provenance.get(key, "")).strip()
        for key in IMAGE_PROVENANCE_SNAPSHOT_FIELDS
    }
    if not current_provenance["rights_record"]:
        errors.append(f"{image_id}: provenance rights_record is missing.")
    reviewed_provenance = evidence.get("provenance_snapshot")
    reviewed_hash = str(evidence.get("provenance_sha256", "")).strip()
    if not isinstance(reviewed_provenance, dict):
        errors.append(f"{image_id}: reviewed provenance snapshot is missing.")
    else:
        evidence_hash = canonical_json_sha256(reviewed_provenance)
        if evidence_hash != reviewed_hash:
            errors.append(
                f"{image_id}: source review provenance evidence was modified."
            )
        if (
            current_provenance != reviewed_provenance
            or canonical_json_sha256(current_provenance) != reviewed_hash
        ):
            errors.append(f"{image_id}: provenance changed after source review.")

    checklist = evidence.get("checklist")
    if not isinstance(checklist, dict):
        errors.append(f"{image_id}: source review checklist must be an object.")
        checklist = {}
    required_checks = config.get("quality_gates", {}).get(
        "image_source_review_checklist",
        [],
    )
    missing = [key for key in required_checks if key not in checklist]
    failed = [
        key
        for key in required_checks
        if str(checklist.get(key, "")).strip().casefold() != "passed"
    ]
    if missing:
        errors.append(
            f"{image_id}: source review checklist is missing: "
            + ", ".join(missing)
        )
    if failed:
        errors.append(
            f"{image_id}: source review checklist has not passed: "
            + ", ".join(failed)
        )
    return errors


def set_status(
    client: str | Path,
    slug: str,
    status: str,
    notes: str = "",
) -> dict[str, Any]:
    if status not in STATUSES:
        raise RuntimeError(
            f"Invalid status {status}; expected one of " + ", ".join(STATUSES)
        )
    package, article = read_package(client, slug)
    current = article.get("status")
    if current not in STATUS_INDEX:
        raise RuntimeError(f"Article has an invalid current status: {current}")
    if status == current:
        return article
    if status not in STATUS_TRANSITIONS[current]:
        raise RuntimeError(
            f"Status transition {current} -> {status} is not allowed. "
            "Advance through the declared gate sequence, or use invalidate_status "
            "for an explicit backward invalidation."
        )
    config = load_effective_config(client, package, article)
    if status == "content_qa_passed":
        report = validate_package(client, slug, "content")
        if not report["passed"]:
            raise RuntimeError(
                "Content QA gate failed: " + "; ".join(report["errors"])
            )
    elif STATUS_INDEX[status] > STATUS_INDEX["content_qa_passed"]:
        review_errors, _ = content_review_validation(package, article, config)
        if review_errors:
            raise RuntimeError(
                "Content review is stale or incomplete: "
                + "; ".join(review_errors)
            )
    timestamp = now_iso()
    article["status"] = status
    article["updated_at"] = timestamp
    article.setdefault("history", []).append(
        {"at": timestamp, "status": status, "notes": notes}
    )
    write_json(package / "article.json", article)
    return article


def invalidate_status(
    client: str | Path,
    slug: str,
    status: str,
    notes: str,
) -> dict[str, Any]:
    if status not in STATUSES:
        raise RuntimeError(
            f"Invalid status {status}; expected one of " + ", ".join(STATUSES)
        )
    if not notes.strip():
        raise RuntimeError("Status invalidation requires non-empty notes.")
    package, article = read_package(client, slug)
    current = article.get("status")
    if current not in STATUS_INDEX:
        raise RuntimeError(f"Article has an invalid current status: {current}")
    if STATUS_INDEX[status] >= STATUS_INDEX[current]:
        raise RuntimeError(
            f"Invalidation target must be earlier than {current}: {status}"
        )
    timestamp = now_iso()
    article["status"] = status
    article["updated_at"] = timestamp
    article.setdefault("history", []).append(
        {
            "at": timestamp,
            "event": "invalidated",
            "from_status": current,
            "status": status,
            "notes": notes,
        }
    )
    write_json(package / "article.json", article)
    return article


def extract_urls(markdown: str) -> list[str]:
    values = MARKDOWN_LINK_RE.findall(markdown)
    values.extend(RAW_LINK_RE.findall(markdown))
    urls: list[str] = []
    for value in values:
        candidate = value.strip()
        if candidate.startswith("<") and ">" in candidate:
            candidate = candidate[1:candidate.index(">")]
        elif re.search(r"\s+[\"']", candidate):
            candidate = re.split(r"\s+[\"']", candidate, maxsplit=1)[0]
        candidate = candidate.strip()
        if not candidate or candidate.startswith(("#", "mailto:", "tel:", "javascript:")):
            continue
        urls.append(candidate)
    return list(dict.fromkeys(urls))


def normalize_domain(value: str) -> str:
    domain = value.lower().strip()
    if "://" in domain:
        domain = urlparse(domain).hostname or domain
    return domain.removeprefix("www.").strip("/")


def site_base_url(config: dict[str, Any], client_path: Path) -> str:
    site = config.get("site", {})
    value = (
        site.get("url")
        or site.get("base_url")
        or config.get("wordpress", {}).get("site_url")
        or site.get("domain")
        or client_path.name
    )
    base = str(value).strip()
    if not base.startswith(("http://", "https://")):
        base = "https://" + base.lstrip("/")
    return base.rstrip("/") + "/"


def canonical_url(value: str, base_url: str) -> str:
    absolute = urljoin(base_url, value)
    parsed = urlsplit(absolute)
    hostname = normalize_domain(parsed.hostname or "")
    port = f":{parsed.port}" if parsed.port else ""
    path = re.sub(r"/{2,}", "/", parsed.path or "/")
    if path != "/":
        path = path.rstrip("/")
    return urlunsplit(
        (
            parsed.scheme.lower() or "https",
            hostname + port,
            path,
            parsed.query,
            "",
        )
    )


def is_relative_url(value: str) -> bool:
    parsed = urlparse(value)
    return not parsed.scheme and not parsed.netloc


def target_url(value: Any, label: str) -> str:
    if isinstance(value, str):
        url = value.strip()
    elif isinstance(value, dict):
        url = str(value.get("url", "")).strip()
    else:
        raise RuntimeError(f"{label} targets must be URL strings or objects.")
    if not url:
        raise RuntimeError(f"{label} target is missing url.")
    return url


def domain_matches(hostname: str, configured: str) -> bool:
    return hostname == configured or hostname.endswith("." + configured)


def validate_package(
    client: str | Path,
    slug: str,
    stage: str = "content",
) -> dict[str, Any]:
    if stage not in {"content", "images", "publish"}:
        raise RuntimeError("Stage must be content, images, or publish")

    client_path = resolve_client(client)
    package, article = read_package(client_path, slug)
    config = load_effective_config(client_path, package, article)
    markdown_path = safe_path(package, article["content_file"])
    image_manifest_path = safe_path(package, article["images_file"])
    sources_path = safe_path(package, article["sources_file"])
    markdown = markdown_path.read_text(encoding="utf-8") if markdown_path.exists() else ""
    image_manifest = (
        load_json(image_manifest_path)
        if image_manifest_path.exists()
        else {"items": []}
    )
    sources = load_json(sources_path) if sources_path.exists() else {"internal": [], "external": []}

    errors: list[str] = []
    warnings: list[str] = []
    if not article.get("config_snapshot", {}).get("sha256"):
        warnings.append(
            "Legacy package has no resolved-config fingerprint; initialize a new package "
            "before production publishing."
        )

    current_status = article.get("status")
    if current_status not in STATUS_INDEX:
        errors.append(f"Article has invalid status: {current_status}")
    if len(markdown.strip()) < 100:
        errors.append("Article body is missing or too short for QA.")
    if config["content"]["h1_source"] == "wordpress_title" and H1_RE.search(markdown):
        errors.append("Article body contains an H1 while WordPress title is the H1 source.")
    review_errors, content_review = content_review_validation(
        package,
        article,
        config,
    )
    errors.extend(review_errors)

    inline_items = [
        item for item in image_manifest.get("items", []) if item.get("role") == "inline"
    ]
    placeholders = sorted(int(value) for value in INLINE_PLACEHOLDER_RE.findall(markdown))
    expected_placeholders = list(range(1, len(inline_items) + 1))
    if placeholders != expected_placeholders:
        errors.append(
            f"Inline placeholders {placeholders} do not match expected "
            f"{expected_placeholders}."
        )

    base_url = site_base_url(config, client_path)
    client_domain = normalize_domain(urlparse(base_url).hostname or client_path.name)
    extracted_urls = extract_urls(markdown)
    canonical_content_urls: dict[str, str] = {}
    internal_urls: list[str] = []
    external_urls: list[str] = []
    canonical_internal_urls: set[str] = set()
    canonical_external_urls: set[str] = set()
    external_hosts: dict[str, str] = {}
    for raw_url in extracted_urls:
        canonical = canonical_url(raw_url, base_url)
        canonical_content_urls[canonical] = raw_url
        hostname = normalize_domain(urlparse(canonical).hostname or "")
        if is_relative_url(raw_url):
            if not config["links"].get("allow_relative_internal_links", True):
                errors.append(f"Relative internal link is not allowed: {raw_url}")
            internal_urls.append(raw_url)
            canonical_internal_urls.add(canonical)
        elif domain_matches(hostname, client_domain):
            internal_urls.append(raw_url)
            canonical_internal_urls.add(canonical)
        else:
            external_urls.append(raw_url)
            canonical_external_urls.add(canonical)
            external_hosts[canonical] = hostname
    internal_urls = list(dict.fromkeys(internal_urls))
    external_urls = list(dict.fromkeys(external_urls))

    article_type = article.get("article_type", "cluster")
    minimum_internal = int(
        config["content"]["minimum_internal_links"].get(article_type, 0)
    )
    if len(canonical_internal_urls) < minimum_internal:
        errors.append(
            f"Internal links {len(canonical_internal_urls)} below required "
            f"{minimum_internal}."
        )

    link_plan = article.get("links", {})
    if not isinstance(link_plan, dict):
        errors.append("article.links must be an object.")
        link_plan = {}
    required_groups = config["links"].get("required_target_groups", {}).get(
        article_type,
        [],
    )
    for group in required_groups:
        targets = link_plan.get(group, [])
        if not isinstance(targets, list) or not targets:
            errors.append(f"Required link target group is empty: {group}")
            continue
        for index, target in enumerate(targets, 1):
            try:
                raw_target = target_url(target, f"{group}[{index}]")
                canonical_target = canonical_url(raw_target, base_url)
                hostname = normalize_domain(urlparse(canonical_target).hostname or "")
                if not domain_matches(hostname, client_domain):
                    errors.append(
                        f"{group}[{index}] must be an internal target: {raw_target}"
                    )
                if canonical_target not in canonical_content_urls:
                    errors.append(
                        f"Required target is absent from article content: {raw_target}"
                    )
            except RuntimeError as exc:
                errors.append(str(exc))

    if config["links"].get("require_all_declared_targets", True):
        for group in ("product_targets", "pillar_targets", "related_targets"):
            targets = link_plan.get(group, [])
            if not isinstance(targets, list):
                errors.append(f"article.links.{group} must be an array.")
                continue
            for index, target in enumerate(targets, 1):
                try:
                    raw_target = target_url(target, f"{group}[{index}]")
                    if canonical_url(raw_target, base_url) not in canonical_content_urls:
                        errors.append(
                            f"Declared target is absent from article content: {raw_target}"
                        )
                except RuntimeError as exc:
                    errors.append(str(exc))

    external_policy = config["content"]["external_links"]
    minimum_external = int(external_policy.get("minimum", 0))
    maximum_external = int(external_policy.get("maximum", 0))
    if len(canonical_external_urls) < minimum_external:
        errors.append(
            f"External links {len(canonical_external_urls)} below required "
            f"{minimum_external}."
        )
    if maximum_external and len(canonical_external_urls) > maximum_external:
        warnings.append(
            f"External links {len(canonical_external_urls)} exceed preferred "
            f"{maximum_external}."
        )

    blocked = {
        normalize_domain(item) for item in external_policy.get("blocked_domains", [])
    }
    allowed = {
        normalize_domain(item) for item in external_policy.get("allowed_domains", [])
    }
    for canonical, hostname in external_hosts.items():
        if any(domain_matches(hostname, item) for item in blocked):
            errors.append(f"Blocked external domain used: {hostname}")
        if allowed and not any(domain_matches(hostname, item) for item in allowed):
            errors.append(f"External domain is not allowlisted: {hostname}")

    external_plan = link_plan.get("external_sources", [])
    if not isinstance(external_plan, list):
        errors.append("article.links.external_sources must be an array.")
        external_plan = []
    planned_external: set[str] = set()
    for index, target in enumerate(external_plan, 1):
        try:
            raw_target = target_url(target, f"external_sources[{index}]")
            canonical_target = canonical_url(raw_target, base_url)
            hostname = normalize_domain(urlparse(canonical_target).hostname or "")
            if domain_matches(hostname, client_domain):
                errors.append(
                    f"external_sources[{index}] must be external: {raw_target}"
                )
            planned_external.add(canonical_target)
            if canonical_target not in canonical_content_urls:
                errors.append(
                    f"Planned external source is absent from content: {raw_target}"
                )
        except RuntimeError as exc:
            errors.append(str(exc))
    content_external = canonical_external_urls
    if config["provenance"].get("require_external_plan", True):
        for canonical in sorted(content_external - planned_external):
            errors.append(
                "External content link is missing from article.links.external_sources: "
                + canonical
            )

    source_records = sources.get("external", [])
    if not isinstance(source_records, list):
        errors.append("sources.external must be an array.")
        source_records = []
    recorded_sources: set[str] = set()
    required_source_fields = config["provenance"].get(
        "external_required_fields",
        [],
    )
    for index, record in enumerate(source_records, 1):
        if not isinstance(record, dict):
            errors.append(f"sources.external[{index}] must be an object.")
            continue
        missing = [
            field
            for field in required_source_fields
            if not str(record.get(field, "")).strip()
        ]
        if missing:
            errors.append(
                f"sources.external[{index}] missing fields: " + ", ".join(missing)
            )
        claim = record.get("claim")
        if claim is not None and not isinstance(claim, str):
            errors.append(f"sources.external[{index}].claim must be a string.")
        accessed_at = record.get("accessed_at")
        if accessed_at:
            try:
                datetime.fromisoformat(str(accessed_at).replace("Z", "+00:00"))
            except ValueError:
                errors.append(
                    f"sources.external[{index}].accessed_at must be an ISO date or datetime."
                )
        raw_url = str(record.get("url", "")).strip()
        if not raw_url:
            continue
        canonical = canonical_url(raw_url, base_url)
        hostname = normalize_domain(urlparse(canonical).hostname or "")
        if domain_matches(hostname, client_domain):
            errors.append(f"sources.external[{index}] must reference an external URL.")
        if any(domain_matches(hostname, item) for item in blocked):
            errors.append(
                f"sources.external[{index}] uses blocked domain: {hostname}"
            )
        if allowed and not any(domain_matches(hostname, item) for item in allowed):
            errors.append(
                f"sources.external[{index}] is not allowlisted: {hostname}"
            )
        recorded_sources.add(canonical)
    if config["provenance"].get("require_external_records", True) and not source_records:
        errors.append("sources.external requires provenance records.")
    if config["provenance"].get("require_record_for_every_external_link", True):
        for canonical in sorted(content_external - recorded_sources):
            errors.append(
                "External content link is missing a sources.json record: " + canonical
            )

    if stage in {"images", "publish"}:
        featured = [
            item
            for item in image_manifest.get("items", [])
            if item.get("role") == "featured"
        ]
        if config["images"]["featured"]["required"] and len(featured) != 1:
            errors.append("Exactly one featured image is required.")
        for item in image_manifest.get("items", []):
            image_id = item.get("id", "unknown")
            if not item.get("alt", "").strip():
                errors.append(f"{image_id}: alt text is missing.")
            if not item.get("title", "").strip():
                errors.append(f"{image_id}: media title is missing.")
            if not item.get("prompt", "").strip() and not item.get("source", "").strip():
                errors.append(f"{image_id}: no image prompt or source is recorded.")
            if config["provenance"].get("require_image_records", True):
                provenance = item.get("provenance", {})
                if not isinstance(provenance, dict):
                    errors.append(f"{image_id}: provenance must be an object.")
                else:
                    missing = [
                        field
                        for field in config["provenance"].get(
                            "image_required_fields",
                            [],
                        )
                        if not str(provenance.get(field, "")).strip()
                    ]
                    if missing:
                        errors.append(
                            f"{image_id}: provenance missing fields: "
                            + ", ".join(missing)
                        )
            errors.extend(image_source_review_errors(package, item, config))
            output_value = item.get("output", "")
            if not output_value:
                errors.append(f"{image_id}: output path is missing.")
            else:
                output_path = safe_path(package, output_value)
                if not output_path.exists():
                    errors.append(f"{image_id}: optimized image is missing: {output_path}")
            if item.get("technical_status") != "passed":
                errors.append(f"{image_id}: technical image processing has not passed.")

    if stage == "publish":
        if current_status not in {"images_qa_passed", "publish_ready"}:
            errors.append(
                f"Article status is {current_status}; images_qa_passed or "
                "publish_ready is required."
            )
        if not article.get("seo", {}).get("title", "").strip():
            errors.append("SEO title is missing.")
        if not article.get("seo", {}).get("description", "").strip():
            errors.append("SEO description is missing.")
        for item in image_manifest.get("items", []):
            if item.get("qa_status") != "passed":
                errors.append(f"{item.get('id')}: visual image QA has not passed.")
        if config["wordpress"]["default_status"] != "draft":
            errors.append("Client publishing configuration must default to draft.")
        if not config["quality_gates"].get("draft_only", True):
            errors.append("The content production pipeline must remain draft-only.")

    report = {
        "checked_at": now_iso(),
        "slug": slug,
        "stage": stage,
        "status": current_status,
        "config_snapshot_sha256": article.get("config_snapshot", {}).get("sha256"),
        "effective_config_sha256": canonical_json_sha256(config),
        "article_sha256": content_review["current_article_sha256"],
        "content_review": content_review,
        "internal_links": internal_urls,
        "external_links": external_urls,
        "required_link_groups": required_groups,
        "external_source_records": len(recorded_sources),
        "errors": list(dict.fromkeys(errors)),
        "warnings": list(dict.fromkeys(warnings)),
        "passed": not errors,
    }
    write_json(package / "reports" / f"{stage}-validation.json", report)
    return report


def parse_params(values: list[str]) -> dict[str, str]:
    params: dict[str, str] = {}
    for value in values:
        if "=" not in value:
            raise RuntimeError(f"Adapter parameter must use name=value: {value}")
        key, raw = value.split("=", 1)
        key = key.strip()
        if not ADAPTER_PARAMETER_RE.fullmatch(key):
            raise RuntimeError(f"Invalid adapter parameter name: {key}")
        if SHELL_META_RE.search(raw):
            raise RuntimeError(f"Unsafe adapter parameter value for {key}.")
        params[key] = raw
    return params


def prepare_adapter_command(
    client: str | Path,
    operation: str,
    params: dict[str, str] | None = None,
) -> tuple[Path, list[str]]:
    client_path = resolve_client(client)
    config = load_client_config(client_path)
    engine = config["engine"]
    if engine.get("mode") != "client_native":
        raise RuntimeError("Adapter dispatch requires engine.mode=client_native.")
    if not ADAPTER_OPERATION_RE.fullmatch(operation):
        raise RuntimeError(f"Invalid adapter operation name: {operation}")
    adapter = engine["adapter"]
    operations = adapter["operations"]
    if operation not in operations:
        raise RuntimeError(f"Adapter operation is not configured: {operation}")

    command = parse_adapter_command(operations[operation])
    values = {
        "client": str(client_path),
        "client_root": str(client_path),
    }
    values.update(params or {})
    missing = command_placeholders(command) - values.keys()
    if missing:
        raise RuntimeError(
            "Missing adapter parameters: " + ", ".join(sorted(missing))
        )
    rendered = [token.format_map(values) for token in command]
    validate_adapter_argv(
        client_path,
        rendered,
        list(adapter["allowed_commands"]),
        allow_placeholders=False,
    )
    return client_path, rendered


def run_adapter_operation(
    client: str | Path,
    operation: str,
    params: dict[str, str] | None = None,
    *,
    timeout_seconds: float = 900,
) -> dict[str, Any]:
    if timeout_seconds <= 0:
        raise RuntimeError("Adapter timeout must be positive.")
    client_path, command = prepare_adapter_command(client, operation, params)
    started_at = now_iso()
    completed = subprocess.run(
        command,
        cwd=client_path,
        shell=False,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
        check=False,
    )
    return {
        "operation": operation,
        "client_root": str(client_path),
        "command": command,
        "started_at": started_at,
        "finished_at": now_iso(),
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "passed": completed.returncode == 0,
    }


def iter_packages(client: str | Path) -> list[tuple[str, Path]]:
    client_path = resolve_client(client)
    root = client_path / "content" / "production"
    if not root.exists():
        return []
    packages: list[tuple[str, Path]] = []
    for path in sorted(root.iterdir()):
        if path.is_dir() and SLUG_RE.fullmatch(path.name) and (path / "article.json").is_file():
            packages.append((path.name, path))
    return packages


def batch_status(client: str | Path) -> dict[str, Any]:
    config = load_client_config(client)
    if config["engine"]["mode"] != "generic":
        raise RuntimeError(
            "Generic batch status is disabled for client_native mode. "
            "Use adapter-run --operation status."
        )
    rows: list[dict[str, Any]] = []
    counts = {status: 0 for status in STATUSES}
    counts["invalid"] = 0
    for slug, package in iter_packages(client):
        try:
            article = load_json(package / "article.json")
        except (OSError, RuntimeError, json.JSONDecodeError) as exc:
            counts["invalid"] += 1
            rows.append(
                {
                    "slug": slug,
                    "title": "",
                    "status": "invalid_package",
                    "updated_at": None,
                    "error": str(exc),
                    "publication": {
                        "state": "invalid_package",
                        "passed": False,
                        "checked_at": None,
                        "post_id": None,
                        "post_url": "",
                    },
                }
            )
            continue
        status = article.get("status", "invalid")
        if status in counts:
            counts[status] += 1
        else:
            counts["invalid"] += 1
        publish_report_path = package / "reports" / "wordpress-publish.json"
        wordpress_state = article.get("wordpress", {})
        if not isinstance(wordpress_state, dict):
            wordpress_state = {}
        publication: dict[str, Any] = {
            "state": (
                "missing_publish_evidence"
                if status in {"draft_uploaded", "verified"}
                else "not_started"
            ),
            "passed": None,
            "checked_at": None,
            "post_id": wordpress_state.get("post_id"),
            "post_url": "",
        }
        if publish_report_path.is_file():
            try:
                publish_report = load_json(publish_report_path)
                if publish_report.get("slug") != slug:
                    raise RuntimeError(
                        "wordpress-publish.json slug does not match its article package."
                    )
                checked_at = publish_report.get("checked_at")
                if not isinstance(checked_at, str) or not checked_at.strip():
                    raise RuntimeError(
                        "wordpress-publish.json checked_at must be a non-empty string."
                    )
                verification = publish_report.get("verification", {})
                if not isinstance(verification, dict):
                    raise RuntimeError(
                        "wordpress-publish.json verification must be an object."
                    )
                report_status = str(publish_report.get("status", "")).strip()
                passed = publish_report.get("passed")
                if not isinstance(passed, bool):
                    raise RuntimeError(
                        "wordpress-publish.json passed must be boolean."
                    )
                allowed_report_states = {
                    "",
                    "dry_run",
                    "reconcile_required",
                    "safe_to_retry_publish",
                }
                if report_status not in allowed_report_states:
                    raise RuntimeError(
                        f"Unknown wordpress-publish.json status: {report_status}"
                    )
                article_post_id = wordpress_state.get("post_id")
                verified_post_id = verification.get("post_id")
                if (
                    article_post_id is not None
                    and verified_post_id is not None
                    and article_post_id != verified_post_id
                ):
                    raise RuntimeError(
                        "WordPress post ID differs between article and publish evidence."
                    )
                if report_status:
                    publish_state = report_status
                elif passed is True and status == "verified":
                    publish_state = "verified_draft"
                elif passed is True and status == "draft_uploaded":
                    publish_state = "draft_uploaded"
                elif passed is True:
                    publish_state = "report_passed"
                else:
                    publish_state = "blocked"
                publication = {
                    "state": publish_state,
                    "passed": passed,
                    "checked_at": checked_at,
                    "operation": publish_report.get("operation", ""),
                    "post_id": (
                        wordpress_state.get("post_id")
                        or verification.get("post_id")
                    ),
                    "post_url": verification.get("post_url", ""),
                }
            except (OSError, RuntimeError, json.JSONDecodeError) as exc:
                publication = {
                    "state": "invalid_report",
                    "passed": False,
                    "checked_at": None,
                    "post_id": wordpress_state.get("post_id"),
                    "post_url": "",
                    "error": str(exc),
                }
        rows.append(
            {
                "slug": slug,
                "title": article.get("title", ""),
                "status": status,
                "updated_at": article.get("updated_at"),
                "publication": publication,
            }
        )
    return {
        "checked_at": now_iso(),
        "total": len(rows),
        "counts": counts,
        "articles": rows,
    }


def publishing_status(status_report: dict[str, Any]) -> dict[str, Any]:
    """Return a publishing-only projection from the package status report."""
    rows: list[dict[str, Any]] = []
    counts: dict[str, int] = {}
    for article in status_report["articles"]:
        publication = article["publication"]
        state = publication["state"]
        counts[state] = counts.get(state, 0) + 1
        rows.append(
            {
                "slug": article["slug"],
                "title": article["title"],
                "content_status": article["status"],
                **publication,
            }
        )
    return {
        "checked_at": status_report["checked_at"],
        "total": status_report["total"],
        "counts": counts,
        "articles": rows,
    }


def render_content_dashboard(
    status_report: dict[str, Any],
    publishing_report: dict[str, Any],
) -> str:
    """Render a self-contained status view; JSON package files remain canonical."""
    status_cells = "".join(
        f"<li><strong>{html.escape(name)}</strong>: {count}</li>"
        for name, count in status_report["counts"].items()
        if count
    ) or "<li>No article packages</li>"
    publishing_cells = "".join(
        f"<li><strong>{html.escape(name)}</strong>: {count}</li>"
        for name, count in sorted(publishing_report["counts"].items())
    ) or "<li>No publishing records</li>"
    rows = []
    for article in status_report["articles"]:
        publication = article["publication"]
        post_id = publication.get("post_id") or ""
        post_url = str(publication.get("post_url") or "")
        post_cell = html.escape(str(post_id))
        parsed_post_url = urlparse(post_url)
        if post_url and parsed_post_url.scheme in {"http", "https"}:
            safe_url = html.escape(post_url, quote=True)
            post_cell = f'<a href="{safe_url}">{post_cell or "Open draft"}</a>'
        rows.append(
            "<tr>"
            f"<td>{html.escape(str(article['slug']))}</td>"
            f"<td>{html.escape(str(article['title']))}</td>"
            f"<td><code>{html.escape(str(article['status']))}</code></td>"
            f"<td><code>{html.escape(str(publication['state']))}</code></td>"
            f"<td>{post_cell}</td>"
            f"<td>{html.escape(str(article.get('updated_at') or ''))}</td>"
            "</tr>"
        )
    table_rows = "".join(rows) or (
        '<tr><td colspan="6">No article packages were found.</td></tr>'
    )
    checked_at = html.escape(str(status_report["checked_at"]))
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Content production status</title>
<style>
body{{font:15px/1.5 system-ui,sans-serif;margin:0;background:#f5f7fa;color:#172033}}
main{{max-width:1180px;margin:auto;padding:32px}} .cards{{display:grid;grid-template-columns:1fr 1fr;gap:16px}}
section,table{{background:#fff;border:1px solid #dce3ec;border-radius:10px}} section{{padding:16px}}
table{{width:100%;border-collapse:collapse;margin-top:20px;overflow:hidden}} th,td{{padding:10px;text-align:left;border-bottom:1px solid #e7ebf0}}
th{{background:#edf3f8}} code{{font-size:13px}} a{{color:#075ea8}} @media(max-width:720px){{.cards{{grid-template-columns:1fr}}main{{padding:16px}}table{{display:block;overflow:auto}}}}
</style></head><body><main>
<h1>Content production status</h1><p>Regenerated {checked_at}. Package JSON and WordPress publish reports remain the source of truth.</p>
<div class="cards"><section><h2>Production</h2><ul>{status_cells}</ul></section>
<section><h2>Publishing</h2><ul>{publishing_cells}</ul></section></div>
<table><thead><tr><th>Slug</th><th>Title</th><th>Content</th><th>Publishing</th><th>Draft</th><th>Updated</th></tr></thead>
<tbody>{table_rows}</tbody></table></main></body></html>\n"""


def write_batch_reports(client: str | Path) -> dict[str, Any]:
    """Write regenerated dashboards plus timestamped status snapshots."""
    client_path = resolve_client(client)
    workspace = client_workspace.validate_workspace(client_path)
    if not workspace["passed"]:
        raise RuntimeError(
            "Client workspace routing validation failed: "
            + "; ".join(workspace["errors"])
        )
    with client_workspace.workspace_lock(client_path):
        status_report = batch_status(client_path)
        publishing_report = publishing_status(status_report)
        run_id = (
            datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ").lower()
            + "-"
            + uuid.uuid4().hex[:12]
        )
        day = status_report["checked_at"][:10]
        dashboard_json = client_workspace.route_output(
            client_path,
            "content-dashboard",
            "content-status.json",
        )
        dashboard_html = client_workspace.route_output(
            client_path,
            "content-dashboard",
            "content-status.html",
        )
        status_route = client_workspace.route_output(
            client_path,
            "content-status-report",
        )
        publishing_route = client_workspace.route_output(
            client_path,
            "content-publishing-report",
        )
        manifest_route = client_workspace.route_output(
            client_path,
            "content-batch-report-manifest",
        )
        status_relative = Path(status_route["directory"]).relative_to(client_path)
        publishing_relative = Path(publishing_route["directory"]).relative_to(client_path)
        manifest_relative = Path(manifest_route["directory"]).relative_to(client_path)
        destinations = {
            "status_dashboard_json": Path(dashboard_json["target"]),
            "status_dashboard_html": Path(dashboard_html["target"]),
            "status_snapshot": client_workspace.confined_path(
                client_path,
                status_relative / day / f"content-status-{run_id}.json",
            ),
            "publishing_snapshot": client_workspace.confined_path(
                client_path,
                publishing_relative / day / f"publishing-status-{run_id}.json",
            ),
            "report_manifest": client_workspace.confined_path(
                client_path,
                manifest_relative / day / f"batch-report-{run_id}-manifest.json",
            ),
        }
        immutable = (
            destinations["status_snapshot"],
            destinations["publishing_snapshot"],
            destinations["report_manifest"],
        )
        if any(path.exists() for path in immutable):
            raise RuntimeError("Batch report run ID collision; no file was written.")
        for path in destinations.values():
            path.parent.mkdir(parents=True, exist_ok=True)
        staging = destinations["status_snapshot"].parent / (
            f".{run_id}.staging-{uuid.uuid4().hex}"
        )
        staging.mkdir(parents=True, exist_ok=False)
        staged = {
            key: staging / path.name
            for key, path in destinations.items()
        }
        promoted_immutable: list[Path] = []
        dashboard_backups: dict[str, Path | None] = {}
        try:
            write_json(staged["status_snapshot"], status_report)
            write_json(staged["publishing_snapshot"], publishing_report)
            write_json(staged["status_dashboard_json"], status_report)
            write_text_atomic(
                staged["status_dashboard_html"],
                render_content_dashboard(status_report, publishing_report),
            )
            manifest = {
                "schema_version": "1.0.0",
                "run_id": run_id,
                "checked_at": status_report["checked_at"],
                "source_of_truth": [
                    "content/production/<article-slug>/article.json",
                    "content/production/<article-slug>/reports/wordpress-publish.json",
                ],
                "outputs": {
                    key: {
                        "path": str(path.relative_to(client_path)).replace("\\", "/"),
                        "sha256": file_sha256(staged[key]),
                        "mutable_view": key.startswith("status_dashboard"),
                        **(
                            {
                                "derived_from": str(
                                    destinations["status_snapshot"].relative_to(client_path)
                                ).replace("\\", "/")
                            }
                            if key.startswith("status_dashboard")
                            else {}
                        ),
                    }
                    for key, path in destinations.items()
                    if key != "report_manifest"
                },
                "counts": status_report["counts"],
                "publishing_counts": publishing_report["counts"],
            }
            write_json(staged["report_manifest"], manifest)

            for key in ("status_snapshot", "publishing_snapshot"):
                os.replace(staged[key], destinations[key])
                promoted_immutable.append(destinations[key])
            for key in ("status_dashboard_json", "status_dashboard_html"):
                current = destinations[key]
                backup = staging / f"previous-{current.name}"
                if current.is_file():
                    shutil.copyfile(current, backup)
                    dashboard_backups[key] = backup
                else:
                    dashboard_backups[key] = None
                os.replace(staged[key], current)
            os.replace(staged["report_manifest"], destinations["report_manifest"])
            promoted_immutable.append(destinations["report_manifest"])
        except Exception:
            for path in promoted_immutable:
                try:
                    path.unlink(missing_ok=True)
                except OSError:
                    pass
            for key, backup in dashboard_backups.items():
                current = destinations[key]
                try:
                    if backup is not None and backup.is_file():
                        os.replace(backup, current)
                    else:
                        current.unlink(missing_ok=True)
                except OSError:
                    pass
            raise
        finally:
            shutil.rmtree(staging, ignore_errors=True)
        return {
            "checked_at": status_report["checked_at"],
            "run_id": run_id,
            "source_of_truth": manifest["source_of_truth"],
            "generated": {
                key: str(path.relative_to(client_path)).replace("\\", "/")
                for key, path in destinations.items()
            },
            "total": status_report["total"],
            "counts": status_report["counts"],
            "publishing_counts": publishing_report["counts"],
        }


def batch_validate(client: str | Path, stage: str) -> dict[str, Any]:
    config = load_client_config(client)
    if config["engine"]["mode"] != "generic":
        raise RuntimeError(
            "Generic batch validation is disabled for client_native mode. "
            "Use the configured native validation operation."
        )
    results: list[dict[str, Any]] = []
    for slug, _ in iter_packages(client):
        report = validate_package(client, slug, stage)
        results.append(
            {
                "slug": slug,
                "passed": report["passed"],
                "errors": report["errors"],
                "warnings": report["warnings"],
            }
        )
    return {
        "checked_at": now_iso(),
        "stage": stage,
        "total": len(results),
        "passed_count": sum(1 for item in results if item["passed"]),
        "failed_count": sum(1 for item in results if not item["passed"]),
        "passed": all(item["passed"] for item in results),
        "articles": results,
    }


def batch_initialize(
    client: str | Path,
    manifest_value: str | Path,
    *,
    defaults_profile: str | None = None,
) -> dict[str, Any]:
    client_path = resolve_client(client)
    manifest_path = safe_path(client_path, manifest_value)
    manifest = load_json(manifest_path)
    entries = manifest.get("articles")
    if not isinstance(entries, list):
        raise RuntimeError("Batch manifest must contain an articles array.")
    created: list[str] = []
    skipped: list[str] = []
    errors: list[dict[str, str]] = []
    for index, entry in enumerate(entries, 1):
        if not isinstance(entry, dict):
            errors.append({"row": str(index), "error": "Article entry must be an object."})
            continue
        slug = str(entry.get("slug", "")).strip()
        try:
            package = article_package(client_path, slug)
            if package.exists():
                skipped.append(slug)
                continue
            initialize_package(
                client_path,
                slug,
                str(entry.get("title", "")).strip(),
                str(entry.get("primary_keyword", "")).strip(),
                article_type=str(entry.get("article_type", "cluster")),
                language=entry.get("language"),
                defaults_profile=defaults_profile,
            )
            created.append(slug)
        except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as exc:
            errors.append({"slug": slug, "error": str(exc)})
    return {
        "manifest": str(manifest_path),
        "created": created,
        "skipped": skipped,
        "errors": errors,
        "passed": not errors,
    }


def command_init(args: argparse.Namespace) -> int:
    path = initialize_package(
        args.client,
        args.slug,
        args.title,
        args.primary_keyword,
        article_type=args.article_type,
        language=args.language,
        defaults_profile=args.defaults_profile,
    )
    print(path)
    return 0


def command_status(args: argparse.Namespace) -> int:
    package, article = read_package(args.client, args.slug)
    result = {
        "package": str(package),
        "slug": article["slug"],
        "status": article["status"],
        "updated_at": article["updated_at"],
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def command_set_status(args: argparse.Namespace) -> int:
    article = set_status(args.client, args.slug, args.status, args.notes)
    print(json.dumps({"slug": args.slug, "status": article["status"]}, indent=2))
    return 0


def command_review_content(args: argparse.Namespace) -> int:
    package, _ = read_package(args.client, args.slug)
    review_path = safe_path(package, args.review_file)
    if not review_path.is_file():
        raise RuntimeError(f"Content review input file not found: {review_path}")
    evidence = record_content_review(
        args.client,
        args.slug,
        load_json(review_path),
    )
    print(json.dumps(evidence, ensure_ascii=False, indent=2))
    return 0


def command_invalidate_status(args: argparse.Namespace) -> int:
    article = invalidate_status(
        args.client,
        args.slug,
        args.status,
        args.notes,
    )
    print(json.dumps({"slug": args.slug, "status": article["status"]}, indent=2))
    return 0


def command_validate(args: argparse.Namespace) -> int:
    report = validate_package(args.client, args.slug, args.stage)
    if (
        report["passed"]
        and args.stage == "publish"
        and report["status"] == "images_qa_passed"
    ):
        set_status(
            args.client,
            args.slug,
            "publish_ready",
            "Publish validation passed; package advanced automatically.",
        )
        report["status"] = "publish_ready"
        report["advanced_to"] = "publish_ready"
        package, _ = read_package(args.client, args.slug)
        write_json(package / "reports" / "publish-validation.json", report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["passed"] else 2


def command_config_check(args: argparse.Namespace) -> int:
    config = load_client_config(
        args.client,
        defaults_profile=args.defaults_profile,
    )
    required = list(getattr(args, "require_capability", []) or [])
    capabilities = require_config_capabilities(config, required)
    result = {
        "client": str(resolve_client(args.client)),
        "profile": config["config_policy"]["profile"],
        "engine_mode": config["engine"]["mode"],
        "capabilities": capabilities,
        "required_capabilities": required,
        "passed": True,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def command_adapter_plan(args: argparse.Namespace) -> int:
    client_path, command = prepare_adapter_command(
        args.client,
        args.operation,
        parse_params(args.param),
    )
    print(
        json.dumps(
            {
                "operation": args.operation,
                "client_root": str(client_path),
                "command": command,
                "shell": False,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def command_adapter_run(args: argparse.Namespace) -> int:
    report = run_adapter_operation(
        args.client,
        args.operation,
        parse_params(args.param),
        timeout_seconds=args.timeout,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["passed"] else 2


def command_batch_status(args: argparse.Namespace) -> int:
    print(json.dumps(batch_status(args.client), ensure_ascii=False, indent=2))
    return 0


def command_batch_report(args: argparse.Namespace) -> int:
    print(json.dumps(write_batch_reports(args.client), ensure_ascii=False, indent=2))
    return 0


def command_batch_validate(args: argparse.Namespace) -> int:
    report = batch_validate(args.client, args.stage)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["passed"] else 2


def command_batch_init(args: argparse.Namespace) -> int:
    report = batch_initialize(
        args.client,
        args.manifest,
        defaults_profile=args.defaults_profile,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["passed"] else 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    init = sub.add_parser("init", help="Initialize one article production package.")
    init.add_argument("--client", required=True)
    init.add_argument("--slug", required=True)
    init.add_argument("--title", required=True)
    init.add_argument("--primary-keyword", required=True)
    init.add_argument("--article-type", default="cluster")
    init.add_argument("--language")
    init.add_argument(
        "--defaults-profile",
        choices=["demo", "test"],
        help="Explicitly allow plugin defaults only when no client config exists.",
    )
    init.set_defaults(func=command_init)

    status = sub.add_parser("status", help="Show one article status.")
    status.add_argument("--client", required=True)
    status.add_argument("--slug", required=True)
    status.set_defaults(func=command_status)

    mark = sub.add_parser("set-status", help="Set a reviewed production status.")
    mark.add_argument("--client", required=True)
    mark.add_argument("--slug", required=True)
    mark.add_argument("--status", required=True, choices=STATUSES)
    mark.add_argument("--notes", default="")
    mark.set_defaults(func=command_set_status)

    review_content = sub.add_parser(
        "review-content",
        help="Record structured content QA against the current article SHA-256.",
    )
    review_content.add_argument("--client", required=True)
    review_content.add_argument("--slug", required=True)
    review_content.add_argument(
        "--review-file",
        required=True,
        help="JSON review input confined to the article package.",
    )
    review_content.set_defaults(func=command_review_content)

    invalidate = sub.add_parser(
        "invalidate-status",
        help="Move a package backward after an explicit invalidation event.",
    )
    invalidate.add_argument("--client", required=True)
    invalidate.add_argument("--slug", required=True)
    invalidate.add_argument("--status", required=True, choices=STATUSES)
    invalidate.add_argument("--notes", required=True)
    invalidate.set_defaults(func=command_invalidate_status)

    validate = sub.add_parser("validate", help="Validate a production gate.")
    validate.add_argument("--client", required=True)
    validate.add_argument("--slug", required=True)
    validate.add_argument(
        "--stage",
        choices=["content", "images", "publish"],
        default="content",
    )
    validate.set_defaults(func=command_validate)

    config_check = sub.add_parser(
        "config-check",
        help="Validate one client content-pipeline configuration.",
    )
    config_check.add_argument("--client", required=True)
    config_check.add_argument(
        "--defaults-profile",
        choices=["demo", "test"],
        help="Explicitly validate defaults when no client config exists.",
    )
    config_check.add_argument(
        "--require-capability",
        action="append",
        default=[],
        choices=["end_to_end", "images", "wordpress_draft"],
        help="Fail closed unless the declared capability is complete.",
    )
    config_check.set_defaults(func=command_config_check)

    adapter_plan = sub.add_parser(
        "adapter-plan",
        help="Render and validate a client-native adapter command without executing it.",
    )
    adapter_plan.add_argument("--client", required=True)
    adapter_plan.add_argument("--operation", required=True)
    adapter_plan.add_argument("--param", action="append", default=[])
    adapter_plan.set_defaults(func=command_adapter_plan)

    adapter_run = sub.add_parser(
        "adapter-run",
        help="Execute one allowlisted client-native operation from the client root.",
    )
    adapter_run.add_argument("--client", required=True)
    adapter_run.add_argument("--operation", required=True)
    adapter_run.add_argument("--param", action="append", default=[])
    adapter_run.add_argument("--timeout", type=float, default=900)
    adapter_run.set_defaults(func=command_adapter_run)

    batch_init = sub.add_parser(
        "batch-init",
        help="Initialize packages from a client-root-confined JSON manifest.",
    )
    batch_init.add_argument("--client", required=True)
    batch_init.add_argument("--manifest", required=True)
    batch_init.add_argument(
        "--defaults-profile",
        choices=["demo", "test"],
    )
    batch_init.set_defaults(func=command_batch_init)

    batch_state = sub.add_parser(
        "batch-status",
        help="Show status for all generic production packages.",
    )
    batch_state.add_argument("--client", required=True)
    batch_state.set_defaults(func=command_batch_status)

    batch_report = sub.add_parser(
        "batch-report",
        help="Write regenerated content and publishing dashboards plus snapshots.",
    )
    batch_report.add_argument("--client", required=True)
    batch_report.set_defaults(func=command_batch_report)

    batch_gate = sub.add_parser(
        "batch-validate",
        help="Run one deterministic validation stage across all packages.",
    )
    batch_gate.add_argument("--client", required=True)
    batch_gate.add_argument(
        "--stage",
        choices=["content", "images", "publish"],
        default="content",
    )
    batch_gate.set_defaults(func=command_batch_validate)
    return parser


def _self_test_hook() -> None:
    if "--self-test" in sys.argv[1:]:
        raise SystemExit(_self_test())


def main() -> int:
    _self_test_hook()
    args = build_parser().parse_args()
    try:
        return int(args.func(args))
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2



def _self_test() -> int:
    """Config merge, placeholder detection and shipped defaults load without touching a client."""
    merged = deep_merge({"a": 1, "nested": {"x": 1}}, {"nested": {"y": 2}})
    assert merged["a"] == 1 and merged["nested"] == {"x": 1, "y": 2}, merged
    assert is_placeholder_domain("example.com") and not is_placeholder_domain("biqdaddy.com")
    defaults = load_json(Path(__file__).resolve().parent.parent / "reference" / "content-production" / "defaults.json")
    assert isinstance(defaults, dict) and defaults, "defaults.json missing"
    print("SELF-TEST PASS: deep_merge, placeholder domain, defaults.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
