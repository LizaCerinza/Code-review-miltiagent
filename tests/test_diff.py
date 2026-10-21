from reviewer.diff import commentable_lines, split_unified_diff

PATCH = """@@ -1,3 +1,4 @@
 linea1
-vieja
+nueva
+otra
 linea3
@@ -20,2 +21,2 @@ function x() {
 contexto
-a
+b
\\ No newline at end of file"""


def test_commentable_lines_multiple_hunks():
    # Hunk 1: 1 contexto, 2-3 agregadas, 4 contexto. Hunk 2: 21 contexto, 22 agregada.
    assert commentable_lines(PATCH) == {1, 2, 3, 4, 21, 22}


def test_commentable_lines_empty_patch():
    assert commentable_lines("") == set()


GIT_DIFF = """diff --git a/src/new.ts b/src/new.ts
new file mode 100644
index 0000000..1111111
--- /dev/null
+++ b/src/new.ts
@@ -0,0 +1,2 @@
+export const a = 1;
+export const b = 2;
diff --git a/src/old.ts b/src/old.ts
deleted file mode 100644
index 2222222..0000000
--- a/src/old.ts
+++ /dev/null
@@ -1 +0,0 @@
-export const z = 0;
diff --git a/src/mod.ts b/src/mod.ts
index 3333333..4444444 100644
--- a/src/mod.ts
+++ b/src/mod.ts
@@ -1,2 +1,2 @@
 const x = 1;
-const y = 2;
+const y = 3;
\\ No newline at end of file
"""


def test_split_unified_diff_statuses_and_paths():
    files = split_unified_diff(GIT_DIFF)
    assert [(f.path, f.status) for f in files] == [
        ("src/new.ts", "added"),
        ("src/old.ts", "removed"),
        ("src/mod.ts", "modified"),
    ]
    assert commentable_lines(files[0].patch) == {1, 2}
    assert commentable_lines(files[1].patch) == set()
    assert commentable_lines(files[2].patch) == {1, 2}


def test_split_unified_diff_rename_without_changes():
    diff = """diff --git a/a.ts b/b.ts
similarity index 100%
rename from a.ts
rename to b.ts
"""
    files = split_unified_diff(diff)
    assert [(f.path, f.status) for f in files] == [("b.ts", "renamed")]
