"""Tests for runners."""

from src.runners.import_runner import ImportBatch, ImportedResponse


def test_import_batch_validation():
    """Verify ImportBatch schema validates correctly."""
    batch = ImportBatch(
        responses=[
            ImportedResponse(
                question_id="SOT-001",
                model_name="gpt-4o",
                response_text="Faith and works are related...",
                metadata={"tokens": 150},
            ),
            ImportedResponse(
                question_id="SOT-001",
                model_name="claude-sonnet-4-5",
                response_text="The relationship between faith and works...",
            ),
        ]
    )
    assert len(batch.responses) == 2
    assert batch.responses[0].model_name == "gpt-4o"
    assert batch.responses[1].metadata == {}


def test_import_batch_empty():
    """Empty batch is valid."""
    batch = ImportBatch(responses=[])
    assert len(batch.responses) == 0
