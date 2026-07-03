from __future__ import annotations
from dotenv import load_dotenv
import requests
import ctypes
import asyncio
from livekit import agents , rtc
from livekit.agents import AgentServer, AgentSession, Agent, room_io
from livekit.agents import RunContext
from livekit.agents.llm import function_tool, ChatContext, ChatMessage, ChatRole
from livekit.plugins import google, noise_cancellation
from heart_behavior_prompt import HEART_BEHAVIOR_PROMPT
from heart_response_prompt import HEART_RESPONSE_PROMPT
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import urllib.parse
import keyboard
import shutil
from heart_memory import load_memory, save_memory
from wake_detector import listen, heart_active, init_model
import heart_hud
from livekit import agents
import pyautogui
import psutil
import os
import subprocess
from datetime import datetime
import platform
import sys
if ".venv" not in sys.executable:
    print("[WARNING] Not running inside venv - unsafe environment")

try:
    from pynvml import (
        nvmlInit, nvmlDeviceGetCount, nvmlDeviceGetHandleByIndex,
        nvmlDeviceGetName, nvmlDeviceGetUtilizationRates,
        nvmlDeviceGetMemoryInfo, nvmlDeviceGetTemperature,
        NVMLError, NVML_TEMPERATURE_GPU
    )
    PYNVML_AVAILABLE = True
    nvmlInit()
except (ImportError, NVMLError):
    PYNVML_AVAILABLE = False

try:
    import torch
    TORCH_CUDA_AVAILABLE = torch.cuda.is_available()
except ImportError:
    TORCH_CUDA_AVAILABLE = False
from coding_agent import handle_coding
from ppt_generator import handle_ppt_generation
from typing import Optional
# rest of code

emergency_active: bool = False
_current_agent = None

load_dotenv(".env.local.local")
import atexit

def _emergency_save():
    if _current_agent:
        try:
            save_memory(_current_agent.chat_ctx)
            print("[Memory] Emergency save on exit complete.")
        except Exception as e:
            print(f"[Memory] Emergency save failed: {e}")

atexit.register(_emergency_save)

# Define load_apps to scan Start Menu shortcuts for installed apps
def load_apps():
    apps = {}
    try:
        from win32com.client import Dispatch as dispatch
        shell = dispatch('WScript.Shell')
        # All users start menu
        start_menu_path = shell.SpecialFolders("Programs")
        # Current user start menu
        user_start_menu = shell.SpecialFolders("StartMenu")
        paths = [start_menu_path, user_start_menu]
        for path in paths:
            for root, dirs, files in os.walk(path):
                for file in files:
                    if file.endswith('.lnk'):
                        shortcut_path = os.path.join(root, file)
                        shortcut = shell.CreateShortCut(shortcut_path)
                        target = shortcut.TargetPath
                        if target and os.path.isfile(target):
                            name = file[:-4].strip()
                            apps[name] = target
    except Exception as e:
        print(f"Error loading apps: {e}")
    # Add hardcoded system apps only
    if 'notepad' not in [name.lower() for name in apps]:
        apps['Notepad'] = 'notepad.exe'
    if 'file explorer' not in [name.lower() for name in apps]:
        apps['File Explorer'] = 'explorer.exe'
    if 'calculator' not in [name.lower() for name in apps]:
        apps['Calculator'] = 'calc.exe'
    if 'cmd' not in [name.lower() for name in apps]:
        apps['Command Prompt'] = 'cmd.exe'
    if 'powershell' not in [name.lower() for name in apps]:
        apps['PowerShell'] = 'powershell.exe'
    if 'task manager' not in [name.lower() for name in apps]:
        apps['Task Manager'] = 'taskmgr.exe'
    return apps

# Load installed apps once
apps = load_apps()

