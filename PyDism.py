"""
PyDism - Toolkit DISM in Python
Replica il menu del batch `BATCH/DisMenu.bat` per operare su immagini WIM/ESD.
Richiede privilegi amministrativi per montaggi e modifiche.
"""
from __future__ import annotations
import ctypes
import atexit
import time
import webbrowser
import os
import re
import sys
import tempfile
from pathlib import Path
import json
from typing import Iterable, List, Optional
import subprocess
import shutil
try:
    import colorama  # type: ignore
    _HAS_COLORAMA = True
except Exception:
    _HAS_COLORAMA = False

# Helper unico per la pausa standard (evitare pause locali nei singoli menu)
def pause(msg: str = "Press ENTER to return to the menu...") -> None:
    try:
        input(msg)
    except KeyboardInterrupt:
        # Ignora CTRL+C durante la pausa per non interrompere il loop principale
        print()

# ===== Stato e log =====
TEMP = tempfile.gettempdir()
ERRLOG = Path(TEMP) / "PyDism_Errors.log"
OKCNT = 0
FAILCNT = 0
# ===== Output e colori =====
def supports_color() -> bool:
    try:
        return sys.stdout.isatty() and os.environ.get("NO_COLOR") is None
    except Exception:
        return False

USE_COLOR = supports_color()

def color(text: str, *, fg: Optional[str] = None, bold: bool = False) -> str:
    if not USE_COLOR:
        return text
    codes = []
    if bold:
        codes.append("1")
    fg_map = {
        "black": "30",
        "red": "31",
        "green": "32",
        "yellow": "33",
        "blue": "34",
        "magenta": "35",
        "cyan": "36",
        "white": "37",
        "bright_black": "90",
        "bright_red": "91",
        "bright_green": "92",
        "bright_yellow": "93",
        "bright_blue": "94",
        "bright_magenta": "95",
        "bright_cyan": "96",
        "bright_white": "97",
    }
    if fg and fg in fg_map:
        codes.append(fg_map[fg])
    prefix = "\033[" + ";".join(codes) + "m" if codes else ""
    suffix = "\033[0m" if codes else ""
    return f"{prefix}{text}{suffix}"


# Verbose logging (stdout/stderr completi di DISM)
VERBOSE: bool = False
VERBOSE_FILE: Path = Path(TEMP) / "PyDism_Verbose.log"

# Cartella base per mount temporanei (None => usa TEMP)
MOUNT_BASE: Optional[Path] = None

# Backend per export/convert: 'auto' | 'dism' | 'wimlib'
EXPORT_BACKEND: str = "auto"

# Numero di righe da mostrare per i log recenti
LOG_TAIL_LINES: int = 100

# Config persistente: %APPDATA%\PyDism\settings.json (fallback nella cartella dello script)
APPDATA = os.environ.get("APPDATA")
if APPDATA:
    CONFIG_DIR = Path(APPDATA) / "PyDism"
else:
    CONFIG_DIR = Path(__file__).resolve().parent / "config"
CONFIG_FILE = CONFIG_DIR / "settings.json"
CENTER_CONSOLE: bool = True  # centra la finestra della console all'avvio
LAST_CONSOLE_POS: Optional[dict] = None  # {"x": int, "y": int}
RESTORE_CONSOLE_POS: bool = False  # se true e presente SAVED_CONSOLE_POS, ripristina quella posizione
SAVED_CONSOLE_POS: Optional[dict] = None  # posizione preferita salvata {"x": int, "y": int}
CENTER_RETRY: int = 3  # numero di tentativi di centratura (default più robusto)
CENTER_DELAY_MS: int = 150  # ritardo tra tentativi in millisecondi (default più robusto)
ANSI_VT: bool = False  # abilita/disabilita Virtual Terminal (ANSI) a runtime
DISABLE_QUICK_EDIT: bool = True  # disabilita QuickEdit per evitare pause su click
ALWAYS_ON_TOP: bool = False  # finestra console sempre in primo piano
WIMLIB_PROGRESS_MODE: str = "line"  # 'line' (singola riga) | 'off' (nascosto)
INFO_SPINNER: bool = True  # spinner singola riga per comandi informativi (Get-Features/Get-WimInfo)

# Tracciamento cartelle di mount create da questa istanza per cleanup affidabile
_CREATED_MOUNT_DIRS: List[Path] = []

def load_config() -> None:
    """Carica configurazione persistente, se presente."""
    global MOUNT_BASE, VERBOSE, EXPORT_BACKEND, CENTER_CONSOLE, LAST_CONSOLE_POS, RESTORE_CONSOLE_POS, SAVED_CONSOLE_POS
    try:
        if not CONFIG_FILE.exists():
            return
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        # MOUNT_BASE
        mb = data.get("mount_base")
        if isinstance(mb, str) and mb.strip():
            try:
                MOUNT_BASE = Path(mb)
            except Exception:
                MOUNT_BASE = None
        else:
            MOUNT_BASE = None
        # VERBOSE
        vb = data.get("verbose")
        if isinstance(vb, bool):
            VERBOSE = vb
        # EXPORT_BACKEND
        eb = data.get("export_backend")
        if isinstance(eb, str) and eb.lower() in {"auto", "dism", "wimlib"}:
            EXPORT_BACKEND = eb.lower()
        # CENTER_CONSOLE
        cc = data.get("center_console")
        if isinstance(cc, bool):
            CENTER_CONSOLE = cc
        # Retry/delay
        cr = data.get("center_retry")
        if isinstance(cr, int) and 0 <= cr <= 5:
            CENTER_RETRY = cr
        cd = data.get("center_delay_ms")
        if isinstance(cd, int) and 0 <= cd <= 1000:
            CENTER_DELAY_MS = cd
    # LAST_CONSOLE_POS
        lcp = data.get("last_console_pos")
        if isinstance(lcp, dict):
            x = lcp.get("x")
            y = lcp.get("y")
            if isinstance(x, int) and isinstance(y, int):
                LAST_CONSOLE_POS = {"x": x, "y": y}
    # RESTORE_CONSOLE_POS
        rcp = data.get("restore_console_pos")
        if isinstance(rcp, bool):
            RESTORE_CONSOLE_POS = rcp
        # SAVED_CONSOLE_POS
        scp = data.get("saved_console_pos")
        if isinstance(scp, dict):
            x2 = scp.get("x")
            y2 = scp.get("y")
            if isinstance(x2, int) and isinstance(y2, int):
                SAVED_CONSOLE_POS = {"x": x2, "y": y2}
        # ANSI_VT
        av = data.get("ansi_vt")
        if isinstance(av, bool):
            global ANSI_VT
            ANSI_VT = av
        # DISABLE_QUICK_EDIT
        dq = data.get("disable_quick_edit")
        if isinstance(dq, bool):
            global DISABLE_QUICK_EDIT
            DISABLE_QUICK_EDIT = dq
        # ALWAYS_ON_TOP
        aot = data.get("always_on_top")
        if isinstance(aot, bool):
            global ALWAYS_ON_TOP
            ALWAYS_ON_TOP = aot
        # WIMLIB_PROGRESS_MODE
        wpm = data.get("wimlib_progress")
        if isinstance(wpm, str) and wpm in {"line", "off"}:
            global WIMLIB_PROGRESS_MODE
            WIMLIB_PROGRESS_MODE = wpm
        # INFO_SPINNER
        isp = data.get("info_spinner")
        if isinstance(isp, bool):
            global INFO_SPINNER
            INFO_SPINNER = isp
    except Exception as e:
        log_error(f"Error loading config: {e}")

def save_config() -> None:
    """Salva configurazione persistente su disco."""
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        data = {
            "mount_base": str(MOUNT_BASE) if MOUNT_BASE else "",
            "verbose": VERBOSE,
            "export_backend": EXPORT_BACKEND,
            "center_console": CENTER_CONSOLE,
            "last_console_pos": LAST_CONSOLE_POS if LAST_CONSOLE_POS else None,
            "restore_console_pos": RESTORE_CONSOLE_POS,
            "saved_console_pos": SAVED_CONSOLE_POS if SAVED_CONSOLE_POS else None,
            "center_retry": CENTER_RETRY,
            "center_delay_ms": CENTER_DELAY_MS,
            "ansi_vt": ANSI_VT,
            "disable_quick_edit": DISABLE_QUICK_EDIT,
            "always_on_top": ALWAYS_ON_TOP,
            "wimlib_progress": WIMLIB_PROGRESS_MODE,
            "info_spinner": INFO_SPINNER,
        }
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        log_error(f"Error saving config: {e}")

# ===== Path helper (exe/script dir) & external tools =====
def _app_dir() -> Path:
    """Ritorna la cartella dell'eseguibile (se frozen) o dello script."""
    if getattr(sys, "frozen", False):
        # PyInstaller one-file estrae in _MEIPASS
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            return Path(meipass)
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent

def _find_wimlib_exe() -> str:
    """Ritorna il percorso a wimlib-imagex. Priorità: cartella app -> PATH."""
    exe_dir = _app_dir()
    for name in ("wimlib-imagex.exe", "wimlib-imagex"):
        cand = exe_dir / name
        if cand.exists():
            return str(cand)
    return "wimlib-imagex"

def _wimlib_source_label() -> str:
    """Ritorna una stringa che indica da dove verrà usato wimlib: 'locale', 'PATH' o 'assente'."""
    exe_dir = _app_dir()
    local = any((exe_dir / name).exists() for name in ("wimlib-imagex.exe", "wimlib-imagex"))
    if local:
        return "local (next to executable)"
    # Prova a invocare --version dal PATH senza rumorosità
    try:
        cp = subprocess.run(["wimlib-imagex", "--version"], capture_output=True, text=True)
        if cp.returncode == 0:
            return "system PATH"
    except Exception:
        pass
    return "missing"

def _wimlib_version() -> Optional[str]:
    try:
        exe = _find_wimlib_exe()
        cp = subprocess.run([exe, "--version"], capture_output=True, text=True, encoding="utf-8", errors="replace")
        if cp.returncode == 0:
            out = (cp.stdout or cp.stderr or "").strip()
            # Possibili formati:
            #  - "wimlib v1.14.4"
            #  - "wimlib-imagex 1.14.4 (using wimlib 1.14.4)"
            # Estrai la prima versione numerica che trovi
            m = re.search(r"(\d+\.\d+\.\d+|\d+\.\d+)", out)
            if m:
                return m.group(1)
            return None
    except Exception:
        return None
    return None

def _find_readme() -> Optional[Path]:
    """Trova README_pydism.md in docs/ accanto all'eseguibile o allo script."""
    for base in (_app_dir(), Path(__file__).resolve().parent):
        # Cerca prima in docs/
        cand = base / "docs" / "README_pydism.md"
        if cand.exists():
            return cand
        # Fallback: cartella root (per backward compatibility)
        cand = base / "README_pydism.md"
        if cand.exists():
            return cand
    return None

def _find_readme_main() -> Optional[Path]:
    """Trova README.md in docs/ accanto all'eseguibile o allo script."""
    for base in (_app_dir(), Path(__file__).resolve().parent):
        # Cerca prima in docs/
        cand = base / "docs" / "README.md"
        if cand.exists():
            return cand
        # Fallback: cartella root (per backward compatibility)
        cand = base / "README.md"
        if cand.exists():
            return cand
    return None

