#!/usr/bin/env python3
"""Process article image manifests with exact sizing, logo policy, and metadata QA."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

try:
    from PIL import Image, ImageDraw, ImageFont, ImageOps
except ImportError:
    print("ERROR: Pillow is required. Install with: pip install Pillow", file=sys.stderr)
    raise SystemExit(1)

import content_pipeline


PROVENANCE_SNAPSHOT_FIELDS = (
    "source_type",
    "provider",
    "source_url",
    "rights_record",
    "license_record",
    "generation_notes",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def provenance_snapshot(item: dict[str, Any]) -> dict[str, str]:
    provenance = item.get("provenance")
    if not isinstance(provenance, dict):
        raise RuntimeError(f"{item.get('id')}: provenance record is missing.")
    return {
        key: str(provenance.get(key, "")).strip()
        for key in PROVENANCE_SNAPSHOT_FIELDS
    }


def source_identity(path: Path, package: Path) -> dict[str, Any]:
    with Image.open(path) as image:
        image.load()
        width, height = image.size
        image_format = image.format or ""
    return {
        "path": str(path.relative_to(package)).replace("\\", "/"),
        "sha256": sha256_file(path),
        "bytes": path.stat().st_size,
        "width": width,
        "height": height,
        "format": image_format,
    }


def webp_chunks(path: Path) -> list[str]:
    data = path.read_bytes()
    if len(data) < 12 or data[:4] != b"RIFF" or data[8:12] != b"WEBP":
        return []
    chunks: list[str] = []
    offset = 12
    while offset + 8 <= len(data):
        fourcc = data[offset : offset + 4].decode("ascii", errors="replace")
        size = int.from_bytes(data[offset + 4 : offset + 8], "little")
        chunks.append(fourcc)
        offset += 8 + size + (size % 2)
    return chunks


def load_effective_config(
    client: Path,
    package: Path,
    article: dict[str, Any],
) -> dict[str, Any]:
    for loader_name in ("load_package_config", "load_effective_config"):
        loader = getattr(content_pipeline, loader_name, None)
        if callable(loader):
            return loader(client, package, article)
    frozen = package / "resolved-config.json"
    if frozen.exists():
        config = content_pipeline.load_json(frozen)
    else:
        config = content_pipeline.load_client_config(client)
    article_override = article.get(
        "config_overrides",
        article.get("config_override", {}),
    )
    if article_override:
        config = content_pipeline.deep_merge(config, article_override)
    return config


def validate_provenance(item: dict[str, Any], config: dict[str, Any]) -> None:
    metadata = config["images"].get("metadata", {})
    if not metadata.get("internal_provenance_sidecar", True):
        return
    provenance = item.get("provenance")
    if not isinstance(provenance, dict):
        raise RuntimeError(f"{item.get('id')}: provenance record is missing.")
    source_type = str(provenance.get("source_type", "")).strip().lower()
    provider = str(provenance.get("provider", "")).strip()
    if not source_type or not provider:
        raise RuntimeError(
            f"{item.get('id')}: provenance requires source_type and provider."
        )
    if not str(provenance.get("rights_record", "")).strip():
        raise RuntimeError(
            f"{item.get('id')}: provenance requires a rights_record."
        )
    if source_type in {"licensed", "stock", "third_party"} and not str(
        provenance.get("license_record", "")
    ).strip():
        raise RuntimeError(
            f"{item.get('id')}: licensed sources require an internal license record."
        )
    if source_type in {"generated", "ai_generated"} and not str(
        provenance.get("generation_notes", "")
    ).strip():
        raise RuntimeError(
            f"{item.get('id')}: generated sources require generation notes."
        )


def visual_mode(item: dict[str, Any], role_config: dict[str, Any]) -> str:
    mode = str(
        item.get("visual_mode")
        or role_config.get("visual_mode")
        or role_config.get("asset_type")
        or ""
    ).strip()
    allowed = role_config.get("allowed_visual_modes", [])
    if isinstance(allowed, str):
        allowed = [allowed]
    if allowed and mode not in allowed:
        raise RuntimeError(
            f"{item.get('id')}: visual mode {mode!r} is not allowed for this role."
        )
    return mode


def wrap_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.ImageFont,
    max_width: int,
) -> list[str]:
    words = text.split()
    if not words:
        return []
    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        candidate = current + " " + word
        if draw.textbbox((0, 0), candidate, font=font)[2] <= max_width:
            current = candidate
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def apply_text_overlays(
    image: Image.Image,
    client: Path,
    item: dict[str, Any],
    config: dict[str, Any],
) -> tuple[Image.Image, list[dict[str, Any]]]:
    overlays = item.get("text_overlays") or []
    if not overlays:
        return image, []
    mode = str(item.get("visual_mode", "")).lower()
    if "infographic" not in mode:
        raise RuntimeError(
            f"{item.get('id')}: deterministic text is allowed only in an "
            "infographic visual mode."
        )
    infographic = config["images"].get("infographic", {})
    if not infographic.get("allowed", False):
        raise RuntimeError(
            f"{item.get('id')}: text overlays require an enabled infographic workflow."
        )
    language = str(infographic.get("language", "English")).lower()
    canvas = image.convert("RGBA")
    draw = ImageDraw.Draw(canvas)
    reports: list[dict[str, Any]] = []
    for index, overlay in enumerate(overlays, 1):
        text = str(overlay.get("text", "")).strip()
        if not text:
            raise RuntimeError(f"{item.get('id')}: text overlay {index} is empty.")
        if language == "english" and not text.isascii():
            raise RuntimeError(
                f"{item.get('id')}: infographic text must be English-only."
            )
        font_path_value = str(
            overlay.get("font_path") or infographic.get("font_path") or ""
        ).strip()
        font_size = max(
            10,
            int(
                overlay.get(
                    "font_size_px",
                    round(image.height * float(overlay.get("font_size_ratio", 0.04))),
                )
            ),
        )
        if font_path_value:
            font_path = content_pipeline.safe_path(client, font_path_value)
            if not font_path.exists():
                raise RuntimeError(f"Approved infographic font not found: {font_path}")
            font = ImageFont.truetype(str(font_path), font_size)
        else:
            try:
                font = ImageFont.truetype("DejaVuSans.ttf", font_size)
            except OSError:
                font = ImageFont.load_default()
        x = round(image.width * float(overlay.get("x_ratio", 0.05)))
        y = round(image.height * float(overlay.get("y_ratio", 0.05)))
        max_width = round(
            image.width * float(overlay.get("max_width_ratio", 0.9))
        )
        line_spacing = max(1, int(overlay.get("line_spacing_px", font_size * 0.25)))
        fill = str(overlay.get("fill", "#000000"))
        stroke_fill = str(overlay.get("stroke_fill", "#FFFFFF"))
        stroke_width = max(0, int(overlay.get("stroke_width", 0)))
        lines = wrap_text(draw, text, font, max_width)
        for line in lines:
            draw.text(
                (x, y),
                line,
                font=font,
                fill=fill,
                stroke_fill=stroke_fill,
                stroke_width=stroke_width,
            )
            box = draw.textbbox((x, y), line, font=font, stroke_width=stroke_width)
            y = box[3] + line_spacing
        reports.append(
            {
                "index": index,
                "text": text,
                "language": infographic.get("language", "English"),
                "deterministic": True,
            }
        )
    return canvas.convert("RGB"), reports


def should_apply_logo(policy: dict[str, Any], role: str) -> bool:
    apply_to = policy.get("apply_to", [])
    if isinstance(apply_to, str):
        apply_to = [apply_to]
    if not policy.get("allowed", True):
        if policy.get("required") or apply_to:
            raise RuntimeError(
                "Logo policy cannot request an overlay while logos are disallowed."
            )
        return False
    return bool(
        policy.get("required")
        or "all" in apply_to
        or role in apply_to
    )


def fit_image(
    image: Image.Image,
    width: int,
    height: int,
    fit: str,
    allow_upscale: bool,
) -> Image.Image:
    source = image.convert("RGB")
    if not allow_upscale and (source.width < width or source.height < height):
        raise RuntimeError(
            f"Source image {source.width}x{source.height} is below required "
            f"{width}x{height}; upscaling is disabled."
        )
    if fit == "cover":
        return ImageOps.fit(
            source,
            (width, height),
            method=Image.Resampling.LANCZOS,
            centering=(0.5, 0.5),
        )
    if fit == "contain":
        contained = ImageOps.contain(
            source,
            (width, height),
            method=Image.Resampling.LANCZOS,
        )
        canvas = Image.new("RGB", (width, height), "white")
        x = (width - contained.width) // 2
        y = (height - contained.height) // 2
        canvas.paste(contained, (x, y))
        return canvas
    raise RuntimeError(f"Unsupported image fit mode: {fit}")


def logo_geometry(
    image: Image.Image,
    logo: Image.Image,
    policy: dict[str, Any],
) -> dict[str, int]:
    target_width = round(image.width * float(policy.get("width_ratio", 0.1)))
    target_width = max(int(policy.get("min_width_px", 1)), target_width)
    target_width = min(int(policy.get("max_width_px", image.width)), target_width)
    target_height = max(1, round(logo.height * target_width / logo.width))
    margin_x = max(1, round(image.width * float(policy.get("margin_x_ratio", 0.03))))
    margin_y = max(1, round(image.height * float(policy.get("margin_y_ratio", 0.03))))
    placement = policy.get("placement", "top-right")
    positions = {
        "top-left": (margin_x, margin_y),
        "top-right": (image.width - target_width - margin_x, margin_y),
        "bottom-left": (margin_x, image.height - target_height - margin_y),
        "bottom-right": (
            image.width - target_width - margin_x,
            image.height - target_height - margin_y,
        ),
    }
    if placement not in positions:
        raise RuntimeError(f"Unsupported logo placement: {placement}")
    x, y = positions[placement]
    if x < 0 or y < 0:
        raise RuntimeError("Configured logo is too large for the output image.")
    return {
        "x": x,
        "y": y,
        "width": target_width,
        "height": target_height,
        "margin_x": margin_x,
        "margin_y": margin_y,
    }


def apply_logo(
    image: Image.Image,
    logo_path: Path,
    policy: dict[str, Any],
) -> tuple[Image.Image, dict[str, Any]]:
    with Image.open(logo_path) as logo_image:
        logo = logo_image.convert("RGBA")
        geometry = logo_geometry(image, logo, policy)
        logo = logo.resize(
            (geometry["width"], geometry["height"]),
            Image.Resampling.LANCZOS,
        )
        opacity = max(0.0, min(1.0, float(policy.get("opacity", 1.0))))
        logo.putalpha(
            logo.getchannel("A").point(lambda value: round(value * opacity))
        )
        canvas = image.convert("RGBA")
        canvas.alpha_composite(logo, (geometry["x"], geometry["y"]))
    return canvas.convert("RGB"), {
        "applied": True,
        "asset": str(logo_path),
        "placement": policy.get("placement", "top-right"),
        "opacity": opacity,
        **geometry,
    }


LICENSING_FIELD_TERMS = {"iptc", "xmp", "icc_profile", "c2pa", "copyright", "license", "creator"}


def effective_prohibited_terms(metadata_cfg: dict) -> list[str]:
    """Prohibited metadata terms after the client's declared licensing exception.

    Image licensing badges read creator, credit, and licence fields out of IPTC/XMP
    photo metadata, so a client that wants those badges may declare
    licensing_fields_exception=true to keep exactly those carriers. Privacy and
    provenance terms (gps, exif, software, prompt, parameters, comment) are never
    exempted: the exception is about rights fields, not about shipping device
    location or generator traces.
    """
    terms = list(metadata_cfg["prohibited_terms"])
    if metadata_cfg.get("licensing_fields_exception", False):
        terms = [t for t in terms if t.lower() not in LICENSING_FIELD_TERMS]
    return terms


def audit_metadata(
    path: Path,
    prohibited_terms: list[str],
    expected_width: int,
    expected_height: int,
) -> dict[str, Any]:
    with Image.open(path) as image:
        keys = sorted(str(key) for key in image.info)
        prohibited = sorted(
            key
            for key in keys
            if any(term.lower() in key.lower() for term in prohibited_terms)
        )
        chunks = webp_chunks(path)
        prohibited_chunks = sorted(
            chunk for chunk in chunks if chunk in {"EXIF", "XMP ", "ICCP", "META"}
        )
        passed = (
            image.format == "WEBP"
            and image.size == (expected_width, expected_height)
            and not prohibited
            and not prohibited_chunks
        )
        return {
            "file": path.name,
            "format": image.format,
            "width": image.width,
            "height": image.height,
            "embedded_info_keys": keys,
            "prohibited_keys": prohibited,
            "container_chunks": chunks,
            "prohibited_chunks": prohibited_chunks,
            "passed": passed,
        }


def validate_source_review(
    package: Path,
    item: dict[str, Any],
    config: dict[str, Any],
) -> dict[str, Any]:
    source_value = str(item.get("source", "")).strip()
    if not source_value:
        raise RuntimeError(f"{item.get('id')}: source image path is missing.")
    source = content_pipeline.safe_path(package, source_value)
    if not source.is_file():
        raise RuntimeError(f"{item.get('id')}: source image not found: {source}")
    identity = source_identity(source, package)
    required = config.get("quality_gates", {}).get(
        "image_source_review_required",
        True,
    )
    if not required:
        return identity

    review = item.get("source_review")
    if not isinstance(review, dict) or review.get("status") != "passed":
        raise RuntimeError(
            f"{item.get('id')}: structured image source review has not passed."
        )
    evidence_value = str(review.get("evidence_file", "")).strip()
    if not evidence_value:
        raise RuntimeError(
            f"{item.get('id')}: source review evidence_file is missing."
        )
    evidence_path = content_pipeline.safe_path(package, evidence_value)
    if not evidence_path.is_file():
        raise RuntimeError(
            f"{item.get('id')}: source review evidence is missing: {evidence_path}"
        )
    evidence = content_pipeline.load_json(evidence_path)
    reviewer = str(evidence.get("reviewer", "")).strip()
    if not reviewer:
        raise RuntimeError(
            f"{item.get('id')}: source review evidence is missing reviewer."
        )
    reviewed_identity = evidence.get("source_identity")
    if not isinstance(reviewed_identity, dict):
        raise RuntimeError(
            f"{item.get('id')}: source review identity must be an object."
        )
    for key in ("path", "sha256", "bytes", "width", "height", "format"):
        if reviewed_identity.get(key) != identity.get(key):
            raise RuntimeError(
                f"{item.get('id')}: source {key} changed after source review."
            )

    current_provenance = provenance_snapshot(item)
    current_provenance_hash = content_pipeline.canonical_json_sha256(
        current_provenance
    )
    reviewed_provenance = evidence.get("provenance_snapshot")
    reviewed_provenance_hash = str(
        evidence.get("provenance_sha256", "")
    ).strip()
    if not isinstance(reviewed_provenance, dict):
        raise RuntimeError(
            f"{item.get('id')}: reviewed provenance snapshot is missing."
        )
    if (
        content_pipeline.canonical_json_sha256(reviewed_provenance)
        != reviewed_provenance_hash
    ):
        raise RuntimeError(
            f"{item.get('id')}: source review provenance evidence was modified."
        )
    if (
        current_provenance_hash != reviewed_provenance_hash
        or current_provenance != reviewed_provenance
    ):
        raise RuntimeError(
            f"{item.get('id')}: provenance changed after source review."
        )

    checklist = evidence.get("checklist")
    if not isinstance(checklist, dict):
        raise RuntimeError(
            f"{item.get('id')}: source review checklist must be an object."
        )
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
        raise RuntimeError(
            f"{item.get('id')}: source review checklist is missing: "
            + ", ".join(missing)
        )
    if failed:
        raise RuntimeError(
            f"{item.get('id')}: source review checklist has not passed: "
            + ", ".join(failed)
        )
    return identity


def record_source_review(
    client_value: str | Path,
    slug: str,
    image_id: str,
    review_file: str | Path,
) -> dict[str, Any]:
    client = content_pipeline.resolve_client(client_value)
    package, article = content_pipeline.read_package(client, slug)
    config = load_effective_config(client, package, article)
    if config.get("engine", {}).get("mode") != "generic":
        raise RuntimeError(
            "Generic source review is disabled for client_native mode. "
            "Use the declared review_image_sources adapter operation."
        )
    content_pipeline.require_config_capabilities(config, ["images"])
    if article.get("status") != "image_specs_ready":
        raise RuntimeError(
            "Image source review requires article status image_specs_ready. "
            "Invalidate later states before reviewing changed source assets."
        )

    manifest_path = content_pipeline.safe_path(package, article["images_file"])
    manifest = content_pipeline.load_json(manifest_path)
    target = next(
        (item for item in manifest.get("items", []) if item.get("id") == image_id),
        None,
    )
    if target is None:
        raise RuntimeError(f"Image id not found: {image_id}")
    validate_provenance(target, config)
    source_value = str(target.get("source", "")).strip()
    if not source_value:
        raise RuntimeError(f"{image_id}: source image path is missing.")
    source = content_pipeline.safe_path(package, source_value)
    if not source.is_file():
        raise RuntimeError(f"{image_id}: source image not found: {source}")
    identity = source_identity(source, package)

    input_path = content_pipeline.safe_path(package, review_file)
    if not input_path.is_file():
        raise RuntimeError(f"Source review input file not found: {input_path}")
    review = content_pipeline.load_json(input_path)
    reviewer = str(review.get("reviewer", "")).strip()
    if not reviewer:
        raise RuntimeError("Image source review requires a reviewer.")
    submitted_sha = str(review.get("source_sha256", "")).strip().lower()
    if submitted_sha != identity["sha256"]:
        raise RuntimeError(
            f"{image_id}: source_sha256 does not match the current raw image."
        )
    for field, identity_key in (
        ("source_width", "width"),
        ("source_height", "height"),
    ):
        submitted = review.get(field)
        if submitted != identity[identity_key]:
            raise RuntimeError(
                f"{image_id}: {field} does not match the current raw image."
            )

    submitted_provenance = review.get("provenance")
    if not isinstance(submitted_provenance, dict):
        raise RuntimeError("Image source review provenance must be an object.")
    reviewed_provenance = {
        key: str(submitted_provenance.get(key, "")).strip()
        for key in PROVENANCE_SNAPSHOT_FIELDS
    }
    current_provenance = provenance_snapshot(target)
    if reviewed_provenance != current_provenance:
        raise RuntimeError(
            f"{image_id}: reviewed provenance does not match image-manifest.json."
        )
    provenance_hash = content_pipeline.canonical_json_sha256(
        reviewed_provenance
    )

    checklist = review.get("checklist")
    if not isinstance(checklist, dict):
        raise RuntimeError("Image source review checklist must be an object.")
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
        raise RuntimeError(
            "Image source review checklist is missing required items: "
            + ", ".join(missing)
        )
    if failed:
        raise RuntimeError(
            "Image source review checklist items have not passed: "
            + ", ".join(failed)
        )

    timestamp = content_pipeline.now_iso()
    evidence = {
        "version": "1.0.0",
        "slug": slug,
        "image_id": image_id,
        "reviewer": reviewer,
        "reviewed_at": timestamp,
        "source_identity": identity,
        "provenance_snapshot": reviewed_provenance,
        "provenance_sha256": provenance_hash,
        "checklist": {
            key: str(checklist[key]).strip().casefold()
            for key in required_checks
        },
        "notes": str(review.get("notes", "")).strip(),
    }
    evidence_path = package / "reports" / f"{image_id}-source-review.json"
    content_pipeline.write_json(evidence_path, evidence)
    target["source_review"] = {
        "status": "passed",
        "reviewer": reviewer,
        "reviewed_at": timestamp,
        "evidence_file": str(evidence_path.relative_to(package)).replace("\\", "/"),
        "source_sha256": identity["sha256"],
        "source_width": identity["width"],
        "source_height": identity["height"],
        "provenance_sha256": provenance_hash,
    }
    target["technical_status"] = "pending"
    target["qa_status"] = "pending"
    for key in (
        "technical_report",
        "qa_notes",
        "qa_reviewer",
        "qa_reviewed_at",
        "qa_checklist",
        "qa_evidence_file",
    ):
        target.pop(key, None)
    content_pipeline.write_json(manifest_path, manifest)
    return evidence


def process_item(
    client: Path,
    package: Path,
    item: dict[str, Any],
    config: dict[str, Any],
) -> dict[str, Any]:
    role = item.get("role")
    if role not in {"featured", "inline"}:
        raise RuntimeError(f"Unsupported image role: {role}")
    role_config = config["images"][role]
    mode = visual_mode(item, role_config)
    source_value = item.get("source", "").strip()
    if not source_value:
        raise RuntimeError(f"{item.get('id')}: source image path is missing.")
    source = content_pipeline.safe_path(package, source_value)
    if not source.exists():
        raise RuntimeError(f"{item.get('id')}: source image not found: {source}")
    reviewed_source = validate_source_review(package, item, config)
    validate_provenance(item, config)
    output = content_pipeline.safe_path(package, item["output"])
    width = int(role_config["width"])
    height = int(role_config["height"])

    with Image.open(source) as source_image:
        source_image.load()
        processed = fit_image(
            source_image,
            width,
            height,
            role_config.get("fit", "cover"),
            bool(role_config.get("allow_upscale", False)),
        )

    processed, text_overlay_report = apply_text_overlays(
        processed,
        client,
        item,
        config,
    )
    logo_policy = config["images"]["logo"]
    logo_report: dict[str, Any] = {"applied": False}
    if should_apply_logo(logo_policy, role):
        if item.get("preexisting_logo"):
            raise RuntimeError(
                f"{item.get('id')}: source is marked with a pre-existing logo; "
                "refusing to apply a second overlay."
            )
        asset = logo_policy.get("asset_path", "").strip()
        if not asset:
            raise RuntimeError(
                f"{item.get('id')}: logo is required but asset_path is empty."
            )
        logo_path = content_pipeline.safe_path(client, asset)
        if not logo_path.exists():
            raise RuntimeError(f"Approved logo asset not found: {logo_path}")
        processed, logo_report = apply_logo(processed, logo_path, logo_policy)

    output.parent.mkdir(parents=True, exist_ok=True)
    metadata_cfg = config["images"].get("metadata", {})
    if not metadata_cfg.get("strip_embedded_metadata", True):
        if not metadata_cfg.get("licensing_fields_exception", False):
            raise RuntimeError(
                "Published image production requires strip_embedded_metadata=true, "
                "unless the client config declares licensing_fields_exception=true "
                "to keep IPTC/XMP licensing and creator fields for image licensing "
                "badges. GPS, EXIF device data, and generator traces stay prohibited "
                "either way."
            )
    processed.save(
        output,
        "WEBP",
        quality=int(role_config.get("quality", 85)),
        method=6,
    )
    metadata_report = audit_metadata(
        output,
        effective_prohibited_terms(config["images"]["metadata"]),
        width,
        height,
    )
    if not metadata_report["passed"]:
        raise RuntimeError(
            f"{item.get('id')}: output metadata or dimensions failed validation."
        )
    item["width"] = width
    item["height"] = height
    item["technical_status"] = "passed"
    item["visual_mode"] = mode
    item["qa_status"] = "needs_visual_review"
    for key in (
        "qa_notes",
        "qa_reviewer",
        "qa_reviewed_at",
        "qa_checklist",
        "qa_evidence_file",
    ):
        item.pop(key, None)
    item["technical_report"] = {
        "source": str(source),
        "output": str(output),
        "source_sha256": reviewed_source["sha256"],
        "output_sha256": sha256_file(output),
        "source_bytes": reviewed_source["bytes"],
        "source_width": reviewed_source["width"],
        "source_height": reviewed_source["height"],
        "source_format": reviewed_source["format"],
        "source_review": item.get("source_review"),
        "output_bytes": output.stat().st_size,
        "visual_mode": mode,
        "text_overlays": text_overlay_report,
        "logo": logo_report,
        "metadata": metadata_report,
    }
    return item["technical_report"]


def process_manifest(client_value: str | Path, slug: str) -> dict[str, Any]:
    client = content_pipeline.resolve_client(client_value)
    package, article = content_pipeline.read_package(client, slug)
    current_status = str(article.get("status", ""))
    if current_status not in content_pipeline.STATUSES:
        raise RuntimeError(f"Article has an invalid status: {current_status}")
    if content_pipeline.STATUSES.index(current_status) < content_pipeline.STATUSES.index(
        "image_specs_ready"
    ):
        raise RuntimeError(
            "Image processing requires image_specs_ready or a later state."
        )
    config = load_effective_config(client, package, article)
    manifest_path = content_pipeline.safe_path(package, article["images_file"])
    manifest = content_pipeline.load_json(manifest_path)
    for item in manifest.get("items", []):
        validate_source_review(package, item, config)
        validate_provenance(item, config)
    reports: list[dict[str, Any]] = []
    for item in manifest.get("items", []):
        reports.append(process_item(client, package, item, config))
    content_pipeline.write_json(manifest_path, manifest)

    current_status = content_pipeline.load_json(package / "article.json")["status"]
    current_index = content_pipeline.STATUSES.index(current_status)
    technical_index = content_pipeline.STATUSES.index("images_technical_ready")
    if current_status == "image_specs_ready":
        content_pipeline.set_status(
            client,
            slug,
            "images_technical_ready",
            "All images were reprocessed and previous visual approval was cleared.",
        )
    elif current_index > technical_index:
        invalidator = getattr(content_pipeline, "invalidate_status", None)
        if callable(invalidator):
            invalidator(
                client,
                slug,
                "images_technical_ready",
                "Image processing invalidated every previous visual approval.",
            )
        else:  # Backward-compatible fallback for an older content_pipeline module.
            content_pipeline.set_status(
                client,
                slug,
                "images_technical_ready",
                "Image processing invalidated every previous visual approval.",
            )

    report = {
        "checked_at": content_pipeline.now_iso(),
        "slug": slug,
        "files": reports,
        "passed": all(
            item["metadata"]["passed"]
            and (
                item["logo"]["applied"]
                or not config["images"]["logo"].get("required")
            )
            for item in reports
        ),
        "visual_review_required": bool(
            config["images"].get("style", {}).get(
                "human_visual_review_required",
                True,
            )
        ),
        "synthid_note": config["images"]["metadata"]["synthid_note"],
    }
    content_pipeline.write_json(
        package / "reports" / "image-production-audit.json",
        report,
    )
    return report


def mark_reviewed(
    client_value: str | Path,
    slug: str,
    image_id: str,
    status: str,
    notes: str = "",
    reviewer: str = "",
    checklist_path: str | Path | None = None,
) -> dict[str, Any]:
    if status not in {"passed", "rejected"}:
        raise RuntimeError("Visual review status must be passed or rejected.")
    client = content_pipeline.resolve_client(client_value)
    package, article = content_pipeline.read_package(client, slug)
    config = load_effective_config(client, package, article)
    manifest_path = content_pipeline.safe_path(package, article["images_file"])
    manifest = content_pipeline.load_json(manifest_path)
    target = next(
        (item for item in manifest.get("items", []) if item.get("id") == image_id),
        None,
    )
    if target is None:
        raise RuntimeError(f"Image id not found: {image_id}")
    if target.get("technical_status") != "passed":
        raise RuntimeError(f"{image_id}: technical processing must pass first.")
    reviewer = reviewer.strip()
    if not reviewer:
        raise RuntimeError("Visual review requires a non-empty reviewer.")
    if not notes.strip():
        raise RuntimeError("Visual review requires review notes.")
    checklist: dict[str, Any] = {}
    evidence_file = ""
    if checklist_path:
        checklist_file = content_pipeline.safe_path(package, checklist_path)
        if not checklist_file.exists():
            raise RuntimeError(f"Visual review checklist not found: {checklist_file}")
        evidence = content_pipeline.load_json(checklist_file)
        evidence_reviewer = str(evidence.get("reviewer", "")).strip()
        if evidence_reviewer and evidence_reviewer != reviewer:
            raise RuntimeError(
                "Checklist reviewer does not match the command reviewer."
            )
        raw_checks = evidence.get("checks", {})
        if not isinstance(raw_checks, dict):
            raise RuntimeError("Visual review checklist checks must be an object.")
        checklist = raw_checks
        evidence_file = str(checklist_file.relative_to(package))
    if status == "passed":
        if not checklist:
            raise RuntimeError(
                "A passed visual review requires a structured checklist JSON."
            )
        failed = [
            name
            for name, value in checklist.items()
            if value not in {True, "passed", "pass"}
        ]
        if failed:
            raise RuntimeError(
                "Visual review checklist has non-passing items: "
                + ", ".join(sorted(failed))
            )
        required_checks = config["images"].get("style", {}).get(
            "review_checklist",
            [],
        )
        if isinstance(required_checks, str):
            required_checks = [required_checks]
        missing = [name for name in required_checks if name not in checklist]
        if missing:
            raise RuntimeError(
                "Visual review checklist is missing required items: "
                + ", ".join(missing)
            )
    target["qa_status"] = status
    target["qa_notes"] = notes
    target["qa_reviewer"] = reviewer
    target["qa_checklist"] = checklist
    target["qa_evidence_file"] = evidence_file
    target["qa_reviewed_at"] = content_pipeline.now_iso()
    content_pipeline.write_json(manifest_path, manifest)

    if status == "passed" and all(
        item.get("qa_status") == "passed" for item in manifest.get("items", [])
    ):
        current = content_pipeline.load_json(package / "article.json")["status"]
        if (
            content_pipeline.STATUSES.index(current)
            < content_pipeline.STATUSES.index("images_qa_passed")
        ):
            content_pipeline.set_status(
                client,
                slug,
                "images_qa_passed",
                "Every required image passed full-resolution visual review.",
            )
    return target


def command_process(args: argparse.Namespace) -> int:
    report = process_manifest(args.client, args.slug)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["passed"] else 2


def command_review_source(args: argparse.Namespace) -> int:
    result = record_source_review(
        args.client,
        args.slug,
        args.image_id,
        args.review_file,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def command_mark(args: argparse.Namespace) -> int:
    result = mark_reviewed(
        args.client,
        args.slug,
        args.image_id,
        args.status,
        args.notes,
        args.reviewer,
        args.checklist_json,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    process = sub.add_parser("process", help="Process every image in a manifest.")
    process.add_argument("--client", required=True)
    process.add_argument("--slug", required=True)
    process.set_defaults(func=command_process)

    review_source = sub.add_parser(
        "review-source",
        help="Approve one exact raw source and provenance snapshot before processing.",
    )
    review_source.add_argument("--client", required=True)
    review_source.add_argument("--slug", required=True)
    review_source.add_argument("--image-id", required=True)
    review_source.add_argument(
        "--review-file",
        required=True,
        help="Structured review JSON confined to the article package.",
    )
    review_source.set_defaults(func=command_review_source)

    mark = sub.add_parser(
        "mark-reviewed",
        help="Record the mandatory full-resolution visual review.",
    )
    mark.add_argument("--client", required=True)
    mark.add_argument("--slug", required=True)
    mark.add_argument("--image-id", required=True)
    mark.add_argument("--status", required=True, choices=["passed", "rejected"])
    mark.add_argument("--notes", required=True)
    mark.add_argument("--reviewer", required=True)
    mark.add_argument("--checklist-json")
    mark.set_defaults(func=command_mark)
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
    """Logo policy, prohibited terms and provenance snapshot without an image."""
    assert should_apply_logo({"allowed": True, "apply_to": ["featured"]}, "featured")
    assert not should_apply_logo({"allowed": True, "apply_to": ["featured"]}, "inline")
    try:
        should_apply_logo({"allowed": False, "required": True}, "featured")
        raise AssertionError("disallowed logo with required must raise")
    except RuntimeError:
        pass
    terms = effective_prohibited_terms({"prohibited_terms": ["stock photo"]})
    assert isinstance(terms, list) and "stock photo" in terms
    try:
        provenance_snapshot({"id": "img-1"})
        raise AssertionError("missing provenance must raise")
    except RuntimeError:
        pass
    print("SELF-TEST PASS: logo policy, prohibited terms, provenance gate")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
