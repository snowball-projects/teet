# teet

[Open teet](https://snowball-projects.github.io/teet/).

Twilight’s Eve Evo Toolkit: browse the original item catalogue, choose a class
and dungeon level, and optimize a six-item build. The optional Windows companion
controls the existing repeating-key/click and fishing helpers locally.

This began as Nas Delevski’s personal Warcraft III project: practical tools that
made a much-loved game more enjoyable and combined playing with analytical work.
The original notebooks, scripts and first commit remain in the repository.
The toolkit is maintained by snowball; Nas is its founder.

## Dashboard

The public interface uses only local HTML, CSS and JavaScript. No runtime
libraries, backend, accounts, telemetry or user-data uploads. The bundled snapshot
contains 114 items and 28 class/form profiles from original commit `a6b3d0f`;
its game version and current accuracy are not established. Blank stats follow
the original notebook convention and count as zero, not verified measurements.

```sh
npm ci
npm test
python3 -m unittest discover -s tests -v
npm run build
npm run dev
```

Node 22+ and Python 3.11+ build the static `dist/` directory. GitHub Pages deploys
that directory from main using the pinned workflow. `scripts/build.py` regenerates
`web/data.json` from the canonical CSVs and `helpers.py`. Python's standard library
is sufficient for the build; do not install desktop dependencies to host the site.

### Model

The browser uses an exact dynamic program for the original notebook's additive
class-weighted score. It selects one to six distinct item rows, applies class and
dungeon eligibility, and supports at most one item with positive critical chance
or multiplier, plus at least one magic-resistance or cooldown-speed item when
one is eligible. Those latter requirements are conditional, matching the original
helpers. The original “Grant Templar” weight-row typo is corrected to match
Grand Templar in the class catalogue. Infeasible combinations fail explicitly rather than displaying a partial
solver result. Only the class's primary `Total_DMG_*` weight contributes.

This reproduces the weighted model, not combat damage, stacking mechanics,
proc effects or optimal play. Weights are shown in the interface and remain in
`class_weights.csv`; item facts remain in `items.csv`. Preserve raw and derived
stat distinctions when changing them. Equal-scoring builds may differ from the
original solver's tie choice. Small exhaustive-search cases and an independent
HiGHS/PuLP reference check cover scoring and constraints.

## Local Windows automation

The hosted webpage cannot press game keys. Download `teet-local.zip` from its
Automation page, extract it, and run `start-local.bat` with Python **3.11–3.13**
installed. The launcher creates `.venv`, installs the pinned desktop dependencies,
and opens `http://127.0.0.1:8784/#automation`. Python 3.14 is not part of this
companion dependency baseline. Or run those steps manually:

```bat
py -3 -m venv .venv
.venv\Scripts\python -m pip install -r requirements-local.txt
.venv\Scripts\python companion.py
```

Nothing sends input until Start. Repeating input starts after a three-second
countdown and pauses unless a Warcraft window is foreground. Choose the original
E-key action or F1 twice followed by right click, at an interval from 0.2 to 60
seconds. Stop or Esc ends the helper. Fishing launches the original desktop
assistant, with foreground checks added; it retains F8 pause, F9 calibration,
F3 preview, F5 save and Esc quit. Only one helper runs at a time. Closing the
terminal stops the companion; closing the browser alone is not a stop command.
Keep the console open, and use Stop/Esc before switching tasks.

The server binds only to loopback, serves an explicit web directory and accepts
only bounded JSON start/stop commands from its own exact origin. It has no CORS,
remote control, arbitrary command execution, filesystem API or persistent account
state. The public site does not probe or call the companion. ROI calibration
remains a local `roi_config.json`. Never expose port 8784 on a network.

Controller validation, stop/focus behavior and request-origin protection are
tested with mocks. Real Windows capture/input and an active Warcraft game have
not been verified in this macOS development environment. The original helpers
were previously used by the founder, but that does not establish this new
launcher’s end-to-end compatibility with every Windows/game setup.

## Preservation, publishing and dormancy

Original commit `a6b3d0f` preserves the pre-dashboard project. The public web
release and downloadable companion are separate from those historical notebooks;
no notebook runs automatically. `old/` is intentionally retained for personal
history. No scheduled data refresh or running public server is required.
A dormant deployment keeps the dated item snapshot. Revive by checking the data
against a named game version, running the checks and deploying a new release.
Rollback means redeploying a checked tag. Assets use relative paths, so another
static host can replace Pages without rewriting the app. Hosting providers
process ordinary web request metadata under their own policies.

`docs/icon.png` is the master icon; the 180px and 32px versions in `web/` are
used by the app and browser. Preserve the source artwork when resizing it.

Original software is MIT-licensed; see [LICENSE](LICENSE). The name Warcraft III
and game-derived names/data remain the property of their respective owners and
are not relicensed by this software license. No official affiliation is implied.
