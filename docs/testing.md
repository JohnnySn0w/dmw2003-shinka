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

The September 15 local build passed 18 Shinka suites plus the pinned dependency's
`example` test (19 CTest entries). Coverage includes menu ownership and text,
evolution hints, EXP/encounters, travel policy, controller shortcuts, memory-card
batching and progress, view/layout rules, music switching, movie/CD scheduling,
minimized pause and battle motion. These are regression categories, not a count
of tested game scenes. List the entries in your own configured build with:

```powershell
ctest --test-dir build-windows -C Release -N
```

Native tests, full game compilation, and gameplay validation are not represented
by the Python badges. The full build needs locally owned game inputs and the
pinned framework. Python source coverage does not measure the emulator, generated
game code, or how much of the campaign has been tested.

Badge URLs follow the [GitHub workflow badge documentation](https://docs.github.com/en/actions/how-tos/monitor-workflows/add-a-status-badge).

The separate [website workflow](website-publishing.md) checks local links,
media controls and JavaScript syntax. Its public deployment job runs only on an
explicit manual request from `main`; normal pushes and pull requests only validate.

For website-only edits, run the focused checks from the repository root:

```powershell
python tools/check_website.py
python -m unittest discover -s tests -p test_website.py -v
node --check website/dist/app.js
```

Also inspect desktop and phone layouts, GIF play/stop, video chapter seeking,
pause/resume, and captions. Automated link checks do not prove layout or audio
quality. The September 15 refresh was checked at 1440, 390 and 320 CSS-pixel
viewport widths; media stays idle until the visitor starts it.

For gameplay changes, use copied cards and record the build revision, scene,
settings, entry method and result. Separate ordinary play from developer warps
and synthetic flag fixtures. UI animation fixes need multiple frames or a full
pulse cycle, not just one settled screenshot. Never commit the private cards,
RAM snapshots or generated packet traces used for those checks.
