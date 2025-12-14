# 📚 PyDism Documentation Index

Quick reference guide to all documentation files.

## 🚀 Start Here

**First time?** → Read [`README_pydism.md`](./README_pydism.md)

## 📖 Main Documentation

| Document | Purpose | Read Time |
|----------|---------|-----------|
| **[README_pydism.md](./README_pydism.md)** | Complete feature reference, all 26 menu options, TAB autocompletion | 20 min |
| **[README.md](./README.md)** | Launcher scripts guide, Split WIM workflow | 15 min |
| **[BUILD_INSTRUCTIONS.md](./BUILD_INSTRUCTIONS.md)** | Building executable with auto-py-to-exe, distribution | 15 min |
| **[launcher/README.md](../launcher/README.md)** | How to run PyDism with launcher scripts | 10 min |

## 🎯 Find What You Need

### I want to

#### ...run PyDism right now

```bash
cd C:\SOURCECODE\PYTHON\POSTINSTALL
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
.venv\Scripts\python.exe PyDism.py
```

See: [`launcher/README.md`](../launcher/README.md)

#### ...use TAB autocompletion

→ See: [`docs/README_pydism.md`](./README_pydism.md) > "TAB Autocompletion"

#### ...understand Split WIM for FAT32

→ See: [`docs/README.md`](./README.md) > "Split WIM for FAT32"

#### ...build an executable

→ See: [`docs/BUILD_INSTRUCTIONS.md`](./BUILD_INSTRUCTIONS.md) > "Build Methods"

#### ...troubleshoot TAB not working

→ See: [`docs/README_pydism.md`](./README_pydism.md) > "Troubleshooting Autocompletion"

#### ...distribute to other machines

→ See: [`docs/BUILD_INSTRUCTIONS.md`](./BUILD_INSTRUCTIONS.md) > "Distribution Package"

#### ...learn all the menu options

→ See: [`docs/README_pydism.md`](./README_pydism.md) > "Menu Entries"

#### ...set up a launcher script

→ See: [`launcher/README.md`](../launcher/README.md)

## 📁 File Structure

```text
C:\SOURCECODE\PYTHON\POSTINSTALL\
│
├── 📄 PyDism.py                Main program (~2500 lines)
├── 📄 PyDism.spec              PyInstaller configuration
├── 📄 requirements.txt         Python dependencies (colorama, prompt_toolkit)
│
├── 📁 docs\
│   ├── 📄 README_pydism.md         ← Complete feature reference (start here)
│   ├── 📄 README.md                Launcher scripts guide
│   ├── 📄 BUILD_INSTRUCTIONS.md    Build executable guide
│   └── 📄 README_INDEX.md          This file
│
└── 📁 launcher\
    ├── 📄 PyDism.bat           CMD launcher
    ├── 📄 PyDism.ps1           PowerShell launcher
    ├── 📄 PyDism-Admin.bat     Admin launcher
    └── 📄 README.md            Launcher documentation
```

## 👥 By Role

### 👤 First-Time User

1. [`README_pydism.md`](./README_pydism.md) - Complete feature reference
2. [`README.md`](./README.md) - Launcher scripts usage
3. [`launcher/README.md`](../launcher/README.md) - How to run PyDism

### 👨‍💻 Developer

1. [`README_pydism.md`](./README_pydism.md) - Full documentation
2. [`BUILD_INSTRUCTIONS.md`](./BUILD_INSTRUCTIONS.md) - Building executable
3. [`PyDism.spec`](../PyDism.spec) - PyInstaller configuration

### 🔧 System Administrator

1. [`launcher/README.md`](../launcher/README.md) - Deployment options
2. [`README_pydism.md`](./README_pydism.md) - Troubleshooting
3. [`BUILD_INSTRUCTIONS.md`](./BUILD_INSTRUCTIONS.md) - Distribution

### 🐛 Troubleshooter

| Issue | See |
|-------|-----|
| TAB autocompletion not working | [`README_pydism.md`](./README_pydism.md) |
| Build failures | [`BUILD_INSTRUCTIONS.md`](./BUILD_INSTRUCTIONS.md) |
| Split WIM issues | [`README.md`](./README.md) |
| Can't run script | [`launcher/README.md`](../launcher/README.md) |

## 🔍 Search Guide

**Search for:**

- `TAB autocompletion` → docs/README_pydism.md
- `Split WIM` → docs/README.md
- `launcher` → launcher/README.md
- `PyInstaller` → docs/BUILD_INSTRUCTIONS.md
- `DISM operations` → docs/README_pydism.md
- `configuration` → docs/README_pydism.md
- `prompt_toolkit` → docs/README_pydism.md

## 📋 Quick Reference

### Environment Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### Run PyDism

```bash
# Method 1: Direct Python
.venv\Scripts\python.exe PyDism.py

# Method 2: Launcher batch
launcher\PyDism.bat

# Method 3: Launcher PowerShell
.\launcher\PyDism.ps1

# Method 4: Compiled executable (after building)
dist\PyDism\PyDism.exe
```

### Build Executable

```bash
pip install pyinstaller
pyinstaller --clean --noconfirm PyDism.spec
```

## 📞 Support

- **Feature questions** → [`README_pydism.md`](./README_pydism.md)
- **Launcher scripts** → [`README.md`](./README.md)
- **Build help** → [`BUILD_INSTRUCTIONS.md`](./BUILD_INSTRUCTIONS.md)
- **Running/deployment** → [`launcher/README.md`](../launcher/README.md)

## ✅ Verification

To verify everything works:

```bash
# Check 1: Environment
.venv\Scripts\python -c "import prompt_toolkit; print('✓')"

# Check 2: Run PyDism
.venv\Scripts\python.exe PyDism.py

# Check 3: TAB works (in menu 25, press TAB at path prompt)

# Check 4: Build (if interested)
pyinstaller --clean --noconfirm PyDism.spec
```

---

**Last Updated:** 2025

**Version:** 1.0

**Platform:** Windows 7, 10, 11

**Python:** 3.7+
