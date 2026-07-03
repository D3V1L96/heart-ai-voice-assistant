import os
import psutil

from livekit.agents.llm import function_tool
from app_scanner import load_apps

# Load installed apps once at module load time
# Expected format: {'Notepad': 'C:\\Windows\\notepad.exe', ...}
apps = load_apps()

@function_tool(
    name="handle_apps",
    description="Open, close, install or uninstall applications"
)
def handle_apps(text: str) -> str:
    text = text.lower().strip()

    # ---------- OPEN ----------
    if text.startswith("open "):
        name = text[len("open "):].strip()

        for app_name, path in apps.items():
            if name == app_name.lower():
                if not os.path.isfile(path):
                    return f"Executable path not found for {app_name}: {path}"

                try:
                    print(f"[DEBUG] Opening app '{app_name}' at path: {path}")
                    os.startfile(path)  # Windows-specific
                    return f"{app_name} opened."
                except Exception as e:
                    return f"Failed to open {app_name}: {e}"

        return "Application not found."

    # ---------- CLOSE ----------
    if text.startswith("close "):
        name = text[len("close "):].strip()
        closed_any = False

        for process in psutil.process_iter(['name']):
            proc_name = process.info['name']
            if proc_name and name in proc_name.lower():
                try:
                    process.kill()
                    closed_any = True
                except Exception as e:
                    return f"Failed to close {proc_name}: {e}"

        if closed_any:
            return f"{name} closed."
        else:
            return "Application not running."

    # ---------- INSTALL ----------
    if text.startswith("install "):
        name = text[len("install "):].strip()

        try:
            os.system(f'winget install -e --id {name}')
            return f"Installing {name}."
        except Exception as e:
            return f"Installation failed: {e}"

    # ---------- UNINSTALL ----------
    if text.startswith("uninstall "):
        name = text[len("uninstall "):].strip()

        try:
            os.system(f'winget uninstall {name}')
            return f"Uninstalling {name}."
        except Exception as e:
            return f"Uninstall failed: {e}"

    return "App command not understood."
