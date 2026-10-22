"""The extract cache builds paths from an index's extract_model and a skill's content_hash;
both come from outside and must not leave the cache."""

import pytest

from skillfetch.ingest.extract_cache import ExtractCache

DIGEST = "a" * 64


def test_model_segments_stay_under_the_cache(tmp_path):
    cache = ExtractCache(tmp_path)
    path = cache.path(DIGEST, "openrouter/openai/gpt-6-luna")
    assert path.parent.parts[-3:] == ("openrouter", "openai", "gpt-6-luna")
    assert path.is_relative_to(tmp_path)


@pytest.mark.parametrize("model", ["../../x", "/abs", "a\\..\\b", "C:x", ""])
def test_unsafe_models_are_refused(tmp_path, model):
    with pytest.raises(ValueError, match="refusing extract model"):
        ExtractCache(tmp_path).path(DIGEST, model)


@pytest.mark.parametrize("digest", ["../../x", "A" * 64, "a" * 63, ""])
def test_content_hash_must_be_a_digest(tmp_path, digest):
    with pytest.raises(ValueError, match="refusing content_hash"):
        ExtractCache(tmp_path).path(digest, "m")
