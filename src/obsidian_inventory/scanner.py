"""Shared deterministic scanner for Obsidian vault notes."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

WIKILINK_RE = re.compile(r"\[\[([^\]]+)\]\]")
TAG_RE = re.compile(r"(?:^|\s)#([A-Za-z0-9_/-]+)")
SOURCE_REF_RE = re.compile(r"`([^`]+)`")
HEADING_RE = re.compile(r"^#{1,6}\s+(.+?)\s*$", re.MULTILINE)

VALID_SCOPES = (
    "vault",
    "staging",
    "ingestion",
    "vault-and-staging",
    "vault-and-ingestion",
    "staging-and-ingestion",
    "all",
)


@dataclass(frozen=True)
class IndexRecord:
    path: str
    scope: str
    title: str
    headings: list[str]
    tags: list[str]
    wikilinks: list[str]
    frontmatter: dict[str, str]
    source_refs: list[str]
    status: str
    modified_time: str
    snippets: list[str]
    source_pdf: str | None = None
    source_section: str | None = None
    ingest_run_id: str | None = None
    ingest_provenance: str | None = None
    staging_origin: str | None = None
    promoted_from: str | None = None
    promoted_at: str | None = None
    aliases: list[str] = field(default_factory=list)
    frontmatter_typed: dict[str, Any] = field(default_factory=dict)


@dataclass
class IndexSummary:
    root: Path
    scope: str
    scanned_files: int = 0
    indexed_records: list[IndexRecord] = field(default_factory=list)
    skipped_files: list[Path] = field(default_factory=list)


def build_index(vault_root: str | Path, scope: str) -> IndexSummary:
    root = Path(vault_root).expanduser().resolve(strict=False)
    if not root.exists():
        raise FileNotFoundError(f"Vault root does not exist: {root}")
    if scope not in VALID_SCOPES:
        raise ValueError(f"Invalid scope: {scope}")

    summary = IndexSummary(root=root, scope=scope)
    for file_path in sorted(root.rglob("*.md")):
        if not file_path.is_file():
            continue
        file_scope = scope_for_path(root, file_path)
        if not scope_included(scope, file_scope):
            summary.skipped_files.append(file_path)
            continue

        summary.scanned_files += 1
        content = file_path.read_text(encoding="utf-8")
        frontmatter = extract_frontmatter(content)
        title = frontmatter.get("title") or extract_title(content, file_path)
        headings = extract_headings(content)
        tags = sorted(set(TAG_RE.findall(content)))
        wikilinks = sorted(set(WIKILINK_RE.findall(content)))
        source_refs = sorted(set(SOURCE_REF_RE.findall(content)))
        status = frontmatter.get("status") or default_status(file_scope)
        modified_time = datetime.fromtimestamp(file_path.stat().st_mtime, tz=UTC).isoformat()
        snippet = content.strip().replace("\n", " ")[:240]

        summary.indexed_records.append(
            IndexRecord(
                path=file_path.relative_to(root).as_posix(),
                scope=file_scope,
                title=title,
                headings=headings,
                tags=tags,
                wikilinks=wikilinks,
                frontmatter=frontmatter,
                source_refs=source_refs,
                status=status,
                modified_time=modified_time,
                snippets=[snippet] if snippet else [],
                source_pdf=frontmatter.get("source_pdf"),
                source_section=frontmatter.get("source_section"),
                ingest_run_id=frontmatter.get("ingest_run_id"),
                ingest_provenance=frontmatter.get("ingest_provenance")
                or frontmatter.get("ingest_run_id"),
                staging_origin=frontmatter.get("staging_origin"),
                promoted_from=frontmatter.get("promoted_from"),
                promoted_at=frontmatter.get("promoted_at"),
                aliases=list(extract_aliases(frontmatter)),
                frontmatter_typed=read_frontmatter_typed(content),
            )
        )

    return summary


def scope_for_path(root: Path, path: Path) -> str:
    rel = path.relative_to(root)
    if rel.parts and rel.parts[0] == "90_Staging":
        return "staging"
    if rel.parts and rel.parts[0] == "91_Ingestion":
        return "ingestion"
    return "vault"


def scope_included(scope: str, file_scope: str) -> bool:
    if scope == "all":
        return True
    if scope == "vault-and-staging":
        return file_scope in {"vault", "staging"}
    if scope == "vault-and-ingestion":
        return file_scope in {"vault", "ingestion"}
    if scope == "staging-and-ingestion":
        return file_scope in {"staging", "ingestion"}
    return scope == file_scope


def default_status(scope: str) -> str:
    if scope == "staging":
        return "staged"
    if scope == "ingestion":
        return "ingested"
    return "trusted"


def extract_frontmatter(content: str) -> dict[str, str]:
    frontmatter = frontmatter_text(content)
    fields: dict[str, str] = {}
    if not frontmatter:
        return fields
    pending_key: str | None = None
    pending_values: list[str] = []
    for line in frontmatter.splitlines():
        block_item = re.match(r"^\s+-\s+(.+?)\s*$", line)
        if pending_key and block_item:
            pending_values.append(_clean_scalar(block_item.group(1)))
            continue
        if pending_key:
            fields[pending_key] = ", ".join(pending_values)
            pending_key = None
            pending_values = []
        match = re.match(r"^([A-Za-z0-9_-]+):\s*(.*?)\s*$", line)
        if not match:
            continue
        key, value = match.group(1), match.group(2).strip()
        if value:
            fields[key] = _clean_scalar(value)
        else:
            pending_key = key
            pending_values = []
    if pending_key:
        fields[pending_key] = ", ".join(pending_values)
    return fields


def frontmatter_text(content: str) -> str:
    return split_frontmatter(content)[0]


def read_frontmatter_typed(content: str) -> dict[str, Any]:
    """Return frontmatter as a YAML-faithful mapping.

    Unlike :func:`extract_frontmatter`, this preserves block/flow lists and nested
    mappings so callers can rely on real YAML types. Returns an empty mapping when
    the note has no well-formed frontmatter or the block is not valid YAML. This
    function never raises; malformed input yields ``{}``.
    """
    frontmatter = frontmatter_text(content)
    if not frontmatter:
        return {}
    try:
        parsed = yaml.safe_load(frontmatter)
    except yaml.YAMLError:
        return {}
    if not isinstance(parsed, dict):
        return {}
    return parsed


def split_frontmatter(content: str) -> tuple[str, str]:
    """Split a note into (frontmatter_block, body).

    Returns ("", content) when the note has no well-formed ``---`` frontmatter.
    This is the single canonical frontmatter splitter for both read and write paths.
    """
    if not content.startswith("---\n"):
        return "", content
    rest = content.removeprefix("---\n")
    frontmatter, sep, body = rest.partition("\n---\n")
    if not sep:
        return "", content
    return frontmatter, body


def set_frontmatter_fields(content: str, fields: dict[str, str | None]) -> str:
    """Return ``content`` with the given frontmatter fields set, removed, or replaced.

    A ``None`` value removes the key; any other value replaces (or appends) it while
    leaving untouched fields and their formatting intact. This is the canonical
    frontmatter writer so the index and any writer stay byte-compatible.
    """
    frontmatter, body = split_frontmatter(content)
    lines = frontmatter.splitlines() if frontmatter else []
    for key, value in fields.items():
        lines = [line for line in lines if not re.match(rf"^{re.escape(key)}:\s*", line)]
        if value is not None:
            lines.append(f"{key}: {value}")
    rendered = "\n".join(lines).strip()
    if rendered:
        return f"---\n{rendered}\n---\n{body.lstrip(chr(10))}"
    return body.lstrip("\n")



def extract_aliases(frontmatter: dict[str, str]) -> tuple[str, ...]:
    raw = frontmatter.get("aliases", "").strip()
    if not raw:
        return ()
    if raw.startswith("[") and raw.endswith("]"):
        raw = raw[1:-1]
    values = [_clean_scalar(part) for part in raw.split(",")]
    return tuple(value for value in values if value)


def extract_headings(content: str) -> list[str]:
    return [match.group(1).strip() for match in HEADING_RE.finditer(content)]


def extract_title(content: str, path: Path) -> str:
    for line in content.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return path.stem


def normalize_wikilink_target(target: str) -> str:
    return re.sub(r"\s+", " ", target).strip().casefold()


def _clean_scalar(value: str) -> str:
    return value.strip().strip("\"'")
