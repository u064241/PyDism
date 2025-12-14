# PyDism

Python rewrite of the legacy batch menu to operate on Windows image files (WIM / ESD) using DISM and (optionally) wimlib.

**NEW FEATURE: TAB Autocompletion** — Path input now supports TAB completion powered by `prompt_toolkit`. Press TAB to autocomplete file/folder paths.

> If you prefer the original Italian text it is preserved at the bottom of this file.

## Table of Contents

1. Overview
2. Requirements
3. Quick Start
4. TAB Autocompletion
5. Operational Notes
6. Status Line Indicators
7. Settings & Persistence
8. Menu 19 Defaults
9. Console Window Positioning
10. Packaging (README + binaries)
11. wimlib-imagex Integration
12. Elevation Strategy (UAC)
13. Quick Guide: auto-py-to-exe
14. Console Colors (VT / colorama)
15. Temporary Directory Warnings
16. Menu Entries (Feature List)
17. Split WIM (Best Practices)

## 1. Overview

PyDism is an interactive console tool to list, mount, modify and export Windows image indexes from `.wim` / `.esd` files. It wraps common DISM operations and can optionally leverage `wimlib-imagex` for faster export/convert steps with progress feedback.

## 2. Requirements

- Windows
- Administrator privileges (the script attempts self-elevation)
- DISM available in PATH (standard on Windows)
- (Optional) `wimlib-imagex.exe` in the same folder or in PATH for accelerated export/convert

## 3. Quick Start

Open an elevated PowerShell in the project folder and run:

```powershell
# from C:\SOURCECODE\PYTHON\WIM (or the folder containing PyDism.py)
.venv\Scripts\python.exe PyDism.py
```

If not elevated, the script relaunches with UAC.

### Python Environment Setup

**Important:** PyDism requires the correct Python interpreter with required dependencies installed.

```bash
# Create and activate virtual environment
python -m venv .venv
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

**Verify installation:**

```bash
.venv\Scripts\python -c "import prompt_toolkit; print('✓ OK')"
```

**Run with correct interpreter:**

```bash
# ✓ CORRECT - uses venv with dependencies
.venv\Scripts\python.exe PyDism.py

# ✗ WRONG - uses global Python without dependencies
py PyDism.py
```

## 4. TAB Autocompletion

**New Feature**: Press TAB while typing file paths to autocomplete and browse available files/folders.

### How it Works

When PyDism prompts for a path (e.g., "Path to install.wim:"):

1. Start typing: `C:\Sources\in`
2. Press **TAB** to:
   - Auto-complete the path if it matches exactly one file
   - Show available suggestions if multiple matches exist
   - Cycle through results with repeated TAB presses

**Example:**

```text
Path to install.wim: C:\Sources\in[TAB]
Path to install.wim: C:\Sources\install.wim
```

### Powered by prompt_toolkit

Autocompletion uses the `prompt_toolkit` library with `PathCompleter`:

- **Library**: `prompt_toolkit>=3.0.0`
- **Feature**: Windows/Linux compatible console input
- **Fallback**: If unavailable, falls back to standard `input()` without completion

### Troubleshooting TAB Autocompletion

#### TAB keys not working?

#### Check 1: Python Interpreter

```bash
# ❌ This uses global Python 3.14 which lacks prompt_toolkit
py PyDism.py

# ✓ This uses venv with prompt_toolkit installed
.venv\Scripts\python.exe PyDism.py
```

#### Check 2: Verify prompt_toolkit Installation

```bash
.venv\Scripts\pip list | findstr prompt_toolkit
# Expected output: prompt_toolkit   3.0.52
```

#### Check 3: Look for Debug Messages

```text
[DEBUG] prompt_toolkit caricato con successo  ← autocompletion available
[DEBUG] Usando prompt_toolkit...              ← currently using autocompletion

