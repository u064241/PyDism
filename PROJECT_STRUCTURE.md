# PyDism Project Structure

Complete overview of the PyDism project layout, quick start guide, and file organization.

## Project Overview

**PyDism** is an interactive DISM toolkit for Windows image manipulation, providing a user-friendly menu interface for common Windows imaging tasks.

**Key Features:**

- 25+ DISM operations in interactive menu
- TAB autocompletion for file paths (powered by prompt_toolkit)
- Split WIM support for FAT32 USB drives
- Mount/unmount Windows images
- Add drivers and packages
- Enable/disable Windows features
- Component cleanup and optimization

**Platform:** Windows 7, 10, 11

**Language:** Python 3.7+

## Quick Start

### 1. Setup Environment

```powershell
cd C:\SOURCECODE\PYTHON\POSTINSTALL

# Create virtual environment
python -m venv .venv

# Activate virtual environment
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Run PyDism

```powershell
# Method 1: Direct Python execution
.venv\Scripts\python.exe PyDism.py

# Method 2: Use batch launcher
launcher\PyDism.bat

# Method 3: Use PowerShell launcher
.\launcher\PyDism.ps1
```

### 3. Test TAB Autocompletion

1. Launch PyDism
2. Select menu 25 (Split WIM)
3. When prompted for path, start typing and press **TAB**
4. See file suggestions appear

## Project Structure

```text
C:\SOURCECODE\PYTHON\POSTINSTALL\
│
├── 📄 PyDism.py              Main application (2355 lines)
├── 📄 PyDism.spec            PyInstaller build configuration
├── 📄 requirements.txt        Python dependencies
├── 📄 LICENSE                 Project license
├── 📄 README_7zipAssoc.md     7-Zip file association utility
├── 📄 7zipAssoc.py            7-Zip utility script
│
├── 📁 docs\                   Documentation folder
│   ├── 📄 README.md           Main guide (setup, workflows)
│   ├── 📄 README_PyDism.md   Complete reference (features, troubleshooting)
│   ├── 📄 SETUP.md            Build guide (PyInstaller, distribution)
│   ├── 📄 README_INDEX.md     Documentation index
│   └── 📄 BUILD_INSTRUCTIONS.md  Legacy build notes
│
├── 📁 launcher\               Launcher scripts
│   ├── 📄 PyDism.bat         CMD launcher
│   ├── 📄 PyDism.ps1         PowerShell launcher
│   ├── 📄 PyDism-Admin.bat   Admin launcher (UAC elevation)
│   └── 📄 README.md           Launcher documentation
│
├── 📁 .venv\                  Python virtual environment
│   └── Scripts\
│       └── python.exe         Python interpreter with dependencies
│
└── 📁 dist\                   Build output (after PyInstaller)
    └── PyDism\
        └── PyDism.exe        Standalone executable
