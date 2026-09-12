#!/usr/bin/env python3
"""Create, route, extend, and validate Rainmojo client workspaces."""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import stat
import sys
import tempfile
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


RAINMOJO_ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_ROOT = RAINMOJO_ROOT / "clients" / "demo-client"
ROUTING_FILE = "workspace-routing.json"
REGISTRY_VERSION = "1.0.0"
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
NOVEL_REQUIRED_FIELDS = (
    "id",
    "path",
    "description",
    "owner",
    "artifact_classes",
    "writable_subpaths",
    "source_of_truth",
    "retention",
    "created_at",
)
DEFAULT_NOVEL_OWNER = "client-team"
DEFAULT_ARTIFACT_CLASS = "novel-work-output"
DEFAULT_WRITABLE_SUBPATH = "artifacts"
DEFAULT_RETENTION = "retain-until-explicit-closeout"
ROUTING_NOTE_MARKER = "RAINMOJO-WORKSPACE-ROUTING"
WINDOWS_RESERVED_NAMES = {
    "con",
    "prn",
    "aux",
    "nul",
    *(f"com{number}" for number in range(1, 10)),
    *(f"lpt{number}" for number in range(1, 10)),
}
ROUTING_KEYS = {
    "version",
    "root_policy",
    "required_directories",
    "uploads",
    "routes",
    "novel_work",
}
ROOT_POLICY_KEYS = {
    "allowed_files",
    "allowed_directories",
    "generated_files_forbidden",
}
UPLOAD_KEYS = {"path", "read_only"}
ROUTE_KEYS = {"id", "aliases", "directory", "description", "filename_pattern"}
NOVEL_KEYS = {
    "root",
    "registry",
    "folder_pattern",
    "require_registration",
    "entry_required_fields",
}


class WorkspaceError(RuntimeError):
    """A client workspace violates the routing or containment contract."""


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def normalize_client_slug(value: str) -> str:
    """Return a path-safe lowercase client slug while preserving domain dots."""
    raw = value.strip().lower()
    if not raw:
        raise WorkspaceError("Client name is required.")
    if any(token in raw for token in ("/", "\\", "\x00", ":")) or ".." in raw:
        raise WorkspaceError("Client name contains path traversal or path syntax.")
    slug = re.sub(r"[^a-z0-9.-]+", "-", raw)
    slug = re.sub(r"-+", "-", slug).strip("-.")
    if not slug or len(slug) > 253 or ".." in slug:
        raise WorkspaceError("Client name cannot be converted to a safe slug.")
    for label in slug.split("."):
        if label.casefold() in WINDOWS_RESERVED_NAMES:
            raise WorkspaceError(f"Reserved Windows client slug label: {label!r}")
        if not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", label):
            raise WorkspaceError(f"Unsafe client slug label: {label!r}")
    return slug


def normalize_work_slug(value: str) -> str:
    raw = value.strip().lower()
    if any(token in raw for token in ("/", "\\", "\x00", ":")) or ".." in raw:
        raise WorkspaceError("Work name contains path traversal or path syntax.")
    slug = re.sub(r"[^a-z0-9]+", "-", raw).strip("-")
    if not slug or len(slug) > 64 or not SLUG_RE.fullmatch(slug):
        raise WorkspaceError("Work name cannot be converted to lowercase-kebab form.")
    if slug.casefold() in WINDOWS_RESERVED_NAMES:
        raise WorkspaceError(f"Reserved Windows work slug: {slug!r}")
    return slug


def clean_governance_text(value: str, field: str, maximum: int) -> str:
    clean = value.strip()
    if not clean:
        raise WorkspaceError(f"Novel work {field} may not be empty.")
    if len(clean) > maximum:
        raise WorkspaceError(f"Novel work {field} exceeds {maximum} characters.")
    if any(character in "\r\n\x00" or ord(character) < 32 for character in clean):
        raise WorkspaceError(f"Novel work {field} must be one printable line.")
    if field == "description" and clean.startswith("#"):
        raise WorkspaceError("Novel work description may not inject a Markdown heading.")
    return clean


@contextmanager
def workspace_lock(client: Path, timeout_seconds: float = 30.0):
    """Serialize structural workspace mutations without deleting another owner."""
    work_root = client / "work"
    work_root.mkdir(parents=True, exist_ok=True)
    lock_path = work_root / ".workspace.lock"
    token = f"{os.getpid()}-{uuid.uuid4().hex}"
    deadline = time.monotonic() + timeout_seconds
    descriptor: int | None = None
    while descriptor is None:
        try:
            descriptor = os.open(
                lock_path,
                os.O_CREAT | os.O_EXCL | os.O_WRONLY,
                0o600,
            )
        except FileExistsError:
            if time.monotonic() >= deadline:
                raise WorkspaceError(
                    f"Timed out waiting for client workspace lock: {lock_path}"
                )
            time.sleep(0.05)
    try:
        os.write(descriptor, token.encode("ascii"))
        os.close(descriptor)
        descriptor = None
        yield
    finally:
        if descriptor is not None:
            os.close(descriptor)
        try:
            if lock_path.read_text(encoding="ascii") == token:
                lock_path.unlink()
        except OSError:
            pass