[DEBUG] prompt_toolkit NON disponibile        ← not installed
[DEBUG] Usando input() standard               ← using standard input (no TAB)
```

#### Still not working?

1. **Reinstall prompt_toolkit**:

```bash
.venv\Scripts\pip install --upgrade prompt_toolkit
```

1. **Verify venv activation**:

```bash
# Should show venv path
where python
# Output: C:\SOURCECODE\.venv\Scripts\python.exe
```

1. **Check for console conflicts**:
   - Some SSH clients or terminal emulators may not support TAB input
   - Try running from Windows PowerShell directly

## 5. Operational Notes

- Modification operations (enable/disable feature, add package/driver, component cleanup) are not allowed on `.ESD` images.
- During feature filtering DISM output is forced to English to ensure reliable text matching.
- If you pick `recovery` compression but the destination is `.wim`, it is transparently changed to `max`.
- Temporary mount directories are created under a random folder inside `%TEMP%` and auto-unmounted.
- Error log: `%TEMP%/PyDism_Errors.log`.
- Verbose (captured stdout/stderr) log: enable via menu 19 → `%TEMP%/PyDism_Verbose.log`.
- Set a custom base mount directory via menu 18 (helpful if `%TEMP%` has low free space).
- Fast export/convert: if `wimlib-imagex` is available and backend is `wimlib` (or `auto` selects it) the tool uses it instead of DISM and shows a single-line percentage progress.
- View recent logs via menu 17 (Error and Verbose).
- Backend + wimlib indicator: status line shows `[wimlib …]` next to `[ExportBackend: ...]`; if version detected (e.g. `1.14.x`) it is displayed, else the source (`local next to exe`, `system PATH`) or `missing`.
- Help entry: menu 20 opens this README.
- Utility: menu 21 opens the Split WIM workflow guide (README.md); menu 22 opens the log folder (`%TEMP%`).
- Single-line progress bars: long DISM ops (Mount/Unmount, Add-Package/Driver, Cleanup-Image, Enable/Disable-Feature, DISM export, boot.wim operations) and wimlib show an updating line to avoid flooding the console. Toggle in menu 19.
- Informational spinner: for commands without reliable percentages (Get-Features, Get-WimInfo) a spinner is shown while output is captured. Toggle in menu 19.
- Menu 15 (Integrity check) uses `DISM /Cleanup-Image` with `CheckHealth` and `ScanHealth`.
- Temporary mount folders created in the session are tracked and removed robustly; on exit a cleanup is attempted. Force manual cleanup with menu 22 (reports freed space).

## 6. Status Line Indicators

The status line (below the main menu) summarizes current runtime settings:

- `[MountDirBase: ...]` — base folder for temporary mounts; `%TEMP%` if unset (set in menu 18)
- `[Verbose: on|off]` — detailed logging (menu 19)
- `[ExportBackend: auto|dism|wimlib]` — active export backend (menu 19)
- `[wimlib ...]` — `wimlib-imagex` state: version (e.g. `1.14.x`), origin (`local (next to executable)`, `system PATH`), or `missing`

## 7. Settings & Persistence

The following options persist across sessions: base mount folder, verbose logging, export backend (`auto` / `dism` / `wimlib`), single-line percentage bar, informational spinner, console tweaks (VT, QuickEdit, centering, restore position, AlwaysOnTop).

Configuration file locations (first existing wins):

1. Preferred: `%APPDATA%\PyDism\settings.json`
2. Fallback: `config/settings.json` next to `PyDism.py` (used when `%APPDATA%` is unavailable)

Modify via menu entries:

- 18: Set base folder for temporary mounts (empty = `%TEMP%`).
- 19: Console options (VT, QuickEdit, center, restore position, AlwaysTop), verbose log, export backend, percentage bar mode (applies to wimlib + DISM operations exposing percent) and spinner (Enter = apply defaults below).

Reset to defaults: delete `settings.json` and restart.

## 8. Menu 19 Defaults (Blank Enter)

Pressing Enter without input in menu 19 applies:

- VT (Virtual Terminal): off — prompt: `on/off, Enter=off`.
- Disable QuickEdit: on — prompt: `on/off, Enter=on` (default keeps QuickEdit disabled to avoid accidental pauses).
- Verbose log: on — prompt: `on/off, Enter=on` (a confirmation hint is shown; fresh installs start with verbose off until you choose it here).
- Center console at startup: on — prompt: `on/off, Enter=on`.
- Restore saved position at startup: off — prompt: `on/off, Enter=off`.
- Always on top: off — prompt: `on/off, Enter=off` (takes effect immediately).
- Center retries: Enter keeps current — prompt: `(Enter=keep)`.
- Delay between retries (ms): Enter keeps current — prompt: `(Enter=keep)`.
- Percentage progress bar (wimlib/DISM): `line` / `off`, Enter=`line` (single updating line; `off` hides it).
- Informational spinner (Get-Features, Get-WimInfo): on — prompt: `on/off, Enter=on`.
- Export backend: auto — prompt: `auto/dism/wimlib, Enter=auto`.

Hints are shown after toggling VT, QuickEdit, Verbose, Center and Restore.

## 9. Console Window Position & Behavior (Menu 19)

- Center console at startup: centers on the monitor containing the cursor (multi-monitor aware). Default: on.
- Restore saved position at startup: if a saved position exists and this is on, it overrides centering. Default: off.
- Save current position as preferred: choose `S` inside menu 19 or press `S` in the main menu shortcut.
- Reliability tuning: configure `Center retries` (0–5, default 3) and `Delay between retries (ms)` (0–1000, default 150) for cases where the window repositions slowly.
- Config keys: `center_console` (bool), `restore_console_pos` (bool), `saved_console_pos` ({ x, y }), `center_retry` (int), `center_delay_ms` (int), `last_console_pos` (last computed), `always_on_top` (bool).
- Always on top: keeps the window top-most when enabled (default off).

## 10. Packaging (README Inclusion)

If you build an executable you can ship `README_PyDism.md` next to it so menu 20 opens it directly.

auto-py-to-exe:

- Add under "Additional Files": `README_PyDism.md;.`

PyInstaller:

```bash
--add-data "README_PyDism.md;."
```

## 11. wimlib-imagex Integration

Download Windows binaries from the official wimlib project site (search "wimlib downloads"). You need `wimlib-imagex.exe`.

To bundle without relying on PATH place `wimlib-imagex.exe` beside the executable or add it as an extra file:

- auto-py-to-exe: `wimlib-imagex.exe;.` in Additional Files
- PyInstaller: `--add-binary "wimlib-imagex.exe;."`
- One-file mode: extracted into `_MEIPASS`; code resolves path at runtime.

## 12. Elevation Strategy (UAC)

Launching unelevated triggers a self-relaunch with UAC elevation.

Recommended: build a "Window Based" executable (no console) so only the elevated instance allocates a console. The code:

1. Hides any pre-elevation console (if present)
2. Relaunches elevated
3. Allocates a fresh console in the elevated instance

When running as script (`python PyDism.py`) or a Console based exe you will simply see the current console; the non-elevated stub exits after spawning the elevated one.

## 13. Quick Guide: auto-py-to-exe (Window Based + Extra Files)

1. Install: `pip install auto-py-to-exe`
2. Launch: `auto-py-to-exe`
3. Script Location: choose `PyDism.py`
4. Onefile/Onefolder: choose freely ("One Directory" recommended for clarity)
5. Console Window: "Window Based" (only elevated instance shows a console)
6. Additional Files:
   - `README_PyDism.md;.`
   - `wimlib-imagex.exe;.` (optional)
7. (Optional) Icon: `Python.ico` or custom
8. Click "Convert .py to .exe"
9. Run `PyDism.exe` (it will auto-elevate). Status line will include `[wimlib: ...]`.

Notes:

- In "One File" mode extra files are extracted at runtime (supported via `_MEIPASS`). Using "One Directory" keeps them visible next to the exe.

## 14. Console Colors (VT & colorama)

Menu 19 lets you enable VT (Virtual Terminal) at startup. If `on`, ANSI sequences are used directly; if `off`, native console behavior is retained.

- Disabling QuickEdit prevents accidental pauses when clicking.
- Optional: install `colorama` for reliable ANSI→Win32 translation even with `VT: off`.

Install:

```bash
pip install colorama
```

## 15. Temporary Directory Warnings

In one-file packaging (PyInstaller / auto-py-to-exe) you may sometimes see:

```text
Failed to remove temporary directory: R:\TEMP\...
```

Usually harmless; it stems from cleanup of the extraction directory. The program sets a stable working dir (the exe folder) to reduce locks. Prefer "One Directory" if you want to avoid such transient messages entirely.

## 16. Menu Entries

- 1: List image indexes
- 2: Mount image (RW) and unmount
- 3: Mount image (RO) and unmount
- 4: Show current mounts
- 5: Clean orphaned mounts
- 6: List features (with filter)
- 7: Enable feature
- 8: Disable feature
- 9: Add package (CAB/MSU)
- 10: Add driver
- 11: Component cleanup
- 12: Add drivers to boot.wim (idx 2)
- 13: Remove drivers from boot.wim by folder
- 14: Export indexes to new WIM/ESD
- 15: Image integrity check
- 16: Convert ESD → WIM
- 17: Show recent logs
- 18: Settings: mount folder
- 19: Settings: console / verbose / backend
- 20: Help - PyDism Guide (README_PyDism.md)
- 21: Help - Split WIM Workflow (README.md)
- 22: Open log folder
- 23: Purge temporary mount folders created this session (shows freed space)
- 24: Unmount an existing mount folder (if you left a mount from 2/3)
- 25: Split install.wim for FAT32 (creates install.swm parts)
- 26: Recombine SWM files into WIM (merges split parts back to single image)

Note (menu 2 & 3): After mounting a small sub-menu lets you open the folder, leave it mounted and return to main menu, or unmount (commit/discard). If left mounted you can later unmount via entry 24.

Note (menu 25): Splits large install.wim (>4GB) into install.swm, install2.swm, etc. for FAT32 compatibility. See section 17 for the complete workflow (export → mount → modify → unmount → re-export → split).

Note (menu 26): Recombines split SWM files back into a single WIM when you need to modify the image. Auto-detects all parts (install.swm, install2.swm, etc.), allows index selection, and exports to a new WIM with chosen compression.

## 17. Split WIM (Best Practices)

Purpose: keep the USB stick formatted as FAT32 (best UEFI compatibility) by splitting `install.wim` when it exceeds 4GB.

Windows Setup supports split images out-of-the-box: if `sources\install.swm` exists, it automatically loads `install*.swm` parts. You must not split `boot.wim`.

Recommended sequence when customizing images:

1) Export the desired index to a dedicated WIM
   - DISM: `Dism /Export-Image /SourceImageFile:install.wim /SourceIndex:<N> /DestinationImageFile:install_single.wim /Compress:max`
   - Result: `install_single.wim` with a single index (index=1)

2) Mount the exported WIM and apply changes
   - Mount: `Dism /Mount-Wim /WimFile:install_single.wim /Index:1 /MountDir:C:\Mount`
   - Add drivers: `Dism /Image:C:\Mount /Add-Driver /Driver:C:\Drivers /Recurse`
   - Enable features (example): `Dism /Image:C:\Mount /Enable-Feature /FeatureName:TelnetClient`
   - Unmount & commit: `Dism /Unmount-Wim /MountDir:C:\Mount /Commit`

3) Optimize via re-export (optional but strongly recommended)
   - DISM: `Dism /Export-Image /SourceImageFile:install_single.wim /SourceIndex:1 /DestinationImageFile:install_optimized.wim /Compress:max /CheckIntegrity`
   - Benefit: removes dead space and applies optimal compression; often reduces size enough to avoid splitting entirely

4) Split only if size remains >= 4GB
   - DISM: `Dism /Split-Image /ImageFile:install_optimized.wim /SWMFile:install.swm /FileSize:3800`
   - Output files: `install.swm`, `install2.swm`, `install3.swm`, ...

5) Placement in ISO/USB
   - Copy the resulting files into `sources\` of your ISO/USB tree
   - If split: place all `install*.swm` parts; delete any old `install.wim`
   - Do not touch `boot.wim` (it enables WinPE/Setup boot and stays unsplit)

Notes:

- FAT32 limit is 4GB per file; NTFS avoids the need to split but some UEFI firmwares read FAT32 USB more reliably.
- Splitting acts only on the final image; do not try to modify split parts—always modify the single WIM first, then split.
- If you need to modify split SWM files, use Menu 26 to recombine them into a single WIM first, then follow steps 2-4 above.
- wimlib-imagex can also split (`wimlib-imagex split`), but DISM is sufficient and built-in.

---

**Version**: 1.0  
**Last Updated**: 2025  
**Python**: 3.7+


