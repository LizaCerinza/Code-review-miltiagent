import pytest

from reviewer.tasks import extract_task_names, resolve_tasks


@pytest.fixture
def workspace(tmp_path):
    tasks = tmp_path / "docs" / "tasks"
    tasks.mkdir(parents=True)
    (tasks / "add-user-roles.md").write_text("# Roles\n- Criterio 1", encoding="utf-8")
    (tasks / "tarea-b.md").write_text("# B", encoding="utf-8")
    (tmp_path / "docs" / "secret.md").write_text("no", encoding="utf-8")
    return tmp_path


def test_valid_hashtag(workspace):
    result = resolve_tasks(workspace, "docs/tasks", "Agrega roles", "Implementa #add-user-roles")
    assert result.found == {"docs/tasks/add-user-roles.md": "# Roles\n- Criterio 1"}
    assert result.missing == []


def test_hashtag_with_extension(workspace):
    result = resolve_tasks(workspace, "docs/tasks", "", "Ver #add-user-roles.md.")
    assert list(result.found) == ["docs/tasks/add-user-roles.md"]


def test_numeric_hashtag_is_issue_reference(workspace):
    result = resolve_tasks(workspace, "docs/tasks", "", "Closes #12")
    assert not result.referenced


def test_multiple_tasks_from_title_and_description(workspace):
    result = resolve_tasks(workspace, "docs/tasks", "feat #tarea-b", "#add-user-roles y #tarea-b")
    assert list(result.found) == ["docs/tasks/tarea-b.md", "docs/tasks/add-user-roles.md"]


def test_missing_task_file(workspace):
    result = resolve_tasks(workspace, "docs/tasks", "", "#tarea-x")
    assert result.found == {}
    assert result.missing == [("tarea-x", "docs/tasks/tarea-x.md")]
    assert result.referenced


def test_path_traversal_is_not_resolved(workspace):
    result = resolve_tasks(workspace, "docs/tasks", "", "#../secret y #a..b")
    assert result.found == {}
    assert not result.referenced


def test_ignores_markdown_headings_urls_and_entities():
    text = "# Título\n## Sub\nver https://x.com/page#anchor y &#123; y C#"
    assert extract_task_names(text) == []
