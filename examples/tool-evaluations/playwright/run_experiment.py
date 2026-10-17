"""Compare pinned Playwright routes, without a repository Node dependency.

Provision packages/browsers as documented first. Browser routes allow loopback
only; this does not claim an OS-level network sandbox or an offline installer.
"""

from __future__ import annotations

import argparse
import functools
import http.server
import json
import os
import platform
import queue
import shutil
import subprocess
import tempfile
import threading
from pathlib import Path

HERE = Path(__file__).resolve().parent
RESTRICT = """async page => {
  await page.context().route('**/*', route =>
    new URL(route.request().url()).hostname === '127.0.0.1'
      ? route.continue() : route.abort('internetdisconnected'));
  await page.reload();
  return {externalFetchSucceeded: await page.evaluate(() =>
    fetch('https://example.invalid/probe').then(() => true, () => false))};
}"""


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *_args: object) -> None:
        pass


def run(args: list[str], *, cwd: Path, env: dict[str, str]) -> str:
    result = subprocess.run(args, cwd=cwd, env=env, text=True, capture_output=True, timeout=90)
    if result.returncode:
        raise RuntimeError(f"{args[0]} failed: {result.stdout}\n{result.stderr}")
    return result.stdout


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--npm-dir", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=HERE / "results")
    args = parser.parse_args()
    npm = args.npm_dir.resolve()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    server = http.server.ThreadingHTTPServer(
        ("127.0.0.1", 0), functools.partial(QuietHandler, directory=str(HERE))
    )
    threading.Thread(target=server.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{server.server_port}/local-reviewer.html"
    report: dict[str, object] = {
        "system": platform.system(),
        "architecture": platform.machine(),
        "network_policy": "Browser route aborts all requests except 127.0.0.1; no OS sandbox",
        "packages": {
            name: json.loads((npm / "node_modules" / name / "package.json").read_text())["version"]
            for name in ("@playwright/cli", "@playwright/test", "@playwright/mcp")
        },
    }
    try:
        with tempfile.TemporaryDirectory(prefix="house-s3-browser-") as scratch:
            work = Path(scratch)
            config = work / "cli.config.json"
            config.write_text(
                json.dumps(
                    {
                        "browser": {
                            "browserName": "chromium",
                            "launchOptions": {"channel": "chromium", "headless": True},
                        },
                        "outputDir": str(work / "artifacts"),
                    }
                )
            )
            cli = [str(npm / "node_modules/.bin/playwright-cli"), f"-s=house-s3-{os.getpid()}"]
            logs = []
            try:
                logs.append(run([*cli, "open", url, f"--config={config}"], cwd=work, env=env))
                restriction = run([*cli, "--raw", "run-code", RESTRICT], cwd=work, env=env)
                assert json.loads(restriction)["externalFetchSucceeded"] is False
                logs.append(restriction)
                logs.append(run([*cli, "click", "#measure"], cwd=work, env=env))
                result = run(
                    [*cli, "eval", "() => document.querySelector('output').value"],
                    cwd=work,
                    env=env,
                )
                assert "Total: 60 m²" in result
                logs.append(result)
                logs.append(
                    run([*cli, "screenshot", f"--filename={out / 'cli.png'}"], cwd=work, env=env)
                )
                report["cli"] = {"measurement": "Total: 60 m²", "external_fetch_succeeded": False}
            finally:
                run([*cli, "close"], cwd=work, env=env)
            (out / "cli.txt").write_text(
                "\n".join(logs)
                .replace(str(work), "<scratch>")
                .replace(url, "<loopback>/local-reviewer.html")
            )
            # MCP: tiny newline-delimited JSON-RPC client, no SDK or desktop configuration.
            with (work / "mcp-stderr.txt").open("w") as stderr:
                proc = subprocess.Popen(
                    [str(npm / "node_modules/.bin/playwright-mcp"), "--config", str(config)],
                    cwd=work,
                    env=env,
                    text=True,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=stderr,
                )
                rpc_id = 0
                responses: queue.Queue[dict[str, object]] = queue.Queue()

                def read_responses() -> None:
                    assert proc.stdout
                    for line in proc.stdout:
                        responses.put(json.loads(line))

                threading.Thread(target=read_responses, daemon=True).start()

                def rpc(method: str, params: dict[str, object]) -> dict[str, object]:
                    nonlocal rpc_id
                    rpc_id += 1
                    assert proc.stdin and proc.stdout
                    proc.stdin.write(
                        json.dumps(
                            {"jsonrpc": "2.0", "id": rpc_id, "method": method, "params": params}
                        )
                        + "\n"
                    )
                    proc.stdin.flush()
                    while True:
                        response = responses.get(timeout=90)
                        if response.get("id") == rpc_id:
                            assert "error" not in response, response
                            return response["result"]

                try:
                    rpc(
                        "initialize",
                        {
                            "protocolVersion": "2024-11-05",
                            "capabilities": {},
                            "clientInfo": {"name": "house-s3-evaluation", "version": "1"},
                        },
                    )
                    assert proc.stdin
                    proc.stdin.write(
                        json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}) + "\n"
                    )
                    proc.stdin.flush()
                    available = rpc("tools/list", {})
                    tools = [tool["name"] for tool in available["tools"]]

                    def call(name: str, arguments: dict[str, object]) -> dict[str, object]:
                        value = rpc("tools/call", {"name": name, "arguments": arguments})
                        assert not value.get("isError"), value
                        return value

                    navigation = call("browser_navigate", {"url": url})
                    restrict = call("browser_run_code_unsafe", {"code": RESTRICT})
                    assert "externalFetchSucceeded" in json.dumps(restrict)
                    assert "false" in json.dumps(restrict)
                    call("browser_click", {"target": "#measure"})
                    snapshot = call("browser_snapshot", {})
                    assert "Total: 60 m²" in json.dumps(snapshot, ensure_ascii=False)
                    call(
                        "browser_take_screenshot",
                        {"filename": str(work / "artifacts/mcp.png"), "type": "png"},
                    )
                    shutil.copyfile(work / "artifacts/mcp.png", out / "mcp.png")
                    report["mcp"] = {
                        "measurement": "Total: 60 m²",
                        "external_fetch_succeeded": False,
                        "available_tools": len(tools),
                    }
                    (out / "mcp.json").write_text(
                        json.dumps(
                            {
                                "tool_names": tools,
                                "navigate": navigation,
                                "restriction": restrict,
                                "snapshot": snapshot,
                            },
                            indent=2,
                            ensure_ascii=False,
                        )
                        .replace(str(work), "<scratch>")
                        .replace(url, "<loopback>/local-reviewer.html")
                        + "\n"
                    )
                finally:
                    proc.terminate()
                    proc.wait(timeout=15)
            # Test route uses its own exact browser revision; no npm resolution from repo.
            test_config = work / "playwright.config.cjs"
            test_config.write_text(
                "module.exports = "
                + json.dumps(
                    {
                        "testDir": str(HERE),
                        "testMatch": "*.spec.cjs",
                        "workers": 1,
                        "reporter": "line",
                        "outputDir": str(work / "test-results"),
                    }
                )
                + ";\n"
            )
            test_env = env | {
                "HOUSE_S3_PLAYWRIGHT_TEST": str(npm / "node_modules/@playwright/test"),
                "HOUSE_S3_REVIEWER_URL": url,
                "HOUSE_S3_TEST_SCREENSHOT": str(out / "test.png"),
            }
            test_log = run(
                [
                    str(npm / "node_modules/@playwright/test/cli.js"),
                    "test",
                    "--config",
                    str(test_config),
                ],
                cwd=work,
                env=test_env,
            )
            assert "1 passed" in test_log
            (out / "test.txt").write_text(test_log)
            report["test"] = {"passed": 1, "external_fetch_succeeded": False}
    finally:
        server.shutdown()
    (out / "summary.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
