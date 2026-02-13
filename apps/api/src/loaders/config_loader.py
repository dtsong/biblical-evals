"""Load YAML configuration files."""

import logging
from pathlib import Path

import yaml
from pydantic import BaseModel, Field

from src.models.score import ScoreDimension

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_DIR = Path(__file__).parent.parent.parent / "config"


class ModelConfig(BaseModel):
    """Configuration for a single LLM model."""

    name: str
    provider: str
    litellm_model: str
    api_key_env: str


class ModelsConfig(BaseModel):
    """Top-level models configuration."""

    models: list[ModelConfig]


class PerspectiveConfig(BaseModel):
    """Configuration for a theological perspective."""

    id: str
    name: str
    description: str


class PerspectivesConfig(BaseModel):
    """Top-level perspectives configuration."""

    perspectives: list[PerspectiveConfig]


class DimensionsConfig(BaseModel):
    """Top-level scoring dimensions configuration."""

    dimensions: list[ScoreDimension]


class PromptTemplate(BaseModel):
    """A prompt template configuration."""

    id: str
    name: str
    version: str
    description: str
    template: str


class TemplatesConfig(BaseModel):
    """Top-level prompt templates configuration."""

    templates: list[PromptTemplate]


class AppConfig(BaseModel):
    """Aggregated application configuration from all YAML files."""

    models: list[ModelConfig] = Field(default_factory=list)
    perspectives: list[PerspectiveConfig] = Field(default_factory=list)
    dimensions: list[ScoreDimension] = Field(default_factory=list)
    templates: list[PromptTemplate] = Field(default_factory=list)


def _load_yaml(path: Path) -> dict:
    """Load a YAML file and return its contents."""
    with open(path) as f:
        return yaml.safe_load(f) or {}


def load_app_config(config_dir: Path = DEFAULT_CONFIG_DIR) -> AppConfig:
    """Load all configuration files from the config directory."""
    config = AppConfig()

    models_path = config_dir / "models.yaml"
    if models_path.exists():
        data = _load_yaml(models_path)
        parsed = ModelsConfig.model_validate(data)
        config.models = parsed.models

    perspectives_path = config_dir / "perspectives.yaml"
    if perspectives_path.exists():
        data = _load_yaml(perspectives_path)
        parsed_p = PerspectivesConfig.model_validate(data)
        config.perspectives = parsed_p.perspectives

    dimensions_path = config_dir / "scoring_dimensions.yaml"
    if dimensions_path.exists():
        data = _load_yaml(dimensions_path)
        parsed_d = DimensionsConfig.model_validate(data)
        config.dimensions = parsed_d.dimensions

    templates_path = config_dir / "prompt_templates.yaml"
    if templates_path.exists():
        data = _load_yaml(templates_path)
        parsed_t = TemplatesConfig.model_validate(data)
        config.templates = parsed_t.templates

    logger.info(
        "Loaded config: %d models, %d perspectives, %d dimensions, %d templates",
        len(config.models),
        len(config.perspectives),
        len(config.dimensions),
        len(config.templates),
    )
    return config
