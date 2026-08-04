#!/usr/bin/env python3
"""
UniversalAI — Launcher
=======================
Creates an isolated virtual environment, installs dependencies, validates
the environment, and starts both backend and frontend servers.

Usage:
    python start.py

Supported Python versions: 3.11, 3.12, 3.13 (64-bit)
"""

import hashlib
import os
import shutil
import signal
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path

# ---------------------------------------------------------------------------
# Supported Python versions
# ---------------------------------------------------------------------------
SUPPORTED_PYTHON = {(3, 11), (3, 12), (3, 13)}
SUPPORTED_PYTHON_STR = "3.11, 3.12, or 3.13 (64-bit)"

# Ports for backend and frontend
BACKEND_PORT = 8001
FRONTEND_PORT = 5500

# Project paths
ROOT = Path(__file__).resolve().parent
BACKEND_DIR = ROOT / "backend"
FRONTEND_DIR = ROOT / "frontend"
VENV_DIR = ROOT / "venv"
REQ_FILE = ROOT / "requirements.txt"
ENV_FILE = ROOT / ".env"
ENV_EXAMPLE = ROOT / ".env.example"
REQUIREMENTS_MARKER = VENV_DIR / ".requirements.sha256"
VENV_PYTHON_VERSION_MARKER = VENV_DIR / ".python.version"

# Critical packages to verify after install
CRITICAL_PACKAGES = [
    "pandas",
    "numpy",
    "cryptography",
    "chromadb",
    "fastapi",
    "pydantic",
    "sqlalchemy",
]


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------

def _print_banner(title: str) -> None:
    print(f"\n=== {title} ===")


def _print_error(msg: str, detail: str = "") -> None:
    border = "=" * 60
    print(f"\n{border}", file=sys.stderr)
    print(f"  ERROR: {msg}", file=sys.stderr)
    if detail:
        for line in detail.strip().splitlines():
            print(f"  | {line}", file=sys.stderr)
    print(f"{border}\n", file=sys.stderr)


def _print_info(msg: str) -> None:
    print(f"  {msg}")


def _print_ok(msg: str) -> None:
    """Print a green OK marker and message."""
    print(f"  [OK] {msg}")


# ---------------------------------------------------------------------------
# Python interpreter discovery
# ---------------------------------------------------------------------------

def _check_python_version(python_exe: str) -> tuple[int, int, int] | None:
    """Check if the Python version is in the supported range. Returns version tuple or None."""
    version = _get_python_version(python_exe)
    if version is None:
        return None
    major, minor = version[0], version[1]
    if (major, minor) in SUPPORTED_PYTHON:
        return version
    return None


