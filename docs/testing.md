# Tests, lint and coverage

GitHub Actions runs the Python tooling checks on Windows with Python 3.12 for
pushes to `main`, pull requests, and manual runs. The tests construct synthetic
inputs; they do not need a disc dump, BIOS, save, downloaded soundfont, or running
game. Windows is used because the profiling modules import Windows APIs.

From the repository root, in a Python virtual environment:

```powershell
python -m pip install -r tools/requirements-dev.txt
python -m unittest discover -s tests -p "test_*.py" -v
python -m ruff check tools tests
python -m coverage run -m unittest discover -s tests -p "test_*.py"
python -m coverage report
python -m coverage html
python -m coverage xml
```

The initial Ruff gate checks syntax, invalid control flow and undefined names.
It does not enforce a formatting style. Configuration and coverage scope live
in `pyproject.toml`; coverage includes all Python modules under `tools`, including
unexecuted CLI paths, and measures branches as well as statements.

Open `output/coverage/html/index.html` for annotated source coverage. In Actions,
the **Python coverage** run includes the per-file percentages in its summary and
uploads HTML and XML as the `python-coverage` artifact, retained for 14 days.
The README coverage badge reports whether that job succeeded; it is not a
percentage badge or a coverage threshold. No external coverage account or token
is required. Workflow badges become live after the workflows are pushed and run.

The native C/C++ regression suite is separate. After generating and building the
local Windows targets using the [build instructions](windows-baseline.md), run:

```powershell
ctest --test-dir build-windows -C Release --output-on-failure
```

Native tests, full game compilation, and gameplay validation are not represented
by the Python badges. The full build needs locally owned game inputs and the
pinned framework. Python source coverage does not measure the emulator, generated
game code, or how much of the campaign has been tested.

Badge URLs follow the [GitHub workflow badge documentation](https://docs.github.com/en/actions/how-tos/monitor-workflows/add-a-status-badge).