# Fallback testuale minimale in caso il README non sia disponibile
HELP_TEXT = (
    "PyDism (Python) - Quick guide\n\n"
    "- Administrative privileges are required for RW operations.\n"
    "- .ESD images cannot be modified RW; use export/convert instead.\n"
    "- Menu 17: show recent logs.\n"
    "- Menu 18: set base folder for mounts.\n"
    "- Menu 19: console/verbose/backend settings (ENTER=shown defaults).\n"
    "- Menu 14/16: export/convert (wimlib if present, otherwise DISM).\n"
)

def menu_help() -> None:
    """Menu 20: Apre README_pydism.md (guida completa PyDism)."""
    print_header("Help - PyDism Guide (README_pydism.md)")
    readme_dismenu = _find_readme()
    
    if readme_dismenu:
        print(f"Opening: {readme_dismenu}")
        try:
            subprocess.Popen(["notepad.exe", str(readme_dismenu)])
        except Exception:
            # Fallback: prova ShellExecuteW -> startfile -> webbrowser
            opened = False
            try:
                ret = ctypes.windll.shell32.ShellExecuteW(None, "open", str(readme_dismenu), None, None, 1)
                opened = int(ret) > 32
            except Exception:
                opened = False
            if not opened:
                try:
                    os.startfile(str(readme_dismenu))  # type: ignore[attr-defined]
                    opened = True
                except Exception:
                    opened = False
            if not opened:
                try:
                    opened = bool(webbrowser.open(readme_dismenu.as_uri()))
                except Exception:
                    opened = False
            if not opened:
                print("[WARN] Could not open README_pydism.md")
                print("\n--- Quick guide ---\n" + HELP_TEXT)
    else:
        print("README_pydism.md not found in docs/ folder.")
        print("\n--- Quick guide ---\n" + HELP_TEXT)
    # Nessuna pausa qui: il main gestisce già la pausa di ritorno al menu

def menu_help_workflow() -> None:
    """Menu 25: Apre README.md (workflow split WIM)."""
    print_header("Help - Split WIM Workflow (README.md)")
    readme_main = _find_readme_main()
    
    if readme_main:
        print(f"Opening: {readme_main}")
        try:
            subprocess.Popen(["notepad.exe", str(readme_main)])
        except Exception:
            # Fallback: prova ShellExecuteW -> startfile -> webbrowser
            opened = False
            try:
                ret = ctypes.windll.shell32.ShellExecuteW(None, "open", str(readme_main), None, None, 1)
                opened = int(ret) > 32
            except Exception:
                opened = False
            if not opened:
                try:
                    os.startfile(str(readme_main))  # type: ignore[attr-defined]
                    opened = True
                except Exception:
                    opened = False
            if not opened:
                try:
                    opened = bool(webbrowser.open(readme_main.as_uri()))
                except Exception:
                    opened = False
            if not opened:
                print("[WARN] Could not open README.md")
    else:
        print("README.md not found in docs/ folder.")
    # Nessuna pausa qui: il main gestisce già la pausa di ritorno al menu

def menu_open_logs_folder() -> None:
    print_header("Open logs folder")
    # Logs live in TEMP
    log_dir = Path(TEMP)
    print(f"Opening: {log_dir}")
    try:
        os.startfile(str(log_dir))  # type: ignore[attr-defined]
    except Exception as e:
        print(f"[ERROR] Unable to open folder: {e}")
    # Nessuna pausa qui: il main gestisce già la pausa di ritorno al menu

def menu_cleanup_local_temp_dirs() -> None:
    print_header("Clean temporary folders (session)")
    if not _CREATED_MOUNT_DIRS:
        print("[INFO] No mount folders tracked from this session.")
        return
    removed = 0
    failed = 0
    total = len(_CREATED_MOUNT_DIRS)
    reclaimed_bytes = 0
    # Lavora su una copia così possiamo modificare la lista originale in sicurezza
    for d in list(_CREATED_MOUNT_DIRS):
        try:
            if d.exists():
                size_before = _dir_size(d)
                print(f"- Removing: {d}  (size: {_format_bytes(size_before)})")
                _remove_dir_tree(d)
            else:
                print(f"- Already missing: {d}")
            # If it's gone now, remove it from tracking
            if not d.exists():
                try:
                    _CREATED_MOUNT_DIRS.remove(d)
                except Exception:
                    pass
                removed += 1
                if 'size_before' in locals():
                    reclaimed_bytes += size_before
            else:
                failed += 1
        except Exception as e:
            failed += 1
            log_error(f"[CLEANUP-LOCAL] {d}: {e}")
    print()
    print(color(f"[RESULT] Total: {total}  Removed: {removed}  Not removed: {failed}", fg="yellow"))
    print(color(f"[Space reclaimed] {_format_bytes(reclaimed_bytes)}", fg="bright_green", bold=True))

# ===== Utility =====
def log_error(msg: str) -> None:
    with open(ERRLOG, "a", encoding="utf-8") as f:
        f.write(msg.rstrip() + "\n")

def print_header(title: str) -> None:
    print("\n" + color("=" * 8, fg="bright_green", bold=True), color(title, fg="bright_white", bold=True), color("=" * 8, fg="bright_green", bold=True))

def is_admin() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False

def _get_console_hwnd() -> int:
    try:
        return ctypes.windll.kernel32.GetConsoleWindow()
    except Exception:
        return 0

def hide_console_window() -> None:
    """Nasconde la console corrente (se presente)."""
    try:
        hwnd = _get_console_hwnd()
        if hwnd:
            ctypes.windll.user32.ShowWindow(hwnd, 0)  # SW_HIDE = 0
    except Exception:
        pass

def has_console() -> bool:
    return _get_console_hwnd() != 0

def _set_vt_mode(enabled: bool) -> None:
    """Imposta/azzera ENABLE_VIRTUAL_TERMINAL_PROCESSING per STDOUT/STDERR."""
    try:
        kernel32 = ctypes.windll.kernel32
        ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
        for std_id in (-11, -12):  # STD_OUTPUT_HANDLE, STD_ERROR_HANDLE
            h = kernel32.GetStdHandle(std_id)
            if h and h != ctypes.c_void_p(-1).value:
                mode = ctypes.wintypes.DWORD()
                if kernel32.GetConsoleMode(h, ctypes.byref(mode)):
                    if enabled:
                        new_mode = ctypes.wintypes.DWORD(mode.value | ENABLE_VIRTUAL_TERMINAL_PROCESSING)
                    else:
                        new_mode = ctypes.wintypes.DWORD(mode.value & ~ENABLE_VIRTUAL_TERMINAL_PROCESSING)
                    kernel32.SetConsoleMode(h, new_mode)
    except Exception:
        pass

def _init_colorama() -> None:
    """Inizializza colorama (se disponibile) per convertire ANSI in Win32.
    Utile quando non si vuole abilitare VT ma si vogliono i colori.
    """
    if _HAS_COLORAMA:
        try:
            colorama.init(convert=True, strip=False, autoreset=False)
        except Exception:
            pass

def _set_quick_edit(disable: bool) -> None:
    """Abilita/disabilita QuickEdit per evitare che un click del mouse sospenda l'output."""
    try:
        kernel32 = ctypes.windll.kernel32
        STD_INPUT_HANDLE = -10
        ENABLE_QUICK_EDIT_MODE = 0x0040
        ENABLE_EXTENDED_FLAGS = 0x0080
        hIn = kernel32.GetStdHandle(STD_INPUT_HANDLE)
        if not hIn or hIn == ctypes.c_void_p(-1).value:
            return
        mode = ctypes.wintypes.DWORD()
        if not kernel32.GetConsoleMode(hIn, ctypes.byref(mode)):
            return
        new_mode = mode.value | ENABLE_EXTENDED_FLAGS
        if disable:
            new_mode &= ~ENABLE_QUICK_EDIT_MODE
        else:
            new_mode |= ENABLE_QUICK_EDIT_MODE
        kernel32.SetConsoleMode(hIn, new_mode)
    except Exception:
        pass

def ensure_console() -> None:
    """Alloca una console se non presente (utile per exe 'window based' dopo elevazione)."""
    try:
        global USE_COLOR
        if not has_console():
            ctypes.windll.kernel32.AllocConsole()
            # attendo un attimo che la finestra venga creata
            time.sleep(0.05)
            try:
                # Rebind stream su console
                sys.stdout = open("CONOUT$", "w", encoding="utf-8", buffering=1)
                sys.stderr = open("CONOUT$", "w", encoding="utf-8", buffering=1)
                sys.stdin = open("CONIN$", "r", encoding="utf-8")
            except Exception:
                pass
        # Non forzare VT/ANSI di default: preserva resa grafica
        # Applica VT se richiesto in config
        try:
            if ANSI_VT:
                _set_vt_mode(True)
        except Exception:
            pass
        # Inizializza colorama (se presente) per conversione ANSI->Win32
        _init_colorama()
        # Disabilita QuickEdit per evitare pause su click (configurabile)
        try:
            _set_quick_edit(DISABLE_QUICK_EDIT)
        except Exception:
            pass
        # Applica AlwaysOnTop se richiesto
        try:
            _set_always_on_top(ALWAYS_ON_TOP)
        except Exception:
            pass
        # Assicurati che la finestra sia visibile e non minimizzata
        hwnd = _get_console_hwnd()
        if hwnd:
            try:
                is_iconic = ctypes.windll.user32.IsIconic(hwnd)
                is_zoomed = ctypes.windll.user32.IsZoomed(hwnd)
                if is_iconic or is_zoomed:
                    ctypes.windll.user32.ShowWindow(hwnd, 9)  # SW_RESTORE
                else:
                    ctypes.windll.user32.ShowWindow(hwnd, 5)  # SW_SHOW
            except Exception:
                pass
    except Exception:
        pass

def _enforce_always_on_top_retries() -> None:
    """Riafferma lo stato AlwaysOnTop con piccoli retry per assestamenti della console all'avvio."""
    try:
        if not ALWAYS_ON_TOP:
            return
        for _ in range(3):
            _set_always_on_top(True)
            time.sleep(0.05)
    except Exception:
        pass

def _get_screen_size() -> Optional[tuple[int, int]]:
    try:
        user32 = ctypes.windll.user32
        return (int(user32.GetSystemMetrics(0)), int(user32.GetSystemMetrics(1)))
    except Exception:
        return None