def normalize_writable_subpath(value: str) -> Path:
    raw = Path(value.strip())
    if not value.strip() or raw.is_absolute():
        raise WorkspaceError("Writable subpaths must be non-empty relative paths.")
    for part in raw.parts:
        if (
            part in {"", ".", ".."}
            or not re.fullmatch(r"[a-z0-9][a-z0-9._-]*", part)
            or part.casefold() in WINDOWS_RESERVED_NAMES
        ):
            raise WorkspaceError(
                "Writable subpaths must use safe lowercase path segments."
            )
    return raw


def is_reparse_point(path: Path) -> bool:
    try:
        if path.is_symlink():
            return True
        junction_check = getattr(path, "is_junction", None)
        if junction_check is not None and junction_check():
            return True
        attrs = getattr(path.lstat(), "st_file_attributes", 0)
        return bool(attrs & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0))
    except OSError as exc:
        raise WorkspaceError(f"Cannot inspect path safety for {path}: {exc}") from exc


def assert_no_reparse_components(path: Path) -> None:
    absolute = Path(os.path.abspath(os.fspath(path)))
    parts = absolute.parts
    if not parts:
        return
    cursor = Path(parts[0])
    if cursor.exists() and is_reparse_point(cursor):
        raise WorkspaceError(f"Path crosses a symlink or junction: {cursor}")
    for part in parts[1:]:
        cursor = cursor / part
        if cursor.exists() and is_reparse_point(cursor):
            raise WorkspaceError(f"Path crosses a symlink or junction: {cursor}")


def resolve_plain_root(value: str | Path, *, must_exist: bool = True) -> Path:
    raw = Path(value).expanduser()
    assert_no_reparse_components(raw)
    try:
        resolved = raw.resolve(strict=must_exist)
    except OSError as exc:
        raise WorkspaceError(f"Cannot resolve workspace root {raw}: {exc}") from exc
    if must_exist and not resolved.is_dir():
        raise WorkspaceError(f"Workspace root is not a directory: {resolved}")
    return resolved


def assert_plain_tree(root: Path) -> None:
    root = root.absolute()
    if is_reparse_point(root):
        raise WorkspaceError(f"Workspace root may not be a symlink or junction: {root}")
    for current, directories, files in os.walk(root, followlinks=False):
        base = Path(current)
        for name in [*directories, *files]:
            candidate = base / name
            if is_reparse_point(candidate):
                raise WorkspaceError(
                    f"Symlink or junction is not allowed inside a client workspace: {candidate}"
                )


def confined_path(root: Path, relative: str | Path, *, must_exist: bool = False) -> Path:
    root = root.resolve(strict=True)
    raw = Path(relative)
    if raw.is_absolute():
        raise WorkspaceError(f"Path must be relative to the client root: {relative}")
    candidate = root / raw
    cursor = root
    for part in raw.parts:
        if part in {"", ".", ".."}:
            raise WorkspaceError(f"Unsafe relative path: {relative}")
        cursor = cursor / part
        if cursor.exists() and is_reparse_point(cursor):
            raise WorkspaceError(f"Path crosses a symlink or junction: {cursor}")
    resolved = candidate.resolve(strict=must_exist)
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise WorkspaceError(f"Path escapes the client root: {relative}") from exc
    return resolved


