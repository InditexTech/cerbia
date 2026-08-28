import re

import pytest
from cerbia.core.preprocessors.speculative_decoding._types import (
    DecodedBranch,
    DecoderSpec,
    OutputPolicy,
    Payload,
    RejectionReason,
    SegmentCandidate,
)
from pydantic import ValidationError

pytestmark = pytest.mark.unit


def test_payload_from_text_preserves_utf8_text_and_raw_bytes() -> None:
    payload = Payload.from_text("decoded text")

    assert payload.raw == b"decoded text"
    assert payload.text == "decoded text"


def test_payload_from_bytes_preserves_binary_data_without_text_view() -> None:
    payload = Payload.from_bytes(b"\xff\xfe")

    assert payload.raw == b"\xff\xfe"
    assert payload.text is None


def test_decoder_spec_uses_default_behaviors_when_optional_fields_are_omitted() -> None:
    decoder = DecoderSpec(decoder_id="test")

    assert decoder.extract_patterns == ()
    assert decoder.chain_only is False
    assert decoder.input_gate("candidate") is True
    assert decoder.accepts(Payload.from_text("candidate")) is True
    assert decoder.decode(Payload.from_text("candidate")) == []
    assert decoder.output_policy == OutputPolicy()


def test_decoder_spec_default_gate_accepts_candidate() -> None:
    decoder = DecoderSpec(decoder_id="test")

    assert decoder.input_gate("candidate") is True


def test_decoder_spec_is_immutable_when_configuration_is_updated() -> None:
    decoder = DecoderSpec(decoder_id="test")
    field_name = "decoder_id"

    with pytest.raises(ValidationError):
        setattr(decoder, field_name, "updated")


def test_decoded_branch_and_segment_candidate_preserve_search_state() -> None:
    payload = Payload.from_text("decoded")
    segment = SegmentCandidate(start=4, end=11, text="encoded", hinted_decoders=("base64",))
    branch = DecodedBranch(payload=payload, chain=("base64",), depth=1, score=87.5)

    assert segment.model_dump() == {
        "start": 4,
        "end": 11,
        "text": "encoded",
        "hinted_decoders": ("base64",),
    }
    assert branch.model_dump() == {
        "payload": {"raw": b"decoded", "text": "decoded"},
        "chain": ("base64",),
        "depth": 1,
        "score": 87.5,
    }


def test_output_policy_preserves_expected_regular_expression() -> None:
    pattern = re.compile(r"[a-z]+")
    policy = OutputPolicy(expected_pattern=pattern, require_utf8=True)

    assert policy.expected_pattern is pattern
    assert policy.require_utf8 is True


def test_output_policy_inert_defaults() -> None:
    policy = OutputPolicy()

    assert policy.min_printable_ratio == 0.70
    assert policy.min_text_length == 4
    assert policy.entropy_range is None
    assert policy.expected_pattern is None
    assert policy.require_utf8 is False
    assert policy.min_chi_squared_pvalue == 0.0


def test_rejection_reason_exposes_stable_wire_values() -> None:
    expected_reasons = {
        "INPUT_GATE_FAILED": "INPUT_GATE_FAILED",
        "ACCEPTS_FAILED": "ACCEPTS_FAILED",
        "OUTPUT_POLICY_FAILED": "OUTPUT_POLICY_FAILED",
        "ACCEPTANCE_FAILED": "ACCEPTANCE_FAILED",
        "NO_IMPROVEMENT": "NO_IMPROVEMENT",
        "EXCESSIVE_DEPTH": "EXCESSIVE_DEPTH",
        "BUDGET_EXHAUSTED": "BUDGET_EXHAUSTED",
    }

    assert {reason.name: reason.value for reason in RejectionReason} == expected_reasons
