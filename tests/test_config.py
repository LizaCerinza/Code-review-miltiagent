import pytest

from reviewer.config import ConfigError, ReviewConfig


def test_defaults_match_ci_integration_spec():
    config = ReviewConfig.from_env({})
    assert config.fail_on == "critical"
    assert config.fail_on_agent_error is False
    assert config.tasks_dir == "docs/tasks"
    assert config.spec_globs == ("openspec/specs/**/*.md",)
    assert config.guidelines_file == "REVIEW_GUIDELINES.md"
    assert config.provider == "azure"
    assert config.model_for("security") == "gpt-4.1-mini"
    assert config.azure_api_version == "2024-10-21"


def test_env_overrides_and_per_agent_model():
    config = ReviewConfig.from_env(
        {
            "REVIEWER_FAIL_ON": "none",
            "REVIEWER_FAIL_ON_AGENT_ERROR": "true",
            "REVIEWER_MODEL_DESIGN": "claude-sonnet-5-5",
            "REVIEWER_SPEC_GLOBS": "specs/*.md, docs/**/*.md",
            "REVIEWER_AGENT_TIMEOUT": "120",
        }
    )
    assert config.fail_on == "none"
    assert config.fail_on_agent_error is True
    assert config.model_for("design") == "claude-sonnet-5-5"
    assert config.model_for("security") == "gpt-4.1-mini"
    assert config.spec_globs == ("specs/*.md", "docs/**/*.md")
    assert config.agent_timeout == 120.0


def test_empty_env_values_keep_defaults():
    config = ReviewConfig.from_env({"REVIEWER_TASKS_DIR": "", "REVIEWER_FAIL_ON": "  "})
    assert config.tasks_dir == "docs/tasks"
    assert config.fail_on == "critical"


def test_cli_overrides_ignore_none():
    config = ReviewConfig().with_overrides(fail_on="major", tasks_dir=None)
    assert config.fail_on == "major"
    assert config.tasks_dir == "docs/tasks"


@pytest.mark.parametrize(
    "env",
    [
        {"REVIEWER_FAIL_ON": "blocker"},
        {"REVIEWER_EFFORT": "extreme"},
        {"REVIEWER_AGENT_TIMEOUT": "abc"},
        {"REVIEWER_FAIL_ON_AGENT_ERROR": "quizas"},
        {"REVIEWER_PROVIDER": "gemini"},
    ],
)
def test_invalid_values_raise_config_error(env):
    with pytest.raises(ConfigError):
        ReviewConfig.from_env(env)


def test_anthropic_provider_uses_claude_by_default():
    config = ReviewConfig.from_env({"REVIEWER_PROVIDER": "anthropic"})
    assert config.model_for("functional") == "claude-opus-5-5"
    config = ReviewConfig.from_env({"REVIEWER_PROVIDER": "anthropic", "REVIEWER_MODEL": "x"})
    assert config.model_for("functional") == "x"
