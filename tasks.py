"""DEVELOPMENT FILE WITH INVOKE TASKS"""

from invoke import task


@task
def run(c, host="127.0.0.1", port=8000, reload=True):
    """Run the FastAPI development server with Uvicorn."""
    print(f"[STARTING]: Launching FastAPI server on {host}:{port}...")
    reload_flag = "--reload" if reload else ""
    c.run(
        f"poetry run uvicorn src.documentation_helper.main:app {reload_flag} --host {host} --port {port}"
    )


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
def typecheck(c):
    """Run mypy type checker across the codebase."""
    print("[CHECKING]: Running MyPy static type analysis...")
    c.run("poetry run mypy src")


@task
def test(c):
    """Run the unit test suite using pytest."""
    print("[EXECUTING]: Running unit tests...")
    c.run("poetry run pytest")


@task
def coverage(c, html=True):
    """Run tests and generate coverage report."""
    print("[CALCULATING]: Running pytest coverage analysis...")
    html_flag = "--cov-report=html" if html else ""
    c.run(f"poetry run pytest --cov=src --cov-report=term-missing {html_flag}")
    if html:
        print("[SUCCESS]: HTML coverage report generated in htmlcov/index.html")


@task
def clean(c):
    """Remove cache, temporary files, and build artifacts."""
    print("[CLEANING]: Removing Python caches and test artifacts...")
    c.run('find . -type d -name "__pycache__" -exec rm -rf {} +')
    c.run('find . -type d -name ".pytest_cache" -exec rm -rf {} +')
    c.run('find . -type d -name ".ruff_cache" -exec rm -rf {} +')
    c.run('find . -type d -name ".mypy_cache" -exec rm -rf {} +')
    c.run('find . -type d -name "htmlcov" -exec rm -rf {} +')
    c.run('find . -type f -name ".coverage" -delete')


@task(pre=[check, test])
def ci(c):
    """Run all quality gates (Lint + Type check + Tests) for CI/CD pipelines."""
    print("[SUCCESS]: All quality checks passed successfully!")
