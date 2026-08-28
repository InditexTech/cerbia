import pytest
from cerbia.core.models.entries import Entry
from cerbia.core.preprocessors.speculative_decoding import SpeculativeDecodingPreprocessor

from ._corpus import INTENSIVE_ONLY, MUST_DECODE, MUST_NOT_DECODE, CorpusEntry

pytestmark = pytest.mark.unit


def test_corpus_preserves_the_full_approved_legacy_behavior_inventory() -> None:
    """Keep every approved legacy corpus behavior represented once."""
    assert len(MUST_NOT_DECODE) == 31
    assert len(MUST_DECODE) == 20
    assert len(INTENSIVE_ONLY) == 5


@pytest.mark.parametrize("case", MUST_NOT_DECODE, ids=lambda case: case.id)
def test_preprocessor_preserves_false_positive_corpus_cases(case: CorpusEntry) -> None:
    """Keep safe prose, identifiers, URLs, and colors unchanged through the real engine."""
    entry = Entry(text=case.text, source=f"corpus/{case.id}")

    result = SpeculativeDecodingPreprocessor(intensive_mode=True).process([entry])

    assert result == [entry]
    assert result[0] is entry


@pytest.mark.parametrize("case", MUST_DECODE, ids=lambda case: case.id)
def test_preprocessor_decodes_every_approved_corpus_case(case: CorpusEntry) -> None:
    """Exercise every approved decode family through extraction, search, and derivation."""
    assert case.expected_output is not None

    result = SpeculativeDecodingPreprocessor().process([Entry(text=case.text, source=f"corpus/{case.id}")])

    assert result[0].text == case.expected_output


@pytest.mark.parametrize("case", INTENSIVE_ONLY, ids=lambda case: case.id)
def test_preprocessor_skips_intensive_corpus_cases_by_default(case: CorpusEntry) -> None:
    """Require explicit opt-in before whole-text intensive decoding is attempted."""
    entry = Entry(text=case.text, source=f"corpus/{case.id}")

    result = SpeculativeDecodingPreprocessor().process([entry])

    assert result == [entry]


@pytest.mark.parametrize("case", INTENSIVE_ONLY, ids=lambda case: case.id)
def test_preprocessor_decodes_intensive_corpus_cases_when_enabled(case: CorpusEntry) -> None:
    """Prove intensive-mode decoding uses the real public preprocessor path."""
    assert case.expected_output is not None

    result = SpeculativeDecodingPreprocessor(intensive_mode=True).process(
        [Entry(text=case.text, source=f"corpus/{case.id}")]
    )

    assert result[0].text == case.expected_output
