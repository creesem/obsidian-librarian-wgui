"""Command-line interface for obsidian_operator.

Commands: ``project list|show|review``, ``person list|show|workload``,
``ticket list|show``, ``action list|show``, ``review today|team|projects``, and
``view list|render``. Every command is read-only except ``view render --write``,
which writes generated views under a contained views root and never touches a
canonical note.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from datetime import UTC, date, datetime
from pathlib import Path

from obsidian_operator import __version__
from obsidian_operator.dates import parse_iso_date
from obsidian_operator.models import EntityType
from obsidian_operator.render import (
    attention_to_dict,
    issue_to_dict,
    project_review_to_dict,
    render_attention,
    render_entity,
    render_issues,
    render_list,
    render_project_review,
    render_projects_review,
    render_team_review,
    render_workload,
    to_dict,
    workload_to_dict,
)
from obsidian_operator.repository import OperatorIndex
from obsidian_operator.review import (
    active_people,
    active_projects,
    attention_items,
    build_person_workload,
    build_project_review,
)
from obsidian_operator.views import VIEWS, GeneratedView, build_view
from obsidian_operator.writer import ViewWriteError, WriteResult, write_view

DESCRIPTION = "Work-management operator over an Obsidian vault."
ENTITY_COMMANDS = tuple(member.value for member in EntityType if member is not EntityType.MEETING)
REVIEW_COMMANDS = ("today", "team", "projects")


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--vault", default=".", help="Vault root path.")
    common.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    common.add_argument(
        "--today",
        default=None,
        help="Reference date (YYYY-MM-DD) for attention rules. Defaults to today.",
    )

    parser = argparse.ArgumentParser(prog="obsidian-operator", description=DESCRIPTION)
    parser.add_argument(
        "--version",
        action="version",
        version=f"obsidian-operator {__version__}",
    )

    subparsers = parser.add_subparsers(dest="command")
    for entity_type in ENTITY_COMMANDS:
        entity_parser = subparsers.add_parser(entity_type, help=f"Inspect {entity_type} notes.")
        actions = entity_parser.add_subparsers(dest="action")
        actions.add_parser("list", parents=[common], help=f"List all {entity_type} notes.")
        show = actions.add_parser("show", parents=[common], help=f"Show one {entity_type} note.")
        show.add_argument("name", help="Entity title, alias, or wikilink target.")
        if entity_type == EntityType.PROJECT.value:
            review = actions.add_parser(
                "review", parents=[common], help="Show a project management rollup."
            )
            review.add_argument("name", help="Project title, alias, or wikilink target.")
        if entity_type == EntityType.PERSON.value:
            workload = actions.add_parser(
                "workload", parents=[common], help="Show a person's workload rollup."
            )
            workload.add_argument("name", help="Person title, alias, or wikilink target.")

    review = subparsers.add_parser("review", help="Read-only management review queues.")
    review_actions = review.add_subparsers(dest="review")
    for view in REVIEW_COMMANDS:
        review_actions.add_parser(view, parents=[common], help=f"Review {view}.")

    view = subparsers.add_parser("view", help="Generate management views.")
    view_actions = view.add_subparsers(dest="view")
    view_actions.add_parser("list", parents=[common], help="List available view names.")
    render = view_actions.add_parser("render", parents=[common], help="Render one or all views.")
    render.add_argument("name", nargs="?", help="View name to render.")
    render.add_argument(
        "--all", action="store_true", dest="all_views", help="Render every view."
    )
    render.add_argument(
        "--write", action="store_true", help="Write views under the views root."
    )
    render.add_argument(
        "--force", action="store_true", help="Overwrite existing view files."
    )
    render.add_argument("--out", default=None, help="Views root, relative to the vault.")
    render.add_argument(
        "--generated-at", default=None, help="ISO 8601 generation timestamp."
    )

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the CLI."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 0
    if args.command == "review":
        if getattr(args, "review", None) is None:
            parser.print_help()
            return 0
    elif args.command == "view":
        if getattr(args, "view", None) is None:
            parser.print_help()
            return 0
    elif getattr(args, "action", None) is None:
        parser.print_help()
        return 0

    try:
        index = OperatorIndex.from_vault(args.vault)
    except (FileNotFoundError, NotADirectoryError, ValueError) as exc:
        print(f"Error: {exc}")
        return 2

    if args.command == "view" and args.view == "list":
        return _run_view_list(index)

    try:
        today = _resolve_today(getattr(args, "today", None))
    except ValueError as exc:
        print(f"Error: {exc}")
        return 2

    if args.command == "view":
        return _run_view_render(args, index, today)
    if args.command == "review":
        return _run_review(args, index, today)
    if args.command == EntityType.PROJECT.value and args.action == "review":
        return _run_project_review(args, index, today)
    if args.command == EntityType.PERSON.value and args.action == "workload":
        return _run_person_workload(args, index, today)
    if args.action == "list":
        return _run_list(args, index)
    return _run_show(args, index)


def _run_list(args: argparse.Namespace, index: OperatorIndex) -> int:
    entities = index.list_type(args.command)
    if args.json:
        payload = {
            "type": args.command,
            "count": len(entities),
            "entities": [to_dict(entity) for entity in entities],
            "issues": [issue_to_dict(issue) for issue in index.issues],
        }
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(render_list(args.command, entities))
        if index.issues:
            print("\n## Validation issues")
            print(render_issues(index.issues))
    return 1 if index.errors else 0


def _run_show(args: argparse.Namespace, index: OperatorIndex) -> int:
    entity = index.get(args.command, args.name)
    if entity is None:
        print(f"Error: no {args.command} found matching '{args.name}'")
        return 2

    related = [issue for issue in index.issues if issue.path == entity.path]
    if args.json:
        payload = {
            "entity": to_dict(entity),
            "issues": [issue_to_dict(issue) for issue in related],
        }
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(render_entity(entity))
        if related:
            print("\n## Validation issues")
            print(render_issues(related))
    return 1 if any(issue.severity == "error" for issue in related) else 0


def _run_review(args: argparse.Namespace, index: OperatorIndex, today: date) -> int:
    view = args.review
    if view == "today":
        items = attention_items(index, today)
        if args.json:
            payload = {"view": "today", "items": [attention_to_dict(item) for item in items]}
            print(json.dumps(payload, indent=2, sort_keys=True))
        else:
            print(render_attention("Today", items))
    elif view == "projects":
        reviews = [
            build_project_review(index, project, today) for project in active_projects(index)
        ]
        if args.json:
            payload = {"view": "projects", "projects": [project_review_to_dict(r) for r in reviews]}
            print(json.dumps(payload, indent=2, sort_keys=True))
        else:
            print(render_projects_review(reviews))
    elif view == "team":
        workloads = [build_person_workload(index, person, today) for person in active_people(index)]
        if args.json:
            payload = {"view": "team", "people": [workload_to_dict(w) for w in workloads]}
            print(json.dumps(payload, indent=2, sort_keys=True))
        else:
            print(render_team_review(workloads))
    return 1 if index.errors else 0


def _run_project_review(args: argparse.Namespace, index: OperatorIndex, today: date) -> int:
    project = index.get(EntityType.PROJECT.value, args.name)
    if project is None:
        print(f"Error: no project found matching '{args.name}'")
        return 2
    review = build_project_review(index, project, today)
    if args.json:
        print(json.dumps(project_review_to_dict(review), indent=2, sort_keys=True))
    else:
        print(render_project_review(review))
    return 1 if index.errors else 0


def _run_person_workload(args: argparse.Namespace, index: OperatorIndex, today: date) -> int:
    person = index.get(EntityType.PERSON.value, args.name)
    if person is None:
        print(f"Error: no person found matching '{args.name}'")
        return 2
    workload = build_person_workload(index, person, today)
    if args.json:
        print(json.dumps(workload_to_dict(workload), indent=2, sort_keys=True))
    else:
        print(render_workload(workload))
    return 1 if index.errors else 0


def _resolve_today(value: str | None) -> date:
    if value is None:
        return date.today()
    parsed = parse_iso_date(value)
    if parsed is None:
        raise ValueError(f"invalid --today date: {value}")
    return parsed.date()


def _run_view_list(index: OperatorIndex) -> int:
    for name in VIEWS:
        print(name)
    return 1 if index.errors else 0


def _run_view_render(args: argparse.Namespace, index: OperatorIndex, today: date) -> int:
    try:
        names, generated_at = _resolve_view_request(args)
    except ValueError as exc:
        print(f"Error: {exc}")
        return 2

    views = [build_view(name, index, today=today, generated_at=generated_at) for name in names]

    if not args.write:
        if args.json:
            payload = {
                "write": False,
                "views": [_view_to_dict(view) for view in views],
            }
            print(json.dumps(payload, indent=2, sort_keys=True))
        else:
            for position, view in enumerate(views):
                if position:
                    print()
                print(view.to_markdown(), end="")
        return 1 if index.errors else 0

    try:
        vault_root = Path(args.vault)
        views_root = _resolve_views_root(vault_root, args.out)
    except (ValueError, ViewWriteError) as exc:
        print(f"Error: {exc}")
        return 2

    results: list[WriteResult] = []
    try:
        for view in views:
            results.append(write_view(views_root, vault_root, view, force=args.force))
    except FileExistsError as exc:
        print(f"Error: {exc}")
        return 2
    except (ViewWriteError, OSError) as exc:
        print(f"Error: {exc}")
        return 2

    if args.json:
        payload = {
            "write": True,
            "views_root": str(views_root),
            "change_set": [
                {
                    "view": view.name,
                    "path": result.path.as_posix(),
                    "created": result.created,
                    "overwritten": result.overwritten,
                }
                for view, result in zip(views, results, strict=True)
            ],
        }
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(f"Wrote {len(results)} view(s) under {views_root}:")
        for result in results:
            change = "created" if result.created else "overwritten"
            print(f"  - {change}: {result.path}")
    return 1 if index.errors else 0


def _resolve_view_request(args: argparse.Namespace) -> tuple[list[str], str]:
    if args.all_views:
        if args.name is not None:
            raise ValueError("cannot combine a view name with --all")
        names = list(VIEWS)
    else:
        name = args.name
        if name is None or name not in VIEWS:
            raise ValueError(f"unknown view: {name if name is not None else '(none)'}")
        names = [name]

    generated_at = _resolve_generated_at(args.generated_at)
    return names, generated_at


def _resolve_generated_at(value: str | None) -> str:
    if value is None:
        return datetime.now(UTC).isoformat()
    parsed = parse_iso_date(value)
    if parsed is None:
        raise ValueError(f"invalid --generated-at timestamp: {value}")
    return value


def _resolve_views_root(vault_root: Path, out: str | None) -> Path:
    vault = vault_root.expanduser().resolve(strict=False)
    if out is None:
        return vault / "90_Staging" / "Views"
    candidate = Path(out)
    if candidate.is_absolute():
        raise ValueError(f"--out must be relative to the vault: {out}")
    resolved = (vault / candidate).expanduser().resolve(strict=False)
    if not resolved.is_relative_to(vault):
        raise ValueError(f"--out escapes the vault: {out}")
    return resolved


def _view_to_dict(view: GeneratedView) -> dict[str, object]:
    payload = dict(view.frontmatter())
    payload["markdown"] = view.to_markdown()
    return payload


if __name__ == "__main__":
    raise SystemExit(main())
