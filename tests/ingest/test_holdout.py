"""Holdout measurement (constraints.md §2): pinned public skills, hand-labelled pairs.
Local git sources and oracle extraction; no network."""

from pathlib import Path

import pytest
import yaml
from conftest import SKILLS_DIR, OracleClient, make_git_source

from skillfetch.ingest.backends import AnthropicBackend
from skillfetch.ingest.extract import Extractor
from skillfetch.ingest.extract_cache import ExtractCache
from skillfetch.ingest.holdout import load_holdout, measure_holdout, render_holdout
from skillfetch.ingest.skillfile import content_hash
from skillfetch.ingest.sources import Source

PUBLIC = Path(__file__).parents[1] / "fixtures" / "holdout" / "public-v0.yaml"
NAMES = ("commit-squash", "atomic-commits", "plain-markdown", "emoji-headers")


def test_public_holdout_is_well_formed():
    holdout = load_holdout(PUBLIC)
    labels = holdout.labels()
    assert len(labels) == 34 and len(holdout.skills) == 26
    assert set(labels.values()) == {"independent", "needs_review"}  # no true conflict
    assert {p.v4 for p in holdout.pairs} == {"conflict", "tension", "needs_review"}
    # pins only, no bodies; and nothing from the tuning set
    fixture_names = {d.name for d in SKILLS_DIR.iterdir()}
    for sid, pin in holdout.skills.items():
        assert sid.split("/", 1)[0] in holdout.sources
        assert len(pin.content_hash) == 64
        assert sid.split("/", 1)[1].split("@")[0] not in fixture_names
    assert not any(p.suffix == ".md" for p in PUBLIC.parent.rglob("*"))


@pytest.fixture
def pinned(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    commit = make_git_source(repo, {n: SKILLS_DIR / n for n in NAMES})
    source = Source(
        id="pub",
        kind="git",
        url=f"file://{repo}",
        ref="main",
        root="skills/",
        publisher="p",
        publisher_trust="unknown",
    )
    skills = {
        f"pub/{n}@x": {"path": f"skills/{n}", "content_hash": content_hash(SKILLS_DIR / n)}
        for n in NAMES
    }

    def write(pairs, **overrides):
        data = {"sources": {"pub": commit}, "skills": {**skills, **overrides}, "pairs": pairs}
        path = tmp_path / "holdout.yaml"
        path.write_text(yaml.safe_dump(data))
        return path

    return tmp_path, source, write


def _measure(tmp_path, source, path, extractor=True):
    client = OracleClient()
    ext = Extractor(AnthropicBackend(client, "claude-sonnet-5")) if extractor else None
    result = measure_holdout(
        load_holdout(path),
        [source],
        cache=ExtractCache(tmp_path / "cache"),
        extractor=ext,
        model="anthropic/claude-sonnet-5",
        work_dir=tmp_path / "work",
    )
    return result, client


def test_measure_counts_true_and_false_relations(pinned):
    tmp_path, source, write = pinned
    path = write(
        [
            {"a": "pub/commit-squash@x", "b": "pub/atomic-commits@x", "label": "conflict"},
            {
                "a": "pub/plain-markdown@x",
                "b": "pub/emoji-headers@x",
                "label": "independent",
                "note": "hand label says these agree",
            },
        ]
    )
    result, client = _measure(tmp_path, source, path)
    assert len(client.requests) == 4 and result.fresh == 4
    p = result.pairs
    assert (p.conflict_flagged, p.conflict_true_positives) == (1, 1)
    assert result.hard_pass
    [m] = p.mismatches  # plain-markdown vs emoji-headers is needs_review (object-less ban)
    assert (m.expected, m.got) == ("independent", "needs_review")
    text = render_holdout(result)
    assert "hand label: hand label says these agree" in text
    assert "gate: conflict precision 1.000 (hard, must be 1.0): PASS" in text

    again, client = _measure(tmp_path, source, path)  # from the cache
    assert client.requests == [] and again.fresh == 0


def test_a_false_conflict_fails_the_hard_gate(pinned):
    tmp_path, source, write = pinned
    path = write(
        [{"a": "pub/commit-squash@x", "b": "pub/atomic-commits@x", "label": "independent"}]
    )
    result, _ = _measure(tmp_path, source, path)
    assert not result.hard_pass
    assert "FAIL" in render_holdout(result)


def test_moved_content_is_reported(pinned):
    tmp_path, source, write = pinned
    path = write(
        [], **{"pub/emoji-headers@x": {"path": "skills/emoji-headers", "content_hash": "0" * 64}}
    )
    result, _ = _measure(tmp_path, source, path)
    assert result.moved == ["pub/emoji-headers@x"]


def test_cli_holdout_exit_codes(pinned, monkeypatch, capsys):
    import skillfetch.ingest.backends as backends_mod
    from skillfetch.cli import main

    tmp_path, source, write = pinned
    sources = tmp_path / "sources.yaml"
    sources.write_text(yaml.safe_dump([source.model_dump()]))
    good = write([{"a": "pub/commit-squash@x", "b": "pub/atomic-commits@x", "label": "conflict"}])
    base = ["ingest", "--sources", str(sources), "--holdout", str(good)]
    base += ["--cache-dir", str(tmp_path / "c"), "--work-dir", str(tmp_path / "w")]
    base += ["--model", "anthropic/claude-sonnet-5"]
    assert main(base) == 2  # nothing cached, no --with-api
    assert "rerun with --with-api" in capsys.readouterr().err

    monkeypatch.setattr(
        backends_mod, "make_backend", lambda *a, **k: AnthropicBackend(OracleClient(), "m")
    )
    monkeypatch.setattr(backends_mod, "backend_key", lambda *a, **k: "anthropic/m")
    assert main(base + ["--with-api"]) == 0
    bad = write([{"a": "pub/commit-squash@x", "b": "pub/atomic-commits@x", "label": "tension"}])
    assert main([*base[:4], str(bad), *base[5:], "--with-api"]) == 1
    assert main(["ingest", "--holdout", str(good), str(tmp_path)]) == 2
