"""Load questions from YAML files."""

import logging
from pathlib import Path

import yaml

from src.models.question import Question, QuestionFile

logger = logging.getLogger(__name__)

DEFAULT_QUESTIONS_DIR = Path(__file__).parent.parent.parent / "questions"


def load_question_file(path: Path) -> QuestionFile:
    """Load and validate a single question YAML file."""
    with open(path) as f:
        data = yaml.safe_load(f)
    return QuestionFile.model_validate(data)


def load_all_questions(
    questions_dir: Path = DEFAULT_QUESTIONS_DIR,
) -> list[Question]:
    """Load all questions from the questions directory.

    Recursively finds all .yaml/.yml files in the directory tree.
    """
    questions: list[Question] = []

    if not questions_dir.exists():
        logger.warning("Questions directory not found: %s", questions_dir)
        return questions

    for yaml_path in sorted(questions_dir.rglob("*.yaml")):
        try:
            qf = load_question_file(yaml_path)
            questions.extend(qf.questions)
            logger.info(
                "Loaded %d questions from %s", len(qf.questions), yaml_path.name
            )
        except Exception:
            logger.exception("Failed to load questions from %s", yaml_path)

    # Also check .yml files
    for yaml_path in sorted(questions_dir.rglob("*.yml")):
        try:
            qf = load_question_file(yaml_path)
            questions.extend(qf.questions)
            logger.info(
                "Loaded %d questions from %s", len(qf.questions), yaml_path.name
            )
        except Exception:
            logger.exception("Failed to load questions from %s", yaml_path)

    logger.info("Total questions loaded: %d", len(questions))
    return questions
