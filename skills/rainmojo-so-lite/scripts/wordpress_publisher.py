#!/usr/bin/env python3
"""Upload a validated content package to WordPress as a verified draft."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import mimetypes
import os
import re
import sys
import time
from collections import Counter
from contextlib import contextmanager, nullcontext
from html.parser import HTMLParser
from io import BytesIO
from pathlib import Path
from typing import Any, Iterator
from urllib.parse import urlparse

try:
    import requests
except ImportError:
    print("ERROR: requests is required. Install with: pip install requests", file=sys.stderr)
    raise SystemExit(1)

try:
    from PIL import Image
except ImportError:
    print("ERROR: Pillow is required. Install with: pip install Pillow", file=sys.stderr)
    raise SystemExit(1)

import content_formatter
import content_pipeline


WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
AMBIGUOUS_HTTP_STATUSES = {408, 500, 502, 503, 504, 520, 522, 524}
IDENTITY_RE = re.compile(
    r"<!--\s*rainmojo-media\s+(\{.*?\})\s*-->",
    re.I | re.S,
)
ANCHOR_TAG_RE = re.compile(r"<a\b[^>]*>", re.I)


class WordPressError(RuntimeError):
    """A definite WordPress, configuration, or verification failure."""


class AmbiguousWriteError(WordPressError):
    """A write may have completed, so the caller must reconcile before retrying."""

    def __init__(
        self,
        message: str,
        *,
        category: str = "ambiguous_write",
        method: str = "",
        route: str = "",
        context: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.category = category
        self.method = method
        self.route = route
        self.context = dict(context or {})

    def as_dict(self) -> dict[str, Any]:
        return {
            "category": self.category,
            "method": self.method,
            "route": self.route,
            "message": str(self),
            "context": self.context,
        }


class FileMutex:
    """Small cross-platform advisory file mutex for publisher processes."""

    def __init__(self, path: Path, timeout: float = 300.0) -> None:
        self.path = path
        self.timeout = max(1.0, float(timeout))
        self.handle: Any = None

    def _try_lock(self) -> None:
        assert self.handle is not None
        self.handle.seek(0)
        if os.name == "nt":
            import msvcrt

            msvcrt.locking(self.handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl

            fcntl.flock(self.handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)

    def _unlock(self) -> None:
        assert self.handle is not None
        self.handle.seek(0)
        if os.name == "nt":
            import msvcrt

            msvcrt.locking(self.handle.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            fcntl.flock(self.handle.fileno(), fcntl.LOCK_UN)

    def __enter__(self) -> "FileMutex":
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.handle = self.path.open("a+b")
        self.handle.seek(0, os.SEEK_END)
        if self.handle.tell() == 0:
            self.handle.write(b"0")
            self.handle.flush()
        deadline = time.monotonic() + self.timeout
        while True:
            try:
                self._try_lock()
                return self
            except (OSError, BlockingIOError):
                if time.monotonic() >= deadline:
                    self.handle.close()
                    self.handle = None
                    raise WordPressError(
                        f"Timed out waiting for publisher lock: {self.path}"
                    )
                time.sleep(0.1)

    def __exit__(self, _exc_type: Any, _exc: Any, _tb: Any) -> None:
        if self.handle is None:
            return
        try:
            self._unlock()
        finally:
            self.handle.close()
            self.handle = None


def load_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.strip()
        if (
            len(value) >= 2
            and value[0] == value[-1]
            and value[0] in {"'", '"'}
        ):
            value = value[1:-1]
        values[key.strip()] = value
    return values


ENV_DEFAULT_NAMES: dict[str, tuple[str, ...]] = {
    "url": ("WP_URL", "WP_SITE_URL", "WORDPRESS_URL"),
    "user": ("WP_USER", "WP_USERNAME", "WORDPRESS_USER"),
    "app_password": (
        "WP_APP_PASSWORD",
        "WP_APPLICATION_PASSWORD",
        "WP_APP_PASS",
    ),
    "rest_mode": ("WP_REST_MODE",),
    "rest_base": (
        "WP_REST_BASE",
        "WP_ORIGIN_REST_BASE",
        "WP_ORIGIN_REST_URL",
    ),
    "write_interval": (
        "WP_WRITE_INTERVAL_SECONDS",
        "WP_WRITE_SLEEP_SECONDS",
    ),
    "request_timeout": (
        "WP_REQUEST_TIMEOUT_SECONDS",
        "WP_TIMEOUT_SECONDS",
    ),
    "query_param": ("WP_WAF_QUERY_PARAM", "WP_QUERY_TOKEN_PARAM"),
    "query_token": ("WP_WAF_QUERY_TOKEN", "WP_QUERY_TOKEN"),
    "bypass_header_name": (
        "WP_BYPASS_HEADER_NAME",
        "WP_WAF_HEADER_NAME",
    ),
    "bypass_header_value": (
        "WP_BYPASS_HEADER_VALUE",
        "WP_WAF_HEADER_VALUE",
    ),
    "user_agent": ("WP_USER_AGENT",),
    "operation_lock": ("WP_PUBLISH_LOCK_FILE", "WP_OPERATION_LOCK_FILE"),
    "write_lock": ("WP_WRITE_LOCK_FILE",),
    "write_state": ("WP_WRITE_STATE_FILE",),
    "lock_timeout": ("WP_PUBLISH_LOCK_TIMEOUT_SECONDS", "WP_LOCK_TIMEOUT_SECONDS"),
}


def env_value(
    env: dict[str, str],
    wp_config: dict[str, Any],
    key: str,
    default: str = "",
) -> str:
    configured = wp_config.get("env_aliases", {}).get(key, [])
    if isinstance(configured, str):
        configured = [configured]
    names = list(ENV_DEFAULT_NAMES.get(key, ())) + [
        str(name) for name in configured
    ]
    for name in dict.fromkeys(names):
        value = env.get(name)
        if value is not None and str(value).strip() != "":
            return str(value).strip()
    return default


def resolve_state_path(client_path: Path, value: str, default_name: str) -> Path:
    root = client_path / "content" / "production" / ".publisher-state"
    if not value:
        return root / default_name
    path = Path(value).expanduser()
    return path.resolve() if path.is_absolute() else (client_path / path).resolve()


class WordPressClient:
    def __init__(
        self,
        base_url: str,
        username: str,
        app_password: str,
        *,
        rest_mode: str = "auto",
        rest_base: str = "",
        write_interval: float = 25.0,
        timeout: float = 45.0,
        query_param: str = "",
        query_token: str = "",
        bypass_headers: dict[str, str] | None = None,
        user_agent: str = "rainmojo-so-content-publisher/1.1",
        operation_lock_path: Path | None = None,
        write_lock_path: Path | None = None,
        write_state_path: Path | None = None,
        lock_timeout: float = 300.0,
        session: requests.Session | None = None,
    ) -> None:
        if rest_mode not in {"auto", "direct", "rest_route"}:
            raise WordPressError(f"Unsupported WP_REST_MODE: {rest_mode}")
        self.base_url = base_url.rstrip("/")
        self.rest_base = rest_base.rstrip("/")
        self.rest_mode = rest_mode
        self.active_mode: str | None = None if rest_mode == "auto" else rest_mode
        self.write_interval = max(0.0, float(write_interval))
        self.timeout = max(1.0, float(timeout))
        self.query_param = query_param.strip()
        self.query_token = query_token.strip()
        self.operation_lock_path = operation_lock_path
        self.write_lock_path = write_lock_path
        self.write_state_path = write_state_path
        self.lock_timeout = max(1.0, float(lock_timeout))
        self.last_write_epoch = 0.0
        self.session = session or requests.Session()
        self.session.auth = (username, app_password)
        self.session.headers.update(
            {
                "Accept": "application/json",
                "User-Agent": user_agent,
                **(bypass_headers or {}),
            }
        )

    def operation_lock(self) -> Any:
        if self.operation_lock_path is None:
            return nullcontext()
        return FileMutex(self.operation_lock_path, self.lock_timeout)

    def _request_target(
        self,
        mode: str,
        route: str,
        params: dict[str, Any] | None,
    ) -> tuple[str, dict[str, Any]]:
        route = route.strip("/")
        query = dict(params or {})
        if self.query_token:
            query[self.query_param or "t"] = self.query_token
        if mode == "direct":
            base = self.rest_base or f"{self.base_url}/wp-json/wp/v2"
            return f"{base}/{route}", query
        query = {"rest_route": f"/wp/v2/{route}", **query}
        return f"{self.base_url}/", query

    def _read_global_write_epoch(self) -> float:
        if self.write_state_path is None or not self.write_state_path.exists():
            return 0.0
        try:
            return float(self.write_state_path.read_text(encoding="ascii").strip())
        except (OSError, ValueError):
            return 0.0

    def _write_global_write_epoch(self, value: float) -> None:
        if self.write_state_path is None:
            return
        self.write_state_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.write_state_path.with_name(
            f"{self.write_state_path.name}.{os.getpid()}.tmp"
        )
        temporary.write_text(f"{value:.6f}\n", encoding="ascii")
        temporary.replace(self.write_state_path)

    @contextmanager
    def _write_guard(self) -> Iterator[None]:
        mutex = (
            FileMutex(self.write_lock_path, self.lock_timeout)
            if self.write_lock_path is not None
            else nullcontext()
        )
        with mutex:
            last_epoch = max(
                self.last_write_epoch,
                self._read_global_write_epoch(),
            )
            remaining = self.write_interval - (time.time() - last_epoch)
            if last_epoch and remaining > 0:
                time.sleep(remaining)
            try:
                yield
            finally:
                completed_at = time.time()
                self.last_write_epoch = completed_at
                self._write_global_write_epoch(completed_at)

    @staticmethod
    def _transport_category(exc: requests.exceptions.RequestException) -> str:
        if isinstance(exc, requests.exceptions.Timeout):
            return "transport_timeout"
        if isinstance(exc, requests.exceptions.ConnectionError):
            return "transport_connection"
        return "transport_response"

    def request(
        self,
        method: str,
        route: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
        data: bytes | None = None,
        headers: dict[str, str] | None = None,
    ) -> requests.Response:
        method = method.upper()
        write = method in WRITE_METHODS
        modes = [self.active_mode] if self.active_mode else ["direct", "rest_route"]
        for index, mode in enumerate(modes):
            if mode is None:
                continue
            url, query = self._request_target(mode, route, params)
            guard = self._write_guard() if write else nullcontext()
            try:
                with guard:
                    response = self.session.request(
                        method,
                        url,
                        params=query,
                        json=json_body,
                        data=data,
                        headers=headers,
                        timeout=self.timeout,
                    )
            except (
                requests.exceptions.InvalidURL,
                requests.exceptions.InvalidSchema,
                requests.exceptions.MissingSchema,
                requests.exceptions.URLRequired,
            ) as exc:
                raise WordPressError(
                    f"Invalid WordPress request configuration for {route}: {exc}"
                ) from exc
            except requests.exceptions.RequestException as exc:
                if write:
                    raise AmbiguousWriteError(
                        f"WordPress {method} transport failed and was not retried "
                        "because the write result is ambiguous.",
                        category=self._transport_category(exc),
                        method=method,
                        route=route,
                    ) from exc
                raise WordPressError(f"WordPress read failed for {route}: {exc}") from exc

            status = int(response.status_code)
            if (
                status == 403
                and mode == "direct"
                and self.rest_mode == "auto"
                and index + 1 < len(modes)
            ):
                continue
            if status >= 400:
                excerpt = str(getattr(response, "text", ""))[:500].replace("\n", " ")
                if write and status in AMBIGUOUS_HTTP_STATUSES:
                    raise AmbiguousWriteError(
                        f"WordPress {method} {route} returned HTTP {status}; "
                        "the write was not retried and requires reconciliation.",
                        category=f"http_{status}",
                        method=method,
                        route=route,
                    )
                raise WordPressError(
                    f"WordPress {method} {route} returned {status}: {excerpt}"
                )
            self.active_mode = mode
            return response
        raise WordPressError(f"No usable WordPress REST route for {route}")

    def response_json(
        self,
        response: requests.Response,
        *,
        method: str,
        route: str,
    ) -> Any:
        try:
            return response.json()
        except (ValueError, json.JSONDecodeError) as exc:
            if method.upper() in WRITE_METHODS:
                raise AmbiguousWriteError(
                    f"WordPress {method.upper()} {route} succeeded at transport "
                    "level but returned an unreadable response. Reconcile before retrying.",
                    category="write_response_unreadable",
                    method=method.upper(),
                    route=route,
                ) from exc
            raise WordPressError(
                f"WordPress {method.upper()} {route} returned invalid JSON."
            ) from exc

    def get_json(
        self,
        route: str,
        params: dict[str, Any] | None = None,
    ) -> Any:
        response = self.request("GET", route, params=params)
        return self.response_json(response, method="GET", route=route)

    def options_json(self, route: str) -> Any:
        response = self.request("OPTIONS", route)
        return self.response_json(response, method="OPTIONS", route=route)

    def post_json(self, route: str, payload: dict[str, Any]) -> Any:
        response = self.request("POST", route, json_body=payload)
        return self.response_json(response, method="POST", route=route)

    def download_binary(self, url: str) -> bytes:
        try:
            response = self.session.request(
                "GET",
                url,
                timeout=self.timeout,
            )
        except requests.exceptions.RequestException as exc:
            raise WordPressError(f"Could not read remote media bytes: {exc}") from exc
        if int(response.status_code) >= 400:
            raise WordPressError(
                f"Remote media returned HTTP {response.status_code}: {url}"
            )
        content = getattr(response, "content", None)
        if content is None:
            content = str(getattr(response, "text", "")).encode("utf-8")
        return bytes(content)

    def preflight(
        self,
        *,
        post_type: str | None = None,
        expected_meta_fields: list[str] | None = None,
    ) -> dict[str, Any]:
        user = self.get_json("users/me", {"context": "edit"})
        media = self.get_json(
            "media",
            {"context": "edit", "per_page": 1, "page": 1},
        )
        report: dict[str, Any] = {
            "status": "passed",
            "passed": True,
            "rest_mode": self.active_mode,
            "user_id": user.get("id"),
            "username": user.get("slug") or user.get("name"),
            "roles": user.get("roles", []),
            "media_readable": isinstance(media, list),
            "errors": [],
            "warnings": [],
        }
        capabilities = user.get("capabilities")
        if isinstance(capabilities, dict):
            required = {
                "edit_posts": bool(capabilities.get("edit_posts")),
                "upload_files": bool(capabilities.get("upload_files")),
            }
            report["capabilities"] = required
            for name, allowed in required.items():
                if not allowed:
                    report["errors"].append(
                        f"Authenticated WordPress user lacks capability: {name}"
                    )

        if post_type:
            posts = self.get_json(
                post_type,
                {
                    "context": "edit",
                    "per_page": 1,
                    "page": 1,
                    "status": "any",
                },
            )
            categories = fetch_collection(self, "categories")
            observed_meta: set[str] = set()
            sample_post_id: int | None = None
            if posts:
                sample_post_id = int(posts[0]["id"])
                detail = self.get_json(
                    f"{post_type}/{sample_post_id}",
                    {"context": "edit"},
                )
                observed_meta.update((detail.get("meta") or {}).keys())

            schema_error = ""
            try:
                options = self.options_json(post_type)
                properties = (
                    options.get("schema", {})
                    .get("properties", {})
                    .get("meta", {})
                    .get("properties", {})
                )
                if isinstance(properties, dict):
                    observed_meta.update(properties.keys())
            except WordPressError as exc:
                schema_error = str(exc)
                report["warnings"].append(
                    "Post OPTIONS schema could not be read; sample post meta "
                    "was used for the SEO field check."
                )

            expected = sorted(
                {
                    str(field)
                    for field in (expected_meta_fields or [])
                    if str(field).strip()
                }
            )
            missing = sorted(set(expected) - observed_meta)
            if missing:
                report["errors"].append(
                    "SEO meta fields are not exposed through REST: "
                    + ", ".join(missing)
                )
            report.update(
                {
                    "posts_readable": isinstance(posts, list),
                    "sample_post_id": sample_post_id,
                    "categories_readable": isinstance(categories, list),
                    "categories": [
                        {
                            "id": int(category["id"]),
                            "name": plain_text(field_value(category, "name")),
                            "slug": str(category.get("slug", "")),
                        }
                        for category in categories
                    ],
                    "seo_meta_schema": {
                        "expected": expected,
                        "observed": sorted(observed_meta),
                        "missing": missing,
                        "options_error": schema_error,
                    },
                }
            )

        report["passed"] = not report["errors"]
        report["status"] = "passed" if report["passed"] else "blocked"
        return report


def client_from_env(
    client_path: Path,
    config: dict[str, Any],
    session: requests.Session | None = None,
) -> WordPressClient:
    env = {**os.environ, **load_env(client_path / ".env")}
    wp_config = config["wordpress"]
    url = env_value(env, wp_config, "url")
    rest_base = env_value(env, wp_config, "rest_base")
    if not url and rest_base:
        url = re.sub(r"/wp-json/wp/v2/?$", "", rest_base.rstrip("/"))
    username = env_value(env, wp_config, "user")
    password = env_value(env, wp_config, "app_password")
    if not url or not username or not password:
        raise WordPressError(
            "WP_URL, WP_USER, and WP_APP_PASSWORD (or configured aliases) "
            "are required in the client .env."
        )

    header_name = env_value(env, wp_config, "bypass_header_name")
    header_value = env_value(env, wp_config, "bypass_header_value")
    bypass_headers = (
        {header_name: header_value}
        if header_name and header_value
        else {}
    )
    lock_timeout = float(
        env_value(
            env,
            wp_config,
            "lock_timeout",
            str(wp_config.get("lock_timeout_seconds", 300)),
        )
    )
    state_paths = wp_config.get("state_paths", {})
    operation_lock = resolve_state_path(
        client_path,
        env_value(
            env,
            wp_config,
            "operation_lock",
            str(state_paths.get("operation_lock", "")),
        ),
        "operation.lock",
    )
    write_lock = resolve_state_path(
        client_path,
        env_value(
            env,
            wp_config,
            "write_lock",
            str(state_paths.get("write_lock", "")),
        ),
        "write.lock",
    )
    write_state = resolve_state_path(
        client_path,
        env_value(
            env,
            wp_config,
            "write_state",
            str(state_paths.get("write_state", "")),
        ),
        "last-write.txt",
    )
    return WordPressClient(
        url,
        username,
        password,
        rest_mode=env_value(
            env,
            wp_config,
            "rest_mode",
            str(wp_config.get("rest_mode", "auto")),
        ).lower(),
        rest_base=rest_base,
        write_interval=float(
            env_value(
                env,
                wp_config,
                "write_interval",
                str(wp_config.get("write_interval_seconds", 25)),
            )
        ),
        timeout=float(
            env_value(
                env,
                wp_config,
                "request_timeout",
                str(wp_config.get("request_timeout_seconds", 45)),
            )
        ),
        query_param=env_value(env, wp_config, "query_param", "t"),
        query_token=env_value(env, wp_config, "query_token"),
        bypass_headers=bypass_headers,
        user_agent=env_value(
            env,
            wp_config,
            "user_agent",
            "rainmojo-so-content-publisher/1.1",
        ),
        operation_lock_path=operation_lock,
        write_lock_path=write_lock,
        write_state_path=write_state,
        lock_timeout=lock_timeout,
        session=session,
    )


def field_value(data: dict[str, Any], key: str) -> str:
    value = data.get(key, "")
    if isinstance(value, dict):
        return str(value.get("raw") or value.get("rendered") or "")
    return str(value or "")


def plain_text(value: str) -> str:
    without_tags = re.sub(r"<[^>]+>", " ", value)
    return " ".join(html.unescape(without_tags).split())


def media_slug(path: Path) -> str:
    return re.sub(r"[^a-z0-9-]+", "-", path.stem.lower()).strip("-")


def media_title_value(media: dict[str, Any]) -> str:
    return plain_text(field_value(media, "title"))


def identity_from_bytes(data: bytes, mime_hint: str = "") -> dict[str, Any]:
    with Image.open(BytesIO(data)) as image:
        width, height = image.size
        detected_mime = Image.MIME.get(image.format or "", "")
    return {
        "sha256": hashlib.sha256(data).hexdigest(),
        "bytes": len(data),
        "width": int(width),
        "height": int(height),
        "mime": (detected_mime or mime_hint or "application/octet-stream").lower(),
    }


def local_media_identity(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    guessed = mimetypes.guess_type(path.name)[0] or ""
    return identity_from_bytes(data, guessed)


def identity_marker(identity: dict[str, Any]) -> str:
    compact = {
        "sha256": identity["sha256"],
        "width": int(identity["width"]),
        "height": int(identity["height"]),
        "mime": str(identity["mime"]).lower(),
    }
    return "<!-- rainmojo-media " + json.dumps(
        compact,
        sort_keys=True,
        separators=(",", ":"),
    ) + " -->"


def parse_identity_marker(description: str) -> dict[str, Any] | None:
    match = IDENTITY_RE.search(description)
    if not match:
        return None
    try:
        parsed = json.loads(match.group(1))
    except json.JSONDecodeError:
        return None
    if not isinstance(parsed, dict) or not parsed.get("sha256"):
        return None
    return {
        "sha256": str(parsed["sha256"]),
        "width": int(parsed.get("width", 0)),
        "height": int(parsed.get("height", 0)),
        "mime": str(parsed.get("mime", "")).lower(),
    }


def media_description_payload(credit: str, identity: dict[str, Any]) -> str:
    marker = identity_marker(identity)
    return (
        f"{html.escape(credit.strip())}\n{marker}"
        if credit.strip()
        else marker
    )


def remote_media_identity(
    wp: WordPressClient,
    media: dict[str, Any],
) -> dict[str, Any]:
    details = media.get("media_details") or {}
    server_width = int(details.get("width") or 0)
    server_height = int(details.get("height") or 0)
    server_mime = str(media.get("mime_type") or "").lower()
    marker = parse_identity_marker(field_value(media, "description"))
    if marker:
        return {
            "sha256": marker["sha256"],
            "bytes": int(details.get("filesize") or 0),
            "width": server_width or int(marker["width"]),
            "height": server_height or int(marker["height"]),
            "mime": server_mime or str(marker["mime"]).lower(),
        }
    source_url = str(media.get("source_url") or "")
    if not source_url:
        raise WordPressError(
            f"Media {media.get('id')} has no identity marker or source URL."
        )
    return identity_from_bytes(wp.download_binary(source_url), server_mime)


def identity_matches(expected: dict[str, Any], actual: dict[str, Any]) -> bool:
    return (
        expected["sha256"] == actual.get("sha256")
        and int(expected["width"]) == int(actual.get("width") or 0)
        and int(expected["height"]) == int(actual.get("height") or 0)
        and str(expected["mime"]).lower() == str(actual.get("mime") or "").lower()
    )


def media_metadata_matches(
    media: dict[str, Any],
    item: dict[str, Any],
    identity: dict[str, Any],
) -> bool:
    caption = plain_text(field_value(media, "caption"))
    description = field_value(media, "description")
    credit = plain_text(description)
    marker = parse_identity_marker(description)
    return bool(
        str(media.get("alt_text") or "") == item["alt"]
        and media_title_value(media) == plain_text(item["title"])
        and caption == plain_text(item.get("caption", ""))
        and (
            not item.get("credit")
            or plain_text(item["credit"]) in credit
        )
        and marker
        and identity_matches(identity, marker)
    )


def _fetch_media_candidate(
    wp: WordPressClient,
    media_id: int,
) -> dict[str, Any] | None:
    try:
        return wp.get_json(f"media/{media_id}", {"context": "edit"})
    except WordPressError as exc:
        if "returned 404" in str(exc):
            return None
        raise


def locate_matching_media(
    wp: WordPressClient,
    path: Path,
    item: dict[str, Any],
    identity: dict[str, Any],
) -> tuple[dict[str, Any] | None, int]:
    slug = media_slug(path)
    candidates: dict[int, dict[str, Any]] = {}
    saved_media_id = item.get("wordpress", {}).get("id")
    if saved_media_id:
        saved = _fetch_media_candidate(wp, int(saved_media_id))
        if saved:
            candidates[int(saved["id"])] = saved
    matches = wp.get_json(
        "media",
        {"context": "edit", "slug": slug, "per_page": 100},
    )
    for candidate in matches:
        candidates[int(candidate["id"])] = candidate
    # An upload whose response was lost may have received a WordPress collision
    # suffix (for example ``-2``). Search by the original stem as a recovery
    # path, then accept only an exact byte/dimension/MIME identity below.
    searched = wp.get_json(
        "media",
        {"context": "edit", "search": path.stem, "per_page": 100},
    )
    for candidate in searched:
        candidates[int(candidate["id"])] = candidate

    exact: list[dict[str, Any]] = []
    inspection_errors: list[str] = []
    for candidate in candidates.values():
        details = candidate.get("media_details") or {}
        width = int(details.get("width") or 0)
        height = int(details.get("height") or 0)
        mime = str(candidate.get("mime_type") or "").lower()
        if width and width != int(identity["width"]):
            continue
        if height and height != int(identity["height"]):
            continue
        if mime and mime != str(identity["mime"]).lower():
            continue
        try:
            remote_identity = remote_media_identity(wp, candidate)
        except WordPressError as exc:
            inspection_errors.append(
                f"media {candidate.get('id')}: {exc}"
            )
            continue
        if identity_matches(identity, remote_identity):
            exact.append(candidate)

    if len(exact) > 1:
        ids = ", ".join(str(candidate["id"]) for candidate in exact)
        raise WordPressError(
            f"Duplicate WordPress media match the same local image identity: {ids}"
        )
    if exact:
        return exact[0], len(candidates)
    if inspection_errors:
        raise WordPressError(
            "Could not safely identify existing media; refusing blind reuse or "
            "duplicate upload. " + "; ".join(inspection_errors)
        )
    return None, len(candidates)


def upload_or_reuse_media(
    wp: WordPressClient,
    path: Path,
    item: dict[str, Any],
) -> dict[str, Any]:
    identity = local_media_identity(path)
    media, slug_conflicts = locate_matching_media(wp, path, item, identity)
    reused = media is not None
    if media is None:
        response = wp.request(
            "POST",
            "media",
            data=path.read_bytes(),
            headers={
                "Content-Type": identity["mime"],
                "Content-Disposition": f'attachment; filename="{path.name}"',
            },
        )
        media = wp.response_json(response, method="POST", route="media")
        if not media.get("id"):
            raise AmbiguousWriteError(
                "WordPress media upload returned no media ID. Reconcile before retrying.",
                category="write_response_missing_id",
                method="POST",
                route="media",
            )

    metadata_payload: dict[str, Any] = {
        "alt_text": item["alt"],
        "title": item["title"],
        "caption": item.get("caption", ""),
        "description": media_description_payload(item.get("credit", ""), identity),
    }
    metadata_updated = False
    if not media_metadata_matches(media, item, identity):
        try:
            media = wp.post_json(f"media/{media['id']}", metadata_payload)
        except AmbiguousWriteError as exc:
            exc.context.update(
                {
                    "resource": "media",
                    "id": int(media["id"]),
                    "slug": str(media.get("slug") or media_slug(path)),
                    "identity": identity,
                }
            )
            raise
        metadata_updated = True

    return {
        "id": int(media["id"]),
        "slug": media.get("slug", media_slug(path)),
        "source_url": media.get("source_url", ""),
        "mime_type": media.get("mime_type", identity["mime"]),
        "reused": reused,
        "metadata_updated": metadata_updated,
        "slug_conflicts": slug_conflicts,
        "alt_text": media.get("alt_text", ""),
        "title": media_title_value(media),
        "caption": plain_text(field_value(media, "caption")),
        "credit": item.get("credit", ""),
        "identity": identity,
    }


def figure_html(
    item: dict[str, Any],
    uploaded: dict[str, Any],
    css_class: str,
) -> str:
    alt = html.escape(item["alt"], quote=True)
    source_url = html.escape(uploaded["source_url"], quote=True)
    width = int(item["width"])
    height = int(item["height"])
    caption_parts = [
        value.strip()
        for value in (item.get("caption", ""), item.get("credit", ""))
        if value and value.strip()
    ]
    figcaption = ""
    if caption_parts:
        figcaption = "<figcaption>" + " ".join(
            html.escape(value) for value in caption_parts
        ) + "</figcaption>"
    return (
        f'<figure class="{html.escape(css_class, quote=True)}">'
        f'<img src="{source_url}" alt="{alt}" width="{width}" height="{height}" '
        'loading="lazy" decoding="async" />'
        f"{figcaption}</figure>"
    )


def _tag_attribute(tag: str, name: str) -> str:
    match = re.search(
        rf"\s{name}\s*=\s*([\"'])(.*?)\1",
        tag,
        flags=re.I | re.S,
    )
    return html.unescape(match.group(2)) if match else ""


def _set_tag_attribute(tag: str, name: str, value: str) -> str:
    pattern = re.compile(
        rf"(\s{name}\s*=\s*)([\"'])(.*?)\2",
        flags=re.I | re.S,
    )
    escaped = html.escape(value, quote=True)
    if pattern.search(tag):
        return pattern.sub(rf'\1"{escaped}"', tag, count=1)
    return tag[:-1] + f' {name}="{escaped}">'


def configured_site_domain(config: dict[str, Any], site_url: str = "") -> str:
    value = (
        config.get("site", {}).get("domain")
        or config.get("wordpress", {}).get("site_url")
        or site_url
    )
    parsed = urlparse(str(value) if "://" in str(value) else f"https://{value}")
    return (parsed.hostname or "").lower().removeprefix("www.")


def external_link_policy(config: dict[str, Any]) -> tuple[bool, list[str]]:
    content_policy = config.get("content", {}).get("external_links", {})
    wp_policy = config.get("wordpress", {}).get("external_link_attributes", {})
    target_blank = bool(
        wp_policy.get(
            "target_blank",
            content_policy.get("target_blank", False),
        )
    )
    rel_value = wp_policy.get("rel", content_policy.get("rel", ""))
    if isinstance(rel_value, str):
        rel = rel_value.split()
    elif isinstance(rel_value, list):
        rel = [str(value) for value in rel_value]
    else:
        rel = []
    return target_blank, list(dict.fromkeys(rel))


def is_external_http_link(url: str, site_domain: str) -> bool:
    parsed = urlparse(html.unescape(url))
    hostname = (parsed.hostname or "").lower().removeprefix("www.")
    if parsed.scheme not in {"http", "https"} or not hostname:
        return False
    return not (
        hostname == site_domain
        or (site_domain and hostname.endswith("." + site_domain))
    )


def apply_external_link_attributes(
    rendered: str,
    config: dict[str, Any],
    site_url: str = "",
) -> str:
    site_domain = configured_site_domain(config, site_url)
    target_blank, required_rel = external_link_policy(config)
    if not target_blank and not required_rel:
        return rendered

    def replace(match: re.Match[str]) -> str:
        tag = match.group(0)
        href = _tag_attribute(tag, "href")
        if not is_external_http_link(href, site_domain):
            return tag
        if target_blank:
            tag = _set_tag_attribute(tag, "target", "_blank")
        if required_rel:
            existing = _tag_attribute(tag, "rel").split()
            merged = list(dict.fromkeys(existing + required_rel))
            tag = _set_tag_attribute(tag, "rel", " ".join(merged))
        return tag

    return ANCHOR_TAG_RE.sub(replace, rendered)


def render_article_content(
    markdown: str,
    image_manifest: dict[str, Any],
    uploaded_media: dict[str, dict[str, Any]],
    config: dict[str, Any],
    site_url: str = "",
) -> str:
    rendered = content_formatter.format_content(
        markdown,
        "html",
        toc=bool(config["content"].get("table_of_contents", False)),
    )
    css_class = config["wordpress"].get(
        "inline_figure_class",
        "rainmojo-inline-image",
    )
    for item in image_manifest.get("items", []):
        if item.get("role") != "inline":
            continue
        image_id = item["id"]
        if image_id not in uploaded_media:
            raise WordPressError(f"Uploaded inline media is missing: {image_id}")
        placeholder = item["placeholder"]
        figure = figure_html(item, uploaded_media[image_id], css_class)
        candidates = [f"<p>{placeholder}</p>", placeholder]
        replaced = False
        for candidate in candidates:
            if candidate in rendered:
                rendered = rendered.replace(candidate, figure, 1)
                replaced = True
                break
        if not replaced:
            raise WordPressError(
                f"Inline placeholder was not found after rendering: {placeholder}"
            )
    if re.search(r"\{\{INLINE_IMAGE_\d+\}\}", rendered):
        raise WordPressError("Unresolved inline image placeholder remains.")
    return apply_external_link_attributes(rendered, config, site_url)


def expected_meta_fields(config: dict[str, Any]) -> list[str]:
    return list(
        dict.fromkeys(
            str(value)
            for value in config.get("seo", {}).get("meta_fields", {}).values()
            if str(value).strip()
        )
    )


def ensure_draft_only(config: dict[str, Any]) -> None:
    wp_config = config["wordpress"]
    if wp_config.get("default_status", "draft") != "draft":
        raise WordPressError("WordPress content production must default to draft.")
    if not config.get("quality_gates", {}).get("draft_only", True):
        raise WordPressError("The content production pipeline must remain draft-only.")


def find_post_matches(
    wp: WordPressClient,
    post_type: str,
    slug: str,
) -> list[dict[str, Any]]:
    items = wp.get_json(
        post_type,
        {
            "slug": slug,
            "status": "any",
            "context": "edit",
            "per_page": 100,
        },
    )
    if len(items) > 1:
        ids = ", ".join(str(item.get("id")) for item in items)
        raise WordPressError(
            f"Multiple WordPress {post_type} records use slug {slug}: {ids}"
        )
    return items


def precheck_existing_post(
    wp: WordPressClient,
    post_type: str,
    article: dict[str, Any],
    *,
    refuse_non_draft: bool = True,
) -> dict[str, Any] | None:
    slug = article["slug"]
    matches = find_post_matches(wp, post_type, slug)
    listed = matches[0] if matches else None
    saved_id = article.get("wordpress", {}).get("post_id")
    saved: dict[str, Any] | None = None
    if saved_id:
        try:
            saved = wp.get_json(
                f"{post_type}/{int(saved_id)}",
                {"context": "edit"},
            )
        except WordPressError as exc:
            if "returned 404" not in str(exc):
                raise
        if saved and saved.get("slug") != slug:
            raise WordPressError(
                f"Saved WordPress post id {saved_id} belongs to slug "
                f"{saved.get('slug')}, not {slug}."
            )
    if listed and saved and int(listed["id"]) != int(saved["id"]):
        raise WordPressError(
            f"Slug {slug} and saved post id {saved_id} identify different posts."
        )
    selected = saved or listed
    if selected:
        selected = wp.get_json(
            f"{post_type}/{int(selected['id'])}",
            {"context": "edit"},
        )
        if refuse_non_draft and selected.get("status") != "draft":
            raise WordPressError(
                f"Refusing to overwrite non-draft post {selected.get('id')} "
                f"with status {selected.get('status')}."
            )
    return selected


def find_post(
    wp: WordPressClient,
    post_type: str,
    slug: str,
) -> dict[str, Any] | None:
    matches = find_post_matches(wp, post_type, slug)
    return matches[0] if matches else None


def _int_list(value: Any) -> list[int]:
    if value in (None, ""):
        return []
    values = value if isinstance(value, list) else [value]
    return [int(item) for item in values]


def _string_list(value: Any) -> list[str]:
    if value in (None, ""):
        return []
    values = value if isinstance(value, list) else [value]
    return [str(item).strip() for item in values if str(item).strip()]


def configured_default_categories(
    config: dict[str, Any],
) -> tuple[list[int], list[str]]:
    wp_config = config["wordpress"]
    ids = _int_list(
        wp_config.get("default_category_ids")
        or wp_config.get("default_category_id")
    )
    names = _string_list(
        wp_config.get("default_category_names")
        or wp_config.get("default_category_name")
    )
    default = wp_config.get("default_category")
    if isinstance(default, dict):
        ids.extend(_int_list(default.get("id") or default.get("ids")))
        names.extend(_string_list(default.get("name") or default.get("names")))
    elif isinstance(default, int):
        ids.append(default)
    elif isinstance(default, str) and default.strip():
        names.append(default.strip())
    return list(dict.fromkeys(ids)), list(dict.fromkeys(names))


def validate_preflight_categories(
    report: dict[str, Any],
    config: dict[str, Any],
) -> None:
    expected_ids, expected_names = configured_default_categories(config)
    categories = report.get("categories", [])
    ids = {int(category["id"]) for category in categories}
    names = {plain_text(str(category["name"])).lower() for category in categories}
    missing_ids = [value for value in expected_ids if value not in ids]
    missing_names = [
        value for value in expected_names
        if plain_text(value).lower() not in names
    ]
    if missing_ids:
        report.setdefault("errors", []).append(
            "Default WordPress category IDs are unavailable: "
            + ", ".join(str(value) for value in missing_ids)
        )
    if missing_names:
        if config["wordpress"].get("create_missing_categories", False):
            report.setdefault("warnings", []).append(
                "Default WordPress categories are missing and will be created "
                "only after the target slug passes the non-draft safety check: "
                + ", ".join(missing_names)
            )
        else:
            report.setdefault("errors", []).append(
                "Default WordPress categories are unavailable: "
                + ", ".join(missing_names)
            )
    report["default_category_check"] = {
        "expected_ids": expected_ids,
        "expected_names": expected_names,
        "missing_ids": missing_ids,
        "missing_names": missing_names,
    }
    report["passed"] = not report.get("errors")
    report["status"] = "passed" if report["passed"] else "blocked"


def fetch_collection(wp: WordPressClient, route: str) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for page in range(1, 101):
        batch = wp.get_json(
            route,
            {"context": "edit", "per_page": 100, "page": page},
        )
        result.extend(batch)
        if len(batch) < 100:
            return result
    raise WordPressError(f"WordPress {route} collection exceeded 10,000 records.")


def taxonomy_slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def resolve_taxonomy(
    wp: WordPressClient,
    article: dict[str, Any],
    config: dict[str, Any],
    *,
    allow_create: bool,
) -> dict[str, list[int]]:
    article_wp = article.setdefault("wordpress", {})
    category_ids = _int_list(article_wp.get("category_ids"))
    category_names = _string_list(
        article_wp.get("category_names")
        or article_wp.get("category_name")
        or article.get("category")
    )
    if not category_ids and not category_names:
        default_ids, default_names = configured_default_categories(config)
        category_ids.extend(default_ids)
        category_names.extend(default_names)

    mapping = config["wordpress"].get("category_map", {})
    mapped_names: list[str] = []
    for name in category_names:
        mapped = (
            mapping.get(name)
            or mapping.get(name.lower())
            or mapping.get(taxonomy_slug(name))
        )
        if isinstance(mapped, int):
            category_ids.append(mapped)
        elif isinstance(mapped, dict):
            category_ids.extend(_int_list(mapped.get("id") or mapped.get("ids")))
            mapped_names.extend(
                _string_list(mapped.get("name") or mapped.get("names"))
            )
        elif isinstance(mapped, str) and mapped.isdigit():
            category_ids.append(int(mapped))
        elif isinstance(mapped, str) and mapped.strip():
            mapped_names.append(mapped.strip())
        else:
            mapped_names.append(name)
    category_names = mapped_names

    if category_ids or category_names:
        categories = fetch_collection(wp, "categories")
        by_id = {int(category["id"]): category for category in categories}
        for category_id in category_ids:
            if category_id not in by_id:
                raise WordPressError(
                    f"Configured WordPress category id does not exist: {category_id}"
                )
        for name in category_names:
            normalized = plain_text(name).lower()
            slug = taxonomy_slug(name)
            matches = [
                category
                for category in categories
                if plain_text(field_value(category, "name")).lower() == normalized
                or str(category.get("slug", "")).lower() == slug
            ]
            unique = {int(category["id"]): category for category in matches}
            if len(unique) > 1:
                raise WordPressError(
                    f"Multiple WordPress categories match {name}: "
                    + ", ".join(str(value) for value in sorted(unique))
                )
            if unique:
                category_ids.append(next(iter(unique)))
            elif allow_create and config["wordpress"].get(
                "create_missing_categories",
                False,
            ):
                created = wp.post_json(
                    "categories",
                    {"name": name, "slug": slug},
                )
                if not created.get("id"):
                    raise AmbiguousWriteError(
                        f"Category creation returned no ID for {name}.",
                        category="write_response_missing_id",
                        method="POST",
                        route="categories",
                    )
                category_ids.append(int(created["id"]))
            else:
                raise WordPressError(
                    f"WordPress category does not exist and auto-create is disabled: {name}"
                )

    tag_ids = _int_list(article_wp.get("tag_ids"))
    for tag_id in tag_ids:
        wp.get_json(f"tags/{tag_id}", {"context": "edit"})
    return {
        "category_ids": list(dict.fromkeys(category_ids)),
        "tag_ids": list(dict.fromkeys(tag_ids)),
    }


def build_post_payload(
    article: dict[str, Any],
    content_html: str,
    featured_media_id: int,
    config: dict[str, Any],
    taxonomy: dict[str, list[int]] | None = None,
) -> dict[str, Any]:
    ensure_draft_only(config)
    payload: dict[str, Any] = {
        "title": article["title"],
        "slug": article["slug"],
        "content": content_html,
        "status": "draft",
        "featured_media": int(featured_media_id),
    }
    taxonomy = taxonomy or {
        "category_ids": _int_list(
            article.get("wordpress", {}).get("category_ids")
        ),
        "tag_ids": _int_list(article.get("wordpress", {}).get("tag_ids")),
    }
    if taxonomy["category_ids"]:
        payload["categories"] = taxonomy["category_ids"]
    if taxonomy["tag_ids"]:
        payload["tags"] = taxonomy["tag_ids"]

    meta_fields = config["seo"]["meta_fields"]
    seo = article.get("seo", {})
    meta: dict[str, str] = {}
    for logical_name, article_key in (
        ("title", "title"),
        ("description", "description"),
        ("focus_keyword", "focus_keyword"),
        ("canonical", "canonical"),
    ):
        field_name = str(meta_fields.get(logical_name, "")).strip()
        value = str(seo.get(article_key, "")).strip()
        if field_name and value:
            meta[field_name] = value
    if meta:
        payload["meta"] = meta
    return payload


class LinkCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[dict[str, str]] = []

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        if tag.lower() != "a":
            return
        values = {name.lower(): value or "" for name, value in attrs}
        self.links.append(values)


def collect_links(content: str) -> list[dict[str, str]]:
    parser = LinkCollector()
    parser.feed(content)
    return parser.links


def canonical_html(value: str) -> str:
    normalized = value.replace("\r\n", "\n").replace("\r", "\n")
    normalized = "\n".join(line.rstrip() for line in normalized.splitlines())
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)
    return normalized.strip()


def article_required_urls(article: dict[str, Any]) -> list[str]:
    urls: list[str] = []
    for values in article.get("links", {}).values():
        if not isinstance(values, list):
            continue
        for value in values:
            if isinstance(value, str):
                urls.append(value)
            elif isinstance(value, dict) and value.get("url"):
                urls.append(str(value["url"]))
    return list(dict.fromkeys(urls))


def verify_publication(
    wp: WordPressClient,
    post_type: str,
    post_id: int,
    article: dict[str, Any],
    payload: dict[str, Any],
    image_manifest: dict[str, Any],
    uploaded_media: dict[str, dict[str, Any]],
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    config = config or {
        "site": {"domain": ""},
        "content": {"external_links": {}},
        "wordpress": {"external_link_attributes": {}},
    }
    post = wp.get_json(f"{post_type}/{post_id}", {"context": "edit"})
    errors: list[str] = []
    checks: dict[str, bool] = {}

    checks["status_draft"] = post.get("status") == "draft"
    checks["slug_matches"] = post.get("slug") == article["slug"]
    checks["title_matches"] = (
        plain_text(field_value(post, "title")) == plain_text(article["title"])
    )
    for name, passed in (
        ("status", checks["status_draft"]),
        ("slug", checks["slug_matches"]),
        ("title", checks["title_matches"]),
    ):
        if not passed:
            errors.append(f"Post {name} did not verify.")

    featured_id = int(uploaded_media["featured"]["id"])
    checks["featured_media_matches"] = (
        int(post.get("featured_media") or 0) == featured_id
    )
    if not checks["featured_media_matches"]:
        errors.append("Featured media does not match the expected featured image.")

    content_value = field_value(post, "content")
    expected_content = str(payload["content"])
    checks["full_content_matches"] = (
        canonical_html(content_value) == canonical_html(expected_content)
    )
    if not checks["full_content_matches"]:
        errors.append("Full post content does not match the rendered package.")

    expected_links = collect_links(expected_content)
    actual_links = collect_links(content_value)
    expected_hrefs = Counter(link.get("href", "") for link in expected_links)
    actual_hrefs = Counter(link.get("href", "") for link in actual_links)
    checks["all_rendered_links_match"] = expected_hrefs == actual_hrefs
    if not checks["all_rendered_links_match"]:
        errors.append("Rendered link set or duplicate counts do not match.")
    required_urls = article_required_urls(article)
    actual_canonical_urls = {
        content_pipeline.canonical_url(url, wp.base_url)
        for url in actual_hrefs
        if url
    }
    checks["required_article_links_present"] = all(
        content_pipeline.canonical_url(url, wp.base_url) in actual_canonical_urls
        for url in required_urls
    )
    if not checks["required_article_links_present"]:
        errors.append("One or more article link-plan URLs are missing.")

    site_domain = configured_site_domain(config, wp.base_url)
    target_blank, required_rel = external_link_policy(config)
    external_attr_errors: list[str] = []
    for link in actual_links:
        href = link.get("href", "")
        if not is_external_http_link(href, site_domain):
            continue
        if target_blank and link.get("target") != "_blank":
            external_attr_errors.append(f"{href}: target=_blank missing")
        rel_tokens = set(link.get("rel", "").split())
        missing_rel = [value for value in required_rel if value not in rel_tokens]
        if missing_rel:
            external_attr_errors.append(
                f"{href}: rel tokens missing {', '.join(missing_rel)}"
            )
    checks["external_link_attributes_match"] = not external_attr_errors
    errors.extend(external_attr_errors)

    for field, payload_key in (("categories", "categories"), ("tags", "tags")):
        if payload_key in payload:
            passed = sorted(int(value) for value in post.get(field, [])) == sorted(
                int(value) for value in payload[payload_key]
            )
            checks[f"{field}_match"] = passed
            if not passed:
                errors.append(f"Post {field} did not verify.")

    expected_meta = payload.get("meta", {})
    returned_meta = post.get("meta", {}) or {}
    meta_errors = [
        key for key, value in expected_meta.items()
        if returned_meta.get(key) != value
    ]
    checks["seo_meta_matches"] = not meta_errors
    errors.extend(f"SEO meta field did not verify: {key}" for key in meta_errors)

    media_reports: list[dict[str, Any]] = []
    for item in image_manifest.get("items", []):
        uploaded = uploaded_media[item["id"]]
        media = wp.get_json(f"media/{uploaded['id']}", {"context": "edit"})
        media_errors: list[str] = []
        if media.get("alt_text", "") != item["alt"]:
            media_errors.append("alt_text mismatch")
        if media_title_value(media) != plain_text(item["title"]):
            media_errors.append("media title mismatch")
        if plain_text(field_value(media, "caption")) != plain_text(
            item.get("caption", "")
        ):
            media_errors.append("caption mismatch")
        if item.get("credit") and plain_text(item["credit"]) not in plain_text(
            field_value(media, "description")
        ):
            media_errors.append("credit mismatch")
        expected_identity = uploaded.get("identity")
        try:
            actual_identity = remote_media_identity(wp, media)
        except WordPressError as exc:
            actual_identity = {}
            media_errors.append(f"identity unreadable: {exc}")
        if expected_identity and not identity_matches(
            expected_identity,
            actual_identity,
        ):
            media_errors.append("hash, dimensions, or MIME identity mismatch")
        if str(media.get("source_url") or "") != str(uploaded.get("source_url") or ""):
            media_errors.append("source URL mismatch")
        media_reports.append(
            {
                "image_id": item["id"],
                "media_id": uploaded["id"],
                "source_url": media.get("source_url", ""),
                "expected_identity": expected_identity,
                "actual_identity": actual_identity,
                "errors": media_errors,
                "passed": not media_errors,
            }
        )
        errors.extend(f"{item['id']}: {error}" for error in media_errors)

    return {
        "post_id": post_id,
        "post_url": post.get("link", ""),
        "status": post.get("status"),
        "checks": checks,
        "media": media_reports,
        "errors": errors,
        "passed": not errors,
    }


def write_publish_report(
    package: Path,
    report: dict[str, Any],
) -> None:
    content_pipeline.write_json(
        package / "reports" / "wordpress-publish.json",
        report,
    )


def publish_draft(
    client_value: str | Path,
    slug: str,
    *,
    dry_run: bool = False,
    session: requests.Session | None = None,
) -> dict[str, Any]:
    client_path = content_pipeline.resolve_client(client_value)
    package, article = content_pipeline.read_package(client_path, slug)
    config = content_pipeline.load_effective_config(
        client_path,
        package,
        article,
    )
    ensure_draft_only(config)
    validation = content_pipeline.validate_package(client_path, slug, "publish")
    if not validation["passed"]:
        raise WordPressError(
            "Publish validation failed: " + "; ".join(validation["errors"])
        )
    if article.get("status") == "images_qa_passed" and not dry_run:
        article = content_pipeline.set_status(
            client_path,
            slug,
            "publish_ready",
            "Publish-stage validation passed; package released to draft publisher.",
        )
    manifest_path = content_pipeline.safe_path(package, article["images_file"])
    image_manifest = content_pipeline.load_json(manifest_path)
    markdown = content_pipeline.safe_path(
        package,
        article["content_file"],
    ).read_text(encoding="utf-8")

    if dry_run:
        report = {
            "checked_at": content_pipeline.now_iso(),
            "slug": slug,
            "status": "dry_run",
            "post_type": article["wordpress"]["post_type"],
            "media": [
                {
                    "image_id": item["id"],
                    "file": item["output"],
                    "alt": item["alt"],
                    "title": item["title"],
                    "caption": item.get("caption", ""),
                    "credit": item.get("credit", ""),
                    "identity": local_media_identity(
                        content_pipeline.safe_path(package, item["output"])
                    ),
                }
                for item in image_manifest.get("items", [])
            ],
            "passed": True,
        }
        write_publish_report(package, report)
        return report

    wp = client_from_env(client_path, config, session=session)
    post_type = article.get("wordpress", {}).get(
        "post_type",
        config["wordpress"]["post_type"],
    )
    with wp.operation_lock():
        try:
            preflight = wp.preflight(
                post_type=post_type,
                expected_meta_fields=expected_meta_fields(config),
            )
            validate_preflight_categories(preflight, config)
            if not preflight["passed"]:
                raise WordPressError(
                    "WordPress preflight blocked publishing: "
                    + "; ".join(preflight["errors"])
                )

            existing = precheck_existing_post(
                wp,
                post_type,
                article,
                refuse_non_draft=config["wordpress"].get(
                    "refuse_non_draft_overwrite",
                    True,
                ),
            )
            taxonomy = resolve_taxonomy(
                wp,
                article,
                config,
                allow_create=True,
            )

            uploaded_media: dict[str, dict[str, Any]] = {}
            current_item: dict[str, Any] | None = None
            for item in image_manifest.get("items", []):
                current_item = item
                output_path = content_pipeline.safe_path(package, item["output"])
                uploaded = upload_or_reuse_media(wp, output_path, item)
                uploaded_media[item["id"]] = uploaded
                item["wordpress"] = uploaded
                content_pipeline.write_json(manifest_path, image_manifest)

            if "featured" not in uploaded_media:
                raise WordPressError("Featured image was not uploaded.")
            content_html = render_article_content(
                markdown,
                image_manifest,
                uploaded_media,
                config,
                wp.base_url,
            )
            payload = build_post_payload(
                article,
                content_html,
                uploaded_media["featured"]["id"],
                config,
                taxonomy,
            )
            if existing:
                saved = wp.post_json(f"{post_type}/{existing['id']}", payload)
                operation = "updated"
            else:
                saved = wp.post_json(post_type, payload)
                operation = "created"
            if not saved.get("id"):
                raise AmbiguousWriteError(
                    "WordPress post write returned no post ID. Reconcile before retrying.",
                    category="write_response_missing_id",
                    method="POST",
                    route=post_type,
                )

            post_id = int(saved["id"])
            article.setdefault("wordpress", {})["post_id"] = post_id
            article["wordpress"]["media_ids"] = {
                key: value["id"] for key, value in uploaded_media.items()
            }
            article["wordpress"]["category_ids"] = taxonomy["category_ids"]
            article["wordpress"]["tag_ids"] = taxonomy["tag_ids"]
            content_pipeline.write_json(package / "article.json", article)
            content_pipeline.set_status(
                client_path,
                slug,
                "draft_uploaded",
                f"WordPress draft {operation} with post id {post_id}.",
            )

            verification = verify_publication(
                wp,
                post_type,
                post_id,
                article,
                payload,
                image_manifest,
                uploaded_media,
                config,
            )
            report = {
                "checked_at": content_pipeline.now_iso(),
                "slug": slug,
                "operation": operation,
                "rest_mode": wp.active_mode,
                "preflight": preflight,
                "taxonomy": taxonomy,
                "verification": verification,
                "passed": verification["passed"],
            }
            write_publish_report(package, report)
            if verification["passed"]:
                content_pipeline.set_status(
                    client_path,
                    slug,
                    "verified",
                    f"WordPress draft {post_id} and media verified through REST.",
                )
            else:
                raise WordPressError(
                    "WordPress verification failed: "
                    + "; ".join(verification["errors"])
                )
            return report
        except AmbiguousWriteError as exc:
            if (
                exc.context.get("resource") == "media"
                and "current_item" in locals()
                and current_item is not None
            ):
                current_item["wordpress"] = {
                    "id": exc.context.get("id"),
                    "slug": exc.context.get("slug", ""),
                    "identity": exc.context.get("identity", {}),
                    "reconcile_required": True,
                }
                content_pipeline.write_json(manifest_path, image_manifest)
            report = {
                "checked_at": content_pipeline.now_iso(),
                "slug": slug,
                "status": "reconcile_required",
                "rest_mode": wp.active_mode,
                "ambiguous_write": exc.as_dict(),
                "recovery": (
                    "Run verify-only (or reconcile) for this slug. "
                    "Do not retry publish-draft until reconciliation completes."
                ),
                "passed": False,
            }
            write_publish_report(package, report)
            raise


def validate_recovery_package(
    client_path: Path,
    slug: str,
    article: dict[str, Any],
    config: dict[str, Any],
) -> None:
    ensure_draft_only(config)
    validation = content_pipeline.validate_package(client_path, slug, "images")
    if not validation["passed"]:
        raise WordPressError(
            "Recovery package validation failed: "
            + "; ".join(validation["errors"])
        )
    if article.get("status") not in {
        "publish_ready",
        "draft_uploaded",
        "verified",
    }:
        raise WordPressError(
            f"Article status {article.get('status')} cannot be reconciled."
        )
    if not article.get("seo", {}).get("title", "").strip():
        raise WordPressError("SEO title is missing.")
    if not article.get("seo", {}).get("description", "").strip():
        raise WordPressError("SEO description is missing.")


def verify_only(
    client_value: str | Path,
    slug: str,
    *,
    session: requests.Session | None = None,
    operation: str = "verify_only",
) -> dict[str, Any]:
    client_path = content_pipeline.resolve_client(client_value)
    package, article = content_pipeline.read_package(client_path, slug)
    config = content_pipeline.load_effective_config(
        client_path,
        package,
        article,
    )
    validate_recovery_package(client_path, slug, article, config)
    manifest_path = content_pipeline.safe_path(package, article["images_file"])
    image_manifest = content_pipeline.load_json(manifest_path)
    markdown = content_pipeline.safe_path(
        package,
        article["content_file"],
    ).read_text(encoding="utf-8")
    wp = client_from_env(client_path, config, session=session)
    post_type = article.get("wordpress", {}).get(
        "post_type",
        config["wordpress"]["post_type"],
    )

    with wp.operation_lock():
        preflight = wp.preflight(
            post_type=post_type,
            expected_meta_fields=expected_meta_fields(config),
        )
        validate_preflight_categories(preflight, config)
        if not preflight["passed"]:
            raise WordPressError(
                "WordPress preflight blocked verification: "
                + "; ".join(preflight["errors"])
            )
        existing = precheck_existing_post(
            wp,
            post_type,
            article,
            refuse_non_draft=True,
        )
        if not existing:
            if operation == "reconcile" and article.get("status") == "publish_ready":
                recovered_media: dict[str, dict[str, Any]] = {}
                missing_media: list[str] = []
                for item in image_manifest.get("items", []):
                    output_path = content_pipeline.safe_path(
                        package,
                        item["output"],
                    )
                    identity = local_media_identity(output_path)
                    media, _conflicts = locate_matching_media(
                        wp,
                        output_path,
                        item,
                        identity,
                    )
                    if media is None:
                        missing_media.append(item["id"])
                        continue
                    recovered = {
                        "id": int(media["id"]),
                        "slug": media.get("slug", media_slug(output_path)),
                        "source_url": media.get("source_url", ""),
                        "mime_type": media.get("mime_type", identity["mime"]),
                        "reused": True,
                        "metadata_updated": False,
                        "identity": identity,
                    }
                    recovered_media[item["id"]] = recovered
                    item["wordpress"] = recovered
                article.setdefault("wordpress", {})["post_id"] = None
                article["wordpress"]["media_ids"] = {
                    key: value["id"] for key, value in recovered_media.items()
                }
                content_pipeline.write_json(manifest_path, image_manifest)
                content_pipeline.write_json(package / "article.json", article)
                report = {
                    "checked_at": content_pipeline.now_iso(),
                    "slug": slug,
                    "operation": operation,
                    "status": "safe_to_retry_publish",
                    "rest_mode": wp.active_mode,
                    "preflight": preflight,
                    "confirmed_no_post": True,
                    "recovered_media": recovered_media,
                    "missing_media": missing_media,
                    "safe_to_retry_publish": True,
                    "wordpress_writes": 0,
                    "passed": True,
                }
                write_publish_report(package, report)
                return report
            raise WordPressError(
                f"No WordPress draft exists for slug {article['slug']}."
            )
        taxonomy = resolve_taxonomy(
            wp,
            article,
            config,
            allow_create=False,
        )
        uploaded_media: dict[str, dict[str, Any]] = {}
        for item in image_manifest.get("items", []):
            output_path = content_pipeline.safe_path(package, item["output"])
            identity = local_media_identity(output_path)
            media, _conflicts = locate_matching_media(
                wp,
                output_path,
                item,
                identity,
            )
            if media is None:
                raise WordPressError(
                    f"No exact WordPress media identity matches {item['id']}."
                )
            uploaded = {
                "id": int(media["id"]),
                "slug": media.get("slug", media_slug(output_path)),
                "source_url": media.get("source_url", ""),
                "mime_type": media.get("mime_type", identity["mime"]),
                "reused": True,
                "metadata_updated": False,
                "identity": identity,
            }
            uploaded_media[item["id"]] = uploaded
            item["wordpress"] = uploaded

        if "featured" not in uploaded_media:
            raise WordPressError("Featured media could not be reconciled.")
        content_html = render_article_content(
            markdown,
            image_manifest,
            uploaded_media,
            config,
            wp.base_url,
        )
        payload = build_post_payload(
            article,
            content_html,
            uploaded_media["featured"]["id"],
            config,
            taxonomy,
        )
        post_id = int(existing["id"])
        verification = verify_publication(
            wp,
            post_type,
            post_id,
            article,
            payload,
            image_manifest,
            uploaded_media,
            config,
        )
        report = {
            "checked_at": content_pipeline.now_iso(),
            "slug": slug,
            "operation": operation,
            "rest_mode": wp.active_mode,
            "preflight": preflight,
            "taxonomy": taxonomy,
            "verification": verification,
            "passed": verification["passed"],
        }
        write_publish_report(package, report)
        if not verification["passed"]:
            raise WordPressError(
                "WordPress reconciliation failed: "
                + "; ".join(verification["errors"])
            )

        article.setdefault("wordpress", {})["post_id"] = post_id
        article["wordpress"]["media_ids"] = {
            key: value["id"] for key, value in uploaded_media.items()
        }
        article["wordpress"]["category_ids"] = taxonomy["category_ids"]
        article["wordpress"]["tag_ids"] = taxonomy["tag_ids"]
        content_pipeline.write_json(manifest_path, image_manifest)
        content_pipeline.write_json(package / "article.json", article)
        if article.get("status") == "publish_ready":
            content_pipeline.set_status(
                client_path,
                slug,
                "draft_uploaded",
                f"WordPress draft {post_id} recovered after an ambiguous write.",
            )
        if article.get("status") != "verified":
            content_pipeline.set_status(
                client_path,
                slug,
                "verified",
                f"WordPress draft {post_id} reconciled and verified without writes.",
            )
        return report


def command_preflight(args: argparse.Namespace) -> int:
    client_path = content_pipeline.resolve_client(args.client)
    config = content_pipeline.load_client_config(client_path)
    ensure_draft_only(config)
    post_type = config["wordpress"]["post_type"]
    report = client_from_env(client_path, config).preflight(
        post_type=post_type,
        expected_meta_fields=expected_meta_fields(config),
    )
    validate_preflight_categories(report, config)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["passed"] else 2


def command_publish(args: argparse.Namespace) -> int:
    report = publish_draft(args.client, args.slug, dry_run=args.dry_run)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["passed"] else 2


def command_verify(args: argparse.Namespace) -> int:
    report = verify_only(
        args.client,
        args.slug,
        operation=args.command.replace("-", "_"),
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["passed"] else 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    preflight = sub.add_parser(
        "preflight",
        help="Verify authenticated posts, media, categories, and SEO REST schema.",
    )
    preflight.add_argument("--client", required=True)
    preflight.set_defaults(func=command_preflight)

    publish = sub.add_parser(
        "publish-draft",
        help="Upload media and create or update one verified draft.",
    )
    publish.add_argument("--client", required=True)
    publish.add_argument("--slug", required=True)
    publish.add_argument("--dry-run", action="store_true")
    publish.set_defaults(func=command_publish)

    for name in ("verify-only", "reconcile"):
        verify = sub.add_parser(
            name,
            help="Read WordPress state, reconcile local IDs, and verify without writes.",
        )
        verify.add_argument("--client", required=True)
        verify.add_argument("--slug", required=True)
        verify.set_defaults(func=command_verify)
    return parser


def _self_test_hook() -> None:
    if "--self-test" in sys.argv[1:]:
        raise SystemExit(_self_test())


def main() -> int:
    _self_test_hook()
    args = build_parser().parse_args()
    try:
        return int(args.func(args))
    except AmbiguousWriteError as exc:
        print(
            "ERROR: "
            + str(exc)
            + " Run verify-only or reconcile before any publish retry.",
            file=sys.stderr,
        )
        return 3
    except (
        OSError,
        RuntimeError,
        ValueError,
        json.JSONDecodeError,
        WordPressError,
    ) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2



def _self_test() -> int:
    """Pure helpers: draft-only gate, external link detection, media slug, identity."""
    ensure_draft_only({"wordpress": {"default_status": "draft"}, "quality_gates": {"draft_only": True}})
    try:
        ensure_draft_only({"wordpress": {"default_status": "publish"}, "quality_gates": {"draft_only": True}})
        raise AssertionError("publish default must raise")
    except WordPressError:
        pass
    assert is_external_http_link("https://other.example/x", "example.com")
    assert not is_external_http_link("https://example.com/x", "example.com")
    assert plain_text("<b>Hello</b> world") == "Hello world"
    assert media_slug(Path("Photo Of Clinic.jpg"))
    import io
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (2, 2), (255, 255, 255)).save(buf, format="PNG")
    ident = identity_from_bytes(buf.getvalue(), "image/png")
    assert isinstance(ident, dict) and ident
    print("SELF-TEST PASS: draft-only gate, external links, media helpers")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