def read_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise WorkspaceError(f"Cannot read valid JSON from {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise WorkspaceError(f"Expected a JSON object in {path}")
    return data


def write_json_atomic(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(data, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        os.replace(temporary, path)
    except Exception:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise


def load_routing(client: Path) -> dict[str, Any]:
    path = client / ROUTING_FILE
    if not path.is_file():
        raise WorkspaceError(f"Missing client routing contract: {path}")
    return read_json(path)


def validate_routing_shape(routing: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    unexpected = sorted(set(routing) - ROUTING_KEYS)
    if unexpected:
        errors.append("Unexpected workspace-routing keys: " + ", ".join(unexpected))
    if routing.get("version") != "1.0.0":
        errors.append("workspace-routing.json version must be 1.0.0.")
    root_policy = routing.get("root_policy")
    if not isinstance(root_policy, dict):
        errors.append("root_policy must be an object.")
        root_policy = {}
    unexpected = sorted(set(root_policy) - ROOT_POLICY_KEYS)
    if unexpected:
        errors.append("Unexpected root_policy keys: " + ", ".join(unexpected))
    for key in ("allowed_files", "allowed_directories"):
        value = root_policy.get(key)
        if not isinstance(value, list) or not value or not all(
            isinstance(item, str) and item for item in value
        ):
            errors.append(f"root_policy.{key} must be a non-empty string array.")
        elif len(value) != len(set(value)):
            errors.append(f"root_policy.{key} may not contain duplicates.")
    allowed_files = root_policy.get("allowed_files", [])
    if isinstance(allowed_files, list):
        for item in allowed_files:
            if isinstance(item, str) and Path(item).name != item:
                errors.append(f"Root allowlisted file must be a leaf name: {item}")
    allowed_directories = root_policy.get("allowed_directories", [])
    if isinstance(allowed_directories, list):
        for item in allowed_directories:
            if isinstance(item, str) and not SLUG_RE.fullmatch(item):
                errors.append(f"Root allowlisted directory must be lowercase-kebab: {item}")
    if root_policy.get("generated_files_forbidden") is not True:
        errors.append("root_policy.generated_files_forbidden must be true.")
    required = routing.get("required_directories")
    if not isinstance(required, list) or not all(
        isinstance(item, str) and item for item in required
    ):
        errors.append("required_directories must be a string array.")
        required = []
    elif len(required) != len(set(required)):
        errors.append("required_directories may not contain duplicates.")
    required_set = set(required)
    uploads = routing.get("uploads")
    if not isinstance(uploads, dict) or uploads.get("read_only") is not True:
        errors.append("uploads.read_only must be true.")
    elif uploads.get("path") != "uploads":
        errors.append("uploads.path must be uploads.")
    if isinstance(uploads, dict):
        unexpected = sorted(set(uploads) - UPLOAD_KEYS)
        if unexpected:
            errors.append("Unexpected uploads keys: " + ", ".join(unexpected))
    routes = routing.get("routes")
    if not isinstance(routes, list) or not routes:
        errors.append("routes must be a non-empty array.")
        routes = []
    seen: set[str] = set()
    aliases: set[str] = set()
    for index, route in enumerate(routes):
        if not isinstance(route, dict):
            errors.append(f"routes[{index}] must be an object.")
            continue
        unexpected = sorted(set(route) - ROUTE_KEYS)
        if unexpected:
            errors.append(
                f"Unexpected routes[{index}] keys: " + ", ".join(unexpected)
            )
        route_id = route.get("id")
        directory = route.get("directory")
        if not isinstance(route_id, str) or not SLUG_RE.fullmatch(route_id):
            errors.append(f"routes[{index}].id must be lowercase-kebab.")
        elif route_id in seen or route_id in aliases:
            errors.append(f"Duplicate route identifier: {route_id}")
        else:
            seen.add(route_id)
        if not isinstance(directory, str) or not directory:
            errors.append(f"routes[{index}].directory is required.")
        elif directory not in required_set:
            errors.append(
                f"routes[{index}].directory must be registered in required_directories."
            )
        if not isinstance(route.get("description"), str) or not route["description"].strip():
            errors.append(f"routes[{index}].description is required.")
        if not isinstance(route.get("filename_pattern"), str):
            errors.append(f"routes[{index}].filename_pattern must be a string.")
        route_aliases = route.get("aliases", [])
        if not isinstance(route_aliases, list):
            errors.append(f"routes[{index}].aliases must be an array.")
            continue
        for alias in route_aliases:
            if not isinstance(alias, str) or not SLUG_RE.fullmatch(alias):
                errors.append(f"Invalid route alias: {alias!r}")
            elif alias in seen or alias in aliases:
                errors.append(f"Duplicate route identifier or alias: {alias}")
            else:
                aliases.add(alias)
    novel = routing.get("novel_work")
    if not isinstance(novel, dict):
        errors.append("novel_work must be an object.")
    else:
        unexpected = sorted(set(novel) - NOVEL_KEYS)
        if unexpected:
            errors.append("Unexpected novel_work keys: " + ", ".join(unexpected))
        if novel.get("root") != "work":
            errors.append("novel_work.root must be work.")
        if novel.get("registry") != "work/registry.json":
            errors.append("novel_work.registry must be work/registry.json.")
        if novel.get("folder_pattern") != SLUG_RE.pattern:
            errors.append("novel_work.folder_pattern must use the canonical pattern.")
        if novel.get("require_registration") is not True:
            errors.append("novel_work.require_registration must be true.")
        required_fields = novel.get("entry_required_fields")
        if not isinstance(required_fields, list) or tuple(required_fields) != NOVEL_REQUIRED_FIELDS:
            errors.append(
                "novel_work.entry_required_fields must match the canonical registry fields."
            )
    return errors


def ensure_workspace(client_value: str | Path) -> dict[str, Any]:
    client = resolve_plain_root(client_value)
    assert_plain_tree(client)
    routing = load_routing(client)
    errors = validate_routing_shape(routing)
    if errors:
        raise WorkspaceError("Invalid routing contract: " + "; ".join(errors))
    for relative in routing["required_directories"]:
        directory = confined_path(client, relative)
        directory.mkdir(parents=True, exist_ok=True)
    novel = routing["novel_work"]
    registry_path = confined_path(client, novel["registry"])
    if not registry_path.exists():
        write_json_atomic(
            registry_path,
            {"version": REGISTRY_VERSION, "entries": []},
        )
    return {"client": str(client), "ensured": len(routing["required_directories"])}


def validate_workspace(client_value: str | Path) -> dict[str, Any]:
    client = resolve_plain_root(client_value)
    errors: list[str] = []
    try:
        assert_plain_tree(client)
    except WorkspaceError as exc:
        errors.append(str(exc))
    try:
        routing = load_routing(client)
    except WorkspaceError as exc:
        return {"client": str(client), "passed": False, "errors": [str(exc)]}
    errors.extend(validate_routing_shape(routing))
    if errors:
        return {"client": str(client), "passed": False, "errors": errors}

    root_policy = routing["root_policy"]
    allowed_files = set(root_policy["allowed_files"])
    allowed_directories = set(root_policy["allowed_directories"])
    for item in client.iterdir():
        if item.is_file() and item.name not in allowed_files:
            errors.append(f"Loose or unregistered file at client root: {item.name}")
        elif item.is_dir() and item.name not in allowed_directories:
            errors.append(f"Unregistered directory at client root: {item.name}/")

    uploads_path = str(routing["uploads"].get("path", ""))
    route_ids: set[str] = set()
    for route in routing["routes"]:
        route_ids.add(route["id"])
        route_ids.update(route.get("aliases", []))
        try:
            routed = confined_path(client, route["directory"])
            relative = routed.relative_to(client).as_posix()
            if relative == uploads_path or relative.startswith(uploads_path + "/"):
                errors.append(f"Writable route points into read-only uploads: {route['id']}")
            if not routed.is_dir():
                errors.append(f"Route directory is missing: {route['directory']}")
        except WorkspaceError as exc:
            errors.append(str(exc))

    for relative in routing["required_directories"]:
        try:
            if not confined_path(client, relative).is_dir():
                errors.append(f"Required directory is missing: {relative}")
        except WorkspaceError as exc:
            errors.append(str(exc))

    for instruction in ("AGENTS.md", "CLAUDE.md"):
        path = client / instruction
        if not path.is_file():
            errors.append(f"Missing client instruction file: {instruction}")
        elif ROUTING_FILE not in path.read_text(encoding="utf-8-sig"):
            errors.append(f"{instruction} must reference {ROUTING_FILE}.")

    novel = routing["novel_work"]
    try:
        work_root = confined_path(client, novel["root"], must_exist=True)
        registry_path = confined_path(client, novel["registry"], must_exist=True)
        registry = read_json(registry_path)
        entries = registry.get("entries")
        if registry.get("version") != REGISTRY_VERSION or not isinstance(entries, list):
            errors.append("Novel-work registry has an invalid version or entries array.")
            entries = []
        registered: set[str] = set()
        for entry in entries:
            if not isinstance(entry, dict):
                errors.append("Novel-work registry entries must be objects.")
                continue
            missing_fields = [field for field in NOVEL_REQUIRED_FIELDS if field not in entry]
            if missing_fields:
                errors.append(
                    "Novel-work entry is missing required fields: "
                    + ", ".join(missing_fields)
                )
                continue
            entry_id = entry.get("id")
            entry_path = entry.get("path")
            if not isinstance(entry_id, str) or not SLUG_RE.fullmatch(entry_id):
                errors.append(f"Invalid novel-work id: {entry_id!r}")
                continue
            expected = f"{novel['root'].rstrip('/')}/{entry_id}"
            if entry_id in registered or entry_path != expected:
                errors.append(f"Invalid or duplicate novel-work entry: {entry_id}")
                continue
            registered.add(entry_id)
            try:
                if not confined_path(client, expected).is_dir():
                    errors.append(f"Registered novel-work folder is missing: {expected}")
            except WorkspaceError as exc:
                errors.append(str(exc))
            for field in (
                "description",
                "owner",
                "source_of_truth",
                "retention",
                "created_at",
            ):
                if not isinstance(entry.get(field), str) or not entry[field].strip():
                    errors.append(f"Novel-work {entry_id} has invalid {field}.")
            artifact_classes = entry.get("artifact_classes")
            if (
                not isinstance(artifact_classes, list)
                or not artifact_classes
                or not all(
                    isinstance(item, str) and SLUG_RE.fullmatch(item)
                    for item in artifact_classes
                )
                or len(artifact_classes) != len(set(artifact_classes))
            ):
                errors.append(
                    f"Novel-work {entry_id} artifact_classes must be unique lowercase-kebab values."
                )
            writable_subpaths = entry.get("writable_subpaths")
            if (
                not isinstance(writable_subpaths, list)
                or not writable_subpaths
                or not all(isinstance(item, str) for item in writable_subpaths)
                or len(writable_subpaths) != len(set(writable_subpaths))
            ):
                errors.append(
                    f"Novel-work {entry_id} writable_subpaths must be a non-empty unique array."
                )
                writable_subpaths = []
            for writable in writable_subpaths:
                if not isinstance(writable, str) or not writable.startswith(expected + "/"):
                    errors.append(
                        f"Novel-work {entry_id} writable path must stay below {expected}/."
                    )
                    continue
                try:
                    suffix = Path(writable).relative_to(Path(expected))
                    normalize_writable_subpath(suffix.as_posix())
                    if not confined_path(client, writable).is_dir():
                        errors.append(f"Novel-work writable directory is missing: {writable}")
                except WorkspaceError as exc:
                    errors.append(str(exc))
                except ValueError:
                    errors.append(
                        f"Novel-work {entry_id} writable path escapes {expected}/."
                    )
            source_value = entry.get("source_of_truth")
            if isinstance(source_value, str) and source_value.strip():
                try:
                    if not confined_path(client, source_value, must_exist=True).exists():
                        errors.append(
                            f"Novel-work source of truth is missing: {source_value}"
                        )
                except WorkspaceError as exc:
                    errors.append(str(exc))
            created_value = entry.get("created_at")
            if isinstance(created_value, str) and created_value.strip():
                try:
                    parsed_created = datetime.fromisoformat(
                        created_value.replace("Z", "+00:00")
                    )
                    if parsed_created.tzinfo is None:
                        raise ValueError("timezone is required")
                except ValueError:
                    errors.append(
                        f"Novel-work {entry_id} created_at must be timezone-aware ISO 8601."
                    )
        ignored = {
            Path(novel["registry"]).name,
            "README.md",
            ".gitkeep",
            ".workspace.lock",
        }
        for item in work_root.iterdir():
            if item.is_dir() and item.name not in registered:
                errors.append(f"Unregistered novel-work folder: work/{item.name}")
            elif item.is_file() and item.name not in ignored:
                errors.append(f"Loose file in work root: work/{item.name}")
    except WorkspaceError as exc:
        errors.append(str(exc))

    return {"client": str(client), "passed": not errors, "errors": errors}


def find_route(routing: dict[str, Any], output_type: str) -> dict[str, Any]:
    key = normalize_work_slug(output_type)
    for route in routing["routes"]:
        if key == route["id"] or key in route.get("aliases", []):
            return route
    raise WorkspaceError(
        f"No registered route for {output_type!r}. Use create-work only when no existing "
        "route reasonably fits."
    )


def safe_leaf_filename(filename: str) -> Path:
    leaf = Path(filename)
    reserved_stem = leaf.stem.casefold()
    if (
        leaf.name != filename
        or filename in {".", ".."}
        or filename.endswith((" ", "."))
        or any(character in filename for character in '<>:"/\\|?*')
        or any(ord(character) < 32 for character in filename)
        or reserved_stem in WINDOWS_RESERVED_NAMES
    ):
        raise WorkspaceError("Filename must be a single path-safe leaf name.")
    return leaf


def route_output(
    client_value: str | Path,
    output_type: str,
    filename: str | None = None,
    *,
    create: bool = False,
) -> dict[str, Any]:
    client = resolve_plain_root(client_value)
    routing = load_routing(client)
    errors = validate_routing_shape(routing)
    if errors:
        raise WorkspaceError("Invalid routing contract: " + "; ".join(errors))
    route = find_route(routing, output_type)
    directory = confined_path(client, route["directory"])
    if create:
        directory.mkdir(parents=True, exist_ok=True)
    if not directory.is_dir():
        raise WorkspaceError(f"Registered route directory is missing: {route['directory']}")
    target = directory
    if filename:
        leaf = safe_leaf_filename(filename)
        target = confined_path(client, Path(route["directory"]) / leaf)
    return {
        "client": str(client),
        "route": route["id"],
        "directory": str(directory),
        "target": str(target),
        "filename_pattern": route.get("filename_pattern", ""),
    }


def route_novel_work(
    client_value: str | Path,
    name: str,
    writable_subpath: str,
    filename: str | None = None,
) -> dict[str, Any]:
    """Resolve a registered novel-work writable destination without path guessing."""
    client = resolve_plain_root(client_value)
    validation = validate_workspace(client)
    if not validation["passed"]:
        raise WorkspaceError(
            "Client workspace routing validation failed: "
            + "; ".join(validation["errors"])
        )
    work_id = normalize_work_slug(name)
    if work_id != name:
        raise WorkspaceError("Novel work name must already use lowercase-kebab form.")
    subpath = normalize_writable_subpath(writable_subpath).as_posix()
    if subpath != writable_subpath:
        raise WorkspaceError("Novel writable subpath must already be normalized.")
    routing = load_routing(client)
    novel = routing["novel_work"]
    registry_path = confined_path(client, novel["registry"], must_exist=True)
    registry = read_json(registry_path)
    entries = registry.get("entries", [])
    entry = next(
        (
            item
            for item in entries
            if isinstance(item, dict) and item.get("id") == work_id
        ),
        None,
    )
    if entry is None:
        raise WorkspaceError(f"Novel work is not registered: {work_id}")
    relative = f"{novel['root'].rstrip('/')}/{work_id}/{subpath}"
    if relative not in entry.get("writable_subpaths", []):
        raise WorkspaceError(
            f"Novel writable subpath is not registered for {work_id}: {subpath}"
        )
    directory = confined_path(client, relative, must_exist=True)
    if not directory.is_dir():
        raise WorkspaceError(f"Registered novel writable path is missing: {relative}")
    target = directory
    if filename:
        target = confined_path(client, Path(relative) / safe_leaf_filename(filename))
    return {
        "client": str(client),
        "route": f"work:{work_id}:{subpath}",
        "directory": str(directory),
        "target": str(target),
        "filename_pattern": "registered novel-work leaf",
    }


def create_novel_work(
    client_value: str | Path,
    name: str,
    description: str,
    owner: str = DEFAULT_NOVEL_OWNER,
    artifact_classes: list[str] | None = None,
    writable_subpaths: list[str] | None = None,
    source_of_truth: str | None = None,
    retention: str = DEFAULT_RETENTION,
) -> dict[str, Any]:
    client = resolve_plain_root(client_value)
    description_value = clean_governance_text(description, "description", 500)
    owner_value = clean_governance_text(owner, "owner", 120)
    retention_value = clean_governance_text(retention, "retention", 240)
    class_values = artifact_classes or [DEFAULT_ARTIFACT_CLASS]
    normalized_classes = list(dict.fromkeys(normalize_work_slug(item) for item in class_values))
    subpath_values = writable_subpaths or [DEFAULT_WRITABLE_SUBPATH]
    normalized_subpaths = list(
        dict.fromkeys(normalize_writable_subpath(item).as_posix() for item in subpath_values)
    )
    work_id = normalize_work_slug(name)
    with workspace_lock(client):
        routing = load_routing(client)
        errors = validate_routing_shape(routing)
        if errors:
            raise WorkspaceError("Invalid routing contract: " + "; ".join(errors))
        try:
            existing = find_route(routing, work_id)
        except WorkspaceError:
            existing = None
        if existing is not None:
            raise WorkspaceError(
                f"Use existing route {existing['id']!r} at {existing['directory']}; "
                "do not create duplicate novel work."
            )
        novel = routing["novel_work"]
        target_relative = f"{novel['root'].rstrip('/')}/{work_id}"
        target = confined_path(client, target_relative)
        source_value = (source_of_truth or f"{target_relative}/README.md").strip()
        if not source_value:
            raise WorkspaceError("Novel work source_of_truth may not be empty.")
        if source_of_truth:
            source_path = confined_path(client, source_value, must_exist=True)
            source_value = source_path.relative_to(client).as_posix()
        writable_values = [
            f"{target_relative}/{subpath}" for subpath in normalized_subpaths
        ]
        registry_path = confined_path(client, novel["registry"])
        registry = (
            read_json(registry_path)
            if registry_path.exists()
            else {"version": REGISTRY_VERSION, "entries": []}
        )
        entries = registry.setdefault("entries", [])
        if not isinstance(entries, list):
            raise WorkspaceError("Novel-work registry entries must be an array.")
        if any(isinstance(item, dict) and item.get("id") == work_id for item in entries):
            raise WorkspaceError(f"Novel work is already registered: {work_id}")
        if target.exists():
            raise WorkspaceError(f"Unregistered work folder already exists: {target}")
        original_registry = json.loads(json.dumps(registry))
        staging = client / "work" / f".{work_id}.staging-{uuid.uuid4().hex}"
        promoted = False
        try:
            staging.mkdir(parents=False)
            (staging / "README.md").write_text(
                f"# {work_id}\n\n{description_value}\n",
                encoding="utf-8",
                newline="\n",
            )
            for subpath in normalized_subpaths:
                writable_path = staging / subpath
                writable_path.mkdir(parents=True, exist_ok=True)
                (writable_path / ".gitkeep").touch(exist_ok=True)
            staging.rename(target)
            promoted = True
            entries.append(
                {
                    "id": work_id,
                    "path": target_relative,
                    "description": description_value,
                    "owner": owner_value,
                    "artifact_classes": normalized_classes,
                    "writable_subpaths": writable_values,
                    "source_of_truth": source_value,
                    "retention": retention_value,
                    "created_at": now_iso(),
                }
            )
            write_json_atomic(registry_path, registry)
            log_path = client / "log.md"
            with log_path.open("a", encoding="utf-8", newline="\n") as stream:
                stream.write(
                    f"\n## [{datetime.now().date().isoformat()}] workspace - registered "
                    f"{target_relative} - {description_value}\n"
                )
        except Exception:
            write_json_atomic(registry_path, original_registry)
            if promoted and target.exists():
                shutil.rmtree(target)
            if staging.exists():
                shutil.rmtree(staging)
            raise
    return {
        "client": str(client),
        "id": work_id,
        "path": str(target),
        "owner": owner_value,
        "artifact_classes": normalized_classes,
        "writable_subpaths": writable_values,
        "source_of_truth": source_value,
        "retention": retention_value,
    }


def initialize_workspace(workspace_value: str | Path, client_name: str) -> dict[str, Any]:
    workspace = resolve_plain_root(workspace_value, must_exist=False)
    workspace.mkdir(parents=True, exist_ok=True)
    assert_plain_tree(TEMPLATE_ROOT)
    slug = normalize_client_slug(client_name)
    clients_root = workspace / "clients"
    clients_root.mkdir(parents=True, exist_ok=True)
    if is_reparse_point(clients_root):
        raise WorkspaceError(f"clients/ may not be a symlink or junction: {clients_root}")
    destination = clients_root / slug
    if destination.exists():
        raise WorkspaceError(f"Client already exists: {destination}")
    temporary = clients_root / f".{slug}.initializing-{os.getpid()}"
    if temporary.exists():
        raise WorkspaceError(f"Temporary initialization path already exists: {temporary}")
    try:
        shutil.copytree(TEMPLATE_ROOT, temporary, symlinks=False)
        config_path = temporary / "content-pipeline.json"
        config = read_json(config_path)
        config.setdefault("config_policy", {})["profile"] = "production"
        config.setdefault("site", {})["domain"] = slug
        write_json_atomic(config_path, config)
        ensure_workspace(temporary)
        report = validate_workspace(temporary)
        if not report["passed"]:
            raise WorkspaceError("Initialized workspace failed validation: " + "; ".join(report["errors"]))
        temporary.rename(destination)
    except Exception:
        if temporary.exists():
            shutil.rmtree(temporary)
        raise
    return {"workspace": str(workspace), "client": slug, "path": str(destination)}


def adopt_workspace(client_value: str | Path) -> dict[str, Any]:
    """Add the routing contract to an existing client without moving or deleting data."""
    client = resolve_plain_root(client_value)
    assert_plain_tree(client)
    assert_plain_tree(TEMPLATE_ROOT)
    routing_path = client / ROUTING_FILE
    routing_created = False
    if not routing_path.exists():
        shutil.copy2(TEMPLATE_ROOT / ROUTING_FILE, routing_path)
        routing_created = True
    elif not routing_path.is_file():
        raise WorkspaceError(f"Existing routing path is not a regular file: {routing_path}")

    ensure_result = ensure_workspace(client)
    instruction_status: dict[str, str] = {}
    note = (
        f"\n\n<!-- {ROUTING_NOTE_MARKER}:BEGIN -->\n"
        "## Rainmojo Client Workspace Routing\n\n"
        "Before any write, read workspace-routing.json and resolve the most precise "
        "destination with client_workspace.py route. Never write generated files to "
        "the client root or working directory. Treat uploads/ as read-only. Use "
        "create-work only for genuinely novel registered work, and run validate "
        "before handoff.\n"
        f"<!-- {ROUTING_NOTE_MARKER}:END -->\n"
    )
    for filename in ("AGENTS.md", "CLAUDE.md"):
        destination = client / filename
        if not destination.exists():
            shutil.copy2(TEMPLATE_ROOT / filename, destination)
            instruction_status[filename] = "created-from-canonical-template"
            continue
        if not destination.is_file():
            raise WorkspaceError(f"Existing instruction path is not a file: {destination}")
        current = destination.read_text(encoding="utf-8-sig")
        if ROUTING_NOTE_MARKER in current or ROUTING_FILE in current:
            instruction_status[filename] = "preserved-existing-routing-note"
            continue
        with destination.open("a", encoding="utf-8", newline="\n") as stream:
            stream.write(note)
        instruction_status[filename] = "appended-routing-note"

    validation = validate_workspace(client)
    return {
        "client": str(client),
        "routing_created": routing_created,
        "routing_preserved": not routing_created,
        "ensured": ensure_result["ensured"],
        "instruction_files": instruction_status,
        "destructive_changes": False,
        "passed": validation["passed"],
        "remaining_issues": validation["errors"],
    }


def print_result(result: dict[str, Any]) -> None:
    print(json.dumps(result, ensure_ascii=False, indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    init = sub.add_parser("init", help="Clone the authoritative demo into clients/<slug>.")
    init.add_argument("--workspace", default=".")
    init.add_argument("--client", required=True)

    adopt = sub.add_parser(
        "adopt",
        help="Add routing to an existing client without moving, deleting, or overwriting data.",
    )
    adopt.add_argument("--client", required=True)

    ensure = sub.add_parser("ensure", help="Create registered folders missing from a client.")
    ensure.add_argument("--client", required=True)

    route = sub.add_parser("route", help="Resolve an output type to its precise client path.")
    route.add_argument("--client", required=True)
    route.add_argument("--type", required=True)
    route.add_argument("--filename")
    route.add_argument("--create", action="store_true")

    route_work = sub.add_parser(
        "route-work",
        help="Resolve a registered novel-work writable subpath.",
    )
    route_work.add_argument("--client", required=True)
    route_work.add_argument("--name", required=True)
    route_work.add_argument("--subpath", required=True)
    route_work.add_argument("--filename")

    create = sub.add_parser(
        "create-work",
        help="Create and register genuinely novel work under work/<lowercase-kebab>/.",
    )
    create.add_argument("--client", required=True)
    create.add_argument("--name", required=True)
    create.add_argument("--description", required=True)
    create.add_argument("--owner", default=DEFAULT_NOVEL_OWNER)
    create.add_argument("--artifact-class", action="append", dest="artifact_classes")
    create.add_argument("--writable-subpath", action="append", dest="writable_subpaths")
    create.add_argument(
        "--source-of-truth",
        help="Existing client-relative source path; defaults to the work README.",
    )
    create.add_argument("--retention", default=DEFAULT_RETENTION)

    validate = sub.add_parser("validate", help="Validate routing, containment, and scaffold state.")
    validate.add_argument("--client", required=True)
    return parser


def _self_test_hook() -> None:
    if "--self-test" in sys.argv[1:]:
        raise SystemExit(_self_test())


def main() -> int:
    _self_test_hook()
    args = build_parser().parse_args()
    try:
        if args.command == "init":
            result = initialize_workspace(args.workspace, args.client)
        elif args.command == "adopt":
            result = adopt_workspace(args.client)
            print_result(result)
            return 0 if result["passed"] else 2
        elif args.command == "ensure":
            result = ensure_workspace(args.client)
        elif args.command == "route":
            result = route_output(
                args.client,
                args.type,
                args.filename,
                create=args.create,
            )
        elif args.command == "route-work":
            result = route_novel_work(
                args.client,
                args.name,
                args.subpath,
                args.filename,
            )
        elif args.command == "create-work":
            result = create_novel_work(
                args.client,
                args.name,
                args.description,
                owner=args.owner,
                artifact_classes=args.artifact_classes,
                writable_subpaths=args.writable_subpaths,
                source_of_truth=args.source_of_truth,
                retention=args.retention,
            )
        else:
            result = validate_workspace(args.client)
            print_result(result)
            return 0 if result["passed"] else 2
        print_result(result)
        return 0
    except WorkspaceError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2



def _self_test() -> int:
    """Clone the demo client into a temp dir, validate it and route one output."""
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        result = initialize_workspace(tmp, "Self Test Clinic")
        client = result["path"]
        report = validate_workspace(client)
        assert report.get("passed"), report
        routed = route_output(client, "seo-audit-report", "example.com_report_2026-01-01.md")
        target = str(routed.get("path") or routed.get("target") or routed)
        assert "seo-audits" in target.replace("\\", "/") or "reports" in target.replace("\\", "/"), routed
    print("SELF-TEST PASS: init, validate, route")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
