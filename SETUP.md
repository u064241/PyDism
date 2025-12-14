# PyDism Build & Distribution Guide

Complete guide to building PyDism.py as a standalone executable with PyInstaller.

## 1. Prerequisites

Install required tools:

```powershell
pip install pyinstaller
pip install colorama
pip install prompt_toolkit
```

## 2. Build Methods

### Method A: PyInstaller with Spec File (Recommended)

```powershell
cd C:\SOURCECODE\PYTHON\POSTINSTALL
pyinstaller --clean --noconfirm PyDism.spec
```

Output: `dist\PyDism\PyDism.exe` (~35-40 MB)

### Method B: Manual PyInstaller Command

```powershell
pyinstaller --onedir --console --name PyDism ^
  --add-data "docs\README_PyDism.md;docs" ^
  --add-data "docs\README.md;docs" ^
  --add-data "docs\SETUP.md;docs" ^
  --hidden-import colorama ^
  --hidden-import prompt_toolkit ^
  --hidden-import prompt_toolkit.completion ^
  PyDism.py
```

### Method C: auto-py-to-exe GUI

```powershell
pip install auto-py-to-exe
auto-py-to-exe
```

Configure in GUI:

- **Script Location**: `PyDism.py`
- **Onefile/Onedir**: One Directory (recommended)
- **Console Window**: Console Based (required)
- **Additional Files**:
  - `docs\README_PyDism.md` → `docs`
  - `docs\README.md` → `docs`
  - `docs\SETUP.md` → `docs`
- **Hidden Imports**: `colorama`, `prompt_toolkit`

Click "Convert .py to .exe"

## 3. Build Configuration

### One Directory vs One File

#### One Directory (Recommended)

Creates: `dist\PyDism\` folder with exe + dependencies

**Pros:**

- Faster startup time
- Easier to debug
- Clearer dependency structure

**Cons:**

- Multiple files to distribute

#### One File

Creates: Single `PyDism.exe`

**Pros:**

- Single file distribution
- Simpler to share

**Cons:**

- Slower startup (extracts to temp)
- May trigger antivirus false positives

### Console Mode

**CRITICAL**: Must use Console Based mode

- PyDism requires interactive console input
- Window Based mode would hide the console
- DISM operations need visible output

### Documentation Files

**CRITICAL**: Include `docs/` folder

PyDism menus 20, 21, 25 open documentation files:

- Menu 20: Opens `docs\README_PyDism.md`
- Menu 21: Opens `docs\README.md`
- Menu 25: Split WIM references documentation

**How to include:**

PyInstaller spec file:

```python
datas=[
    ('docs/README_PyDism.md', 'docs'),
    ('docs/README.md', 'docs'),
    ('docs/SETUP.md', 'docs'),
],
```

auto-py-to-exe:

- Add Folder: `docs\` → Destination: `docs`

## 4. Hidden Imports

Required dependencies that PyInstaller may not detect automatically:

```python
hiddenimports=[
    'colorama',                    # Console colors
    'prompt_toolkit',              # TAB autocompletion
    'prompt_toolkit.completion',   # PathCompleter
],
```

## 5. Testing the Build

After building, test thoroughly:

```powershell
cd dist\PyDism
.\PyDism.exe
```

### Test Checklist

- [ ] Executable launches without errors
- [ ] Menu 20 opens `README_PyDism.md` in Notepad
- [ ] Menu 21 opens `README.md` in Notepad
- [ ] Menu 1 (Get-ImageInfo) works on a test WIM file
- [ ] TAB autocompletion works (menu 25, press TAB at path prompt)
- [ ] Console colors display correctly
- [ ] UAC elevation prompt appears for DISM operations

### Debug Failed Build

If executable fails to start:

```powershell
# Run from PowerShell to see error messages
.\PyDism.exe

# Check for missing dependencies
.\PyDism.exe > error.log 2>&1
```

Common issues:

- Missing `colorama`: Add to `hiddenimports`
- Missing `prompt_toolkit`: Add to `hiddenimports`
- Missing docs: Verify `datas` configuration

## 6. Distribution Package

### Structure

Create distribution package:

```text
PyDism_v1.0\
├── PyDism.exe
├── docs\
│   ├── README.md
│   ├── README_PyDism.md
│   ├── SETUP.md
│   └── README_INDEX.md
├── launcher\
│   ├── PyDism.bat
│   ├── PyDism.ps1
│   └── PyDism-Admin.bat
└── [PyInstaller dependencies]
```

### Create ZIP Package

```powershell
# Copy distribution files
New-Item -ItemType Directory -Path PyDism_v1.0
Copy-Item -Path dist\PyDism\* -Destination PyDism_v1.0\ -Recurse
Copy-Item -Path launcher -Destination PyDism_v1.0\launcher -Recurse