```

## Core Files

### PyDism.py

Main application file containing all functionality.

**Lines of Code:** ~2355

**Key Components:**

- Interactive menu system
- DISM wrapper functions
- TAB autocompletion integration
- Settings persistence
- Error logging
- UAC elevation handling

**Dependencies:**

- `os`, `sys`, `subprocess` (stdlib)
- `pathlib` (stdlib, path handling)
- `ctypes` (stdlib, Windows API)
- `json` (stdlib, settings)
- `colorama` (ANSI colors)
- `prompt_toolkit` (TAB autocompletion)

### PyDism.spec

PyInstaller configuration for building standalone executable.

**Includes:**

- Hidden imports (`colorama`, `prompt_toolkit`)
- Documentation files bundling
- Console mode configuration
- UPX compression settings

**Usage:**

```powershell
pyinstaller --clean --noconfirm PyDism.spec
```

### requirements.txt

Python dependencies required to run PyDism.

**Contents:**

```text
colorama>=0.4.6           # Console colors
prompt_toolkit>=3.0.0     # TAB autocompletion
```

**Install:**

```powershell
pip install -r requirements.txt
```

## Documentation Files

### docs/README.md

Main documentation covering:

- Setup instructions
- Split WIM workflow for FAT32
- Menu usage guide
- Troubleshooting

**Target Audience:** End users, system administrators

### docs/README_PyDism.md

Complete reference documentation:

- All 25+ menu entries explained
- TAB autocompletion guide
- Advanced troubleshooting
- Configuration options

**Target Audience:** Power users, developers

### docs/SETUP.md

Build and distribution guide:

- PyInstaller configuration
- Build methods (spec file, auto-py-to-exe)
- Distribution package creation
- Troubleshooting build issues

**Target Audience:** Developers, package maintainers

### docs/README_INDEX.md

Quick reference index for all documentation.

**Target Audience:** All users (navigation hub)

## Launcher Scripts

### launcher/PyDism.bat

CMD batch launcher with auto-detection.

**Features:**

- Detects compiled exe or Python venv
- Colored output (if terminal supports ANSI)
- Error messages if PyDism not found

**Usage:**

```batch
PyDism.bat
PyDism.bat C:\path\to\image.wim
```

### launcher/PyDism.ps1

PowerShell launcher with flexible options.

**Features:**

- Auto-detection (exe vs Python)
- Admin elevation flag: `-Admin`
- Bypass Python mode: `-NoVenv`
- Color-coded status messages

**Usage:**

```powershell
.\PyDism.ps1
.\PyDism.ps1 -Admin
.\PyDism.ps1 -NoVenv
```

### launcher/PyDism-Admin.bat

Batch launcher with automatic UAC elevation.

**Features:**

- Requests admin privileges automatically
- Simple one-file execution
- Status and error messages

**Usage:**

```batch
PyDism-Admin.bat
```

## Build Output

### dist/PyDism/

Output directory after PyInstaller build.

**Contents:**

```text
dist\PyDism\
├── PyDism.exe              Main executable (~35-40 MB)
├── docs\                    Documentation files
│   ├── README.md
│   ├── README_PyDism.md
│   └── SETUP.md
└── [PyInstaller dependencies]  Python runtime, libraries
```

**Created by:**

```powershell
pyinstaller --clean --noconfirm PyDism.spec
```

## Configuration

### Settings Location

PyDism saves configuration to:

**Primary:**

```text
%APPDATA%\PyDism\settings.json
```

**Fallback:**

```text
C:\SOURCECODE\PYTHON\POSTINSTALL\config\settings.json
```

### Settings Content

```json
{
  "mount_dir_base": "C:\\Mount",
  "verbose": true,
  "export_backend": "auto",
  "center_console": true,
  "restore_console_pos": false,
  "saved_console_pos": {"x": 100, "y": 100},
  "always_on_top": false
}
```

**Modify via:**

- Menu 18: Mount directory
- Menu 19: Console options, verbose logging, export backend

## Logs

### Error Log

**Location:** `%TEMP%\PyDism_Errors.log`

**Contains:** Error messages, exceptions, DISM failures

**Access:** Menu 22 (opens log folder)

### Verbose Log

**Location:** `%TEMP%\PyDism_Verbose.log`

**Contains:** Full command output, debug messages

**Enable:** Menu 19 → Verbose: on

**Access:** Menu 17 (show recent logs)

## Development Workflow

### Setup Development Environment

```powershell
# Clone or navigate to project
cd C:\SOURCECODE\PYTHON\POSTINSTALL

# Create virtual environment
python -m venv .venv

# Activate
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Verify installation
python -c "import prompt_toolkit; print('✓ OK')"
```

### Run for Testing

```powershell
# With TAB autocompletion
.venv\Scripts\python.exe PyDism.py

# Quick test specific menu
.venv\Scripts\python.exe PyDism.py --test-menu 25
```

### Build Executable

```powershell
# Install PyInstaller
pip install pyinstaller

# Build
pyinstaller --clean --noconfirm PyDism.spec

# Test
dist\PyDism\PyDism.exe
```

### Modify and Rebuild

```powershell
# 1. Edit PyDism.py
code PyDism.py

# 2. Test changes
.venv\Scripts\python.exe PyDism.py