class Assistant(Agent):
    def __init__(self, chat_ctx: ChatContext):
        super().__init__(instructions=HEART_BEHAVIOR_PROMPT, chat_ctx=chat_ctx)

    @function_tool(
        name="heart_security_utility",
        description="""Security and performance monitoring tool for Heart Assistant.
    - Returns real-time system report including CPU, RAM, Disk, Network, and GPU (0 & 1 if available)
    - Detects high resource usage and generates security alerts
    - Lists active processes that may be using microphone, camera, or location
    - Suggests redirects to Privacy settings or Task Manager for permission management
    - Supports one-time checks or continuous live monitoring"""
    )
    async def heart_security_utility(
            live_mode: bool = False,
            duration_seconds: int = 60
    ) -> str:
        """
        Real-time system monitoring and privacy check (optimized for Windows).
        Returns a formatted multi-line string report.
        """
        if platform.system() != "Windows":
            return "This monitoring tool is currently optimized for Windows systems only."

        report_lines = []
        report_lines.append("Heart Security & Performance Monitoring Report")
        report_lines.append("=" * 80)
        report_lines.append(f"Report generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append("")

        def get_gpu_status() -> str:
            """Collect GPU usage, memory, and temperature (NVIDIA priority)."""
            gpu_lines = []

            # NVIDIA GPU monitoring (using nvidia-ml-py)
            if PYNVML_AVAILABLE:
                try:
                    device_count = nvmlDeviceGetCount()
                    for i in range(min(device_count, 2)):
                        handle = nvmlDeviceGetHandleByIndex(i)
                        name = nvmlDeviceGetName(handle).decode('utf-8')
                        util = nvmlDeviceGetUtilizationRates(handle)
                        mem_info = nvmlDeviceGetMemoryInfo(handle)
                        temp = nvmlDeviceGetTemperature(handle, NVML_TEMPERATURE_GPU)

                        gpu_lines.append(
                            f"GPU {i}: {name}\n"
                            f"   Utilization: {util.gpu}% | "
                            f"Memory Used: {mem_info.used / 1024 ** 3:.1f} / {mem_info.total / 1024 ** 3:.1f} GB\n"
                            f"   Temperature: {temp}°C"
                        )
                    if gpu_lines:
                        return "\n".join(gpu_lines)
                except Exception:
                    pass

            # Fallback for CUDA (via PyTorch)
            if TORCH_CUDA_AVAILABLE:
                try:
                    for i in range(min(torch.cuda.device_count(), 2)):
                        name = torch.cuda.get_device_name(i)
                        allocated = torch.cuda.memory_allocated(i) / 1024 ** 3
                        reserved = torch.cuda.memory_reserved(i) / 1024 ** 3
                        gpu_lines.append(
                            f"GPU {i} (CUDA/Torch): {name}\n"
                            f"   Memory Allocated: {allocated:.1f} GB\n"
                            f"   Memory Reserved:  {reserved:.1f} GB"
                        )
                    if gpu_lines:
                        return "\n".join(gpu_lines)
                except Exception:
                    pass

            return "No GPU detected or GPU monitoring libraries not available."

        def generate_report():
            nonlocal report_lines

            cpu_percent = psutil.cpu_percent(interval=1)
            ram_percent = psutil.virtual_memory().percent
            disk_percent = psutil.disk_usage('C:\\').percent
            net_io = psutil.net_io_counters()

            ts = datetime.now().strftime('%H:%M:%S')
            report_lines.append(f"[{ts}] SYSTEM PERFORMANCE SNAPSHOT")
            report_lines.append(f"  CPU Usage:          {cpu_percent:6.1f}%")
            report_lines.append(f"  RAM Usage:          {ram_percent:6.1f}%")
            report_lines.append(f"  Disk Usage (C:):    {disk_percent:6.1f}%")
            report_lines.append(f"  Network Sent:       {net_io.bytes_sent / (1024 * 1024):.1f} MB")
            report_lines.append(f"  Network Received:   {net_io.bytes_recv / (1024 * 1024):.1f} MB")

            report_lines.append("\nGPU STATUS (if available)")
            report_lines.append(get_gpu_status())

            # Top CPU consumers
            top_processes = sorted(
                psutil.process_iter(['name', 'cpu_percent', 'memory_percent']),
                key=lambda p: p.info['cpu_percent'], reverse=True
            )[:6]

            report_lines.append("\nTop 6 CPU-consuming processes:")
            for proc in top_processes:
                report_lines.append(
                    f"  • {proc.info['name']:<25} | CPU: {proc.info['cpu_percent']:5.1f}% | "
                    f"RAM: {proc.info['memory_percent']:5.1f}%"
                )

            # Security & performance alerts
            alerts = []
            if cpu_percent > 85:
                alerts.append("HIGH CPU USAGE DETECTED - possible background mining or malware activity")
            if ram_percent > 90:
                alerts.append("CRITICAL RAM USAGE - system performance may degrade")
            if disk_percent > 95:
                alerts.append("DISK SPACE NEARLY EXHAUSTED - immediate cleanup recommended")

            if alerts:
                report_lines.append("\nSECURITY & PERFORMANCE ALERTS:")
                for alert in alerts:
                    report_lines.append(f"  {alert}")

            # Basic privacy/process check
            report_lines.append("\nACTIVE PROCESSES (potential microphone/camera/location users)")
            try:
                cmd = (
                    "Get-Process | Where-Object {$_.MainWindowTitle} | "
                    "Select-Object Name, Id, CPU | Sort-Object CPU -Descending | Select-Object -First 10"
                )
                result = subprocess.run(
                    ['powershell', '-Command', cmd],
                    capture_output=True,
                    text=True,
                    timeout=8
                )
                output = result.stdout.strip() or "No active windowed processes detected"
                report_lines.append(output)
            except Exception:
                report_lines.append("Privacy/process details unavailable (run as Administrator for full access)")

            report_lines.append("\nPermission Management:")
            report_lines.append("  → Press 'P' → Open Windows Privacy & Security settings")
            report_lines.append("  → Press 'T' → Open Task Manager for detailed process inspection")

        # Run monitoring
        if live_mode:
            report_lines.append(f"\nLIVE MONITORING MODE ENABLED ({duration_seconds} seconds)")
            report_lines.append("Press Ctrl+C in the terminal to stop monitoring early\n")
            try:
                start_time = time.time()
                while time.time() - start_time < duration_seconds:
                    generate_report()
                    time.sleep(5)
            except KeyboardInterrupt:
                report_lines.append("\nLive monitoring stopped by user.")
        else:
            generate_report()

        report_lines.append("\n" + "=" * 80)
        report_lines.append("Heart Security Utility - Report Complete")
        report_lines.append("Protect your personal data and stay vigilant.")

        return "\n".join(report_lines)

    # ────────────────────────────────────────────────
    # Standalone test / demo (run directly: python this_file.py)
    # ────────────────────────────────────────────────
    if __name__ == "__main__":
        result = asyncio.run(
            heart_security_utility(live_mode=False)
        )

        print(result)

    @function_tool(
        name="smart_send_file_to_contact",
        description="""File WhatsApp Desktop se bhejta hai.
    Pehle fast search karta hai, na mile to full system scan.
    Sirf file naam aur contact naam do."""
    )
    async def smart_send_file_to_contact(self, context: RunContext, file_name: str, contact_name: str) -> str:
        _ = context
        try:
            import os
            import time
            import pyautogui
            import win32gui
            import win32con

            pyautogui.FAILSAFE = False

            found_file_path = None
            file_name_lower = file_name.lower()

            # ================== PHASE 1: Fast Search ==================
            print("[INFO] Phase 1: Fast search in common folders...")
            common_folders = [
                os.path.expanduser("~/Desktop"),
                os.path.expanduser("~/Downloads"),
                os.path.expanduser("~/Documents"),
                os.path.expanduser("~/Pictures"),
                os.path.expanduser("~/Videos"),
                os.path.expanduser("~/Music"),
            ]

            for folder in common_folders:
                if not os.path.exists(folder):
                    continue
                for root, _, files in os.walk(folder):
                    for f in files:
                        if f.lower() == file_name_lower:
                            found_file_path = os.path.join(root, f)
                            print(f"[INFO] Found: {found_file_path}")
                            break
                    if found_file_path:
                        break
                if found_file_path:
                    break

            # ================== PHASE 2: Full System Scan ==================
            if not found_file_path:
                print("[INFO] Starting full system scan...")
                drives = [f"{d}:\\" for d in "ABCDEFGHIJKLMNOPQRSTUVWXYZ" if os.path.exists(f"{d}:\\")]
                for drive in drives:
                    try:
                        for root, _, files in os.walk(drive):
                            for f in files:
                                if f.lower() == file_name_lower:
                                    found_file_path = os.path.join(root, f)
                                    print(f"[INFO] Found in full scan: {found_file_path}")
                                    break
                            if found_file_path:
                                break
                    except:
                        continue
                    if found_file_path:
                        break

            if not found_file_path:
                return f" File '{file_name}' nahi mili. Name sahi likho."

            # ================== WHATSAPP SEND ==================
            print(f"[INFO] Sending file: {found_file_path}")

            # Strong WhatsApp focus
            hwnd = win32gui.FindWindow(None, "WhatsApp")
            if hwnd:
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                win32gui.SetForegroundWindow(hwnd)
                win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
                time.sleep(1.2)
            else:
                pyautogui.hotkey('win', 's')
                time.sleep(0.7)
                pyautogui.write('whatsapp')
                time.sleep(0.6)
                pyautogui.press('enter')
                time.sleep(7)

            # Search contact
            pyautogui.hotkey('ctrl', 'f')
            time.sleep(1.0)
            pyautogui.hotkey('ctrl', 'a')
            pyautogui.press('delete')
            time.sleep(0.5)
            pyautogui.write(contact_name)
            time.sleep(2.0)
            pyautogui.press('enter')
            time.sleep(1.8)

            # Click Attachment (+)
            pyautogui.hotkey('ctrl', 'shift', 'm')  # Media menu shortcut (best)
            time.sleep(1.6)

            # Click "Document"
            # You can replace with image recognition later if needed
            pyautogui.press('tab', presses=3)  # Adjust if needed
            pyautogui.press('enter')
            time.sleep(2.5)

            # File dialog mein path paste karo
            pyautogui.hotkey('ctrl', 'l')  # Go to address bar
            time.sleep(0.6)
            pyautogui.write(found_file_path)
            time.sleep(1.0)
            pyautogui.press('enter')
            time.sleep(2.0)

            # Final Send
            pyautogui.press('enter')
            time.sleep(1.5)
            pyautogui.press('enter')  # Extra press for safety
            time.sleep(1.5)

            return f" File successfully bhej diya!\n• File: {os.path.basename(found_file_path)}\n• To: {contact_name}"

        except Exception as e:
            return f" Error: {str(e)}\nMake sure WhatsApp Desktop is open and visible."
    @function_tool(
        name="generate_code",
        description="""When user asks to write, generate, bana do, likh do, code, program, script, function, class, coding kar do, create code — ALWAYS call this tool immediately.
    Do NOT write code yourself — call this function with the full request and return its result."""
    )
    async def generate_code(self, context: RunContext, request: str) -> str:
        _ = context
        try:
            result = await handle_coding(request)
            return result
        except Exception as e:
            return f"Code generation failed: {str(e)}"

    @function_tool(
        name="create_presentation",
        description="""
        When user asks to create PPT, presentation,
        slides, PowerPoint, deck, prez, etc —
        IMMEDIATELY call this tool.

        Supports:
        - Quick Generate
        - Deep Custom
        - File-Based Presentation
        - Full Custom Presentation
        """
    )
    async def create_presentation(
            self,
            context: RunContext,
            topic_or_request: str,
            mode: str = "1",
            custom_prompt: str = ""
    ) -> str:

        _ = context

        try:
            # Clean topic
            topic = (
                topic_or_request
                .replace("create presentation", "")
                .replace("make ppt", "")
                .replace("bana do", "")
                .strip()
            )

            if not topic or len(topic) < 3:
                topic = "Artificial Intelligence"

            # Call PPT generator
            result = await handle_ppt_generation(
                topic=topic,
                mode=mode,
                custom_prompt=custom_prompt,
                user_files=[]
            )

            return result

        except Exception as e:
            return f" Presentation creation failed: {str(e)}"
    @function_tool(
        name="handle_apps",
        description="Open, close, install or uninstall applications. Also handles IDEs like VS Code."
    )
    async def handle_apps(self, context: RunContext, text: str) -> str:
        _ = context
        global apps  # Declare global at the top of the function
        text = text.lower().strip()
        # ---------- OPEN ----------
        if text.startswith("open "):
            name = text[len("open "):].strip()
            try:
                # Simulate Windows Start button search
                pyautogui.press('win')
                await asyncio.sleep(0.5)
                pyautogui.typewrite(name)
                await asyncio.sleep(0.5)
                pyautogui.press('enter')
                return f"{name} opened."
            except Exception as e:
                return f"Failed to open {name}: {e}"
        # ---------- CLOSE ----------
        if text.startswith("close "):
            name = text[len("close "):].strip()
            closed_any = False
            for process in psutil.process_iter(['name', 'exe']):
                proc_name = process.info['name']
                proc_exe = process.info['exe']
                if proc_name and (name in proc_name.lower() or (proc_exe and name in proc_exe.lower())):
                    try:
                        process.terminate()  # Gentler than kill
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
                subprocess.call(f'winget install -e --id {name} --accept-package-agreements --accept-source-agreements', shell=True)
                # Reload apps after install
                apps = load_apps()
                return f"Installing {name}."
            except Exception as e:
                return f"Installation failed: {e}"
        # ---------- UNINSTALL ----------
        if text.startswith("uninstall "):
            name = text[len("uninstall "):].strip()
            try:
                subprocess.call(f'winget uninstall {name}', shell=True)
                # Reload apps after uninstall
                apps = load_apps()
                return f"Uninstalling {name}."
            except Exception as e:
                return f"Uninstall failed: {e}"
        return "App command not understood."

    from heart_mouse import HeartInput

    @function_tool(
        name="input_control",
        description="Advanced HEART Input Control: mouse, keyboard, window, screenshot, summarization, save to notepad, rewrite, delete text, folder management, and more."
    )
    async def input_control(
            self,
            context: RunContext,
            action: str,

            # Mouse Control
            x: int = None,
            y: int = None,
            duration: float = 0.5,
            pixels: int = 100,
            amount: int = 100,  # for scroll
            clicks: int = 1,
            button: str = "left",

            # Keyboard
            text: str = None,
            key: str = None,
            keys: list = None,
            interval: float = 0.05,

            # Summarization & Text Processing
            topic: str = None,
            instruction: str = None,  # for rewrite_summary (e.g. "shorter", "improve")

            # File & Summary Management
            filename: str = None,
            folder: str = None,
            folder_name: str = None,
            filepath: str = None,

            # Screenshot
            save_as: str = None,
            region: tuple = None,


    ) -> str:

        _ = context  # unused

        try:
            from heart_mouse import HeartInput

            # Pass everything to HeartInput.control()
            return await HeartInput.control(
                action=action,
                x=x,
                y=y,
                text=text,
                key=key,
                keys=keys,
                pixels=pixels,
                save_as=save_as,
                region=region,
                duration=duration,
                amount=amount,
                clicks=clicks,
                button=button,
                topic=topic,
                instruction=instruction,
                filename=filename,
                folder=folder,
                folder_name=folder_name,
                filepath=filepath,
                interval=interval,
            )

        except ImportError:
            return "Error: Could not import HeartInput from heart_mouse.py"
        except Exception as e:
            return f" Input control failed: {str(e)}"
    @function_tool(
        name="get_weather",
        description="Get current weather for a city."
    )
    async def get_weather(self, context: RunContext, city: str) -> str:
        _ = context

        # Hardcoded OpenWeatherMap API key (no .env needed anymore)
        key = "key denied"  

        url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={key}&units=metric"

        try:
            response = requests.get(url)
            if response.status_code == 200:
                data = response.json()
                temp = data['main']['temp']
                desc = data['weather'][0]['description']
                return f"Weather in {city}: {temp}°C, {desc}."
            else:
                return f"Weather fetch failed: {response.status_code} - {response.text}"
        except Exception as e:
            return f"Weather fetch failed: {str(e)}"

    @function_tool(
        name="get_time",
        description="Get current accurate time. Default is Indian time (Asia/Kolkata). You can also ask for any other timezone."
    )
    async def get_time(self, context: RunContext, timezone: str = "Asia/Kolkata") -> str:
        _ = context

        try:
            import pytz
            from datetime import datetime

            # Default timezone = India (IST)
            tz = pytz.timezone(timezone)

            # Current time in given timezone
            now = datetime.now(tz)

            # Beautiful format
            date_str = now.strftime("%d %B %Y")  # e.g. 09 February 2026
            time_str = now.strftime("%I:%M %p")  # e.g. 10:25 PM
            tz_name = now.tzname() or timezone  # e.g. IST

            return f"Aaj ki tareekh hai {date_str} aur waqt hai **{time_str}** ({tz_name})."

        except ImportError:
            return "pytz library missing. Run: pip install pytz"

        except Exception as e:
            return f"Timezone error: {str(e)}. Default Indian time use kar rahe hain."
    @function_tool(
        name="file_manager",
        description="Manage files: list, search, open, read, create, delete, rename files or directories. Supports C drive access with paths like 'C:/path/to/file'."
    )
    async def file_manager(self, context: RunContext, action: str, path: str = "C:/", new_path: str = None, item_type: str = "file") -> str:
        _ = context
        path = os.path.expanduser(path)  # Handle ~ for home dir, also allows C:/ paths
        if action == "list":
            try:
                files = os.listdir(path)
                return f"Files in {path}:\n" + "\n".join(files[:20]) + ("\n... (truncated)" if len(files) > 20 else "")
            except Exception as e:
                return f"Failed to list files: {str(e)}"
        elif action == "search":
            if not new_path:
                return "Search term required in new_path."
            try:
                found = []
                for root, dirs, files in os.walk(path):
                    for file in files:
                        if new_path.lower() in file.lower():
                            found.append(os.path.join(root, file))
                return f"Found files matching '{new_path}':\n" + "\n".join(found[:20]) + ("\n... (truncated)" if len(found) > 20 else "")
            except Exception as e:
                return f"Failed to search: {str(e)}"
        elif action == "open":
            try:
                os.startfile(path)
                return f"Opened {path}."
            except Exception as e:
                return f"Failed to open {path}: {str(e)}"
        elif action == "read":
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
                return f"Content of {path}:\n{content[:2000]}..."  # Truncate to avoid overload
            except Exception as e:
                return f"Failed to read {path}: {str(e)}"
        elif action == "create":
            try:
                if item_type == "dir":
                    os.makedirs(path, exist_ok=True)
                    return f"Directory {path} created."
                else:
                    os.makedirs(os.path.dirname(path), exist_ok=True)
                    open(path, 'a').close()
                    return f"File {path} created."
            except Exception as e:
                return f"Failed to create: {str(e)}"
        elif action == "delete":
            try:
                if item_type == "dir":
                    import shutil
                    shutil.rmtree(path)  # Allow deleting non-empty dirs
                    return f"Directory {path} deleted."
                else:
                    os.unlink(path)
                    return f"File {path} deleted."
            except Exception as e:
                return f"Failed to delete: {str(e)}"
        elif action == "rename":
            if new_path:
                try:
                    os.rename(path, new_path)
                    return f"Renamed {path} to {new_path}."
                except Exception as e:
                    return f"Failed to rename: {str(e)}"
            else:
                return "New path required for rename."
        return "File manager command not understood. Use 'list', 'search', 'open', 'read', 'create', 'delete', or 'rename'."

    @function_tool(
        name="system_control",
        description="Control system functions like volume, brightness, shutdown, restart, sleep, lock (use cautiously). For volume, requires pycaw and comtypes (pip install pycaw comtypes)."
    )
    async def system_control(self, context: RunContext, action: str, value: str = None) -> str:
        _ = context
        sys = platform.system()
        if sys != "Windows":
            return "System control currently supports Windows only."
        if action == "shutdown":
            # WARNING: This will shut down the PC immediately - use with care!
            subprocess.call(["shutdown", "/s", "/t", "0"])
            return "Shutting down the system."
        elif action == "restart":
            subprocess.call(["shutdown", "/r", "/t", "0"])
            return "Restarting the system."
        elif action == "sleep":
            os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")
            return "Putting system to sleep."
        elif action == "lock":
            ctypes.windll.user32.LockWorkStation()
            return "System locked."
        elif action == "volume":
            try:
                from comtypes import CLSCTX_ALL
                from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
                devices = AudioUtilities.GetSpeakers()
                interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
                vol = interface.QueryInterface(IAudioEndpointVolume)
                current = vol.GetMasterVolumeLevelScalar()
                if value == "up":
                    vol.SetMasterVolumeLevelScalar(min(1.0, current + 0.1), None)
                    return "Volume increased."
                elif value == "down":
                    vol.SetMasterVolumeLevelScalar(max(0.0, current - 0.1), None)
                    return "Volume decreased."
                elif value == "mute":
                    vol.SetMute(1, None)
                    return "Volume muted."
                elif value.isdigit():
                    level = float(int(value) / 100)
                    vol.SetMasterVolumeLevelScalar(level, None)
                    return f"Volume set to {value}%."
                else:
                    return "Specify 'up', 'down', 'mute', or a number 0-100 for volume."
            except ImportError:
                return "pycaw or comtypes not installed. Use pip install pycaw comtypes for full volume control."
            except Exception as e:
                return f"Volume control failed: {str(e)}"
        elif action == "brightness":
            try:
                import screen_brightness_control as sbc  # pip install screen-brightness-control
                current = sbc.get_brightness()
                if isinstance(current, list):
                    current = current[0]  # Take first display if multiple
                if value == "up":
                    sbc.set_brightness(min(100, current + 10))
                    return "Brightness increased."
                elif value == "down":
                    sbc.set_brightness(max(0, current - 10))
                    return "Brightness decreased."
                else:
                    try:
                        level = int(value.strip('% ').strip())
                        sbc.set_brightness(level)
                        return f"Brightness set to {level}%."
                    except ValueError:
                        return "Invalid brightness value. Use number or number%."
            except ImportError:
                return "screen-brightness-control not installed. Use pip install screen-brightness-control."
            except Exception as e:
                return f"Brightness control failed: {str(e)}"
        return "System control command not understood."

    @function_tool(
        name="media_control",
        description="Control media playback (play/pause/resume, next, previous). Windows-specific using key simulation. Resume is same as play/pause toggle."
    )
    async def media_control(self, context: RunContext, action: str) -> str:
        _ = context
        try:
            pyautogui.FAILSAFE = False  # Disable failsafe
            if action in ["play_pause", "resume"]:
                pyautogui.press('playpause')
                return "Media play/paused/resumed."
            elif action == "next":
                pyautogui.press('nexttrack')
                return "Next track."
            elif action == "previous":
                pyautogui.press('prevtrack')
                return "Previous track."
            else:
                return "Media command not understood. Use 'play_pause', 'resume', 'next', or 'previous'."
        except Exception as e:
            return f"Media control failed: {str(e)}"



    @function_tool(
        name="detect_mood",
        description="Detect mood from user text (simple sentiment analysis)."
    )
    async def detect_mood(self, context: RunContext, text: str) -> str:
        _ = context
        try:
            from textblob import TextBlob  # Requires pip install textblob
            blob = TextBlob(text)
            sentiment = blob.sentiment.polarity
            if sentiment > 0.5:
                return "Positive/Happy mood."
            elif sentiment < -0.5:
                return "Negative/Sad mood."
            else:
                return "Neutral mood."
        except ImportError:
            return "textblob not installed. Use pip install textblob for mood detection."
        except Exception as e:
            return f"Mood detection failed: {str(e)}"

    @function_tool(
        name="play_mood_music",
        description="Detect mood from text and play music accordingly on YouTube."
    )
    async def play_mood_music(self, context: RunContext, text: str) -> str:
        mood = await self.detect_mood(context, text)
        if "positive" in mood.lower() or "happy" in mood.lower():
            query = "happy upbeat music"
        elif "negative" in mood.lower() or "sad" in mood.lower():
            query = "soothing relaxing music"
        else:
            query = "chill neutral music"
        return await self.play_music(context, query, source="youtube")

    @function_tool(
        name="play_music",
        description="Play music from a local file, app, YouTube or Spotify. For romantic music, suggest or play specific genres."
    )
    async def play_music(self, context: RunContext, path_or_query: str, genre: str = None, source: str = "local") -> str:
        _ = context
        query = path_or_query if not genre else f"{genre} {path_or_query}"
        if genre == "romantic":
            query = "romantic music"
        if source.lower() == "youtube":
            try:
                driver = webdriver.Chrome()
                driver.get(f"https://www.youtube.com/results?search_query={urllib.parse.quote(query)}")
                wait = WebDriverWait(driver, 10)
                first_video = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'a#video-title')))
                first_video.click()
                # Do not quit the driver to keep the video playing
                return f"Playing '{query}' on YouTube."
            except Exception as e:
                if 'driver' in locals():
                    driver.quit()
                return f"Failed to play on YouTube: {str(e)}"
        elif source.lower() == "spotify":
            try:
                # Open Spotify and search using URI
                search_uri = f"spotify:search:{urllib.parse.quote(query)}"
                os.startfile(search_uri)
                await asyncio.sleep(5)  # Wait for Spotify to open and load search
                # Use keyboard to attempt play (adjusted tabs for better chance of hitting play button on first result)
                for _ in range(6):  # Increased tabs to navigate to play button
                    keyboard.send('tab')
                    await asyncio.sleep(0.1)
                keyboard.send('enter')  # Play
                return f"Playing '{query}' on Spotify."
            except Exception as e:
                return f"Failed to play on Spotify: {str(e)}"
        elif os.path.isfile(path_or_query):
            try:
                os.startfile(path_or_query)
                return f"Playing music from {path_or_query}."
            except Exception as e:
                return f"Failed to play music: {str(e)}"
        else:
            # Treat as app, e.g., "spotify"
            return await self.handle_apps(context, f"open {path_or_query}")

    @function_tool(
        name="handle_pdf",
        description="Handle PDF files: open, extract text, or merge (requires pypdf)."
    )
    async def handle_pdf(self, context: RunContext, action: str, file_path: str, other_files: str = "", output_path: str = "merged.pdf") -> str:
        _ = context
        file_path = os.path.expanduser(file_path)
        if action == "open":
            try:
                os.startfile(file_path)
                return f"Opened PDF: {file_path}."
            except Exception as e:
                return f"Failed to open PDF: {str(e)}"
        elif action == "extract_text":
            try:
                from pypdf import PdfReader  # Requires pip install pypdf
                reader = PdfReader(file_path)
                text = ""
                for page in reader.pages:
                    text += page.extract_text() + "\n"
                return f"Extracted text from {file_path}:\n{text[:2000]}..."  # Increased limit
            except ImportError:
                return "pypdf not installed. Use pip install pypdf for PDF handling."
            except Exception as e:
                return f"PDF extraction failed: {str(e)}"
        elif action == "merge":
            try:
                from pypdf import PdfMerger  # Requires pip install pypdf
                merger = PdfMerger()
                merger.append(file_path)
                for f in other_files.split(','):
                    merger.append(os.path.expanduser(f.strip()))
                merger.write(os.path.expanduser(output_path))
                merger.close()
                return f"PDFs merged to {output_path}."
            except ImportError:
                return "pypdf not installed. Use pip install pypdf for PDF handling."
            except Exception as e:
                return f"PDF merge failed: {str(e)}"
        return "PDF command not understood. Use 'open', 'extract_text', or 'merge'."

    @function_tool(
        name="web_search",
        description="Perform a web search using SerpAPI."
    )
    async def web_search(self, context: RunContext, query: str, max_results: int = 3) -> str:
        _ = context

        # Hardcoded SerpAPI key (no .env needed anymore)
        key = "dennied"

        try:
            from serpapi import GoogleSearch
            search = GoogleSearch({"q": query, "api_key": key})
            results = search.get_dict().get("organic_results", [])
            formatted = "\n".join([
                f"{r.get('title', '')}: {r.get('snippet', '')} ({r.get('link', '')})"
                for r in results[:max_results]
            ])
            return formatted or "No results found."
        except ImportError:
            return "google-search-results not installed"
        except Exception as e:
            return f"Search failed: {str(e)}"

    @function_tool(
        name="browse_web",
        description="Open a URL in the default browser."
    )
    async def browse_web(self, context: RunContext, url: str) -> str:
        _ = context
        try:
            import webbrowser
            webbrowser.open(url)
            return f"Opened {url} in browser."
        except ImportError:
            return "webbrowser module not available."
        except Exception as e:
            return f"Failed to open URL: {str(e)}"


    @function_tool(
        name="get_love_quote",
        description="Get a random love quote. Requires QUOTES_API_KEY from api-ninjas.com in .env.local.local."
    )
    async def get_love_quote(self, context: RunContext) -> str:
        _ = context
        key = os.getenv("dennied")
        if not key:
            return "API key not set for quotes. Add QUOTES_API_KEY to .env.local.local (get from api-ninjas.com)."
        url = "https://api.api-ninjas.com/v1/quotes?category=love"
        try:
            response = requests.get(url, headers={'X-Api-Key': key})
            if response.status_code == 200:
                data = response.json()[0]  # Returns list of 1
                return f"\"{data['quote']}\" - {data['author']}"
            else:
                return f"Could not get quote: {response.status_code} - {response.text}"
        except Exception as e:
            return f"Quote fetch failed: {str(e)}"

    emergency_active = False

    @function_tool(
        name="send_heart_live_location_emergency",
        description="The system securely shares the user’s live location with trusted contacts through WhatsApp Desktop.।"
    )
    async def send_heart_live_location_emergency(self, context: RunContext) -> str:
        global emergency_active  # यहाँ global जरूरी है

        if emergency_active:
            return "इमरजेंसी पहले से चल रही है। Ctrl+Alt+S दबाकर रोकें।"

        emergency_active = True

        try:
            # CONFIG
            trusted_contacts = ["Mummy", "papa jii",]
            search_bar_x = 203
            search_bar_y = 140

            def get_live_location() -> str:
                try:
                    resp = requests.get('https://ipinfo.io/json', timeout=6)
                    data = resp.json()
                    city = data.get('city', 'Unknown')
                    region = data.get('region', 'Unknown')
                    country = data.get('country', 'Unknown')
                    loc = data.get('loc', 'Unknown')
                    ts = time.strftime("%I:%M %p")
                    return f" Heart लाइव लोकेशन ({ts}):\n{city}, {region}, {country}\nLat/Long: {loc}"
                except Exception as err:
                    return f"लोकेशन नहीं मिली ({time.strftime('%I:%M %p')})"

            def focus_and_send(contact: str, message: str) -> bool:
                try:
                    pyautogui.hotkey('win', 's')
                    time.sleep(0.7)
                    pyautogui.write('whatsapp')
                    time.sleep(0.7)
                    pyautogui.press('enter')
                    time.sleep(5.5)

                    pyautogui.hotkey('ctrl', 'f')
                    time.sleep(1.0)
                    pyautogui.click(x=search_bar_x, y=search_bar_y)
                    time.sleep(0.8)

                    pyautogui.hotkey('ctrl', 'a')
                    pyautogui.press('backspace')
                    time.sleep(0.4)

                    pyautogui.write(contact)
                    time.sleep(2.0)
                    pyautogui.press('down')
                    pyautogui.press('enter')
                    time.sleep(3.5)

                    pyautogui.write(message)
                    time.sleep(0.8)
                    pyautogui.press('enter')
                    time.sleep(1.5)
                    return True
                except Exception as err:
                    print(f"{contact} fail: {err}")
                    return False


            def emergency_loop():
                global emergency_active  # यहाँ भी global जरूरी है
                while emergency_active:
                    loc = get_live_location()
                    msg = f" HEART EMERGENCY UPDATE\n{loc}\n need help"
                    for contact in trusted_contacts:
                        focus_and_send(contact, msg)
                    time.sleep(60)

                    # ================== STOP FUNCTION ==================

                def stop_emergency():
                    global emergency_active
                    emergency_active = False
                    print(" Emergency Stopped by Assistant/User")

                    # Save stop function so main assistant can call it

                self.stop_emergency = stop_emergency

                # Start emergency in background
                threading.Thread(target=emergency_loop, daemon=True).start()

                # Hotkey backup
                keyboard.add_hotkey('ctrl+alt+s', stop_emergency)

                return " HEART EMERGENCY MODE ACTIVATED!\n\nAssistant को बोलें:\n\"stop emergency\" या \"emergency band kar do\""

        except Exception as err:
            emergency_active = False
            return f"problem: {str(err)}"


    @function_tool(
        name="get_horoscope",
        description="Get daily motivation"
    )
    async def get_horoscope(self, context: RunContext, zodiac: str, date: str = None) -> str:
        _ = context
        key = os.getenv("dennied")
        if not key:
            return "API key not set for horoscope."
        url = f"https://api.api-ninjas.com/v1/horoscope?sign={zodiac.lower()}"
        if date:
            url += f"&date={date}"  # Format: YYYY-MM-DD
        try:
            response = requests.get(url, headers={'X-Api-Key': key})
            if response.status_code == 200:
                data = response.json()
                return f"Horoscope for {zodiac.capitalize()}: {data['horoscope']}"
            else:
                return f"Could not get horoscope: {response.status_code} - {response.text}"
        except Exception as e:
            return f"Horoscope fetch failed: {str(e)}"



    @function_tool(
        name="send_whatsapp_desktop",
        description="""Send message via Desktop WhatsApp app.
    Contact name search on whatsaap (like  Mummy, Jaan, Dost) and then send message via WhatsApp.
    Desktop WhatsApp app should and  phone also linked with system."""
    )
    async def send_whatsapp_desktop(self, context: RunContext, contact_name: str, message: str = None,
                                    file_path: str = None) -> str:
        _ = context
        try:
            import pyautogui
            import pygetwindow as gw
            import time
            import os
            import win32gui
            import win32con
            import time
            import os
            # === 1. Ensure WhatsApp Desktop is open and focused ===
            pyautogui.FAILSAFE = False

            # === STRONG FOCUS ON WHATSAPP ===
            hwnd = win32gui.FindWindow(None, "WhatsApp")

            if hwnd:
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)  # Restore if minimized
                win32gui.SetForegroundWindow(hwnd)  # Force focus
                time.sleep(1.0)
                win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)  # Maximize
                time.sleep(0.8)
            else:
                # Open WhatsApp if not running
                pyautogui.hotkey('win', 's')
                time.sleep(0.7)
                pyautogui.write('whatsapp')
                time.sleep(0.6)
                pyautogui.press('enter')
                time.sleep(7.5)

            # === 2. Focus search bar reliably ===
            pyautogui.hotkey('ctrl', 'f')
            time.sleep(0.8)

            # Clear previous search if any
            pyautogui.hotkey('ctrl', 'a')
            pyautogui.press('backspace')
            time.sleep(0.5)

            # Type contact name
            pyautogui.write(contact_name)
            time.sleep(1.8)  # Wait for search results

            # Select first result
            pyautogui.press('enter')
            time.sleep(2.0)  # Wait for chat to open

            # === 3. Send file (if provided) ===
            if file_path and os.path.exists(file_path):
                # Click attachment icon (you may need to adjust coordinates or use image recognition)
                # Alternative: Use Ctrl + Shift + M or hotkey if available
                pyautogui.hotkey('ctrl', 'shift', 'm')  # Common shortcut for media in newer WhatsApp
                time.sleep(1.5)

                # Type full file path and send
                pyautogui.write(file_path)
                time.sleep(0.8)
                pyautogui.press('enter')
                time.sleep(2.0)  # Wait for upload to start

            # === 4. Send text message (if provided) ===
            if message:
                pyautogui.write(message)
                time.sleep(0.6)
                pyautogui.press('enter')

            return f" Message sent successfully to '{contact_name}'"

        except Exception as e:
            return f" Desktop WhatsApp failed: {str(e)}\nMake sure WhatsApp Desktop is installed, linked, and visible on screen."
