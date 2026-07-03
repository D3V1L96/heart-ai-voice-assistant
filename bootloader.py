import os
import re
import sys
import time
import queue
import threading
import traceback
import subprocess
from pathlib import Path

# =========================================
# CONFIG
# =========================================
PROJECT_DIR = Path(__file__).parent.resolve()

PYTHON_EXE = PROJECT_DIR / ".venv" / "Scripts" / "python.exe"

MAIN_FILE = PROJECT_DIR / "heart.py"

CHECK_INTERVAL = 1
RESTART_DELAY = 2
MAX_RESTARTS = 999999

# =========================================
# GLOBALS
# =========================================
restart_count = 0
last_error = None
auto_heal_failed = False

# =========================================
# LOGGER
# =========================================
def log(msg):
    print(f"[HEART-WATCHDOG] {msg}")


# =========================================
# UI
# =========================================
def banner():

    os.system("cls" if os.name == "nt" else "clear")

    print("\n")
    print("╔══════════════════════════════════════════════╗")
    print("║               H.E.A.R.T AI WATCHDOG         ║")
    print("║        Autonomous Self-Healing Engine       ║")
    print("╚══════════════════════════════════════════════╝")
    print()


# =========================================
# VALIDATION
# =========================================
def validate():

    if not PYTHON_EXE.exists():

        log("Python executable missing")
        return False

    if not MAIN_FILE.exists():

        log("heart.py missing")
        return False

    return True


# =========================================
# PACKAGE INSTALLER
# =========================================
def install_package(package):

    log(f"Installing/Repairing: {package}")

    try:

        result = subprocess.run(
            [
                str(PYTHON_EXE),
                "-m",
                "pip",
                "install",
                "--upgrade",
                package
            ],
            text=True,
            encoding="utf-8",
            errors="ignore"
        )

        return result.returncode == 0

    except Exception as e:

        log(f"Install failed: {e}")

        return False


# =========================================
# ERROR ANALYZER
# =========================================
def analyze_error(line):

    # =====================================
    # No module named
    # =====================================
    no_module = re.search(
        r"No module named ['\"](.+?)['\"]",
        line
    )

    if no_module:

        module = no_module.group(1).split(".")[0]

        return {
            "type": "missing_module",
            "target": module,
            "raw": line
        }

    # =====================================
    # cannot import name
    # =====================================
    import_error = re.search(
        r"cannot import name ['\"](.+?)['\"] from ['\"](.+?)['\"]",
        line
    )

    if import_error:

        package = import_error.group(2).split(".")[0]

        return {
            "type": "api_mismatch",
            "target": package,
            "raw": line
        }

    # =====================================
    # DLL FAIL
    # =====================================
    if "DLL load failed" in line:

        return {
            "type": "binary_issue",
            "target": "torch",
            "raw": line
        }

    # =====================================
    # CUDA FAIL
    # =====================================
    if "CUDA" in line or "cuda" in line:

        return {
            "type": "cuda_issue",
            "target": "torch",
            "raw": line
        }

    return None


# =========================================
# AUTO HEAL ENGINE
# =========================================
def auto_heal(error):

    if not error:
        return False

    etype = error["type"]
    target = error["target"]

    log(f"Auto-Heal Triggered → {etype}")

    try:

        # =====================================
        # MISSING MODULE
        # =====================================
        if etype == "missing_module":

            return install_package(target)

        # =====================================
        # API MISMATCH
        # =====================================
        elif etype == "api_mismatch":

            return install_package(target)

        # =====================================
        # TORCH BINARY
        # =====================================
        elif etype == "binary_issue":

            ok1 = install_package("torch")
            ok2 = install_package("torchaudio")

            return ok1 and ok2

        # =====================================
        # CUDA ISSUE
        # =====================================
        elif etype == "cuda_issue":

            return install_package("torch")

        return False

    except Exception as e:

        log(f"Heal engine crash: {e}")

        return False


# =========================================
# STREAM READER
# =========================================
def enqueue_output(pipe, q):

    try:

        for line in iter(pipe.readline, ''):

            try:

                q.put(line)

            except UnicodeDecodeError:

                continue

    finally:

        pipe.close()


# =========================================
# LAUNCH HEART
# =========================================
def launch_heart():

    log("Launching HEART Core")

    process = subprocess.Popen(
        [
            str(PYTHON_EXE),
            "-B",
            str(MAIN_FILE),
            "console"
        ],
        cwd=str(PROJECT_DIR),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="ignore",
        bufsize=1
    )

    return process


