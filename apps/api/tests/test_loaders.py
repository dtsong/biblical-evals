"""Tests for question and config loaders."""

from pathlib import Path

from src.loaders.config_loader import load_app_config
from src.loaders.question_loader import load_all_questions


def test_load_all_questions():
    """Verify all YAML question files load and validate."""
    questions = load_all_questions()
    assert len(questions) >= 10, f"Expected at least 10 questions, got {len(questions)}"

    # Check each question has required fields
    ids = set()
    for q in questions:
        assert q.id, "Question must have an ID"
        assert q.text, "Question must have text"
        assert q.type in ("theological", "factual", "interpretive")
        assert q.id not in ids, f"Duplicate question ID: {q.id}"
        ids.add(q.id)


def test_load_app_config():
    """Verify all YAML config files load and validate."""
    config = load_app_config()
    assert len(config.models) >= 1, "Should have at least one model configured"
    assert len(config.perspectives) >= 1, "Should have at least one perspective"
    assert len(config.dimensions) >= 1, "Should have at least one scoring dimension"
    assert len(config.templates) >= 1, "Should have at least one prompt template"


def test_question_files_exist():
    """Verify the questions directory structure exists."""
    questions_dir = Path(__file__).parent.parent / "questions"
    assert questions_dir.exists(), "questions/ directory should exist"

    categories = {"theological", "factual", "interpretive"}
    found = {d.name for d in questions_dir.iterdir() if d.is_dir()}
    assert categories.issubset(found), f"Missing categories: {categories - found}"


def test_config_files_exist():
    """Verify all config files exist."""
    config_dir = Path(__file__).parent.parent / "config"
    expected = [
        "models.yaml",
        "perspectives.yaml",
        "scoring_dimensions.yaml",
        "prompt_templates.yaml",
    ]
    for filename in expected:
        assert (config_dir / filename).exists(), f"Missing config file: {filename}"