def center_console_window() -> None:
    """Centra la finestra della console sullo schermo principale e salva l'ultima posizione."""
    global LAST_CONSOLE_POS
    try:
        hwnd = _get_console_hwnd()
        if not hwnd:
            return
        # Assicurati che la finestra sia ripristinata prima di muoverla
        try:
            is_iconic = ctypes.windll.user32.IsIconic(hwnd)
            is_zoomed = ctypes.windll.user32.IsZoomed(hwnd)
            if is_iconic or is_zoomed:
                ctypes.windll.user32.ShowWindow(hwnd, 9)  # SW_RESTORE
        except Exception:
            pass
        # Dimensioni finestra corrente
        rect = ctypes.wintypes.RECT()
        ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect))
        w = rect.right - rect.left
        h = rect.bottom - rect.top
        # Rettangolo monitor su cui si trova il cursore
        mon = _get_cursor_monitor_rect()
        if mon:
            ml, mt, mr, mb = mon
            sw = mr - ml
            sh = mb - mt
            x = max(ml, ml + (sw - w) // 2)
            y = max(mt, mt + (sh - h) // 3)  # leggermente più alto del centro
        else:
            scr = _get_screen_size()
            if not scr:
                return
            sw, sh = scr
            x = max(0, (sw - w) // 2)
            y = max(0, (sh - h) // 3)
        # Salva posizione
        LAST_CONSOLE_POS = {"x": x, "y": y}
        # Muovi finestra con piccoli retry
        tries = max(1, int(CENTER_RETRY))
        for i in range(tries):
            ctypes.windll.user32.MoveWindow(hwnd, x, y, w, h, True)
            time.sleep(max(0, CENTER_DELAY_MS) / 1000.0)
    except Exception:
        pass

def _get_cursor_monitor_rect() -> Optional[tuple[int, int, int, int]]:
    """Rettangolo del monitor dove si trova il cursore. Usa area completa del monitor (rcMonitor)."""
    try:
        class POINT(ctypes.Structure):
            _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]
        class MONITORINFO(ctypes.Structure):
            _fields_ = [
                ("cbSize", ctypes.c_ulong),
                ("rcMonitor", ctypes.wintypes.RECT),
                ("rcWork", ctypes.wintypes.RECT),
                ("dwFlags", ctypes.c_ulong),
            ]
        pt = POINT()
        ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
        MONITOR_DEFAULTTONEAREST = 2
        hmon = ctypes.windll.user32.MonitorFromPoint(pt, MONITOR_DEFAULTTONEAREST)
        mi = MONITORINFO()
        mi.cbSize = ctypes.sizeof(MONITORINFO)
        if ctypes.windll.user32.GetMonitorInfoW(hmon, ctypes.byref(mi)):
            r = mi.rcMonitor
            return (r.left, r.top, r.right, r.bottom)
    except Exception:
        pass
    return None

def _set_always_on_top(enabled: bool) -> None:
    try:
        hwnd = _get_console_hwnd()
        if not hwnd:
            return
        HWND_TOPMOST = -1
        HWND_NOTOPMOST = -2
        SWP_NOMOVE = 0x0002
        SWP_NOSIZE = 0x0001
        # Quando abilitiamo AlwaysOnTop, evitiamo NOACTIVATE per portare la finestra visibile in primo piano
        flags = SWP_NOMOVE | SWP_NOSIZE
        ctypes.windll.user32.SetWindowPos(hwnd, HWND_TOPMOST if enabled else HWND_NOTOPMOST, 0, 0, 0, 0, flags)
        if enabled:
            try:
                # Mostra e porta in foreground per evitare che resti dietro ad altre finestre
                ctypes.windll.user32.ShowWindow(hwnd, 5)  # SW_SHOW
                ctypes.windll.user32.SetForegroundWindow(hwnd)
            except Exception:
                pass
    except Exception:
        pass

def get_console_rect() -> Optional[tuple[int, int, int, int]]:
    try:
        hwnd = _get_console_hwnd()
        if not hwnd:
            return None
        rect = ctypes.wintypes.RECT()
        if ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect)):
            return (rect.left, rect.top, rect.right, rect.bottom)
    except Exception:
        pass
    return None

def save_current_console_position() -> None:
    """Salva la posizione attuale della finestra come preferita (SAVED_CONSOLE_POS)."""
    global SAVED_CONSOLE_POS
    rc = get_console_rect()
    if not rc:
        return
    l, t, r, b = rc
    SAVED_CONSOLE_POS = {"x": l, "y": t}
    save_config()

def restore_console_position() -> None:
    """Ripristina la posizione salvata, se presente."""
    try:
        if not SAVED_CONSOLE_POS:
            return
        hwnd = _get_console_hwnd()
        if not hwnd:
            return
        # Mantieni dimensioni correnti, cambia solo x,y
        rect = ctypes.wintypes.RECT()
        ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect))
        w = rect.right - rect.left
        h = rect.bottom - rect.top
        x = int(SAVED_CONSOLE_POS.get("x", rect.left))
        y = int(SAVED_CONSOLE_POS.get("y", rect.top))
        ctypes.windll.user32.MoveWindow(hwnd, x, y, w, h, True)
    except Exception:
        pass

def relaunch_as_admin() -> None:
    # Evita loop infinito con flag
    if "--elevated" in sys.argv:
        print("[!] Privilegi amministrativi non disponibili.")
        sys.exit(1)

    def _quote(a: str) -> str:
        return f'"{a}"' if re.search(r"\s", a) else a

    script_path = Path(__file__).resolve()
    # Working dir stabile: per exe 'frozen' usa la cartella dell'eseguibile (evita lock su temp one-file)
    if getattr(sys, "frozen", False):
        workdir = str(Path(sys.executable).parent)
    else:
        workdir = str(script_path.parent)

    # Se eseguibile impacchettato (es. auto-py-to-exe): rilancia direttamente l'exe
    if getattr(sys, "frozen", False):
        app = sys.executable  # path all'exe corrente
        args = sys.argv[1:] + ["--elevated"]
        params = " ".join(_quote(a) for a in args)
    else:
        # Rilancia l'interprete con percorso assoluto allo script
        app = sys.executable
        args = [str(script_path)] + sys.argv[1:] + ["--elevated"]
        params = " ".join(_quote(a) for a in args)

    # Se siamo in exe 'frozen' e abbiamo una console, nascondila per evitare finestre inutili persistenti
    if getattr(sys, "frozen", False):
        hide_console_window()
    ret = ctypes.windll.shell32.ShellExecuteW(None, "runas", app, params, workdir, 1)
    if int(ret) <= 32:
        print("[!] Impossibile elevare privilegi (codice ShellExecuteW:", ret, ")")
        sys.exit(1)
    # In caso di successo, termina il processo corrente (nuovo processo elevato parte a parte)
    sys.exit(0)


def run(cmd: List[str], check: bool = False, capture: Optional[bool] = None, cwd: Optional[Path] = None) -> subprocess.CompletedProcess:
    # Usa esecuzione sicura senza shell, cattura stdout/stderr opzionalmente
    if capture is None:
        capture = VERBOSE
    try:
        cp = subprocess.run(
            cmd,
            check=False,
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=capture,
            cwd=str(cwd) if cwd else None,
        )
    except FileNotFoundError:
        log_error(f"Comando non trovato: {cmd[0]}")
        raise
    # Verbose: scrivi su file e riproduci su console
    if VERBOSE:
        try:
            with open(VERBOSE_FILE, "a", encoding="utf-8") as f:
                f.write("\n== CMD ==\n" + " ".join(cmd) + "\n")
                f.write(f"RC: {cp.returncode}\n")
                if cp.stdout:
                    f.write("-- STDOUT --\n" + cp.stdout + ("\n" if not cp.stdout.endswith("\n") else ""))
                if cp.stderr:
                    f.write("-- STDERR --\n" + cp.stderr + ("\n" if not cp.stderr.endswith("\n") else ""))
        except Exception:
            pass
        # Nota: non riproduciamo qui su console. I call-site che passano capture=True
        # decidono se stampare o meno l'output. Questo evita doppi output.
    if check and cp.returncode != 0:
        # Log minimo
        log_error(f"RUN ERR rc={cp.returncode} cmd={' '.join(cmd)}")
        if capture:
            if cp.stdout:
                log_error("STDOUT:\n" + cp.stdout)
            if cp.stderr:
                log_error("STDERR:\n" + cp.stderr)
    return cp


def dism(*args: str, capture: Optional[bool] = None, check: bool = False) -> subprocess.CompletedProcess:
    return run(["dism", *args], capture=capture, check=check)


def cleanup_mountpoints() -> None:
    run(["dism", "/Cleanup-Mountpoints"], check=False)

def _onerror_make_writable(func, path, exc_info):
    try:
        os.chmod(path, 0o777)
        func(path)
    except Exception:
        pass

def _remove_dir_tree(p: Path, retries: int = 5, delay: float = 0.2) -> None:
    """Rimozione ricorsiva con retry e fix permessi su Windows."""
    for i in range(max(1, retries)):
        try:
            if not p.exists():
                return
            shutil.rmtree(p, onerror=_onerror_make_writable)
            return
        except Exception:
            time.sleep(delay)
    # Ultimo tentativo: rinomina per sbloccare e riprovare
    try:
        tmp = p.with_name(p.name + "_to_delete")
        p.rename(tmp)
        shutil.rmtree(tmp, onerror=_onerror_make_writable)
    except Exception as e:
        log_error(f"[CLEANUP] Impossibile rimuovere {p}: {e}")

def _dir_size(p: Path) -> int:
    """Calcola dimensione totale (in byte) della directory p in modo tollerante."""
    total = 0
    try:
        if not p.exists():
            return 0
        for root, dirs, files in os.walk(p, onerror=lambda e: None):
            # Evita di seguire symlink di directory
            # (os.walk non segue symlink di default, ma essere espliciti aiuta)
            for f in files:
                try:
                    fp = Path(root) / f
                    if not fp.is_symlink() and fp.exists():
                        total += fp.stat().st_size
                except Exception:
                    pass
    except Exception:
        pass
    return total

def _format_bytes(n: int) -> str:
    units = ["B", "KB", "MB", "GB", "TB"]
    size = float(n)
    idx = 0
    while size >= 1024.0 and idx < len(units) - 1:
        size /= 1024.0
        idx += 1
    if idx == 0:
        return f"{int(size)} {units[idx]}"
    return f"{size:.2f} {units[idx]}"

def _atexit_cleanup() -> None:
    """Cleanup finale di eventuali mount creati rimasti e cleanup mountpoints DISM."""
    try:
        # Prova a smontare mount orfani (in generale)
        cleanup_mountpoints()
    except Exception:
        pass
    # Rimuovi qualsiasi cartella creata ancora presente
    for d in list(_CREATED_MOUNT_DIRS):
        try:
            _remove_dir_tree(d)
        except Exception:
            pass

atexit.register(_atexit_cleanup)

def show_mounted_wims() -> None:
    print_header("Current mounted WIMs")
    cp = dism("/Get-MountedWimInfo", capture=True)
    if cp.stdout:
        print(cp.stdout, end="" if cp.stdout.endswith("\n") else "\n")
    elif cp.stderr:
        print(cp.stderr, end="" if cp.stderr.endswith("\n") else "\n")

def cleanup_orphan_mounts() -> None:
    print_header("Clean orphan mounts")
    ans = input("Run DISM /Cleanup-Mountpoints? (y/N): ").strip().lower()
    if ans not in {"y", "yes"}:
        print("Operation cancelled.")
        return
    cleanup_mountpoints()
    print("[OK] Cleanup completed.")
    # Show mount status immediately for verification
    print()
    print_header("Mounts status after cleanup")
    show_mounted_wims()


def make_temp_mount(prefix: str = "mnt_") -> Path:
    cleanup_mountpoints()
    base_dir: Optional[str] = None
    if MOUNT_BASE:
        try:
            MOUNT_BASE.mkdir(parents=True, exist_ok=True)
            base_dir = str(MOUNT_BASE)
        except Exception as e:
            print(f"[WARN] Unable to use custom mount folder '{MOUNT_BASE}': {e}. Using TEMP.")
            base_dir = None
    mount_dir = Path(tempfile.mkdtemp(prefix=prefix, dir=base_dir))
    # Traccia per cleanup a fine processo
    _CREATED_MOUNT_DIRS.append(mount_dir)
    return mount_dir