def _create_backup(full_path: str) -> tuple[bool, str]:
    """
    Create timestamped backup copy before modification.
    Returns (success: bool, message: str)
    """
    if not os.path.exists(full_path):
        return False, "No backup needed (file did not exist)"

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base, ext = os.path.splitext(full_path)
    backup_path = f"{base}_backup_{timestamp}{ext}"

    try:
        shutil.copy2(full_path, backup_path)
        return True, f"Backup created: {os.path.basename(backup_path)}"
    except Exception as e:
        return False, f"Backup failed: {str(e)}"


@function_tool(
    name="manage_heart_note",
    description="""Manages heart-related notes, moods, feelings, quotes, memories etc.

Supported operations:
  append   - add new entry at the end (default)
  write    - overwrite the entire file
  edit     - replace content of a specific line (needs line_number & data)
  delete   - remove a line by number (needs line_number)
  rename   - change filename (needs new_file_name)

Every call requires folder and file_name.
Folder is created automatically if it does not exist.
Timestamps are added automatically on append & write.

Examples:
manage_heart_note(folder="C:/Diary", file_name="mood.txt", data="Feeling calm today ")
manage_heart_note(folder="C:/Diary", file_name="mood.txt", operation="edit",   line_number=3, data="New version of line 3")
manage_heart_note(folder="C:/Diary", file_name="mood.txt", operation="delete", line_number=5)
manage_heart_note(folder="C:/Diary", file_name="mood.txt", operation="rename", new_file_name="mood_2026.txt")
"""
)
async def manage_heart_note(
    self,
    context,
    folder: str,
    file_name: str,
    operation: str = "append",
    data: Optional[str] = None,
    line_number: Optional[int] = None,
    new_file_name: Optional[str] = None,
) -> str:
    """
    Manage emotional / heart-related notes with full control.
    """
    try:
        folder = folder.strip()
        file_name = file_name.strip()
        operation = operation.lower().strip()

        if not folder:
            return "Error: folder path is required"
        if not file_name:
            return "Error: file_name is required"

        full_path = os.path.join(folder, file_name)

        # Create folder if needed
        os.makedirs(folder, exist_ok=True)

        if operation in ("append", "write"):
            if not data:
                return "Error: 'data' is required for append/write"

            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            entry = f"[{timestamp}] {data.strip()}"

            if operation == "append":
                exists = os.path.exists(full_path)
                with open(full_path, "a", encoding="utf-8") as f:
                    if exists and os.path.getsize(full_path) > 0:
                        f.write("\n")
                    f.write(entry + "\n")
                action = "appended"
            else:  # write
                with open(full_path, "w", encoding="utf-8") as f:
                    f.write(entry + "\n")
                action = "overwritten"

            return (
                f"Note successfully {action}\n"
                f"File     : {file_name}\n"
                f"Folder   : {folder}\n"
                f"Full path: {full_path}\n"
                f"Entry    : {entry}"
            )

        elif operation == "edit":
            if line_number is None or data is None:
                return "Error: 'line_number' and 'data' are both required for edit"

            if not os.path.exists(full_path):
                return f"File not found: {full_path}"

            with open(full_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            if line_number < 1 or line_number > len(lines):
                return f"Invalid line number. File has {len(lines)} lines (1–{len(lines)})."

            old_content = lines[line_number - 1].rstrip("\n")
            lines[line_number - 1] = data.rstrip() + "\n"

            with open(full_path, "w", encoding="utf-8") as f:
                f.writelines(lines)

            return (
                f"Line {line_number} updated successfully\n"
                f"File     : {file_name}\n"
                f"Old text : {old_content}\n"
                f"New text : {data}"
            )

        elif operation == "delete":
            if line_number is None:
                return "Error: 'line_number' is required for delete"

            if not os.path.exists(full_path):
                return f"File not found: {full_path}"

            with open(full_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            if line_number < 1 or line_number > len(lines):
                return f"Invalid line number. File has {len(lines)} lines (1–{len(lines)})."

            removed = lines.pop(line_number - 1).rstrip("\n")

            with open(full_path, "w", encoding="utf-8") as f:
                f.writelines(lines)

            return (
                f"Line {line_number} deleted\n"
                f"File     : {file_name}\n"
                f"Removed  : {removed}"
            )

        elif operation == "rename":
            if not new_file_name:
                return "Error: 'new_file_name' is required for rename"

            new_file_name = new_file_name.strip()
            new_path = os.path.join(folder, new_file_name)

            if not os.path.exists(full_path):
                return f"Source file not found: {full_path}"

            if os.path.exists(new_path):
                return f"Target already exists: {new_path}"

            os.rename(full_path, new_path)

            return (
                f"File renamed successfully\n"
                f"Old name : {file_name}\n"
                f"New name : {new_file_name}\n"
                f"Folder   : {folder}"
            )

        else:
            return "Invalid operation. Allowed: append, write, edit, delete, rename"

    except PermissionError:
        return f"Permission denied: {full_path}\nCheck folder permissions."
    except Exception as e:
        return f"Operation failed: {str(e)}"
import re
import webbrowser
import requests
import json
import time
import subprocess
import sys
import os


# -----------------------------
# FUNCTION TOOL DECORATOR
# -----------------------------
def function_tool(name: str, description: str):
    def decorator(func):
        func._is_tool = True
        func._tool_name = name
        func._tool_description = description
        return func

    return decorator


# -----------------------------
# CONFIG
# -----------------------------
OPENROUTER_API_KEY = "dennied"


# =============================================
# MAIN EMAIL TOOL
# =============================================
@function_tool(
    name="send_email",
    description="Send professional email. Generates email and opens ready-to-send draft in Gmail."
)
def send_email(command: str, auto_send: bool = True) -> dict:
    """
    Main function for HEART Voice Assistant
    """
    print(f" HEART Email Tool Activated: {command}")

    recipient_name, topic = extract_recipient_and_topic(command)
    if not recipient_name:
        return {"status": "error", "message": "Could not detect recipient"}

    if is_email(recipient_name):
        to_email = recipient_name
        to_name = None
    else:
        to_email = input(f"📧 Enter email for {recipient_name}: ").strip()
        to_name = recipient_name

    if not is_email(to_email):
        return {"status": "error", "message": "Invalid email address"}

    email_data = generate_natural_email(to_name, topic)

    print("\n📧 EMAIL GENERATED:")
    print(f"Subject: {email_data['subject']}")
    print(f"Body:\n{email_data['body']}\n")

    # Open Gmail with pre-filled content (Ready in Draft)
    open_email_web(to_email, email_data['subject'], email_data['body'])

    return {
        "status": "draft_ready",
        "message": f" Gmail compose window opened with ready draft for {to_email}",
        "subject": email_data['subject']
    }


# =============================================
# HELPER FUNCTIONS
# =============================================
def is_email(text: str) -> bool:
    return bool(re.match(r"[^@]+@[^@]+\.[^@]+", text))


def extract_recipient_and_topic(command: str):
    clean = re.sub(r'(send email to|send to|email to|mail to)', '', command, flags=re.I).strip()
    if ' about ' in clean.lower():
        parts = clean.split(' about ', 1)
        return parts[0].strip(), parts[1].strip()
    words = clean.split()
    return words[0] if words else clean, " ".join(words[1:]) if len(words) > 1 else "general discussion"


def generate_natural_email(to_name: str, topic: str):
    name_part = to_name if to_name else "there"
    prompt = f"""You are a professional and friendly executive assistant.
Write a natural, human-sounding email.

Recipient: {name_part}
Topic: {topic}

Requirements:
- Warm professional tone
- Unique and natural
- Excellent subject line
- Concise body (4-7 sentences)
- Polite call to action
- Output ONLY JSON: {{"subject": "...", "body": "..."}}"""

    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {OPENROUTER_API_KEY}", "Content-Type": "application/json"},
            json={"model": "nex-agi/nex-n2-pro:free", "messages": [{"role": "user", "content": prompt}],
                  "temperature": 0.7, "max_tokens": 600},
            timeout=30
        )
        if response.status_code == 200:
            content = response.json()['choices'][0]['message']['content'].strip()
            try:
                return json.loads(content)
            except:
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group())
    except:
        pass

    # Fallback
    return {
        "subject": f"Regarding {topic}",
        "body": f"Hi {name_part},\n\nI'm reaching out about {topic}.\n\nBest regards,\nYour Assistant"
    }


