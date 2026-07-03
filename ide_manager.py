import subprocess
import psutil
import shutil


KNOWN_IDES = {
    "vscode": "code",
    "pycharm": "pycharm64",
    "intellij": "idea64",
    "notepad++": "notepad++",
    "sublime": "sublime_text",
    "atom": "atom"
}


def detect_installed_ides():
    installed = []

    for name, cmd in KNOWN_IDES.items():
        if shutil.which(cmd):
            installed.append(name)

    return installed


def detect_running_ide():
    for process in psutil.process_iter(['name']):
        name = process.info['name'].lower()

        for ide in KNOWN_IDES:
            if ide in name:
                return ide

    return None


def launch_ide(ide):
    cmd = KNOWN_IDES.get(ide)

    if cmd:
        subprocess.Popen(cmd)
        return True

    return False


def open_notepad():
    subprocess.Popen("notepad")
