# Istruzioni Build con auto-py-to-exe

Guida completa per compilare PyDism.py in un eseguibile standalone con **auto-py-to-exe**.

---

## 1. Installazione dipendenze

```powershell
# Installa auto-py-to-exe (wrapper GUI per PyInstaller)
pip install auto-py-to-exe

# Installa PyInstaller (backend, se non già presente)
pip install pyinstaller

# Installa dipendenze di PyDism
pip install -r requirements.txt
# Oppure manualmente:
pip install colorama>=0.4.6 prompt_toolkit>=3.0.0
```

**Dipendenze richieste:**

- `colorama>=0.4.6` - Colori console ANSI per Windows
- `prompt_toolkit>=3.0.0` - TAB autocompletion per path input

---

## 2. Avvio auto-py-to-exe

```powershell
cd c:\SOURCECODE\PYTHON\POSTINSTALL
auto-py-to-exe
```

Si aprirà l'interfaccia web nel browser.

---

## 3. Configurazione build

### Script Location

- **Script Location**: Seleziona `PyDism.py`

### Onefile / Onedir

Scegli una delle due modalità:

#### Opzione A: **One Directory** (consigliata per debug)

- Crea una cartella `dist\PyDism\` con l'eseguibile + DLL/librerie
- **Pro**: Tempi di avvio più rapidi, più facile da debuggare
- **Contro**: Più file da distribuire

#### Opzione B: **One File**

- Crea un singolo `PyDism.exe`
- **Pro**: File unico facile da distribuire
- **Contro**: Estrazione temporanea a ogni avvio (più lento), potenziale rilevamento antivirus

**Raccomandazione**: Usa **One Directory** per development, **One File** per distribuzione finale.

### Console Window

- **Console Based** (NON Window Based)
  - PyDism.py richiede una console per input interattivi e output DISM
  - Window Based nasconderebbe la console causando malfunzionamenti

### Icon (opzionale)

- Se hai un file `.ico`, selezionalo qui per personalizzare l'icona dell'eseguibile

---

## 4. Additional Files - INCLUDERE docs/

**CRITICO**: Devi includere la cartella `docs/` con i README:

Nel campo **Additional Files**:

1. Clicca **Add Folder**
2. Seleziona la cartella `docs\` (quella contenente `README.md` e `README_PyDism.md`)
3. Nel campo **Destination**: scrivi `docs`

Questo crea la struttura:

```text
dist/PyDism/
├── PyDism.exe
└── docs/
    ├── README.md
    ├── README_PyDism.md
    └── BUILD_INSTRUCTIONS.md (questo file)
```

**Note**:

- PyDism.py cerca i README prima in `docs/` poi nella cartella root
- Se ometti `docs/`, i menu 20 e 21 (Help) mostreranno "README not found"

---

## 5. Advanced Options (opzionali)

### Name

- Rinomina l'output (default: `PyDism`)

### Add Data Files (altri file opzionali)

Se hai bisogno di:

- **wimlib-imagex.exe**: Aggiungi come file separato se vuoi includerlo
  - Source: percorso a `wimlib-imagex.exe`
  - Destination: `.` (cartella root dell'exe)
  
- **Config files**: Se avessi file `.json` o `.ini` di configurazione

### Hidden Imports

Non necessario per PyDism.py. Le dipendenze sono rilevate automaticamente:

- **stdlib** (os, sys, pathlib, subprocess, ctypes, json, etc.)
- **colorama>=0.4.6** - Colori console (rilevato automaticamente)
- **prompt_toolkit>=3.0.0** - TAB autocompletion (rilevato automaticamente)

Se hai problemi con import mancanti, aggiungi manualmente:

- `prompt_toolkit`
- `prompt_toolkit.completion`

### UPX (compressione)

- **Disabilita** se hai problemi con antivirus (UPX può triggerare falsi positivi)

---

## 6. Build

1. Clicca **Convert .PY to .EXE** in fondo alla pagina
2. Auto-py-to-exe esegue PyInstaller con i parametri configurati
3. Output nella cartella `output\` (o `dist\` se hai modificato PyInstaller direttamente)

### Output atteso

- **One Directory**: `output/PyDism/PyDism.exe` + cartella `docs/`
- **One File**: `output/PyDism.exe` (con `docs/` embedded)

---

## 7. Test del build

Dopo il build:

```powershell
# Testa l'eseguibile
cd output\PyDism  # (One Directory)
.\PyDism.exe