# Create ZIP
Compress-Archive -Path PyDism_v1.0 -DestinationPath PyDism_v1.0.zip
```

### Distribution Checklist

- [ ] All documentation files included
- [ ] Launcher scripts included
- [ ] Executable runs on clean Windows 10/11 system
- [ ] No antivirus false positives
- [ ] ZIP file size reasonable (~40-50 MB)

## 7. Advanced Configuration

### Custom Icon

Add custom icon to executable:

```powershell
pyinstaller --icon=icon.ico PyDism.py
```

Or in spec file:

```python
exe = EXE(
    ...
    icon='icon.ico',
    ...
)
```

### UPX Compression

Reduce executable size with UPX:

```python
exe = EXE(
    ...
    upx=True,  # Enable UPX compression
    ...
)
```

**Warning**: UPX may trigger antivirus false positives

Disable if needed:

```python
upx=False,
```

### wimlib-imagex Integration

Include wimlib-imagex.exe for faster WIM operations:

```python
datas=[
    ('wimlib-imagex.exe', '.'),
    ('docs/README_PyDism.md', 'docs'),
    ...
],
```

Or add as Additional File in auto-py-to-exe:

- File: `wimlib-imagex.exe`
- Destination: `.`

## 8. Troubleshooting

### Issue: "README not found"

**Cause**: Documentation files not included in build

**Solution**: Verify `datas` configuration includes `docs/` folder

```python
datas=[
    ('docs/README_PyDism.md', 'docs'),
    ('docs/README.md', 'docs'),
],
```

### Issue: "DISM error 740"

**Cause**: PyDism not running with administrator privileges

**Solution**: Run as administrator

```powershell
# Right-click PyDism.exe → Run as administrator
```

Or use launcher with elevation:

```powershell
.\launcher\PyDism-Admin.bat
```

### Issue: Antivirus blocks executable

**Cause**: PyInstaller executables may trigger heuristic detection

**Solutions:**

1. Disable UPX compression
2. Sign executable with code signing certificate
3. Add exclusion in antivirus software
4. Submit false positive report to antivirus vendor

### Issue: Slow startup (One File mode)

**Cause**: PyInstaller extracts libraries to temp folder on every launch

**Solution**: Switch to One Directory mode

```powershell
pyinstaller --onedir PyDism.py
```

### Issue: TAB autocompletion not working

**Cause**: `prompt_toolkit` not included in build

**Solution**: Add to hidden imports

```python
hiddenimports=[
    'prompt_toolkit',
    'prompt_toolkit.completion',
],
```

### Issue: Console colors broken

**Cause**: `colorama` not included in build

**Solution**: Add to hidden imports

```python
hiddenimports=[
    'colorama',
],
```

## 9. Automated Build Script

Create `build.ps1` for automated builds:

```powershell
# build.ps1 - Automated PyDism build script

$ErrorActionPreference = "Stop"

Write-Host "Building PyDism..." -ForegroundColor Cyan

# Clean previous builds
if (Test-Path dist) { Remove-Item -Recurse -Force dist }
if (Test-Path build) { Remove-Item -Recurse -Force build }

# Build with PyInstaller
pyinstaller --clean --noconfirm PyDism.spec

if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Build successful" -ForegroundColor Green
    Write-Host "Output: dist\PyDism\PyDism.exe" -ForegroundColor Yellow
    
    # Test executable
    Write-Host "Testing executable..." -ForegroundColor Cyan
    $testResult = & "dist\PyDism\PyDism.exe" "--version" 2>&1
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ Executable works" -ForegroundColor Green
    } else {
        Write-Host "✗ Executable test failed" -ForegroundColor Red
    }
} else {
    Write-Host "✗ Build failed" -ForegroundColor Red
    exit 1
}
```

Run:

```powershell
.\build.ps1
```

## 10. Continuous Integration

### GitHub Actions Example

```yaml
name: Build PyDism

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  build:
    runs-on: windows-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.10'
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install pyinstaller
    
    - name: Build with PyInstaller
      run: pyinstaller --clean --noconfirm PyDism.spec
    
    - name: Upload artifact
      uses: actions/upload-artifact@v3
      with:
        name: PyDism-executable
        path: dist/PyDism/
```

## Quick Reference

### Build Commands

```powershell
# Standard build
pyinstaller --clean --noconfirm PyDism.spec

# Build with custom icon
pyinstaller --icon=icon.ico PyDism.py

# One file build
pyinstaller --onefile --console PyDism.py

# With debug mode
pyinstaller --debug all PyDism.py
```

### Common Flags

- `--clean`: Remove temp files before build
- `--noconfirm`: Overwrite output without prompt
- `--onedir`: Create directory with executable + dependencies (default)
- `--onefile`: Create single executable
- `--console`: Console-based application
- `--windowed`: Window-based application (no console)
- `--icon=FILE`: Set application icon
- `--add-data`: Include data files
- `--hidden-import`: Force include module

---

**Version**: 1.0

**Last Updated**: 2025

**Platform**: Windows 7, 10, 11
