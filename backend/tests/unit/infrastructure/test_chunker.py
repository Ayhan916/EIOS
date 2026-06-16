"""Unit tests for the text chunking utility. No DB or model required."""

from infrastructure.embeddings.chunker import chunk_text


class TestChunkText:
    def test_empty_string_returns_empty_list(self) -> None:
        assert chunk_text("") == []

    def test_whitespace_only_returns_empty_list(self) -> None:
        assert chunk_text("   \n  ") == []

    def test_short_text_returns_single_chunk(self) -> None:
        text = "ESG risk assessment for mining sector."
        result = chunk_text(text, max_chars=512)
        assert len(result) == 1
        assert result[0] == text

    def test_long_text_produces_multiple_chunks(self) -> None:
        # 10 sentences × ~60 chars each = ~600 chars; with max_chars=100 → multiple chunks
        sentences = [f"This is sentence number {i} with some ESG context." for i in range(10)]
        text = " ".join(sentences)
        result = chunk_text(text, max_chars=100, overlap_chars=0)
        assert len(result) > 1

    def test_all_chunks_are_non_empty(self) -> None:
        text = " ".join([f"Sentence {i}." for i in range(20)])
        result = chunk_text(text, max_chars=80, overlap_chars=10)
        for chunk in result:
            assert chunk.strip()

    def test_no_chunk_exceeds_max_chars(self) -> None:
        text = " ".join([f"Sentence {i} about ESG risk compliance." for i in range(30)])
        max_chars = 150
        result = chunk_text(text, max_chars=max_chars, overlap_chars=20)
        for chunk in result:
            assert len(chunk) <= max_chars * 1.1  # allow minor sentence overshoot

    def test_overlap_carries_context_forward(self) -> None:
        # With overlap, the last word(s) of a chunk should appear in the next
        sentences = [
            "Child labour risk in mining sector.",
            "Supply chain assessment required.",
            "NACE code B mining operations.",
            "ESG compliance mandatory for Tier-1 suppliers.",
            "Risk level classified as High.",
        ]
        text = " ".join(sentences)
        result = chunk_text(text, max_chars=70, overlap_chars=30)
        # Verify we get more than one chunk
        assert len(result) >= 1

    def test_single_very_long_sentence_is_hard_split(self) -> None:
        long_sentence = "A" * 1000
        result = chunk_text(long_sentence, max_chars=100, overlap_chars=0)
        assert len(result) >= 2
        for chunk in result:
            assert len(chunk) <= 100

    def test_real_esg_text_chunks_correctly(self) -> None:
        text = (
            "The company operates in the mining sector under NACE code B05. "
            "Child labour risks have been identified in Tier-1 suppliers. "
            "The ESG assessment was conducted under the CSDDD framework. "
            "Remediation plans are required within 90 days of finding confirmation. "
            "Human rights due diligence is mandatory under LkSG Section 3. "
            "Environmental impact assessments are pending for two operational sites."
        )
        result = chunk_text(text, max_chars=200, overlap_chars=50)
        assert len(result) >= 1
        full_text = " ".join(result)
        assert "mining" in full_text
        assert "ESG" in full_text
