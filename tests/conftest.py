import subprocess


def git(cwd, *args):
    """Ejecuta git en `cwd`; si falla, el test muestra el mensaje de error de git."""
    result = subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, text=True)
    if result.returncode != 0:
        raise AssertionError(
            f"git {' '.join(args)} falló ({result.returncode}): {result.stderr.strip()}"
        )