def unmount(mount_dir: Path, commit: bool = False) -> None:
    if not mount_dir or not mount_dir.exists():
        return
    args = ["/Unmount-Wim", f"/MountDir:{str(mount_dir)}", "/Commit" if commit else "/Discard"]
    _stream_dism_progress(args)
    # Togli la cartella
    try:
        _remove_dir_tree(mount_dir)
    except Exception:
        pass
    # Rimuovi dalla lista di tracciamento
    try:
        if mount_dir in _CREATED_MOUNT_DIRS:
            _CREATED_MOUNT_DIRS.remove(mount_dir)
    except Exception:
        pass


def ensure_rw_allowed(image_path: Path) -> None:
    if image_path.suffix.lower() == ".esd":
        raise RuntimeError("Operation not allowed on ESD. Convert to WIM first.")


# ===== Input e autocompletamento =====
try:
    from prompt_toolkit import prompt  # type: ignore
    from prompt_toolkit.completion import PathCompleter  # type: ignore
    HAVE_PTK = True
except Exception as e:
    HAVE_PTK = False
    print(color(f"[DEBUG] prompt_toolkit NON disponibile: {e}", fg="bright_red"))

def input_path(prompt_text: str) -> str:
    """Input percorso con autocompletamento TAB."""
    if HAVE_PTK:
        try:
            result = prompt(prompt_text, completer=PathCompleter())
            return result
        except Exception as e:
            print(color(f"[DEBUG] prompt_toolkit ERRORE: {type(e).__name__}: {e}", fg="bright_yellow"))
            log_error(f"prompt_toolkit error: {type(e).__name__}: {e}")
    
    # Fallback
    print(color("[DEBUG] Usando input() standard", fg="bright_yellow"))
    return input(prompt_text)


def ask_path(prompt: str) -> Optional[Path]:
    p = input_path(prompt).strip().strip('"')
    if not p:
        return None
    path = Path(p)
    if not path.exists():
        print(f"[ERRORE] File/Cartella non trovato: {path}")
        return None
    return path


def ask_output_path(prompt: str) -> Optional[Path]:
    """Chiede un percorso di OUTPUT.
    - Accetta file che NON esistono ancora.
    - Richiede che la cartella padre esista ed è una directory.
    - Rifiuta percorsi che puntano a una cartella esistente.
    """
    p = input_path(prompt).strip().strip('"')
    if not p:
        return None
    path = Path(p)
    # Se è una directory esistente, non è valido come file di output
    if path.exists() and path.is_dir():
        print(f"[ERRORE] Il percorso indicato è una cartella: {path}")
        return None
    parent = path.parent if str(path.parent) != '' else Path.cwd()
    if not parent.exists() or not parent.is_dir():
        print(f"[ERRORE] La cartella di destinazione non esiste: {parent}")
        return None
    return path


def ask_index() -> Optional[int]:
    s = input("Indice: ").strip()
    if not s:
        return None
    if not re.fullmatch(r"\d+", s):
        print("[ERRORE] L'indice deve essere numerico.")
        return None
    return int(s)


def ask_compression() -> Optional[str]:
    print("\n[Compressione] Valori: max, fast, none, recovery")
    while True:
        c = input("Compressione: ").strip().lower()
        if c in {"max", "fast", "none", "recovery"}:
            return c
        print("[ERRORE] Valore non valido.")


def get_wiminfo(path: Path) -> None:
    dism("/Get-WimInfo", f"/WimFile:{str(path)}")


def mount_image(wim: Path, index: int, ro: bool = False) -> Path:
    mdir = make_temp_mount("mnt_")
    args = [
        "/Mount-Wim",
        f"/WimFile:{str(wim)}",
        f"/Index:{index}",
        f"/MountDir:{str(mdir)}",
    ]
    if ro:
        args.append("/ReadOnly")
    rc = _stream_dism_progress(args)
    if rc != 0:
        log_error("Mount fallito: DISM rc=" + str(rc))
        unmount(mdir, commit=False)
        raise RuntimeError("Montaggio immagine fallito")
    return mdir


# ====== Operazioni di menu ======

def menu_getinfo() -> None:
    wim = ask_path("WIM/ESD path: ")
    if not wim:
        return
    cp = _run_dism_with_spinner_capture(["/Get-WimInfo", f"/WimFile:{str(wim)}"])
    if cp.stdout:
        print(cp.stdout, end="" if cp.stdout.endswith("\n") else "\n")


def menu_mount_rw() -> None:
    wim = ask_path("WIM/ESD path: ")
    if not wim:
        return
    idx = ask_index()
    if idx is None:
        return
    ensure_rw_allowed(wim)
    mdir = mount_image(wim, idx, ro=False)
    # Piccolo sottomenu operativo
    if (mdir / "Windows").is_dir():
        print("[OK] Mounted (RW):", mdir)
    else:
        print("[INFO] Windows folder not found (different image?)")
    while True:
        print("\nActions:")
        print("  1) Open folder in File Explorer")
        print("  2) Leave mounted and return to menu")
        print("  3) Unmount and save (Commit)")
        print("  4) Unmount and discard (Discard)")
        print("  0) Back (leave mounted)")
        try:
            pre = input("Scelta: ").strip()
        except KeyboardInterrupt:
            print()
            pre = "2"
        if pre == "1":
            try:
                os.startfile(str(mdir))  # type: ignore[attr-defined]
            except Exception as e:
                print(f"[ERROR] Unable to open Explorer: {e}")
            continue
        if pre in {"2", "0"}:
            print("[INFO] Left mounted. Use menu 23 to unmount later.")
            return
        if pre == "3":
            unmount(mdir, commit=True)
            print("[OK] Unmounted with save.")
            return
        if pre == "4":
            unmount(mdir, commit=False)
            print("[OK] Unmounted without saving (discard).")
            return
        print("[ERROR] Invalid choice.")


def menu_mount_ro() -> None:
    wim = ask_path("WIM/ESD path: ")
    if not wim:
        return
    idx = ask_index()
    if idx is None:
        return
    mdir = mount_image(wim, idx, ro=True)
    if (mdir / "Windows").is_dir():
        print("[OK] Mounted (RO):", mdir)
    else:
        print("[INFO] Windows folder not found (different image?)")
    while True:
        print("\nActions:")
        print("  1) Open folder in File Explorer")
        print("  2) Leave mounted and return to menu")
        print("  3) Unmount (Discard)")
        print("  0) Back (leave mounted)")
        try:
            pre = input("Scelta: ").strip()
        except KeyboardInterrupt:
            print()
            pre = "2"
        if pre == "1":
            try:
                os.startfile(str(mdir))  # type: ignore[attr-defined]
            except Exception as e:
                print(f"[ERROR] Unable to open Explorer: {e}")
            continue
        if pre in {"2", "0"}:
            print("[INFO] Left mounted in read-only. Use menu 23 to unmount later.")
            return
        if pre == "3":
            unmount(mdir, commit=False)
            print("[OK] Unmounted (discard).")
            return
        print("[ERROR] Invalid choice.")

def menu_unmount_dir() -> None:
    print_header("Unmount mounted directory")
    mdir = ask_path("MountDir path to unmount: ")
    if not mdir:
        return
    try:
        ans = input("Save changes (commit)? (y/N): ").strip().lower()
    except KeyboardInterrupt:
        print()
        ans = "n"
    commit = ans in {"s", "si", "sì", "y", "yes", "y"}
    try:
        unmount(mdir, commit=commit)
        print("[OK] Unmounted.")
    except Exception as e:
        print(f"[ERROR] Unmount failed: {e}")


def _features_with_filter(wim: Path, idx: int) -> None:
    print("\n=== Available features list ===")
    print("[1] All")
    print("[2] Only Disabled")
    print("[3] Only Payload Removed")
    print("[0] Back")
    choice = input("Choice: ").strip()
    if choice not in {"0", "1", "2", "3"}:
        print("[ERROR] Invalid choice.")
        return
    if choice == "0":
        return
    mdir = mount_image(wim, idx, ro=True)
    try:
        # Usa spinner a riga singola durante la raccolta dell'output delle feature
        cp = _run_dism_with_spinner_capture(["/Image:" + str(mdir), "/Get-Features", "/English"])
        out = cp.stdout or ""
        lines = out.splitlines()
        if choice == "1":
            print(out)
        else:
            # Raggruppa blocchi Feature Name/State per stamparli completi
            current_name = None
            current_state = None
            matched = 0
            for line in lines:
                if line.strip().startswith("Feature Name :"):
                    current_name = line.strip()
                elif line.strip().startswith("State :"):
                    current_state = line.strip()
                    if choice == "2" and "Disabled" in current_state:
                        # stampa nome e stato
                        if current_name:
                            print(current_name)
                        print(current_state)
                        print()
                        matched += 1
                    if choice == "3" and "Payload Removed" in current_state:
                        if current_name:
                            print(current_name)
                        print(current_state)
                        print()
                        matched += 1
            if matched == 0:
                print("[INFO] No matching features found.")
    finally:
        unmount(mdir, commit=False)
        # nessuna pausa qui; il loop principale gestisce la pausa di ritorno


def menu_listfeat() -> None:
    wim = ask_path("WIM/ESD path: ")
    if not wim:
        return
    idx = ask_index()
    if idx is None:
        return
    _features_with_filter(wim, idx)


def menu_enablefeat() -> None:
    wim = ask_path("WIM/ESD path: ")
    if not wim:
        return
    idx = ask_index()
    if idx is None:
        return
    print("\n[Filter] 1=All 2=Disabled 3=Payload Removed 0=Skip")
    pre = input("Choice: ").strip()
    if pre in {"1", "2", "3"}:
        _features_with_filter(wim, idx)
    feat = input("Feature to ENABLE: ").strip()
    if not feat:
        return
    ensure_rw_allowed(wim)
    mdir = mount_image(wim, idx, ro=False)
    try:
        rc = _stream_dism_progress(["/Image:" + str(mdir), "/Enable-Feature", f"/FeatureName:{feat}", "/All"])
        commit_ok = (rc == 0)
        if rc != 0:
            log_error(f"ENABLEFEAT: enable fallito ({feat})")
        # Verifica stato finale
        try:
            cpv = _run_dism_with_spinner_capture(["/Image:" + str(mdir), "/Get-FeatureInfo", f"/FeatureName:{feat}", "/English"])
            out = (cpv.stdout or "") + "\n" + (cpv.stderr or "")
            m = re.search(r"^\s*State\s*:\s*(.+)$", out, re.MULTILINE)
            state = (m.group(1).strip() if m else "?")
            if re.search(r"Enabled", state, re.IGNORECASE):
                print(color(f"[OK] Feature '{feat}' enabled (state: {state}).", fg="bright_green", bold=True))
                commit_ok = True
            elif re.search(r"Enable Pending", state, re.IGNORECASE):
                print(color(f"[INFO] Enable pending for '{feat}' (state: {state}).", fg="bright_cyan"))
                commit_ok = True
            else:
                print(color(f"[WARN] Resulting state for '{feat}': {state}.", fg="bright_yellow"))
        except Exception as e:
            print(color(f"[WARN] Impossibile verificare lo stato della feature: {e}", fg="bright_yellow"))
    finally:
        try:
            unmount(mdir, commit=locals().get("commit_ok", False))
        except Exception:
            pass


