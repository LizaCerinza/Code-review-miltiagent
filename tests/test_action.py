"""Comprueba que action.yml es coherente con la configuración y la spec de ci-integration."""

from pathlib import Path

import yaml

from reviewer.config import ReviewConfig

ROOT = Path(__file__).resolve().parent.parent
ACTION = yaml.safe_load((ROOT / "action.yml").read_text(encoding="utf-8"))
INPUTS = ACTION["inputs"]


def test_expected_inputs():
    assert set(INPUTS) == {
        "provider", "azure-openai-api-key", "azure-openai-endpoint", "azure-openai-api-version",
        "anthropic-api-key", "github-token", "sonar-token", "sonar-host-url", "fail-on",
        "fail-on-agent-error", "model", "agent-timeout", "tasks-dir", "spec-globs",
        "guidelines-file", "skills-dir", "image", "model-functional", "model-security",
        "model-design", "azure-reasoning-effort",
    }


def test_defaults_match_reviewer_config():
    defaults = ReviewConfig()
    assert INPUTS["provider"]["default"] == defaults.provider
    assert INPUTS["azure-openai-api-version"]["default"] == defaults.azure_api_version
    assert INPUTS["model"]["default"] == ""
    assert INPUTS["azure-reasoning-effort"]["default"] == defaults.azure_reasoning_effort
    assert INPUTS["fail-on"]["default"] == defaults.fail_on
    assert INPUTS["fail-on-agent-error"]["default"] == "false"
    assert INPUTS["tasks-dir"]["default"] == defaults.tasks_dir
    assert INPUTS["spec-globs"]["default"] == ",".join(defaults.spec_globs)
    assert INPUTS["guidelines-file"]["default"] == defaults.guidelines_file
    assert INPUTS["skills-dir"]["default"] == defaults.skills_dir
    assert float(INPUTS["agent-timeout"]["default"]) == defaults.agent_timeout
    assert INPUTS["sonar-host-url"]["default"] == defaults.sonar_host


def test_composite_and_no_expressions_inside_run():
    """Las entradas llegan por `env`; interpolarlas en `run` permitiría inyección de shell."""
    assert ACTION["runs"]["using"] == "composite"
    for step in ACTION["runs"]["steps"]:
        assert "${{" not in step.get("run", "")


def test_every_input_reaches_a_step():
    env_text = " ".join(str(step.get("env", {})) for step in ACTION["runs"]["steps"])
    for name in INPUTS:
        assert f"inputs.{name}" in env_text, name


def test_docker_run_forwards_every_reviewer_variable():
    review = next(step for step in ACTION["runs"]["steps"] if step.get("id") == "review")
    for name in review["env"]:
        if name != "IMAGE":
            assert f"-e {name}" in review["run"], name


def test_private_ghcr_login_uses_stdin_token():
    """El token nunca debe pasar como argumento de línea de comandos (quedaría en los logs)."""
    review = next(step for step in ACTION["runs"]["steps"] if step.get("id") == "review")
    run = review["run"]
    login = next(line for line in run.splitlines() if "docker login ghcr.io" in line)
    assert "--password-stdin" in login
    assert " -p " not in login and "--password " not in login
    assert run.index("docker login") < run.index("docker pull")