# =========================================
# EMERGENCY MODE
# =========================================
def emergency_mode():

    global last_error

    while True:

        print("\n")
        print("╔══════════════════════════════════════╗")
        print("║         EMERGENCY CONTROL MODE       ║")
        print("╚══════════════════════════════════════╝")
        print()

        print("1. Retry HEART")
        print("2. Manual Install Package")
        print("3. Show Last Error")
        print("4. Upgrade pip")
        print("5. Exit")
        print()

        choice = input("Select option: ").strip()

        # =====================================
        # RETRY
        # =====================================
        if choice == "1":

            log("Retrying autonomous mode")

            return

        # =====================================
        # MANUAL INSTALL
        # =====================================
        elif choice == "2":

            pkg = input("Package Name: ").strip()

            if pkg:
                install_package(pkg)

        # =====================================
        # LAST ERROR
        # =====================================
        elif choice == "3":

            print("\nLAST ERROR:\n")

            print(last_error)

        # =====================================
        # UPGRADE PIP
        # =====================================
        elif choice == "4":

            subprocess.run(
                [
                    str(PYTHON_EXE),
                    "-m",
                    "pip",
                    "install",
                    "--upgrade",
                    "pip"
                ]
            )

        # =====================================
        # EXIT
        # =====================================
        elif choice == "5":

            sys.exit(0)


# =========================================
# SUPERVISOR
# =========================================
def supervisor():

    global restart_count
    global last_error
    global auto_heal_failed

    while True:

        try:

            banner()

            process = launch_heart()

            stdout_q = queue.Queue()
            stderr_q = queue.Queue()

            # =====================================
            # OUTPUT THREADS
            # =====================================
            threading.Thread(
                target=enqueue_output,
                args=(process.stdout, stdout_q),
                daemon=True
            ).start()

            threading.Thread(
                target=enqueue_output,
                args=(process.stderr, stderr_q),
                daemon=True
            ).start()

            # =====================================
            # LIVE MONITOR
            # =====================================
            while True:

                # ================================
                # STDOUT
                # ================================
                while not stdout_q.empty():

                    line = stdout_q.get().rstrip()

                    print(line)

                # ================================
                # STDERR
                # ================================
                while not stderr_q.empty():

                    line = stderr_q.get().rstrip()

                    print(line)

                    detected = analyze_error(line)

                    if detected:

                        last_error = detected

                        log("Runtime issue detected")

                        process.kill()

                        healed = auto_heal(detected)

                        # ============================
                        # AUTO HEAL SUCCESS
                        # ============================
                        if healed:

                            log("Auto-Heal Successful")
                            log("Restarting HEART")

                            time.sleep(RESTART_DELAY)

                            break

                        # ============================
                        # AUTO HEAL FAILED
                        # ============================
                        else:

                            auto_heal_failed = True

                            log("Auto-Heal FAILED")
                            log("Switching to Emergency Mode")

                            emergency_mode()

                            break

                # ================================
                # PROCESS EXIT
                # ================================
                code = process.poll()

                if code is not None:

                    log(f"HEART exited with code {code}")

                    restart_count += 1

                    log(f"Restart Count: {restart_count}")

                    if restart_count >= MAX_RESTARTS:

                        log("Max restart limit reached")

                        emergency_mode()

                    time.sleep(RESTART_DELAY)

                    break

                time.sleep(CHECK_INTERVAL)

        except KeyboardInterrupt:

            log("Shutdown requested")

            return

        except Exception as e:

            log(f"Supervisor crash: {e}")

            traceback.print_exc()

            print("\nSwitching to Emergency Mode...\n")

            emergency_mode()


# =========================================
# ENTRY
# =========================================
if __name__ == "__main__":

    os.environ["PYTHONASYNCIODEBUG"] = "0"
    os.environ["TOKENIZERS_PARALLELISM"] = "false"
    os.environ["PYTHONIOENCODING"] = "utf-8"

    banner()

    # =====================================
    # VALIDATE ENVIRONMENT
    # =====================================
    if not validate():

        print("\n[BOOT ERROR] Environment validation failed\n")

        emergency_mode()

    # =====================================
    # AUTO START WATCHDOG
    # =====================================
    try:

        log("Starting Autonomous Self-Healing Mode")

        supervisor()

    # =====================================
    # CTRL + C
    # =====================================
    except KeyboardInterrupt:

        log("System shutdown requested")

        sys.exit(0)

    # =====================================
    # FATAL BOOT FAILURE
    # =====================================
    except Exception as e:

        log(f"Fatal Boot Error: {e}")

        traceback.print_exc()

        print("\nSwitching to Emergency Mode...\n")

        emergency_mode()