def menu_disablefeat() -> None:
    wim = ask_path("WIM/ESD path: ")
    if not wim:
        return
    idx = ask_index()
    if idx is None:
        return
    print("\n[Filter] 1=All 2=Disabled 3=Payload Removed 0=Skip")
    pre = input("Choice: ").strip()
    if pre in {"1", "2", "3"}:
        _features_with_filter(wim, idx)
    feat = input("Feature to DISABLE: ").strip()
    if not feat:
        return
    ensure_rw_allowed(wim)
    mdir = mount_image(wim, idx, ro=False)
    try:
        rc = _stream_dism_progress(["/Image:" + str(mdir), "/Disable-Feature", f"/FeatureName:{feat}"])
        commit_ok = (rc == 0)
        if rc != 0:
            log_error(f"DISABLEFEAT: disable fallito ({feat})")
        # Verifica stato finale
        try:
            cpv = _run_dism_with_spinner_capture(["/Image:" + str(mdir), "/Get-FeatureInfo", f"/FeatureName:{feat}", "/English"])
            out = (cpv.stdout or "") + "\n" + (cpv.stderr or "")
            m = re.search(r"^\s*State\s*:\s*(.+)$", out, re.MULTILINE)
            state = (m.group(1).strip() if m else "?")
            if re.search(r"Disabled", state, re.IGNORECASE):
                print(color(f"[OK] Feature '{feat}' disabled (state: {state}).", fg="bright_green", bold=True))
                commit_ok = True
            elif re.search(r"Disable Pending", state, re.IGNORECASE):
                print(color(f"[INFO] Disable pending for '{feat}' (state: {state}).", fg="bright_cyan"))
                commit_ok = True
            else:
                print(color(f"[WARN] Resulting state for '{feat}': {state}.", fg="bright_yellow"))
        except Exception as e:
            print(color(f"[WARN] Impossibile verificare lo stato della feature: {e}", fg="bright_yellow"))
    finally:
        try:
            unmount(mdir, commit=locals().get("commit_ok", False))
        except Exception:
            pass


def menu_addpkg() -> None:
    wim = ask_path("WIM/ESD path: ")
    if not wim:
        return
    idx = ask_index()
    if idx is None:
        return
    pkg = ask_path("CAB/MSU package path: ")
    if not pkg:
        return
    ensure_rw_allowed(wim)
    mdir = mount_image(wim, idx, ro=False)
    try:
        rc = _stream_dism_progress(["/Image:" + str(mdir), "/Add-Package", f"/PackagePath:{str(pkg)}"])
        if rc != 0:
            log_error(f"ADDPKG: add-package fallito ({pkg})")
        _stream_dism_progress(["/Unmount-Wim", f"/MountDir:{str(mdir)}", "/Commit"])
    finally:
        unmount(mdir, commit=False)


def menu_adddrv() -> None:
    wim = ask_path("WIM/ESD path: ")
    if not wim:
        return
    idx = ask_index()
    if idx is None:
        return
    drv = ask_path("Driver path (.inf or folder): ")
    if not drv:
        return
    ensure_rw_allowed(wim)
    mdir = mount_image(wim, idx, ro=False)
    try:
        # Opzionale: forza driver non firmati
        try:
            fu = input("Force unsigned drivers? (y/N): ").strip().lower()
        except KeyboardInterrupt:
            print()
            fu = ""
        force = fu in {"s", "si", "sì", "y", "yes", "y"}

        # Conteggio driver terze parti prima
        pre_cnt = _count_third_party_drivers(mdir)

        args = ["/Image:" + str(mdir), "/Add-Driver", f"/Driver:{str(drv)}", "/Recurse"]
        if force:
            args.append("/ForceUnsigned")
        rc = _stream_dism_progress(args)
        commit_ok = (rc == 0)
        if rc != 0:
            log_error(f"ADDDRV: add-driver fallito ({drv})")

        # Verifica: conteggio driver terze parti dopo
        post_cnt = _count_third_party_drivers(mdir)
        delta = post_cnt - pre_cnt
        if delta > 0:
            print(color(f"[OK] Added {delta} drivers (before: {pre_cnt}, after: {post_cnt}).", fg="bright_green", bold=True))
            commit_ok = True
        else:
            print(color(f"[INFO] No new drivers detected (before: {pre_cnt}, after: {post_cnt}).", fg="bright_cyan"))
    finally:
        # Commit solo se l'operazione principale è riuscita
        try:
            unmount(mdir, commit=locals().get("commit_ok", False))
        except Exception:
            pass


def menu_cleanup() -> None:
    wim = ask_path("WIM/ESD path: ")
    if not wim:
        return
    idx = ask_index()
    if idx is None:
        return
    ensure_rw_allowed(wim)
    mdir = mount_image(wim, idx, ro=False)
    try:
        rc = _stream_dism_progress(["/Image:" + str(mdir), "/Cleanup-Image", "/StartComponentCleanup", "/ResetBase"])
        if rc != 0:
            log_error("CLEANUP: StartComponentCleanup failed")
        _stream_dism_progress(["/Unmount-Wim", f"/MountDir:{str(mdir)}", "/Commit"])
    finally:
        unmount(mdir, commit=False)


def _boot_has_index2(boot_wim: Path) -> bool:
    cp = dism("/Get-WimInfo", f"/WimFile:{str(boot_wim)}", "/English", capture=True)
    out = (cp.stdout or "") + "\n" + (cp.stderr or "")
    return bool(re.search(r"Index\s*:\s*2\b", out))


def menu_adddrvboot() -> None:
    boot = ask_path("Full path to boot.wim: ")
    if not boot:
        return
    drv = ask_path("Driver folder (.inf or folder): ")
    if not drv:
        return
    if not _boot_has_index2(boot):
        print("[ERRORE] boot.wim non contiene l'indice 2.")
        return
    mdir = make_temp_mount("mnt_boot_")
    try:
        rc = _stream_dism_progress(["/Mount-Wim", f"/WimFile:{str(boot)}", "/Index:2", f"/MountDir:{str(mdir)}"])
        if rc != 0:
            log_error("ADDDRVBOOT: mount fallito")
            raise RuntimeError("Montaggio boot.wim fallito")

        # Opzionale: forza driver non firmati
        try:
            fu = input("Force unsigned drivers? (y/N): ").strip().lower()
        except KeyboardInterrupt:
            print()
            fu = ""
        force = fu in {"s", "si", "sì", "y", "yes", "y"}

        # Conteggio driver terze parti prima
        pre_cnt = _count_third_party_drivers(mdir)

        args = ["/Image:" + str(mdir), "/Add-Driver", f"/Driver:{str(drv)}", "/Recurse"]
        if force:
            args.append("/ForceUnsigned")
        rc2 = _stream_dism_progress(args)
        commit_ok = (rc2 == 0)
        if rc2 != 0:
            log_error(f"ADDDRVBOOT: add-driver fallito ({drv})")

        # Verifica: conteggio driver terze parti dopo
        post_cnt = _count_third_party_drivers(mdir)
        delta = post_cnt - pre_cnt
        if delta > 0:
            print(color(f"[OK] Added {delta} drivers to boot.wim (before: {pre_cnt}, after: {post_cnt}).", fg="bright_green", bold=True))
            commit_ok = True
        else:
            print(color(f"[INFO] No new drivers detected on boot.wim (before: {pre_cnt}, after: {post_cnt}).", fg="bright_cyan"))
    finally:
        # Commit solo se l'operazione principale è riuscita
        try:
            unmount(mdir, commit=locals().get("commit_ok", False))
        except Exception:
            pass


def menu_remdrvbootfolder() -> None:
    boot = ask_path("Percorso completo di boot.wim: ")
    if not boot:
        return
    folder = ask_path("Cartella da cui rimuovere driver (.inf ricorsivo): ")
    if not folder:
        return
    if not _boot_has_index2(boot):
        print("[ERRORE] boot.wim non contiene l'indice 2.")
        return
    mdir = make_temp_mount("mnt_boot_")
    try:
        rc = _stream_dism_progress(["/Mount-Wim", f"/WimFile:{str(boot)}", "/Index:2", f"/MountDir:{str(mdir)}"])
        if rc != 0:
            log_error("REMDRVBOOTFOLDER: mount fallito")
            raise RuntimeError("Montaggio boot.wim fallito")
        errcnt = 0
        for root, _, files in os.walk(folder):
            for fn in files:
                if fn.lower().endswith(".inf"):
                    driver_inf = Path(root) / fn
                    rc2 = _stream_dism_progress(["/Image:" + str(mdir), "/Remove-Driver", f"/Driver:{str(driver_inf)}"])
                    if rc2 != 0:
                        errcnt += 1
                        log_error(f"REMDRVBOOTFOLDER: remove-driver fallito {driver_inf}")
        _stream_dism_progress(["/Unmount-Wim", f"/MountDir:{str(mdir)}", "/Commit"])
        if errcnt == 0:
            print(color("[OK] Removal completed.", fg="bright_green", bold=True))
        else:
            print(color(f"[INFO] Not removed: {errcnt} (see log)", fg="bright_cyan"))
    finally:
        unmount(mdir, commit=False)


def _ask_indexes() -> Optional[List[int]]:
    print()
    ind = input("Indici (spazio separati): ").strip()
    if not ind:
        return None
    out: List[int] = []
    for tok in ind.split():
        if not tok.isdigit():
            print(f"[ERRORE] Indice non numerico: {tok}")
            return None
        out.append(int(tok))
    return out


def _normalize_compression_for_dest(compress: str, dest: Path) -> str:
    if dest.suffix.lower() == ".wim" and compress.lower() == "recovery":
        print("[INFO] 'recovery' non valido per WIM, imposto 'max'.")
        return "max"
    return compress


def menu_export() -> None:
    src = ask_path("WIM/ESD sorgente: ")
    if not src:
        return
    cp_info = dism("/Get-WimInfo", f"/WimFile:{str(src)}", capture=True)
    if cp_info.stdout:
        print(cp_info.stdout, end="" if cp_info.stdout.endswith("\n") else "\n")
    indexes = _ask_indexes()
    if not indexes:
        return
    dest = ask_output_path("File WIM/ESD destinazione: ")
    if not dest:
        return
    comp = ask_compression()
    if not comp:
        return
    comp = _normalize_compression_for_dest(comp, dest)
    export_indices(src, indexes, dest, comp, label="EXPORT")


def menu_checkhealth() -> None:
    wim = ask_path("Percorso WIM/ESD: ")
    if not wim:
        return
    idx = ask_index()
    if idx is None:
        return
    print(color("[INFO] ", fg="bright_cyan", bold=True) + "Montaggio immagine per Check/Scan Health...")
    mdir = mount_image(wim, idx, ro=True)
    try:
        print("\n[CheckHealth]")
        # DISM richiede il contesto /Cleanup-Image per usare CheckHealth/ScanHealth
        cp1 = dism("/Image:" + str(mdir), "/Cleanup-Image", "/CheckHealth", capture=True)
        if cp1.stdout:
            print(cp1.stdout, end="" if cp1.stdout.endswith("\n") else "\n")
        print("\n[ScanHealth]")
        cp2 = dism("/Image:" + str(mdir), "/Cleanup-Image", "/ScanHealth", capture=True)
        if cp2.stdout:
            print(cp2.stdout, end="" if cp2.stdout.endswith("\n") else "\n")
    finally:
        unmount(mdir, commit=False)