# 3. Rebuild if satisfied
pyinstaller --clean --noconfirm PyDism.spec
```

## Dependencies

### Runtime Dependencies

**colorama** (>=0.4.6)

- ANSI color support for Windows console
- Converts ANSI escape codes to Windows console API calls
- Optional but recommended

**prompt_toolkit** (>=3.0.0)

- TAB autocompletion for file paths
- Rich console input with history
- Required for autocompletion feature

### Build Dependencies

**pyinstaller** (latest)

- Creates standalone Windows executable
- Bundles Python runtime and dependencies
- Required only for building, not for running

### System Dependencies

**DISM** (built-in)

- Windows Deployment Image Servicing and Management
- Built into Windows 7, 10, 11
- Required for all WIM operations

**wimlib-imagex** (optional)

- Faster WIM export/convert operations
- Progress bars for long operations
- Download from wimlib project site

## Common Tasks

### Running PyDism

```powershell
# Standard (requires venv with dependencies)
.venv\Scripts\python.exe PyDism.py

# With launcher (auto-detects exe or Python)
launcher\PyDism.bat

# Compiled executable (after build)
dist\PyDism\PyDism.exe
```

### Building Executable

```powershell
# One-time setup
pip install pyinstaller

# Build
pyinstaller --clean --noconfirm PyDism.spec

# Output
dist\PyDism\PyDism.exe
```

### Updating Documentation

```powershell
# Edit markdown files
code docs\README_PyDism.md

# Changes take effect immediately (no rebuild needed)
# Menu 20/21 open updated files directly
```

### Testing TAB Autocompletion

```powershell
# 1. Ensure prompt_toolkit installed
.venv\Scripts\pip list | findstr prompt_toolkit

# 2. Run with venv Python (NOT global Python)
.venv\Scripts\python.exe PyDism.py

# 3. Select menu 25 and press TAB at path prompt
# Should see: [DEBUG] prompt_toolkit caricato con successo
```

## Troubleshooting

### "TAB not working"

**Cause:** Using wrong Python interpreter or missing prompt_toolkit

**Solution:**

```powershell
# Check current Python
where python

# Should be: C:\SOURCECODE\PYTHON\POSTINSTALL\.venv\Scripts\python.exe

# Install prompt_toolkit if missing
.venv\Scripts\pip install prompt_toolkit
```

### "PyDism not found" (launcher scripts)

**Cause:** Neither executable nor Python venv available

**Solution:**

```powershell
# Option 1: Build executable
pyinstaller --clean --noconfirm PyDism.spec

# Option 2: Setup Python venv
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
```

### "README not found" (menu 20/21)

**Cause:** Documentation files not in `docs/` folder

**Solution:**

```powershell
# Verify files exist
dir docs\README*.md

# If missing, restore from repository
```

### "DISM error 740"

**Cause:** Not running with administrator privileges

**Solution:**

```powershell
# Use admin launcher
launcher\PyDism-Admin.bat

# Or right-click executable → Run as administrator
```

## Project Conventions

### Code Style

- **Language:** Python 3.7+
- **Encoding:** UTF-8
- **Line Length:** ~100-120 characters
- **Indentation:** 4 spaces
- **Naming:** snake_case for functions, UPPER_CASE for constants

### Documentation Style

- **Format:** Markdown
- **Headings:** ATX style (`#` prefix)
- **Code Blocks:** Fenced with language specifier
- **Line Length:** ~80 characters (readable in terminal)

### Commit Messages

- **Format:** `[Component] Brief description`
- **Examples:**
  - `[Docs] Update TAB autocompletion guide`
  - `[Launcher] Fix PowerShell elevation issue`
  - `[Core] Add split WIM progress indicator`

## Next Steps

### For End Users

1. Read: `docs/README.md` (main guide)
2. Read: `docs/README_PyDism.md` (complete reference)
3. Use: `launcher/PyDism.bat` (easy execution)

### For Developers

1. Read: This file (PROJECT_STRUCTURE.md)
2. Read: `docs/SETUP.md` (build instructions)
3. Review: `PyDism.spec` (PyInstaller config)
4. Explore: `PyDism.py` (source code)

### For System Admins

1. Read: `launcher/README.md` (deployment)
2. Read: `docs/SETUP.md` (distribution)
3. Build: Standalone executable for deployment

---

**Version:** 1.0

**Last Updated:** 2025

**Maintainer:** PyDism Project

**Repository:** C:\SOURCECODE\PYTHON\POSTINSTALL
