import nox


@nox.session
def install_deps(session, test=True, dev=False):

    pyproject = nox.project.load_toml("pyproject.toml")
    deps = pyproject["project"]["dependencies"]
    if test:
        deps.update(**pyproject["project"]["optional-dependencies"]["test"])
    if dev:
        deps.update(**pyproject["project"]["optional-dependencies"]["dev"])

    session.install(*deps)