def menu_convertesd() -> None:
    src = ask_path("Percorso file ESD: ")
    if not src:
        return
    cp_info = dism("/Get-WimInfo", f"/WimFile:{str(src)}", capture=True)
    if cp_info.stdout:
        print(cp_info.stdout, end="" if cp_info.stdout.endswith("\n") else "\n")
    indexes = _ask_indexes()
    if not indexes:
        return
    dest = ask_output_path("File WIM di destinazione (.wim): ")
    if not dest:
        return
    comp = ask_compression()
    if not comp:
        return
    comp = _normalize_compression_for_dest(comp, dest)
    export_indices(src, indexes, dest, comp, label="CONVERTESD")

# ====== Wimlib integration & export helpers ======
def has_wimlib() -> bool:
    try:
        cp = run([_find_wimlib_exe(), "--version"], capture=True)
        return cp.returncode == 0
    except Exception:
        return False


def _wimlib_compress_args(dest: Path, compress: str) -> List[str]:
    args: List[str] = []
    # Se il target è .esd o l'utente ha scelto 'recovery', forziamo --esd
    if dest.suffix.lower() == ".esd" or compress.lower() == "recovery":
        args.append("--esd")
        return args
    comp = compress.lower()
    if comp == "none":
        args.append("--compress=none")
    elif comp == "fast":
        args.append("--compress=XPRESS")
    else:  # max
        args.append("--compress=LZX")
    return args


def export_with_wimlib(src: Path, indexes: List[int], dest: Path, compress: str, label: str) -> None:
    for i in indexes:
        print(("Converto" if label == "CONVERTESD" else "Esporto"), f"indice {i} (wimlib)...")
        cmd = [
            _find_wimlib_exe(),
            "export",
            str(src),
            str(i),
            str(dest),
            "--check",
        ] + _wimlib_compress_args(dest, compress)
        rc = _stream_wimlib_progress(cmd)
        if rc != 0:
            log_error(f"{label}: indice {i} fallito (wimlib)")


def export_with_dism(src: Path, indexes: List[int], dest: Path, compress: str, label: str) -> None:
    for i in indexes:
        print(("Converto" if label == "CONVERTESD" else "Esporto"), f"indice {i} (dism)...")
        # Usa una barra di progresso a riga singola anche per DISM (stderr parsing)
        args = [
            "/Export-Image",
            f"/SourceImageFile:{str(src)}",
            f"/SourceIndex:{i}",
            f"/DestinationImageFile:{str(dest)}",
            f"/Compress:{compress}",
            "/CheckIntegrity",
        ]
        rc = _stream_dism_progress(args)
        if rc != 0:
            log_error(f"{label}: indice {i} fallito (dism)")


def export_indices(src: Path, indexes: List[int], dest: Path, compress: str, label: str) -> None:
    # Se il file di destinazione esiste, chiedi conferma per cancellare
    if dest.exists() and dest.is_file():
        ans = input(f"Il file di destinazione esiste ({dest}). Cancellarlo? [s/N]: ").strip().lower()
        if ans not in {"s", "si", "sì", "y", "yes"}:
            print("Operazione annullata.")
            return
        try:
            dest.unlink()
        except Exception as e:
            print(f"[ERRORE] Impossibile cancellare {dest}: {e}")
            return
    backend = EXPORT_BACKEND
    if backend == "auto":
        backend = "wimlib" if has_wimlib() else "dism"
    if backend == "wimlib":
        export_with_wimlib(src, indexes, dest, compress, label)
    else:
        export_with_dism(src, indexes, dest, compress, label)

