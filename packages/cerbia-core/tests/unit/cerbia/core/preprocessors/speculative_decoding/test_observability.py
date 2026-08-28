import pytest
from cerbia.core.models.entries import Entry
from cerbia.core.preprocessors.speculative_decoding import SpeculativeDecodingPreprocessor
from cerbia.core.preprocessors.speculative_decoding._observability import capture_rejections, record_rejection
from cerbia.core.preprocessors.speculative_decoding._types import (
    DecodedBranch,
    Payload,
    RejectionReason,
    SegmentCandidate,
)

pytestmark = pytest.mark.unit


def test_capture_rejections_counts_only_non_null_reasons() -> None:
    with capture_rejections() as rejections:
        record_rejection(reason=None)
        record_rejection(reason=RejectionReason.NO_IMPROVEMENT)

    assert rejections == {RejectionReason.NO_IMPROVEMENT: 1}


def test_preprocessor_preserves_decoded_output_and_rejection_metadata(mocker) -> None:
    sensitive_payload = "wave8-sensitive-payload-DO-NOT-LOG"
    segment = SegmentCandidate(
        start=7,
        end=7 + len(sensitive_payload),
        text=sensitive_payload,
        hinted_decoders=("base64",),
    )
    branch = DecodedBranch(
        payload=Payload.from_text("decoded"),
        chain=("base64", "rot13"),
        depth=2,
        score=75.0,
    )
    preprocessor = SpeculativeDecodingPreprocessor()
    mocker.patch(
        "cerbia.core.preprocessors.speculative_decoding._preprocessor.decode_text",
        return_value=[(segment, branch)],
    )

    result = preprocessor.process([Entry(text=f"prefix {sensitive_payload} suffix", source="inline")])

    assert result[0].text == "prefix decoded suffix"
    assert result[0].metadata.preprocessors["speculative_decoding"] == {
        "rejections": {},
        "decoded_segments": [
            {
                "decoder_chain": ["base64", "rot13"],
                "span": [7, 7 + len(sensitive_payload)],
                "original_segment": sensitive_payload,
                "decoded_segment": "decoded",
            }
        ],
    }


def test_record_rejection_increments_counter_for_concrete_reason() -> None:
    with capture_rejections() as rejections:
        record_rejection(
            reason=RejectionReason.OUTPUT_POLICY_FAILED,
        )

    assert rejections == {RejectionReason.OUTPUT_POLICY_FAILED: 1}
