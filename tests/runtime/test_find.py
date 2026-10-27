"""`skillfetch find` and the MCP tool find_skills (index-format.md §5.2): index matches for a
request, with size, license and an advice read from the record. No model, no network."""

import asyncio
import json

from indexkit import make_index, skill_id
from mcp import Client

from skillfetch import cli
from skillfetch.index.find import record_advice, render_find, scan_url
from skillfetch.index.loader import Index
from skillfetch.ingest.extract_cache import ExtractCache
from skillfetch.mcp.server import build_vet_server
from skillfetch.mcp.session import Session


def _payload(result) -> dict:
    if getattr(result, "structured_content", None):
        return result.structured_content
    return json.loads(result.content[0].text)


def test_find_ranks_the_index_and_adds_advice(tmp_path):
    root = make_index(tmp_path)
    session = Session(Index.load(root), extract_cache=ExtractCache(tmp_path / "xc"))
    found = session.find_skills("python types", k=3)
    assert len(found["results"]) <= 3
    top = found["results"][0]
    assert top["id"] == skill_id(root, "typed-python")
    assert top["advice"] == "recommended" and top["advice_reasons"] == []
    assert {"summary", "tier", "token_estimate", "files", "license", "scan_url"} <= set(top)
    assert "scan_skill" in found["advice_note"]
    assert session.find_skills("  ")["error"].startswith("invalid request")


def test_record_advice_follows_the_install_rule():
    base = {"lint": {"errors": []}, "scan": {}, "token_estimate": 100, "files": {"SKILL.md": "x"}}
    assert record_advice(base) == ("recommended", [])
    assert record_advice({**base, "lint": {"errors": [{"rule": "x"}]}})[0] == "not_recommended"
    assert record_advice({**base, "scan": {"failures": [{"rule_id": "x"}]}})[0] == (
        "not_recommended"
    )
    assert record_advice({**base, "has_scripts": True}) == ("caution", ["bundles scripts"])
    big = {**base, "token_estimate": 9000}
    assert record_advice(big) == ("caution", ["over a size limit (~9,000 tokens, 1 files)"])
    # a stored warning whose rule is info under the current rules (v6) does not count
    bare = {**base, "scan": {"warnings": [{"rule_id": "network.bare-url"}]}}
    assert record_advice(bare) == ("recommended", [])
    sudo = {**base, "scan": {"warnings": [{"rule_id": "privilege.sudo"}]}}
    assert record_advice(sudo) == ("caution", ["injection-scan warnings: privilege.sudo"])


def test_scan_url_points_at_the_pinned_folder():
    record = {
        "source_url": "https://github.com/acme/skills/blob/abc123/skills/pdf/SKILL.md",
        "commit": "abc123",
        "path": "skills/pdf",
    }
    assert scan_url(record) == "https://github.com/acme/skills/tree/abc123/skills/pdf"
    assert scan_url({"source_url": "file:///x", "commit": "a"}) is None


def test_cli_find_text_and_json(tmp_path, capsys):
    root = make_index(tmp_path)
    assert cli.main(["find", "python types", "-k", "2", "--index", str(root)]) == 0
    text = capsys.readouterr().out
    assert text.startswith('Skills for "python types" (top 2 in the index):')
    assert "advice: RECOMMENDED" in text and "Note: advice from the index record" in text
    assert cli.main(["find", "python types", "--json", "--index", str(root)]) == 0
    assert json.loads(capsys.readouterr().out)["results"][0]["id"] == skill_id(root, "typed-python")
    assert cli.main(["find", "x", "--index", str(tmp_path / "none")]) == 2
    assert "skillfetch sync" in capsys.readouterr().err
    assert render_find("x", {"results": [], "advice_note": ""}) == 'No indexed skill matches "x".\n'


def test_find_skills_through_the_vet_server(tmp_path):
    root = make_index(tmp_path)

    async def run():
        async with Client(build_vet_server(Index.load(root), ExtractCache(tmp_path / "xc"))) as c:
            return _payload(await c.call_tool("find_skills", {"want": "python types", "k": 1}))

    found = asyncio.run(run())
    assert [r["id"] for r in found["results"]] == [skill_id(root, "typed-python")]