# ====== Helpers UI/log e progresso wimlib ======
def tail_file(p: Path, n: int) -> List[str]:
    if not p.exists():
        return []
    try:
        with open(p, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
        return lines[-n:]
    except Exception:
        return []


def menu_show_logs() -> None:
    print_header("Log recenti")
    print(f"[Error log] {ERRLOG}")
    for line in tail_file(ERRLOG, LOG_TAIL_LINES):
        print(line, end="")
    print("\n")
    print(f"[Verbose log] {VERBOSE_FILE}")
    for line in tail_file(VERBOSE_FILE, LOG_TAIL_LINES):
        print(line, end="")
    print("\n")
    # Nessuna pausa qui: il main gestisce già la pausa di ritorno al menu


def _stream_wimlib_progress(cmd: List[str]) -> int:
    """Esegue wimlib-imagex in streaming, mostrando una progress bar su UNA sola riga.
    - Legge da stderr (dove wimlib scrive il progresso)
    - Sopprime stdout (DEVNULL) per evitare output indesiderato e possibili wrap
    - Adatta la lunghezza della barra alla larghezza della console per evitare il going-to-next-line
    Ritorna il codice di uscita del processo.
    """
    def term_width(default: int = 80) -> int:
        try:
            import shutil as _sh
            return int(_sh.get_terminal_size((default, 20)).columns)
        except Exception:
            return default

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except FileNotFoundError:
        log_error("wimlib-imagex non trovato")
        return 1

    percent_last = -1
    last_print_len = 0
    cols = max(40, term_width(80))

    # Limiti fissi per evitare wrap: calcola una barra che non superi la larghezza
    # Formato: "Progresso: XXX% [##########...]"
    prefix_plain = "Progresso: "
    suffix_plain = " []"
    # riserva 12 char per "XXX% " e 2 per le parentesi + 2 margini
    bar_max = max(10, min(50, cols - (len(prefix_plain) + 12 + 2 + 2)))

    assert proc.stderr is not None
    try:
        for line in proc.stderr:
            raw = line.rstrip("\r\n")
            # Cerca percentuali intere o decimali e arrotonda
            m = re.search(r"(\d+(?:\.\d+)?)%", raw)
            if m:
                try:
                    p = int(float(m.group(1)) + 0.5)
                    p = max(0, min(100, p))
                    if p != percent_last:
                        percent_last = p
                        if WIMLIB_PROGRESS_MODE != "off":
                            # Calcola barra
                            filled = int((p / 100.0) * bar_max)
                            bar_plain = "#" * filled
                            # Costruisci stringa colorata (stessa lunghezza visiva)
                            prog = (
                                color("Progresso:", fg="bright_cyan", bold=True)
                                + f" {p:3d}% ["
                                + color(f"{bar_plain:<{bar_max}}", fg="bright_green")
                                + "]"
                            )
                            # Stampa su una riga: CR + stringa + padding spazi per cancellare residui
                            sys.stdout.write("\r" + prog)
                            # Padding per cancellare eventuali residui da stampe più lunghe
                            vis_len_est = len(prefix_plain) + 5 + 2 + bar_max  # stima senza codici ANSI
                            pad = max(0, last_print_len - vis_len_est)
                            if pad:
                                sys.stdout.write(" " * pad)
                            sys.stdout.flush()
                            last_print_len = vis_len_est
                except Exception:
                    pass
            # In verbose, riporta anche le linee complete sul file
            if VERBOSE:
                try:
                    with open(VERBOSE_FILE, "a", encoding="utf-8") as f:
                        f.write(raw + "\n")
                except Exception:
                    pass
    except KeyboardInterrupt:
        try:
            proc.terminate()
        except Exception:
            pass
        proc.wait(timeout=5)
        print("\n[INFO] Operazione annullata dall'utente.")
        return 130

    rc = proc.wait()
    if percent_last >= 0 and WIMLIB_PROGRESS_MODE != "off":
        # Forza 100% su singola riga e a capo finale
        filled = bar_max
        prog = (
            color("Progresso:", fg="bright_cyan", bold=True)
            + " 100% ["
            + color("#" * filled, fg="bright_green")
            + "]"
        )
        sys.stdout.write("\r" + prog + "\n")
        sys.stdout.flush()
    return rc

def _count_third_party_drivers(image_dir: Path) -> int:
    """Conta i driver di terze parti nell'immagine montata usando DISM /Get-Drivers.
    Ritorna un intero >= 0. In caso di errore restituisce 0 e logga l'evento.
    """
    try:
        cp = _run_dism_with_spinner_capture(["/Image:" + str(image_dir), "/Get-Drivers", "/English"])
        out = (getattr(cp, "stdout", "") or "") + "\n" + (getattr(cp, "stderr", "") or "")
        cnt = 0
        for line in out.splitlines():
            if re.search(r"^\s*Published Name\s*:\s*", line, re.IGNORECASE):
                cnt += 1
        return max(0, cnt)
    except Exception as e:
        log_error(f"_count_third_party_drivers error: {e}")
        return 0

def _stream_dism_progress(args: List[str]) -> int:
    """Esegue DISM in streaming e mostra progresso su una sola riga.
    Analogo a _stream_wimlib_progress: legge stderr, estrae percentuali e riscrive la riga.
    """
    def term_width(default: int = 80) -> int:
        try:
            import shutil as _sh
            return int(_sh.get_terminal_size((default, 20)).columns)
        except Exception:
            return default

    cmd = ["dism", *args]
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except FileNotFoundError:
        log_error("DISM non trovato nel PATH")
        return 1

    percent_last = -1
    last_print_len = 0
    cols = max(40, term_width(80))
    prefix_plain = "Progresso: "
    bar_max = max(10, min(50, cols - (len(prefix_plain) + 12 + 2 + 2)))

    assert proc.stderr is not None
    try:
        for line in proc.stderr:
            raw = line.rstrip("\r\n")
            # Cerca percentuali stile "10%", "10.0%" etc.
            m = re.search(r"(\d+(?:\.\d+)?)%", raw)
            if m:
                try:
                    p = int(float(m.group(1)) + 0.5)
                    p = max(0, min(100, p))
                    if p != percent_last:
                        percent_last = p
                        # Riusa lo stesso schema della barra (rispettando eventuale preferenza)
                        if WIMLIB_PROGRESS_MODE != "off":
                            filled = int((p / 100.0) * bar_max)
                            prog = (
                                color("Progresso:", fg="bright_cyan", bold=True)
                                + f" {p:3d}% ["
                                + color(f"{'#'*filled:<{bar_max}}", fg="bright_green")
                                + "]"
                            )
                            sys.stdout.write("\r" + prog)
                            # Stima lunghezza visiva per pulizia residui
                            vis_len_est = len(prefix_plain) + 5 + 2 + bar_max
                            pad = max(0, last_print_len - vis_len_est)
                            if pad:
                                sys.stdout.write(" " * pad)
                            sys.stdout.flush()
                            last_print_len = vis_len_est
                except Exception:
                    pass
            if VERBOSE:
                try:
                    with open(VERBOSE_FILE, "a", encoding="utf-8") as f:
                        f.write(raw + "\n")
                except Exception:
                    pass
    except KeyboardInterrupt:
        try:
            proc.terminate()
        except Exception:
            pass
        proc.wait(timeout=5)
        print("\n[INFO] Operazione annullata dall'utente.")
        return 130

    rc = proc.wait()
    if percent_last >= 0 and WIMLIB_PROGRESS_MODE != "off":
        filled = bar_max
        prog = (
            color("Progresso:", fg="bright_cyan", bold=True)
            + " 100% ["
            + color("#" * filled, fg="bright_green")
            + "]"
        )
        sys.stdout.write("\r" + prog + "\n")
        sys.stdout.flush()
    return rc

def menu_split_wim() -> None:
    """Split install.wim into install.swm parts for FAT32 compatibility.
    DISM /Split-Image creates install.swm, install2.swm, etc.
    """
    print_header("Split install.wim for FAT32")
    try:
        wim_path = input_path("Path to install.wim: ").strip().strip('"')
    except KeyboardInterrupt:
        print()
        return
    
    if not wim_path:
        print("[!] Path required.")
        pause()
        return
    
    wim = Path(wim_path)
    if not wim.exists():
        print(f"[!] File not found: {wim}")
        pause()
        return
    
    if not wim.suffix.lower() == ".wim":
        print("[!] Not a .wim file.")
        pause()
        return
    
    # Check size
    size_bytes = wim.stat().st_size
    size_gb = size_bytes / (1024**3)
    print(f"[INFO] install.wim size: {size_gb:.2f} GB ({size_bytes:,} bytes)")
    
    if size_gb < 4.0:
        print(f"[INFO] File is < 4GB, splitting not required for FAT32.")
        try:
            cont = input("Continue anyway? (y/N): ").strip().lower()
        except KeyboardInterrupt:
            print()
            return
        if cont not in {"y", "yes", "si", "sì"}:
            return
    
    # Default output: install.swm in same folder
    output_folder = wim.parent
    swm_base = output_folder / "install.swm"
    
    print(f"[INFO] Output will be: {swm_base}, install2.swm, ...")
    
    # File size for split (default 3800 MB)
    try:
        chunk = input("Chunk size in MB (ENTER=3800): ").strip()
    except KeyboardInterrupt:
        print()
        return
    
    if not chunk:
        chunk = "3800"
    
    try:
        chunk_mb = int(chunk)
        if chunk_mb < 100:
            print("[!] Chunk size too small, minimum 100 MB.")
            pause()
            return
    except ValueError:
        print("[!] Invalid number.")
        pause()
        return
    
    print(f"[INFO] Splitting with DISM, chunk size: {chunk_mb} MB...")
    
    cmd = [
        "/Split-Image",
        f"/ImageFile:{wim}",
        f"/SWMFile:{swm_base}",
        f"/FileSize:{chunk_mb}"
    ]
    
    rc = _stream_dism_progress(cmd)
    
    if rc == 0:
        # Count created .swm files
        swm_files = sorted(output_folder.glob("install*.swm"))
        print(f"\n[SUCCESS] Split completed. Created {len(swm_files)} file(s):")
        for sf in swm_files:
            sz = sf.stat().st_size / (1024**3)
            print(f"  - {sf.name} ({sz:.2f} GB)")
        print(f"\n[INFO] Copy all install*.swm files to sources\\ folder in ISO/USB.")
        print(f"[INFO] Windows Setup will auto-read split images.")
        print(f"[INFO] Do NOT split boot.wim (it stays as-is for boot).")
        try:
            clean = input("\nDelete original install.wim? (y/N): ").strip().lower()
        except KeyboardInterrupt:
            print()
            pause()
            return
        if clean in {"y", "yes", "si", "sì"}:
            try:
                wim.unlink()
                print(f"[INFO] Deleted: {wim}")
            except Exception as e:
                print(f"[!] Failed to delete: {e}")
    else:
        print("\n[!] Split failed. Check error log.")


def menu_unsplit_swm() -> None:
    """Ricombina file SWM splittati in un unico WIM.
    Usa DISM /Export-Image con /SWMFile per leggere tutti i pezzi.
    """
    print_header("Ricombina file SWM in WIM")
    print("[INFO] Questo comando ricombina install.swm, install2.swm, ... in un unico .wim")
    print("[INFO] Utile se hai splittato e ora devi modificare l'immagine (aggiungere driver/features)")
    print()
    
    try:
        swm_path = input_path("Path al primo file .swm (es: install.swm): ").strip().strip('"')
    except KeyboardInterrupt:
        print()
        return
    
    if not swm_path:
        print("[!] Path required.")
        pause()
        return
    
    swm = Path(swm_path)
    if not swm.exists():
        print(f"[!] File not found: {swm}")
        pause()
        return
    
    if not swm.suffix.lower() == ".swm":
        print("[!] Not a .swm file.")
        pause()
        return
    
    # Auto-detect altri file swm nella stessa cartella
    swm_folder = swm.parent
    swm_base = swm.stem  # es: "install"
    swm_pattern = f"{swm_base}*.swm"
    swm_files = sorted(swm_folder.glob(swm_pattern))
    
    if len(swm_files) == 0:
        print(f"[!] No .swm files found matching pattern: {swm_pattern}")
        pause()
        return
    
    print(f"[INFO] Found {len(swm_files)} .swm file(s):")
    total_size = 0
    for sf in swm_files:
        sz = sf.stat().st_size / (1024**3)
        total_size += sz
        print(f"  - {sf.name} ({sz:.2f} GB)")
    print(f"[INFO] Total size: {total_size:.2f} GB")
    print()
    
    # Get image info per scegliere index
    print("[INFO] Reading image info from .swm...")
    info_cmd = ["/Get-ImageInfo", f"/ImageFile:{swm}", f"/SWMFile:{swm_folder / (swm_base + '*.swm')}"]
    info_result = _run_dism_with_spinner_capture(info_cmd)
    
    if info_result.returncode != 0:
        print(f"[!] Failed to read image info: {info_result.stderr}")
        pause()
        return
    
    # Parse indexes
    indexes = []
    for line in info_result.stdout.splitlines():
        if line.strip().lower().startswith("index :"):
            try:
                idx = int(line.split(":")[1].strip())
                indexes.append(idx)
            except:
                pass
    
    if not indexes:
        print("[!] No indexes found in .swm files.")
        pause()
        return
    
    print(f"[INFO] Available indexes: {indexes}")
    
    try:
        idx_input = input(f"Select index to export (ENTER={indexes[0]}): ").strip()
    except KeyboardInterrupt:
        print()
        return
    
    if not idx_input:
        idx_input = str(indexes[0])
    
    try:
        selected_idx = int(idx_input)
        if selected_idx not in indexes:
            print(f"[!] Invalid index. Must be one of: {indexes}")
            pause()
            return
    except ValueError:
        print("[!] Invalid number.")
        pause()
        return
    
    # Output WIM path
    default_output = swm_folder / f"{swm_base}_ricombinato.wim"
    try:
        output_path = input_path(f"Output WIM path (ENTER={default_output}): ").strip().strip('"')
    except KeyboardInterrupt:
        print()
        return
    
    if not output_path:
        output_path = str(default_output)
    
    output_wim = Path(output_path)
    
    if output_wim.exists():
        print(f"[!] Output file already exists: {output_wim}")
        try:
            overwrite = input("Overwrite? (y/N): ").strip().lower()
        except KeyboardInterrupt:
            print()
            return
        if overwrite not in {"y", "yes", "si", "sì"}:
            return
        try:
            output_wim.unlink()
        except Exception as e:
            print(f"[!] Failed to delete existing file: {e}")
            pause()
            return
    
    # Compression type
    try:
        comp = input("Compression (max/fast/none, ENTER=max): ").strip().lower()
    except KeyboardInterrupt:
        print()
        return
    
    if not comp:
        comp = "max"
    
    if comp not in {"max", "fast", "none"}:
        print(f"[!] Invalid compression: {comp}")
        pause()
        return
    
    print(f"\n[INFO] Recombining .swm files into: {output_wim}")
    print(f"[INFO] Using compression: {comp}")
    print(f"[INFO] This may take several minutes...")
    print()
    
    # DISM Export command
    swm_wildcard = swm_folder / f"{swm_base}*.swm"
    cmd = [
        "/Export-Image",
        f"/SourceImageFile:{swm}",
        f"/SWMFile:{swm_wildcard}",
        f"/SourceIndex:{selected_idx}",
        f"/DestinationImageFile:{output_wim}",
        f"/Compress:{comp}",
        "/CheckIntegrity"
    ]
    
    rc = _stream_dism_progress(cmd)
    
    if rc == 0:
        output_size = output_wim.stat().st_size / (1024**3)
        print(f"\n[SUCCESS] Recombined WIM created: {output_wim}")
        print(f"[INFO] Size: {output_size:.2f} GB")
        print(f"\n[INFO] You can now:")
        print(f"  1. Mount this WIM (Menu 2)")
        print(f"  2. Add drivers/features (Menu 7, 10)")
        print(f"  3. Unmount with commit")
        print(f"  4. Re-export optimized (Menu 14)")
        print(f"  5. Re-split if needed (Menu 25)")
    else:
        print("\n[!] Recombine failed. Check error log.")


def _run_dism_with_spinner_capture(args: List[str]):
    """Esegue DISM catturando stdout/stderr ma mostrando una singola riga di attività (spinner).
    Utile per comandi informativi (es. /Get-Features) dove DISM non stampa percentuali.
    Ritorna un oggetto semplice con attributi: returncode, stdout, stderr.
    """
    cmd = ["dism", *args]
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except FileNotFoundError:
        log_error("DISM non trovato nel PATH")
        class _R:  # simple result
            def __init__(self):
                self.returncode = 1
                self.stdout = ""
                self.stderr = "DISM not found"
        return _R()

    out_lines: List[str] = []
    err_lines: List[str] = []

    import threading

    def _reader(stream, acc: List[str]):
        try:
            for line in stream:  # type: ignore
                acc.append(line)
        except Exception:
            pass
        try:
            stream.close()  # type: ignore
        except Exception:
            pass

    t_out = threading.Thread(target=_reader, args=(proc.stdout, out_lines), daemon=True)  # type: ignore
    t_err = threading.Thread(target=_reader, args=(proc.stderr, err_lines), daemon=True)  # type: ignore
    t_out.start(); t_err.start()

    spinner = "|/-\\"
    si = 0
    try:
        while proc.poll() is None:
            if INFO_SPINNER and WIMLIB_PROGRESS_MODE != "off":
                msg = color("DISM in corso (info)", fg="bright_cyan", bold=True)
                sys.stdout.write("\r" + f"{msg}  " + spinner[si % len(spinner)])
                sys.stdout.flush()
                si += 1
            time.sleep(0.12)
    except KeyboardInterrupt:
        try:
            proc.terminate()
        except Exception:
            pass
        proc.wait(timeout=5)
        print("\n[INFO] Operazione annullata dall'utente.")
    finally:
        t_out.join(timeout=2)
        t_err.join(timeout=2)
        # pulisci la riga spinner
        try:
            sys.stdout.write("\r" + " " * 80 + "\r")
            sys.stdout.flush()
        except Exception:
            pass

    class _Result:
        def __init__(self, rc, so, se):
            self.returncode = rc
            self.stdout = so
            self.stderr = se

    return _Result(proc.returncode, "".join(out_lines), "".join(err_lines))

MENU_ITEMS = {
    "1": ("List image indexes", menu_getinfo),
    "2": ("Mount image (RW) and unmount", menu_mount_rw),
    "3": ("Mount image (RO) and unmount", menu_mount_ro),
    "4": ("Show mounted WIMs", show_mounted_wims),
    "5": ("Cleanup orphan mounts", cleanup_orphan_mounts),
    "6": ("List features with filter", menu_listfeat),
    "7": ("Enable feature", menu_enablefeat),
    "8": ("Disable feature", menu_disablefeat),
    "9": ("Add package (CAB/MSU)", menu_addpkg),
    "10": ("Add driver", menu_adddrv),
    "11": ("Component cleanup", menu_cleanup),
    "12": ("Add driver to boot.wim (idx 2)", menu_adddrvboot),
    "13": ("Remove drivers from boot.wim by folder", menu_remdrvbootfolder),
    "14": ("Export indexes to new WIM/ESD", menu_export),
    "15": ("Image health check", menu_checkhealth),
    "16": ("Convert ESD to WIM", menu_convertesd),
    "17": ("Show recent logs", menu_show_logs),
    "18": ("Settings: mount folder", None),
    "19": ("Settings: console/verbose/backend", None),
    "20": ("Help - PyDism Guide (README_pydism.md)", menu_help),
    "21": ("Help - Split WIM Workflow (README.md)", menu_help_workflow),
    "22": ("Open logs folder", menu_open_logs_folder),
    "23": ("Clean temp folders created (session)", menu_cleanup_local_temp_dirs),
    "24": ("Unmount an existing mount directory", menu_unmount_dir),
    "25": ("Split install.wim for FAT32 (install.swm)", menu_split_wim),
    "26": ("Recombine SWM files into WIM", menu_unsplit_swm),
}

def main() -> None:
    global MOUNT_BASE, VERBOSE, EXPORT_BACKEND, CENTER_CONSOLE, RESTORE_CONSOLE_POS, ANSI_VT, DISABLE_QUICK_EDIT, CENTER_RETRY, CENTER_DELAY_MS
    os.system("title PyDism - DISM Toolkit")
    print("PyDism - DISM Toolkit")
    # Pulizia log
    try:
        if ERRLOG.exists():
            ERRLOG.unlink()
    except Exception:
        pass
    # Elevazione: dipende solo dai privilegi amministrativi
    if not is_admin():
        print("[!] Privilegi amministrativi richiesti.")
        relaunch_as_admin()
        return
    # Carica configurazione persistente (se esiste) PRIMA di allocare/inizializzare la console,
    # così VT/QuickEdit/AlwaysOnTop vengono applicati subito in ensure_console().
    load_config()
    # Siamo elevati: assicura una console visibile in scenari exe 'window based' e applica impostazioni
    ensure_console()
    # In alcuni ambienti la finestra può subire riattacchi iniziali: riafferma AlwaysOnTop
    _enforce_always_on_top_retries()
    # Ripristino o centratura console
    try:
        if RESTORE_CONSOLE_POS and SAVED_CONSOLE_POS:
            restore_console_position()
        elif CENTER_CONSOLE:
            center_console_window()
        # Riapplica AlwaysOnTop dopo eventuale spostamento per garantire lo z-order corretto (con piccoli retry)
        _enforce_always_on_top_retries()
    except Exception:
        pass
    # Config già caricata
    while True:
        # Header colorato
        print("\n" + color("================= DISM MENU =================", fg="bright_green", bold=True))
        keys_sorted = sorted((int(k) for k in MENU_ITEMS.keys()))
        for ik in keys_sorted:
            # separatore prima delle utility
            if ik == 17:
                print(color("---------------------------------------------", fg="bright_yellow"))
            kstr = f"{ik:>2}"
            txt = color(MENU_ITEMS[str(ik)][0], fg="bright_white")
            print(f" {color(kstr, fg='bright_cyan', bold=True)}) {txt}")
        # Stato impostazioni
        mb = str(MOUNT_BASE) if MOUNT_BASE else "%TEMP%"
        try:
            ver = _wimlib_version()
            if ver:
                wlbl = f"{ver}"
            else:
                src = _wimlib_source_label()
                wlbl = "assente" if src == "assente" else src
        except Exception:
            wlbl = "?"
        print(color(f"    [MountDirBase: {mb}]  [Verbose: {VERBOSE}]  [ExportBackend: {EXPORT_BACKEND}]  [wimlib {wlbl}]", fg="yellow"))
        print(color("    Shortcuts: S = save position now", fg="bright_black"))
        print(color("  0) Exit", fg="bright_cyan", bold=True))
        print(color("=============================================", fg="bright_green", bold=True))
        try:
            scelta = input("Choice: ").strip()
        except KeyboardInterrupt:
            print("\n[INFO] Exit requested by user.")
            break
        if scelta == "0":
            break
        # Shortcuts: S = save position now
        if scelta.upper() == "S":
            try:
                save_current_console_position()
                save_config()
            except Exception:
                pass
            continue
        # Impostazioni speciali
        if scelta == "18":
            try:
                path = input("Base folder for temporary mounts (empty = use TEMP): ").strip().strip('"')
            except KeyboardInterrupt:
                print()
                continue
            MOUNT_BASE = Path(path) if path else None
            save_config()
            continue
        if scelta == "19":
            # Info sul rilevamento di wimlib
            try:
                src = _wimlib_source_label()
                print(f"[INFO] wimlib: {src}")
            except Exception:
                pass
            try:
                vt = input("Enable VT (ANSI colors) at startup (on/off, ENTER=off): ").strip().lower()
            except KeyboardInterrupt:
                print()
                vt = ""
            if vt in {"on", "off", ""}:
                if vt == "":
                    vt = "off"
                ANSI_VT = (vt == "on")
                # Applica subito alla console corrente
                try:
                    _set_vt_mode(ANSI_VT)
                    print(color(f"[INFO] VT {'enabled' if ANSI_VT else 'disabled' }.", fg="bright_cyan"))
                except Exception:
                    pass
            try:
                qe = input("Disable QuickEdit to avoid pauses on click (on/off, ENTER=on): ").strip().lower()
            except KeyboardInterrupt:
                print()
                qe = ""
            if qe in {"on", "off", ""}:
                if qe == "":
                    qe = "on"
                DISABLE_QUICK_EDIT = (qe == "on")
                try:
                    _set_quick_edit(DISABLE_QUICK_EDIT)
                    print(color(f"[INFO] QuickEdit {'disabled' if DISABLE_QUICK_EDIT else 'enabled'}.", fg="bright_cyan"))
                except Exception:
                    pass
            try:
                aot = input("AlwaysTop: on/off, ENTER=OFF: ").strip().lower()
            except KeyboardInterrupt:
                print()
                continue
            if aot in {"on", "off", ""}:
                if aot == "":
                    aot = "off"
                ALWAYS_ON_TOP = (aot == "on")
                try:
                    _set_always_on_top(ALWAYS_ON_TOP)
                    print(color(f"[INFO] AlwaysTop {'enabled' if ALWAYS_ON_TOP else 'disabled' }.", fg="bright_cyan"))
                except Exception:
                    pass
            try:
                wpm = input("Wimlib progress bar: line/off, ENTER=line: ").strip().lower()
            except KeyboardInterrupt:
                print()
                continue
            if wpm in {"line", "off", ""}:
                if wpm == "":
                    wpm = "line"
                WIMLIB_PROGRESS_MODE = wpm
            # Spinner informativi separato
            try:
                isp = input("Info commands spinner (Get-Features/Get-WimInfo): on/off, ENTER=on: ").strip().lower()
            except KeyboardInterrupt:
                print()
                isp = ""
            if isp in {"on", "off", ""}:
                if isp == "":
                    isp = "on"
                INFO_SPINNER = (isp == "on")
            
            try:
                v = input("Verbose log (on/off, ENTER=on): ").strip().lower()
            except KeyboardInterrupt:
                print()
                continue
            if v == "":
                v = "on"  # default richiesto
            if v in {"on", "off"}:
                VERBOSE = (v == "on")
                if VERBOSE:
                    # Reset file verbose
                    try:
                        if VERBOSE_FILE.exists():
                            VERBOSE_FILE.unlink()
                    except Exception:
                        pass
                # Hint stato verbose
                try:
                    print(color(f"[INFO] Verbose {'enabled' if VERBOSE else 'disabled' }.", fg="bright_cyan"))
                except Exception:
                    pass
            try:
                cc = input("Center console window at startup (on/off, ENTER=on): ").strip().lower()
            except KeyboardInterrupt:
                print()
                continue
            if cc in {"on", "off", ""}:
                if cc == "":
                    cc = "on"
                CENTER_CONSOLE = (cc == "on")
                # Hint stato center console
                try:
                    print(color(f"[INFO] Center console {'enabled' if CENTER_CONSOLE else 'disabled' }.", fg="bright_cyan"))
                except Exception:
                    pass
            try:
                rp = input("Restore saved position at startup (on/off, ENTER=off): ").strip().lower()
            except KeyboardInterrupt:
                print()
                continue
            if rp in {"on", "off", ""}:
                if rp == "":
                    rp = "off"  # default prudente
                RESTORE_CONSOLE_POS = (rp == "on")
                # Hint stato restore console
                try:
                    print(color(f"[INFO] Restore console {'enabled' if RESTORE_CONSOLE_POS else 'disabled' }.", fg="bright_cyan"))
                except Exception:
                    pass
            try:
                sv = input("Save current position as preferred now? (y/N, ENTER=N): ").strip().lower()
            except KeyboardInterrupt:
                print()
                continue
            if sv in {"s", "si", "sì", "y", "yes"}:
                save_current_console_position()
            # Retry/delay centratura finestra
            try:
                rr = input(f"Center attempts (0-5) [current {CENTER_RETRY}] (ENTER=keep): ").strip()
            except KeyboardInterrupt:
                print()
                continue
            if rr != "":
                try:
                    val = int(rr)
                    if 0 <= val <= 5:
                        CENTER_RETRY = val
                    else:
                        print("[WARN] Value out of range (0-5), ignored.")
                except ValueError:
                    print("[WARN] Non-numeric value, ignored.")
            try:
                dl = input(f"Delay between attempts (ms, 0-1000) [current {CENTER_DELAY_MS}] (ENTER=keep): ").strip()
            except KeyboardInterrupt:
                print()
                continue
            if dl != "":
                try:
                    val2 = int(dl)
                    if 0 <= val2 <= 1000:
                        CENTER_DELAY_MS = val2
                    else:
                        print("[WARN] Value out of range (0-1000), ignored.")
                except ValueError:
                    print("[WARN] Non-numeric value, ignored.")
            try:
                b = input("Export backend (auto/dism/wimlib, ENTER=auto): ").strip().lower()
            except KeyboardInterrupt:
                print()
                continue
            if b == "":
                b = "auto"  # default richiesto
                print("[INFO] Export backend: default 'auto' applied.")
            if b in {"auto", "dism", "wimlib"}:
                EXPORT_BACKEND = b
            save_config()
            continue
        item = MENU_ITEMS.get(scelta)
        if not item:
            continue
        try:
            item[1]()
        except KeyboardInterrupt:
            print("\n[INFO] Operation cancelled by user.")
            # prosegui al menu
            pass
        except RuntimeError as e:
            print("[ERROR]", e)
            log_error(str(e))
        except Exception as e:
            print("[ERROR] unexpected exception:", e)
            log_error(repr(e))
        # Pausa standard tra un'operazione e il ritorno al menu
        pause()

    print("\n===== SESSION SUMMARY =====")
    print(f"Successful operations: {OKCNT}")
    print(f"Failed operations:     {FAILCNT}")
    if ERRLOG.exists():
        print(f"Error details in: {ERRLOG}")
    print("=============================")


if __name__ == "__main__":
    main()