def open_email_web(to_email="", subject="", body=""):
    """Open Gmail with pre-filled content (Ready Draft)"""
    # URL Encoding
    subject = subject.replace(" ", "%20")
    body = body.replace(" ", "%20").replace("\n", "%0A").replace("&", "%26")

    url = f"https://mail.google.com/mail/u/0/?view=cm&fs=1&to={to_email}&su={subject}&body={body}"

    webbrowser.open(url)
    print(" Gmail compose window opened with ready draft!")
    print(" Just review and press Ctrl + Enter to send")



@function_tool(
    name="monitor_whatsapp_incoming",
    description="""WhatsApp Web ko Brave browser mein khol kar incoming messages monitor karegi.
Naya message aate hi padhegi, sender bata degi, aur reply suggest karegi.
Pehli baar QR code scan karna padega."""
)
async def monitor_whatsapp_incoming(self, context: RunContext, sender_name: str = None,
                                    check_interval_sec: int = 15) -> str:
    _ = context
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.service import Service
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        import time

        # Brave browser path (change if your installation path is different)
        brave_path = r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"

        # Use Brave as the browser
        options = webdriver.ChromeOptions()
        options.binary_location = brave_path  # Brave ko use karo
        options.add_argument(
            "--user-data-dir=C:\\Users\\Tilak Kumar\\AppData\\Local\\BraveSoftware\\Brave-Browser\\User Data")  # Brave ka profile use karo

        driver = webdriver.Chrome(options=options)
        driver.get("https://web.whatsapp.com")

        print(
            "Brave mein WhatsApp Web khul gaya! Phone se QR code scan kar do (WhatsApp → Linked Devices → Link a Device)")
        time.sleep(45)  # QR scan ke liye time

        last_message = ""
        while True:
            try:
                # Latest incoming message find karo
                messages = driver.find_elements(By.CSS_SELECTOR, 'div.message-in span.selectable-text')
                if messages:
                    current = messages[-1].text.strip()
                    if current and current != last_message:
                        last_message = current
                        sender = sender_name or "Unknown"
                        emotion = "neutral"
                        if "happy" in current.lower() or "love" in current.lower():
                            emotion = "happy"
                        elif "sad" in current.lower() or "miss" in current.lower():
                            emotion = "sad"
                        reply = "Aww, kitna pyaara message! " if emotion == "happy" else "Arey, sad mat ho na... "
                        return f"**Naya message from {sender}:** {current}\nEmotion: {emotion}\nReply idea: {reply}"
            except:
                pass

            await asyncio.sleep(check_interval_sec)  # har 15 second check

    except Exception as e:
        return f"Monitoring failed: {str(e)}\nBrave browser mein WhatsApp Web open rakho aur QR scan karo."


