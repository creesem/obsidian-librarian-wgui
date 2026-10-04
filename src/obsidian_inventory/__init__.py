"""Shared deterministic Obsidian inventory primitives."""

from obsidian_inventory.scanner import (
    VALID_SCOPES,
    IndexRecord,
    IndexSummary,
    build_index,
    extract_aliases,
    extract_frontmatter,
    extract_headings,
    frontmatter_text,
    normalize_wikilink_target,
    read_frontmatter_typed,
    scope_for_path,
    set_frontmatter_fields,
    split_frontmatter,
)

__all__ = [
    "IndexRecord",
    "IndexSummary",
    "VALID_SCOPES",
    "build_index",
    "extract_aliases",
    "extract_frontmatter",
    "extract_headings",
    "frontmatter_text",
    "normalize_wikilink_target",
    "read_frontmatter_typed",
    "scope_for_path",
    "set_frontmatter_fields",
    "split_frontmatter",
]