def _get_python_version(python_exe: str) -> tuple[int, int, int] | None:
    """Get the Python version tuple from a Python executable."""
    try:
        result = subprocess.run(
            [python_exe, "-c",
             "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            parts = result.stdout.strip().split(".")
            return (int(parts[0]), int(parts[1]), int(parts[2]))
    except (subprocess.TimeoutExpired, OSError, ValueError, IndexError):
        pass
    return None


def _find_windows_python_launcher() -> str | None:
    """Try to find a supported Python via the `py` launcher on Windows."""
    if os.name != "nt":
        return None
    for minor in sorted({v[1] for v in SUPPORTED_PYTHON}, reverse=True):
        try:
            result = subprocess.run(
                ["py", f"-{minor}", "-c", "import sys; print(sys.executable)"],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode == 0:
                exe = result.stdout.strip()
                if exe and Path(exe).exists():
                    return exe
        except (subprocess.TimeoutExpired, OSError):
            continue
    return None


def _find_system_python() -> str | None:
    """Find a supported Python interpreter on the system PATH."""
    candidates = ["python3", "python"]
    seen = set()
    for candidate in candidates:
        try:
            result = subprocess.run(
                [candidate, "-c", "import sys; print(sys.executable)"],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode == 0:
                exe = result.stdout.strip()
                if exe and exe not in seen and Path(exe).exists():
                    seen.add(exe)
                    if _check_python_version(candidate):
                        return candidate
        except (subprocess.TimeoutExpired, OSError):
            continue
    return None


def _find_any_supported_python() -> str | None:
    """Try to find any supported Python interpreter, returning the executable name or path."""
    # 1. Try current interpreter first
    if _check_python_version(sys.executable):
        return sys.executable

    # 2. On Windows, try `py` launcher
    if os.name == "nt":
        launcher = _find_windows_python_launcher()
        if launcher:
            return launcher

    # 3. Search PATH
    system = _find_system_python()
    if system:
        return system

    return None


def _detect_os_and_python() -> tuple[str, str | None]:
    """Detect OS and find a supported Python interpreter.

    Returns (os_name, python_executable_path).
    """
    if os.name == "nt":
        os_name = "Windows"
    elif sys.platform == "darwin":
        os_name = "macOS"
    else:
        os_name = "Linux"

    python_exe = _find_any_supported_python()
    return os_name, python_exe


def _read_venv_python_version() -> tuple[int, int, int] | None:
    """Read the Python version that was used to create the current venv."""
    marker = VENV_PYTHON_VERSION_MARKER
    if marker.exists():
        try:
            parts = marker.read_text(encoding="utf-8").strip().split(".")
            return (int(parts[0]), int(parts[1]), int(parts[2]))
        except (ValueError, IndexError):
            pass
    return None


def _write_venv_python_version(version: tuple[int, int, int]) -> None:
    """Write the Python version used to create the venv."""
    VENV_PYTHON_VERSION_MARKER.write_text(
        f"{version[0]}.{version[1]}.{version[2]}\n", encoding="utf-8"
    )


def _get_venv_python() -> str:
    """Get the path to the Python executable inside the venv."""
    if os.name == "nt":
        return str(VENV_DIR / "Scripts" / "python.exe")
    return str(VENV_DIR / "bin" / "python")


# ---------------------------------------------------------------------------
# Environment validation
# ---------------------------------------------------------------------------

def ensure_virtualenv(python_exe: str) -> str:
    """Create or validate the virtual environment."""
    venv_python = _get_venv_python()
    recreate = False

    if VENV_DIR.exists():
        # Check if venv is functional
        venv_version = _read_venv_python_version()
        current_version = _get_python_version(python_exe)

        if current_version and venv_version and current_version[:2] != venv_version[:2]:
            print(f"  Venv was created with Python {venv_version[0]}.{venv_version[1]}, "
                  f"but {current_version[0]}.{current_version[1]} is available.")
            recreate = True

        if not recreate:
            # Check if the venv Python actually works
            test_version = _get_python_version(venv_python)
            if test_version is None:
                print("  Existing virtual environment appears broken.")
                recreate = True

        if recreate:
            print("  Recreating virtual environment...")
            shutil.rmtree(VENV_DIR)

    if not VENV_DIR.exists():
        print(f"  Creating virtual environment using {python_exe}...")
        subprocess.run([python_exe, "-m", "venv", str(VENV_DIR)], check=True, capture_output=True, cwd=ROOT)
        current_version = _get_python_version(python_exe)
        if current_version:
            _write_venv_python_version(current_version)

    return _get_venv_python()


def install_requirements(python_exe: str) -> None:
    """Install project dependencies if the requirements file has changed."""
    fingerprint = hashlib.sha256(REQ_FILE.read_bytes()).hexdigest()
    if REQUIREMENTS_MARKER.exists() and REQUIREMENTS_MARKER.read_text(encoding="utf-8") == fingerprint:
        print("  Dependencies up to date.")
        return

    print("  Installing dependencies (this may take a few minutes)...")
    subprocess.run(
        [python_exe, "-m", "pip", "install", "--upgrade", "pip"],
        check=True, capture_output=True, cwd=ROOT,
    )
    result = subprocess.run(
        [python_exe, "-m", "pip", "install", "-r", str(REQ_FILE)],
        capture_output=True, text=True, cwd=ROOT,
    )
    if result.returncode != 0:
        _print_error(
            "Dependency installation failed.",
            result.stderr.strip() or result.stdout.strip(),
        )
        sys.exit(1)

    REQUIREMENTS_MARKER.write_text(fingerprint, encoding="utf-8")
    print("  Dependencies installed successfully.")


def run_health_check(python_exe: str) -> None:
    """Verify that critical packages import correctly inside the venv."""
    print("  Running import health check...")

    # Build the import test script
    imports = "; ".join(f"import {pkg}" for pkg in CRITICAL_PACKAGES)
    test_script = (
        "import sys, importlib\n"
        f"{imports}\n"
        'print("All critical packages imported successfully.")\n'
    )

    result = subprocess.run(
        [python_exe, "-c", test_script],
        capture_output=True, text=True, timeout=30,
    )

    if result.returncode != 0:
        stderr = result.stderr.strip()

        # Check for Application Control blocking
        if "Application Control policy" in stderr or "blocked this file" in stderr:
            _print_error(
                "Windows Application Control blocked a required Python package.",
                (
                    "A Windows security policy (AppLocker / WDAC) prevented one or more\n"
                    "required Python packages from loading.\n"
                    "\n"
                    "UniversalAI will NOT bypass or disable your system security policy.\n"
                    "\n"
                    "If this is a managed computer, contact your administrator.\n"
                    "If this is your personal computer:\n"
                    "  1. Check Windows Event Viewer > Applications and Services Logs\n"
                    "     > Microsoft > Windows > AppLocker for the exact block reason.\n"
                    "  2. Running from a different folder (e.g. C:\\Users\\<you>\\) can\n"
                    "     sometimes avoid the policy restriction.\n"
                    "  3. Alternatively, use Docker to run UniversalAI:\n"
                    "     docker compose -f docker-compose.all.yml up -d\n"
                    "\n"
                    "No security settings were modified."
                ),
            )
            sys.exit(1)

        _print_error(
            "Import health check failed — a critical package could not be loaded.",
            stderr,
        )
        sys.exit(1)

    print(f"  {result.stdout.strip()}")


def ensure_env_file() -> None:
    """Create .env from .env.example if missing, and generate MASTER_KEY."""
    if not ENV_FILE.exists() and ENV_EXAMPLE.exists():
        shutil.copy2(ENV_EXAMPLE, ENV_FILE)
        print(f"  Created {ENV_FILE.name} from {ENV_EXAMPLE.name}.")
        print("  Add API keys for the providers you want to use, or configure later")
        print("  from Settings -> Provider API Keys.")

    if not ENV_FILE.exists():
        return

    # Generate MASTER_KEY if missing
    if "MASTER_KEY" in os.environ and os.environ["MASTER_KEY"].strip():
        return

    lines = ENV_FILE.read_text(encoding="utf-8").splitlines()
    has_real_value = any(
        line.strip().startswith("MASTER_KEY=")
        and not line.strip().startswith("#")
        and line.split("=", 1)[1].strip()
        for line in lines
    )
    if has_real_value:
        return

    # Generate a fresh Fernet key
    venv_python = _get_venv_python()
    result = subprocess.run(
        [venv_python, "-c",
         "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"],
        capture_output=True, text=True, timeout=10,
    )
    if result.returncode == 0:
        new_key = result.stdout.strip()
        if any(line.strip().startswith("MASTER_KEY=") for line in lines):
            lines = [
                f"MASTER_KEY={new_key}" if line.strip().startswith("MASTER_KEY=") else line
                for line in lines
            ]
        else:
            lines.append(f"MASTER_KEY={new_key}")
        ENV_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print("  Generated a new MASTER_KEY in .env (used to encrypt provider API keys at rest).")


def _get_python_arch(python_exe: str) -> str:
    """Return '64-bit' or '32-bit' for the given Python interpreter."""
    try:
        result = subprocess.run(
            [python_exe, "-c", "import struct; print(struct.calcsize('P') * 8)"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            bits = result.stdout.strip()
            return f"{bits}-bit"
    except (subprocess.TimeoutExpired, OSError):
        pass
    return "unknown"


def _print_environment_header(os_name: str, python_exe: str | None) -> None:
    """Print environment detection header."""
    print()
    _print_banner("UniversalAI Environment Check")
    print()
    print(f"  OS:      {os_name}")

    if python_exe:
        version = _get_python_version(python_exe)
        arch = _get_python_arch(python_exe)
        if version:
            print(f"  Python:  {version[0]}.{version[1]}.{version[2]} ({arch})")
        else:
            print(f"  Python:  {python_exe}")
    else:
        print("  Python:  Not detected")


# ---------------------------------------------------------------------------
# Server management
# ---------------------------------------------------------------------------

def free_port(port: int) -> None:
    """Terminate any process currently holding *port*."""
    import psutil  # type: ignore[import-untyped]

    pids: set[int] = set()
    try:
        for conn in psutil.net_connections(kind="tcp"):
            if getattr(conn, "laddr", None) and getattr(conn.laddr, "port", None) == port:
                if conn.pid:
                    pids.add(conn.pid)
    except Exception:
        # Fall back to netstat on Windows
        if os.name == "nt":
            try:
                out = subprocess.run(
                    ["netstat", "-ano", "-p", "TCP"],
                    capture_output=True, text=True,
                ).stdout
                for line in out.splitlines():
                    parts = line.split()
                    if len(parts) >= 5 and parts[1].endswith(f":{port}") and parts[3] == "LISTENING":
                        try:
                            pids.add(int(parts[4]))
                        except ValueError:
                            pass
            except Exception:
                pass

    for pid in pids:
        try:
            os.kill(pid, signal.SIGTERM)
        except Exception:
            continue
    if pids:
        time.sleep(1)


def build_commands(python_exe: str):
    backend_cmd = [python_exe, "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", str(BACKEND_PORT)]
    frontend_cmd = [python_exe, "-m", "http.server", str(FRONTEND_PORT)]
    return backend_cmd, frontend_cmd


def wait_for_port(port: int, timeout: float = 3.0) -> bool:
    """Wait for a TCP port to start listening."""
    import socket
    for _ in range(int(timeout / 0.1)):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.5)
            if s.connect_ex(("127.0.0.1", port)) == 0:
                return True
        time.sleep(0.1)
    return False


def check_backend_health(timeout: float = 5.0) -> bool:
    """Check if the backend responds to health checks."""
    import urllib.request
    import urllib.error

    for _ in range(int(timeout / 0.2)):
        try:
            r = urllib.request.urlopen(
                f"http://127.0.0.1:{BACKEND_PORT}/api/auth/status",
                timeout=1.0,
            )
            return r.status == 200
        except Exception:
            time.sleep(0.2)
    return False


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    # Phase 1: Environment detection
    os_name, python_exe = _detect_os_and_python()
    _print_environment_header(os_name, python_exe)

    if python_exe is None:
        _print_error(
            "No supported Python interpreter found.",
            (
                f"UniversalAI requires Python {SUPPORTED_PYTHON_STR} (64-bit).\n"
                "\n"
                "Install a supported version from https://www.python.org/downloads/\n"
                "and ensure it is available on your system PATH.\n"
                "\n"
                "On Windows, the Python Launcher (py) is also supported."
            ),
        )
        sys.exit(1)

    # Verify the selected Python is supported
    version = _check_python_version(python_exe)
    if version is None:
        detected = _get_python_version(python_exe)
        version_str = f"{detected[0]}.{detected[1]}.{detected[2]}" if detected else "unknown"
        _print_error(
            f"Python {version_str} is not supported.",
            (
                f"UniversalAI supports Python {SUPPORTED_PYTHON_STR} (64-bit).\n"
                f"Detected: Python {version_str}\n"
                "\n"
                "Install a supported Python version and run UniversalAI again."
            ),
        )
        sys.exit(1)

    version_str = f"{version[0]}.{version[1]}.{version[2]}"
    _print_info(f"Python {version_str} (supported)")

    # Phase 2: Virtual environment
    _print_banner("Setting up virtual environment")
    try:
        venv_python = ensure_virtualenv(python_exe)
        _print_ok(f"Virtual environment ready ({VENV_DIR})")
    except Exception as exc:
        _print_error("Virtual environment creation failed.", str(exc))
        sys.exit(1)

    # Phase 3: Dependency installation
    _print_banner("Checking dependencies")
    try:
        install_requirements(venv_python)
    except subprocess.CalledProcessError as exc:
        _print_error("Dependency installation failed.", str(exc))
        sys.exit(1)

    # Phase 4: Import health check
    _print_banner("Validating environment")
    try:
        run_health_check(venv_python)
        _print_ok("Environment healthy")
    except SystemExit:
        raise
    except Exception as exc:
        _print_error("Unexpected error during import validation.", str(exc))
        sys.exit(1)

    # Phase 5: Configuration
    _print_banner("Configuration")
    try:
        ensure_env_file()
        _print_ok("Configuration ready")
    except Exception as exc:
        _print_error("Configuration setup failed.", str(exc))
        sys.exit(1)

    # Phase 6: Free ports
    _print_banner("Starting servers")
    free_port(BACKEND_PORT)
    free_port(FRONTEND_PORT)
    _print_ok("Ports available")

    # Phase 7: Start backend
    backend_cmd, frontend_cmd = build_commands(venv_python)

    backend_proc = subprocess.Popen(
        backend_cmd, cwd=BACKEND_DIR,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, bufsize=1,
    )

    # Tee backend output to console
    def _tee_backend_output():
        try:
            for line in backend_proc.stdout or []:
                print(line, end="", flush=True)
        except Exception:
            pass

    tee_thread = threading.Thread(target=_tee_backend_output, daemon=True)
    tee_thread.start()

    # Wait for backend to be ready
    if not wait_for_port(BACKEND_PORT):
        # Check if process already crashed
        if backend_proc.poll() is not None:
            _print_error(
                "Backend failed to start.",
                "The backend process exited before it could bind to the port. "
                "Check the output above for the exact error.",
            )
        else:
            _print_error(
                "Backend failed to start within the time limit.",
                "Check the output above for errors.",
            )
        backend_proc.terminate()
        sys.exit(1)

    if not check_backend_health():
        if backend_proc.poll() is not None:
            _print_error(
                "Backend started but is not healthy.",
                "Check the output above for the exact error.",
            )
            backend_proc.terminate()
            sys.exit(1)

    _print_ok(f"Backend running at http://127.0.0.1:{BACKEND_PORT}")

    # Phase 8: Start frontend
    frontend_proc = subprocess.Popen(frontend_cmd, cwd=FRONTEND_DIR)

    if wait_for_port(FRONTEND_PORT, timeout=2.0):
        _print_ok(f"Frontend running at http://127.0.0.1:{FRONTEND_PORT}")
    else:
        _print_error("Frontend failed to start.")
        backend_proc.terminate()
        frontend_proc.terminate()
        sys.exit(1)

    # Phase 9: Open browser
    webbrowser.open(f"http://127.0.0.1:{FRONTEND_PORT}")

    print()
    print("=== UniversalAI — running ===")
    print(f"-> Backend:  http://127.0.0.1:{BACKEND_PORT}/docs")
    print(f"-> Frontend: http://127.0.0.1:{FRONTEND_PORT}")
    print("-> Provider keys can be added from Settings -> Provider API Keys")
    print("-> Press Ctrl+C to stop all servers")

    # Phase 10: Wait for shutdown
    def stop_all(_signum, _frame):
        for proc in (backend_proc, frontend_proc):
            if proc.poll() is None:
                proc.terminate()
        raise KeyboardInterrupt

    signal.signal(signal.SIGINT, stop_all)
    signal.signal(signal.SIGTERM, stop_all)

    try:
        while True:
            if backend_proc.poll() is not None or frontend_proc.poll() is not None:
                break
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down servers...")
    finally:
        for proc in (backend_proc, frontend_proc):
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
        print("Servers stopped.")


if __name__ == "__main__":
    main()