# Verifica che i menu funzionino:
# - Menu 20: Deve aprire README_PyDism.md
# - Menu 21: Deve aprire README.md (Split WIM workflow)
# - Menu 1: Testa GetImageInfo su un WIM di prova
# - Menu 25: Verifica split WIM (richiede file > 4GB)
# - TAB: Premi TAB quando richiede un path per testare autocompletion
```

### Checklist test

- [ ] L'exe si avvia senza errori
- [ ] Menu 20 apre `docs\README_PyDism.md` in Notepad
- [ ] Menu 21 apre `docs\README.md` in Notepad (Split WIM workflow)
- [ ] Menu 1 esegue `dism /get-imageinfo` correttamente
- [ ] **TAB autocompletion funziona** quando richiede path file
- [ ] Console centering funziona (se abilitato in settings)
- [ ] Elevazione UAC richiesta per operazioni DISM
- [ ] Menu 25 (Split WIM) funziona con file > 4GB

---

## 8. Distribuzione

### One Directory (dist/PyDism/)

Zippa l'intera cartella:

```powershell
Compress-Archive -Path dist\PyDism -DestinationPath PyDism_v1.0.zip
```

Contenuto:

```text
PyDism_v1.0.zip
├── PyDism.exe
├── docs/
│   ├── README.md
│   ├── README_PyDism.md
│   └── BUILD_INSTRUCTIONS.md
└── [altre DLL PyInstaller]
```

### One File (dist/PyDism.exe)

Se hai usato One File, copia manualmente `docs/` accanto all'exe:

```powershell
# Struttura finale per distribuzione:
PyDism_v1.0/
├── PyDism.exe
└── docs/
    ├── README.md
    ├── README_PyDism.md
    └── BUILD_INSTRUCTIONS.md
```

Poi zippa:

```powershell
Compress-Archive -Path PyDism_v1.0 -DestinationPath PyDism_v1.0.zip
```

**IMPORTANTE**: Nel One File mode, `docs/` NON è embedded nell'exe ma deve essere distribuita separatamente.

---

## 9. Configurazione JSON (opzionale - per automazione)

Se preferisci usare direttamente PyInstaller via terminale:

```powershell
# Genera uno .spec file per customizzazioni avanzate
pyi-makespec --onedir --console --name PyDism --add-data "docs;docs" PyDism.py

# Modifica PyDism.spec se necessario, poi:
pyinstaller PyDism.spec
```

### Esempio PyDism.spec minimale

```python
# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['PyDism.py'],
    pathex=[],
    binaries=[],
    datas=[('docs', 'docs')],  # Include cartella docs/
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='PyDism',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,  # Disabilita UPX per evitare falsi positivi AV
    console=True,  # CONSOLE MODE (non window)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='PyDism',
)
```

---

## 10. Troubleshooting

### Problema: "README not found"

- **Causa**: Cartella `docs/` non inclusa nel build
- **Fix**: Aggiungi `docs/` come **Additional Files** in auto-py-to-exe (destination: `docs`)

### Problema: TAB autocompletion non funziona

- **Causa**: `prompt_toolkit` non incluso nel build
- **Fix**:
  1. Verifica che `prompt_toolkit>=3.0.0` sia installato: `pip list | findstr prompt_toolkit`
  2. Se mancante, installa: `pip install prompt_toolkit>=3.0.0`
  3. Rebuilda con auto-py-to-exe (PyInstaller lo rileverà automaticamente)
  4. Se persiste, aggiungi `prompt_toolkit` in **Hidden Imports**

### Problema: "DISM error 740 - Elevation required"

- **Causa**: PyDism non ha permessi amministratore
- **Fix**: Esegui `PyDism.exe` come amministratore (tasto destro → "Run as administrator")

### Problema: Antivirus blocca l'exe

- **Causa**: PyInstaller exe possono triggerare euristiche AV (falsi positivi)
- **Fix**:
  - Disabilita UPX compression in build settings
  - Firma digitalmente l'exe con un certificato code-signing
  - Aggiungi eccezione in Windows Defender

### Problema: Exe si chiude immediatamente

- **Causa**: Eccezione Python non catturata
- **Fix**: Esegui l'exe da PowerShell per vedere l'errore:

  ```powershell
  .\PyDism.exe
  # Leggi il traceback prima che si chiuda
  ```

### Problema: Lentezza avvio (One File mode)

- **Causa**: PyInstaller estrae librerie in temp a ogni avvio
- **Fix**: Passa a **One Directory** mode per performance migliori

---

## 11. Note finali

- **UAC elevation**: DISM richiede sempre privilegi amministratore
- **TAB autocompletion**: Funziona solo se `prompt_toolkit>=3.0.0` è installato e incluso nel build
- **wimlib-imagex** (opzionale): Se vuoi includerlo, aggiungi come Additional File
- **Portabilità**: One Directory è self-contained, copia la cartella `dist/PyDism/` ovunque
- **Aggiornamenti**: Per rebuild dopo modifiche, rilancia auto-py-to-exe con stessa config
- **requirements.txt**: Mantieni aggiornato con tutte le dipendenze per build riproducibili

---

## Quick Start (TL;DR)

```powershell
# 1. Installa tool e dipendenze
pip install auto-py-to-exe
pip install -r requirements.txt

# 2. Avvia GUI
cd c:\SOURCECODE\PYTHON\POSTINSTALL
auto-py-to-exe

# 3. Configura:
# - Script: PyDism.py
# - One Directory
# - Console Based
# - Additional Files: docs/ → docs

# 4. Build → Convert .PY to .EXE

# 5. Test:
cd output\PyDism
.\PyDism.exe

# 6. Distribuisci:
Compress-Archive -Path output\PyDism -DestinationPath PyDism_v1.0.zip
```

---

**Versione**: 1.1  
**Ultima modifica**: 2025-12-04  
**Autore**: PyDism Project  
**Dipendenze**: colorama>=0.4.6, prompt_toolkit>=3.0.0
