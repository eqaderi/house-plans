"""CLI commands for the 2D plan option reviewer application: export and serve."""

from __future__ import annotations

import argparse
import functools
import http.server
import socketserver
from pathlib import Path

from house_ai.cli.plan_cmds import add_plan_options_dir_argument, existing_plan_options_dir
from house_ai.constants.reviewer import REVIEWER_DEFAULT_PORT
from house_ai.orchestration.reviewer_bundle import export_reviewer_bundle
from house_ai.storage import ProjectStore
from house_ai.storage.projects import resolve_project_dir

from .exit_codes import EXIT_FAIL, EXIT_OK


def _out(text: str = "") -> None:
    print(text)


def cmd_reviewer_export(args: argparse.Namespace) -> int:
    """Export a read-only reviewer bundle of the plan options."""
    store = ProjectStore(resolve_project_dir(args.dir))
    plan_options_dir = existing_plan_options_dir(store, args.plan_options_dir)
    bundle_file = export_reviewer_bundle(
        store,
        Path(args.out),
        plan_options_dir=plan_options_dir,
        exploratory=args.exploratory,
    )
    _out(f"wrote reviewer bundle to {bundle_file}")
    return EXIT_OK


def cmd_reviewer_serve(args: argparse.Namespace) -> int:
    """Serve reviewer bundle and static assets over local loopback."""
    store = ProjectStore(resolve_project_dir(args.dir))
    port = args.port or REVIEWER_DEFAULT_PORT
    dist_dir = (
        Path(args.dist)
        if args.dist
        else Path(__file__).resolve().parents[3] / "apps" / "reviewer" / "dist"
    )

    if not (dist_dir / "index.html").is_file():
        _out(
            f"no built reviewer at {dist_dir}; run `pnpm install && pnpm build` in "
            "apps/reviewer, or pass --dist"
        )
        return EXIT_FAIL
    bundle_file = export_reviewer_bundle(
        store, dist_dir, plan_options_dir=existing_plan_options_dir(store)
    )

    url = f"http://127.0.0.1:{port}/?bundle={bundle_file.name}"
    _out(f"Serving the 2D plan option reviewer for project {store.manifest().name} at {url}")
    _out(f"Bundle: {bundle_file}")
    _out("Press Ctrl+C to stop.")

    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(dist_dir))
    with socketserver.TCPServer(("127.0.0.1", port), handler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            _out("\nStopped reviewer server.")
    return EXIT_OK


def register(sub, actor_arg=None) -> None:
    rv = sub.add_parser("reviewer", help="2D desktop reviewer app for plan options (Stage S4)")
    rv = rv.add_subparsers(dest="sub", required=True)

    s = rv.add_parser(
        "export", help="export a read-only bundle of the plan options for the reviewer app"
    )
    s.add_argument("dir", help="project directory or name")
    s.add_argument("--out", required=True, help="output directory for bundle.json")
    add_plan_options_dir_argument(s)
    s.add_argument(
        "--exploratory",
        action="store_true",
        help="include exploratory plan options",
    )
    s.set_defaults(func=cmd_reviewer_export)

    s = rv.add_parser("serve", help="serve the reviewer on local loopback")
    s.add_argument("dir", help="project directory or name")
    s.add_argument(
        "--port",
        type=int,
        default=REVIEWER_DEFAULT_PORT,
        help=f"port (default: {REVIEWER_DEFAULT_PORT})",
    )
    s.add_argument("--dist", help="path to built reviewer web assets")
    s.set_defaults(func=cmd_reviewer_serve)
