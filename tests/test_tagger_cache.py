from __future__ import annotations

from types import SimpleNamespace

import numpy as np

from imgtagplus.tagger import Tagger


class _DummyTokenizer:
    def tokenize(self, texts: list[str]) -> np.ndarray:
        return np.ones((len(texts), 4), dtype=np.int64)


class _DummyTextSession:
    def __init__(self) -> None:
        self.calls = 0

    def get_inputs(self) -> list[SimpleNamespace]:
        return [SimpleNamespace(name="input_ids")]

    def run(self, _output_names, feeds):
        self.calls += 1
        batch_size = feeds["input_ids"].shape[0]
        return [np.ones((batch_size, 3), dtype=np.float32)]


class _FailingTextSession(_DummyTextSession):
    def run(self, _output_names, feeds):
        raise AssertionError("Expected cached embeddings to be used instead of recomputing")


def test_precompute_tag_embeddings_uses_disk_cache(tmp_path) -> None:
    tags = ["alpha", "beta"]
    tagger = Tagger.__new__(Tagger)
    tagger._model_dir = tmp_path
    tagger._tokenizer = _DummyTokenizer()
    tagger._txt_session = _DummyTextSession()
    tagger._text_embeds = None

    tagger.precompute_tag_embeddings(tags)

    cache_path = tagger._tag_embedding_cache_path(tags)
    assert cache_path.exists()
    assert tagger._txt_session.calls == 1

    tagger._txt_session = _FailingTextSession()
    tagger._text_embeds = None
    tagger.precompute_tag_embeddings(tags)

    assert tagger._text_embeds is not None
    assert tagger._text_embeds.shape == (2, 3)
