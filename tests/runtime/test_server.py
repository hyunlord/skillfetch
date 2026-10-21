"""The MCP server: tools are listed and callable over a real MCP client (in-process),
and `skillfetch serve` speaks MCP over stdio."""

import asyncio
import json
import sys

from indexkit import make_index, skill_id
from mcp import Client
from mcp.client.stdio import StdioServerParameters

from skillfetch.index.fetch import BodyCache
from skillfetch.index.loader import Index
from skillfetch.ingest.extract_cache import ExtractCache
from skillfetch.mcp.server import build_server
from skillfetch.mcp.session import Session

TOOLS = {"profile_repo", "search_skills", "resolve_set", "load_skills"}


def _payload(result) -> dict:
    if getattr(result, "structured_content", None):
        return result.structured_content
    return json.loads(result.content[0].text)


def test_search_resolve_load_through_mcp(tmp_path):
    root = make_index(tmp_path)
    session = Session(
        Index.load(root),
        extract_cache=ExtractCache(tmp_path / "xc"),
        bodies=BodyCache(tmp_path / "bodies"),
    )

    async def run():
        async with Client(build_server(session)) as client:
            names = {t.name for t in (await client.list_tools()).tools}
            assert names >= TOOLS
            found = _payload(await client.call_tool("search_skills", {"query": "squash commits"}))
            ids = [r["id"] for r in found["results"]]
            assert skill_id(root, "commit-squash") in ids
            resolved = _payload(
                await client.call_tool(
                    "resolve_set",
                    {
                        "auto_ids": [
                            skill_id(root, "commit-squash"),
                            skill_id(root, "atomic-commits"),
                        ]
                    },
                )
            )
            assert resolved["excluded"][0]["reason"] == "conflict"
            loaded = _payload(await client.call_tool("load_skills", {"set_id": resolved["set_id"]}))
            assert "Squash every feature" in loaded["content"]
            assert loaded["errors"] == []

    asyncio.run(run())


def test_serve_over_stdio(tmp_path):
    root = make_index(tmp_path)
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "skillfetch.cli", "serve", "--index", str(root)],
    )

    async def run():
        async with Client(params) as client:
            names = {t.name for t in (await client.list_tools()).tools}
            assert names >= TOOLS
            found = _payload(await client.call_tool("search_skills", {"query": "python types"}))
            assert found["results"][0]["id"] == skill_id(root, "typed-python")

    asyncio.run(run())


def test_serve_without_an_index_fails_cleanly(tmp_path, capsys):
    from skillfetch.cli import main

    assert main(["serve", "--index", str(tmp_path / "nope")]) == 2
    assert "missing manifest.json" in capsys.readouterr().err
