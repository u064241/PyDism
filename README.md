# PyDism Launcher Scripts

Ready-to-use launcher scripts for running PyDism.

## Quick Start

Run PyDism with one of these commands:

### Batch (CMD.exe)

```batch
PyDism.bat
```

### PowerShell

```powershell
.\PyDism.ps1
```

### PowerShell with Admin Elevation

```powershell
.\PyDism.ps1 -Admin
```

### Admin Launcher (Batch)

```batch
PyDism-Admin.bat
```

## Script Descriptions

### PyDism.bat

Generic launcher for Windows Command Prompt (CMD.exe).

**Features:**

- Auto-detects compiled executable or Python script
- Supports command-line arguments
- Shows helpful error messages if not found
- Colored output (if terminal supports ANSI)

**Usage:**

```batch
PyDism.bat
PyDism.bat C:\path\to\image.wim
```

### PyDism.ps1

PowerShell launcher with flexible options.

**Features:**

- Auto-detection of executable or venv Python
- Optional admin elevation with `-Admin` flag
- Bypass Python mode with `-NoVenv` flag
- Color-coded status messages
- Works in PowerShell 3.0+ and PowerShell Core

**Usage:**

```powershell
# Standard launch
.\PyDism.ps1

# With admin privileges
.\PyDism.ps1 -Admin

# Force Python mode (skip executable check)
.\PyDism.ps1 -NoVenv

# With arguments
.\PyDism.ps1 "C:\path\to\image.wim"

# Combined options
.\PyDism.ps1 -Admin -NoVenv "C:\Sources\install.wim"
```

**Execution Policy:**

If you get an execution policy error:

```powershell
powershell -ExecutionPolicy Bypass -File PyDism.ps1
```

### PyDism-Admin.bat

Batch launcher that automatically requests administrator privileges.

**Features:**

- UAC elevation (requests privileges if not admin)
- Simple one-file execution
- Automatically detects executable or Python
- Shows status and errors clearly

**Usage:**

```batch
PyDism-Admin.bat
PyDism-Admin.bat C:\path\to\image.wim
```

## How They Work

All launchers follow this priority:

1. **Check for compiled executable** (`dist\PyDism\PyDism.exe`)
   - If found, run directly
   - Fastest startup, no dependencies

2. **Fallback to Python venv** (`.venv\Scripts\python.exe`)
   - If executable not found
   - Requires venv with dependencies installed

3. **Error if nothing found**
   - Shows helpful message and instructions

## Setup Instructions

### Option A: Use Compiled Executable (Recommended)

```bash
# Build executable once
pyinstaller --clean --noconfirm PyDism.spec

# Then use launchers
PyDism.bat
.\PyDism.ps1
```

Output: `dist\PyDism\PyDism.exe` (~35-40 MB)

### Option B: Use Python Venv

```bash
# Setup venv (one time)
python -m venv ..\..\.venv
..\..\..venv\Scripts\pip install -r ..\requirements.txt

# Launchers auto-detect and use it
PyDism.bat
.\PyDism.ps1
```

### Option C: Both Available

Launchers prefer executable over Python:

- If `PyDism.exe` exists → runs executable
- Otherwise → falls back to Python venv

## Troubleshooting

### "PyDism executable or Python environment not found"

**Solution:** Build the executable or setup venv:

```bash
# Option 1: Build with PyInstaller
cd ..\
pyinstaller --clean --noconfirm PyDism.spec

# Option 2: Setup Python venv
python -m venv ..\..\..venv
..\..\..venv\Scripts\pip install -r ..\requirements.txt
```

### "Cannot be loaded because running scripts is disabled"

### PowerShell execution policy error

**Solution:** Use bypass flag:

```powershell
powershell -ExecutionPolicy Bypass -File PyDism.ps1
```

Or set policy temporarily:

```powershell
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope CurrentUser -Force
.\PyDism.ps1
```

### "TAB autocompletion not working"

**Solution:** Must use Python venv for autocompletion:

```bash
# Verify venv Python has prompt_toolkit
..\..\..venv\Scripts\pip list | findstr prompt_toolkit
# Should show: prompt_toolkit   3.0.52
```

### Launcher runs but PyDism doesn't start

**Possible causes:**

1. DISM not available (check: `dism /?`)
2. Not running as administrator
3. Python import errors in PyDism.py

**Try direct Python to see error:**

```bash
..\..\..venv\Scripts\python.exe ..\PyDism.py
```

## Integration with Windows

### Desktop Shortcut

Create shortcut to `PyDism.bat` or `PyDism-Admin.bat`:

1. Right-click desktop → New → Shortcut
2. Target: `PyDism.bat` or `PyDism-Admin.bat` (full path)
3. Start in: folder containing scripts
4. Advanced: check "Run as administrator"
5. OK

### Start Menu

Copy `PyDism.bat` to:

```text
C:\Users\[YourUser]\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\
```

Or create shortcut there.

### Context Menu (Right-click)

Advanced: Create registry entry for "Send To" menu in Windows Explorer.

## Distribution

Include all three launchers in your distribution package:

```text
PyDism-Package/
├── PyDism.exe          (or Python source + venv)
├── PyDism.bat
├── PyDism.ps1
├── PyDism-Admin.bat
└── README.txt
```

Users can then run:

```bash
# Simple
PyDism.bat

# Or with admin
PyDism-Admin.bat

# Or with PowerShell
powershell -File PyDism.ps1
```

---

**Version**: 1.0  
**Last Updated**: 2025  
**Platform**: Windows 7+