server = AgentServer()

def async_event_handler(session, event_name):
    def decorator(func):
        def wrapper(*args, **kwargs):
            asyncio.create_task(func(*args, **kwargs))
        session.on(event_name, wrapper)
        return func
    return decorator

@server.rtc_session()
async def my_agent(ctx: agents.JobContext):
    session = AgentSession(
        llm=google.beta.realtime.RealtimeModel( voice="Leda")
    )
    chat_ctx = load_memory()
    global _current_agent
    agent = Assistant(chat_ctx=chat_ctx)
    _current_agent = agent
    await session.start(
        room=ctx.room,
        agent=agent,
        room_options=room_io.RoomOptions(
            audio_input=room_io.AudioInputOptions(
                noise_cancellation=lambda p: (
                    noise_cancellation.BVCTelephony()
                    if p.participant.kind == rtc.ParticipantKind.PARTICIPANT_KIND_SIP
                    else noise_cancellation.BVC()
                )
            )
        )
    )

    @async_event_handler(session, "user_input_transcribed")
    async def on_user_input(event):
        if not heart_active.is_set():
            return  #  Ignore input until wake-up

        text = getattr(event, "transcription", None)
        if not text:
            return

        print(f"[Debug] User said: {text}")

        async def process_and_persist(text: str):
            await session.generate_reply(
                instructions=HEART_RESPONSE_PROMPT,
                user_message=text,
            )

            save_memory(agent.chat_ctx)

        await process_and_persist(text)

        def wakeup_listener():
            print("Listening for wake-up...")

            while True:
                trigger = input("Say 'wake up heart': ")  

                if trigger.lower() == "wake up":
                    print(" Heart Activated")
                    heart_active.set()
                    break
