#!/usr/bin/env python3
"""
Commands to install dependencies and run tests.

TEST

Extra args:
    - s: Pass `-s` flag to pytest.
    - cov: Write coverage report.

"""

import nox
from pathlib import Path

COVERAGE_DIR = Path("coverage_reports")


def install_deps(session):
    """Install dependencies from requirements.txt."""

    session.install("-r", "requirements.txt")


@nox.session
def test_all(session):
    """Run all tests."""

    show = "s" in session.posargs
    cov = "cov" in session.posargs

    install_deps(session)
    _test_scripts(session, show=show, cov=cov)
    _test_mediabrowser(session, show=show, cov=cov)


@nox.session
def test_scripts(session):
    """Run all tests in `scripts/test`"""

    show = "s" in session.posargs
    cov = "cov" in session.posargs

    install_deps(session)
    _test_scripts(session, show=show, cov=cov)


@nox.session
def test_mediabrowser(session):
    """Run all tests in `mediabrowser/test`"""

    show = "s" in session.posargs
    cov = "cov" in session.posargs

    install_deps(session)
    _test_mediabrowser(session, show=show, cov=cov)


def _test_scripts(session, show=True, cov=True):
    args = _pytest_args(show)
    args += ["scripts/test", "--create-db"]

    if cov:
        cov_dir = COVERAGE_DIR.joinpath("populate_db")
        args += ["--cov=scripts/populate_db", f"--cov-report=html:{cov_dir}"]

    session.run(*args)


def _test_mediabrowser(session, show=True, cov=True):

    args = _pytest_args(show)
    args += ["mediabrowser/test", "--reuse-db"]

    if cov:
        cov_dir = COVERAGE_DIR.joinpath("mediabrowser")
        args += ["--cov=mediabrowser/views", f"--cov-report html:{cov_dir}"]

    session.run(*args)


def _pytest_args(show=False) -> list[str]:
    args = [
        "python",
        "-m",
        "pytest",
        "-v",
    ]
    if show:
        args.append("-s")

    return args
