"""DEVELOPMENT FILE WITH INVOKE TASKS"""

from invoke import task


@task
def format(c):
    """Run code formatters (Ruff format and lint auto-fixes)."""
    print("[FIXING]: Running code formatting and auto-fixes...")
    c.run("poetry run ruff format .")
    c.run("poetry run ruff check . --fix")


@task
def check(c):
    """Check code for linting and formatting issues without modifying files."""
    print("[SEARCHING]: Checking lint rules...")
    c.run("poetry run ruff check .")
    print("[SEARCHING]: Checking code formatting rules...")
    c.run("poetry run ruff format . --check")


@task
def test(c):
    """Run the unit test suite using pytest."""
    print("[EXECUTING]: Running unit tests...")
    c.run("poetry run pytest")


@task(pre=[check, test])
def ci(c):
    """Run all quality gates (Lint check + Tests) for CI/CD pipelines."""
    print("[SUCCESS]: All quality checks passed successfully!")
