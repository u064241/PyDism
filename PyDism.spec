# -*- mode: python ; coding: utf-8 -*-
"""
PyDism.spec - PyInstaller configuration for PyDism.py

Build PyDism as a standalone Windows executable with all dependencies bundled.

Usage:
    pyinstaller --clean --noconfirm PyDism.spec

Output:
    dist/PyDism/PyDism.exe (~35-40 MB with all dependencies)

This spec file ensures:
- All Python dependencies (prompt_toolkit, colorama) are included
- Documentation files are bundled and accessible
- Console mode is enabled for DISM operations
- Hidden imports are properly declared
"""

import sys
from PyInstaller.utils.hooks import collect_data_files

block_cipher = None

a = Analysis(
    ['PyDism.py'],
    pathex=[],
    binaries=[],
    datas=[
        # Include documentation files for menu 20 help
        ('docs/README_pydism.md', 'docs'),
        ('docs/README.md', 'docs'),
        ('docs/SETUP.md', 'docs'),
    ],
    # Critical: Declare hidden imports so PyInstaller bundles them
    hiddenimports=[
        'colorama',                    # Console color support (Windows ANSI)
        'prompt_toolkit',              # TAB autocompletion for path input
        'prompt_toolkit.completion',   # PathCompleter for file path suggestions
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludedimports=[],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='PyDism',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,              # Use UPX compression if available (reduces size)
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,          # PyDism is console-based (don't use windowed mode)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

# Optional: For one-file distribution, uncomment:
# coll = COLLECT(
#     exe,
#     a.binaries,
#     a.zipfiles,
#     a.datas,
#     strip=False,
#     upx=True,
#     upx_exclude=[],
#     name='PyDism'
# )