# =========================================
# HEART MAIN ENGINE + VOICE SECURITY
# FULLY FIXED VERSION
# =========================================

if __name__ == "__main__":

    import threading
    import time
    import sys
    import gc
    import os
    import logging
    import warnings
    import asyncio

    # =========================================
    # PERFORMANCE
    # =========================================
    os.environ["PYTHONASYNCIODEBUG"] = "0"

    warnings.filterwarnings("ignore")

    logging.getLogger("livekit").setLevel(logging.ERROR)
    logging.getLogger("websockets").setLevel(logging.ERROR)
    logging.getLogger("asyncio").setLevel(logging.ERROR)

    gc.disable()

    # =========================================
    # IMPORTS
    # =========================================
    from runtime.monitor import (
        update_activity,
        is_idle,
        get_idle_time,
    )

    from runtime.restart_manager import graceful_restart

    from runtime.healthcheck import (
        is_memory_high,
        memory_usage_mb,
    )

    # =========================================
    # VOICE AUTH
    # =========================================
    from voice_auth import (
        authenticate_once,
        enroll_owner,
        load_embedding,
        STATE as VOICE_STATE
    )

    # =========================================
    # CONFIG
    # =========================================
    IDLE_TIMEOUT = 3600
    MEMORY_LIMIT_MB = 1800

    # =========================================
    # GLOBAL STATE
    # =========================================
    STATE = {
        "running": True,
        "processing": False,
        "hud_started": False,
    }

    wake_lock = threading.Lock()

    heart_active = threading.Event()

    # =========================================
    # BOOT
    # =========================================
    print(" Initializing HEART CORE")

    try:

        init_model()

        print(" Core model loaded")

    except Exception as e:

        print(f"[BOOT ERROR] {e}")

        exit(1)

    # =========================================
    # VOICE SECURITY INIT
    # =========================================
    print(" Initializing Voice Security")

    try:

        VOICE_STATE["owner_embedding"] = load_embedding()

        # =====================================
        # FIRST TIME ENROLLMENT
        # =====================================
        if VOICE_STATE["owner_embedding"] is None:

            print("\n OWNER NOT REGISTERED")
            print(" Starting Voice Enrollment")

            enroll_owner()

            print("\n OWNER VOICE REGISTERED")
            print(" Restart HEART")

            exit(0)

        print(" Voice Security Ready")

    except Exception as e:

        print(f"[VOICE AUTH ERROR] {e}")

        exit(1)

    # =========================================
    # PRELOAD CONSOLE MODE
    # =========================================
    if "console" not in sys.argv:
        sys.argv.append("console")

    # =========================================
    # VOICE AUTH LISTENER
    # =========================================
    def auth_listener():

        print(" Voice authentication listener active")

        while STATE["running"]:

            try:

                # =================================
                # PREVENT MULTIPLE PROCESS
                # =================================
                if STATE["processing"]:

                    time.sleep(0.5)
                    continue

                print(" Waiting for voice authentication...")

                # =================================
                # AUTHENTICATE USER
                # =================================
                auth = authenticate_once()

                # =================================
                # ACCESS DENIED
                # =================================
                if not auth:

                    print("\n")
                    print("╔══════════════════════════════════════╗")
                    print("║         SECURITY BREACH ALERT       ║")
                    print("╠══════════════════════════════════════╣")
                    print("║  ACCESS TO HEART CORE DENIED        ║")
                    print("║                                      ║")
                    print("║  UNAUTHORIZED VOICE DETECTED         ║")
                    print("╚══════════════════════════════════════╝")
                    print("\n")

                    # =================================
                    # ALERT SOUND
                    # =================================
                    try:

                        import winsound

                        winsound.Beep(1200, 400)
                        winsound.Beep(900, 400)

                    except:
                        pass

                    time.sleep(2)

                    continue

                # =================================
                # AUTH SUCCESS
                # =================================
                print(" Voice verified")

                heart_active.set()

                time.sleep(1)

            except Exception as e:

                print(f"[AUTH ERROR] {e}")

                time.sleep(1)

    # =========================================
    # SYSTEM MONITOR
    # =========================================
    def monitor_system():

        while STATE["running"]:

            try:

                time.sleep(20)

                idle = get_idle_time()

                ram = memory_usage_mb()

                print(
                    f"[MONITOR] "
                    f"Idle={int(idle)}s | "
                    f"RAM={ram:.2f}MB"
                )

                # =================================
                # LIGHT CLEANUP
                # =================================
                gc.collect(0)

                # =================================
                # MEMORY PROTECTION
                # =================================
                if is_memory_high(limit_mb=MEMORY_LIMIT_MB):

                    print("[MONITOR] High memory usage")

                    graceful_restart()

                # =================================
                # IDLE RESTART
                # =================================
                if is_idle(IDLE_TIMEOUT):

                    print("[MONITOR] Idle timeout reached")

                    graceful_restart()

            except Exception as e:

                print(f"[MONITOR ERROR] {e}")

    # =========================================
    # START THREADS
    # =========================================
    threading.Thread(
        target=auth_listener,
        daemon=True,
        name="AuthThread"
    ).start()

    threading.Thread(
        target=monitor_system,
        daemon=True,
        name="MonitorThread"
    ).start()

    # =========================================
    # ONLINE
    # =========================================
    print(" HEART SYSTEM ONLINE")
    print("️ Voice Security Enabled")
    print(" Waiting for authorized voice...")

    # =========================================
    # MAIN HEART ENGINE
    # =========================================
    while STATE["running"]:

        heart_active.wait()

        with wake_lock:

            # =================================
            # PREVENT DUPLICATE PROCESS
            # =================================
            if STATE["processing"]:
                continue

            STATE["processing"] = True

            update_activity()

            print(" WELCOME BACK D4RK")

            try:

                # =================================
                # START HUD ONCE
                # =================================
                if not STATE["hud_started"]:

                    threading.Thread(
                        target=heart_hud.start_hud,
                        daemon=True,
                        name="HUDThread"
                    ).start()

                    STATE["hud_started"] = True

                # =================================
                # RUN HEART AGENT
                # =================================
                agents.cli.run_app(server)

            except KeyboardInterrupt:

                print("[SYSTEM] Shutdown requested")

                STATE["running"] = False

                if _current_agent:
                    print("[Memory] Saving before shutdown...")
                    save_memory(_current_agent.chat_ctx)
            except Exception as e:

                print(f"[HEART ERROR] {e}")

                time.sleep(1)

            finally:

                # =================================
                # RESET CLEANLY
                # =================================
                STATE["processing"] = False

                heart_active.clear()

                gc.collect(0)

                print(" HEART STANDBY MODE ACTIVATED")
