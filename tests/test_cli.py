import json

import pytest
from conftest import git

import reviewer.__main__ as cli
from reviewer.models import AgentReport, Finding, ReviewResult

AZURE = {"AZURE_OPENAI_API_KEY": "k", "AZURE_OPENAI_ENDPOINT": "https://r.openai.azure.com"}


@pytest.fixture
def repo(tmp_path):
    git(tmp_path, "init", "-q", "-b", "main")
    git(tmp_path, "config", "user.email", "t@t")
    git(tmp_path, "config", "user.name", "t")
    (tmp_path / "a.ts").write_text("export const a = 1;\n", encoding="utf-8")
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-q", "-m", "init")
    git(tmp_path, "checkout", "-q", "-b", "feature")
    (tmp_path / "a.ts").write_text("export const a = 2;\n", encoding="utf-8")
    git(tmp_path, "commit", "-q", "-am", "feat: cambia a #mi-tarea")
    return tmp_path


def fake_review(result, calls):
    async def _review(ctx, config, provider=None):
        calls.append(ctx)
        return result
    return _review


def make_result(blocking):
    finding = Finding(file="a.ts", line=1, severity="critical" if blocking else "minor",
                      title="t", message="m", evidence="e", agents=["security"])
    return ReviewResult(reports=[AgentReport(agent="security")], findings=[finding],
                        fail_on="critical", blocking=blocking, incomplete=False)


def test_missing_model_credentials_exit_2_without_calling_agents(repo, monkeypatch, capsys):
    calls = []
    monkeypatch.setattr(cli, "review", fake_review(make_result(False), calls))
    code = cli.main(["--local", "--workspace", str(repo)], env={})
    assert code == 2
    assert calls == []
    err = capsys.readouterr().err
    assert "AZURE_OPENAI_API_KEY" in err and "AZURE_OPENAI_ENDPOINT" in err


def test_pr_mode_requires_repo_and_pr(repo):
    assert cli.main(["--workspace", str(repo)], env=AZURE) == 2


def test_blocking_result_exits_1_and_writes_report(repo, tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(cli, "review", fake_review(make_result(True), calls))
    out = tmp_path / "out"
    summary = tmp_path / "summary.md"
    env = {**AZURE, "GITHUB_STEP_SUMMARY": str(summary)}

    code = cli.main(["--local", "--workspace", str(repo), "--output-dir", str(out)], env=env)

    assert code == 1
    ctx = calls[0]
    assert [f.path for f in ctx.files] == ["a.ts"]
    assert "#mi-tarea" in ctx.description
    report = json.loads((out / "ai-review.json").read_text(encoding="utf-8"))
    assert report["failed"] is True and report["blocking"] is True
    assert "Code review multiagente" in summary.read_text(encoding="utf-8")


def test_non_blocking_result_exits_0(repo, tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "review", fake_review(make_result(False), []))
    code = cli.main(["--local", "--workspace", str(repo), "--output-dir", str(tmp_path)],
                    env=AZURE)
    assert code == 0


def test_invalid_base_exits_2(repo):
    code = cli.main(["--local", "--base", "no-existe", "--workspace", str(repo)],
                    env=AZURE)
    assert code == 2


def test_invalid_env_config_exits_2(repo):
    code = cli.main(["--local", "--workspace", str(repo)],
                    env={**AZURE, "REVIEWER_FAIL_ON": "nope"})
    assert code == 2


def test_anthropic_provider_requires_its_own_key(repo):
    code = cli.main(["--local", "--provider", "anthropic", "--workspace", str(repo)], env=AZURE)
    assert code == 2


def test_print_graph(capsys):
    assert cli.main(["--print-graph"], env={}) == 0
    assert "aggregate" in capsys.readouterr().out
