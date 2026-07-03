# =========================================================
# HEART ULTRA INPUT ENGINE
# Stable + Fast + Accurate Desktop Automation
# =========================================================

import asyncio
import time
import pyautogui
import pyperclip

try:
    import pygetwindow as gw
    WINDOW_SUPPORT = True
except Exception:
    WINDOW_SUPPORT = False


# =========================================================
# PERFORMANCE CONFIG
# =========================================================
pyautogui.FAILSAFE = True

# ultra fast
pyautogui.PAUSE = 0

# smoother typing/clicking
pyautogui.MINIMUM_DURATION = 0
pyautogui.MINIMUM_SLEEP = 0
# ====================== PERFORMANCE & SPEED CONFIG ======================
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0
pyautogui.MINIMUM_DURATION = 0
pyautogui.MINIMUM_SLEEP = 0

# NEW: Global Speed Control
SPEED_MODE = "ultra"   # Change to "fast", "ultra", or "safe"

DELAYS = {
    "safe":  {"focus": 0.12, "type": 0.08, "hotkey": 0.05, "after": 0.1},
    "fast":  {"focus": 0.06, "type": 0.04, "hotkey": 0.03, "after": 0.05},
    "ultra": {"focus": 0.04, "type": 0.02, "hotkey": 0.015, "after": 0.03}
}

def get_delay(key):
    return DELAYS.get(SPEED_MODE, DELAYS["fast"])[key]

class HeartInput:

    # =====================================================
    # ACTIVE WINDOW
    # =====================================================
    @staticmethod
    def get_active_window():
        try:
            if not WINDOW_SUPPORT:
                return "pygetwindow_not_installed"
            win = gw.getActiveWindow()
            if win:
                return win.title
            return "Unknown"
        except Exception as err:
            return f"Window detection failed: {err}"

    # =====================================================
    # INTERNAL SAFE EXECUTOR
    # =====================================================
    @staticmethod
    async def run_sync(func, *args, **kwargs):
        return await asyncio.to_thread(func, *args, **kwargs)

    # =====================================================
    # WINDOW FOCUS
    # =====================================================
    @staticmethod
    async def ensure_focus(x=None, y=None):
        try:
            if x is not None and y is not None:
                await HeartInput.run_sync(pyautogui.click, x, y)
                await asyncio.sleep(0.08)

            # release stuck modifier keys
            pyautogui.keyUp('shift')
            pyautogui.keyUp('ctrl')
            pyautogui.keyUp('alt')
            pyautogui.keyUp('win')

            return True
        except Exception:
            return False

    # =====================================================
    # MOUSE MOVE
    # =====================================================
    @staticmethod
    async def move_mouse(x=None, y=None, duration=0):
        try:
            if x is None or y is None:
                return "❌ x and y required"
            await HeartInput.run_sync(pyautogui.moveTo, x, y, duration)
            return f"✅ Mouse moved to ({x}, {y})"
        except Exception as err:
            return f"❌ Move failed: {err}"

    # =====================================================
    # CLICK
    # =====================================================
    @staticmethod
    async def click(x=None, y=None, button="left", clicks=1):
        try:
            await HeartInput.run_sync(pyautogui.click, x=x, y=y, clicks=clicks, button=button)
            return f"✅ {button} click executed"
        except Exception as err:
            return f"❌ Click failed: {err}"

    # =====================================================
    # SUPER FAST TYPE
    # =====================================================
    @staticmethod
    async def type_text(text="", x=None, y=None, clear=False, enter=False):
        try:
            if not text:
                return "❌ No text provided"

            await HeartInput.ensure_focus(x, y)

            if clear:
                await HeartInput.run_sync(pyautogui.hotkey, 'ctrl', 'a')
                await asyncio.sleep(0.05)
                await HeartInput.run_sync(pyautogui.press, 'backspace')
                await asyncio.sleep(0.05)

            pyperclip.copy(str(text))
            await HeartInput.run_sync(pyautogui.hotkey, 'ctrl', 'v')

            if enter:
                await asyncio.sleep(0.03)
                await HeartInput.run_sync(pyautogui.press, 'enter')

            return f"✅ Typed {len(text)} chars"
        except Exception as err:
            return f"❌ Typing failed: {err}"

    # =====================================================
    # HOTKEY
    # =====================================================
    @staticmethod
    async def hotkey(*keys):
        try:
            await HeartInput.run_sync(pyautogui.hotkey, *keys)
            return f"✅ Hotkey executed: {' + '.join(keys)}"
        except Exception as err:
            return f"❌ Hotkey failed: {err}"

    # =====================================================
    # KEY PRESS
    # =====================================================
    @staticmethod
    async def press(key):
        try:
            await HeartInput.run_sync(pyautogui.press, key)
            return f"✅ Pressed: {key}"
        except Exception as err:
            return f"❌ Key press failed: {err}"

    # =====================================================
    # SCROLL
    # =====================================================
    @staticmethod
    async def scroll(direction="down", amount=700):
        try:
            value = -amount if direction == "down" else amount
            await HeartInput.run_sync(pyautogui.scroll, value)
            return f"✅ Scrolled {direction}"
        except Exception as err:
            return f"❌ Scroll failed: {err}"

    # =====================================================
    # AUTO SCROLL
    # =====================================================
    @staticmethod
    async def auto_scroll(duration=5, speed=500):
        try:
            end = time.time() + duration
            while time.time() < end:
                await HeartInput.run_sync(pyautogui.scroll, -speed)
                await asyncio.sleep(0.03)
            return "✅ Auto scroll completed"
        except Exception as err:
            return f"❌ Auto scroll failed: {err}"

    # =====================================================
    # COPY SCREEN CONTENT
    # =====================================================
    @staticmethod
    async def auto_copy():
        try:
            old = pyperclip.paste()
            await HeartInput.run_sync(pyautogui.hotkey, 'ctrl', 'a')
            await asyncio.sleep(0.08)
            await HeartInput.run_sync(pyautogui.hotkey, 'ctrl', 'c')
            await asyncio.sleep(0.15)
            text = pyperclip.paste().strip()

            if not text:
                return "❌ Clipboard empty"
            if text == old:
                return "❌ Copy failed"
            if text.startswith("{\"function\""):
                return "❌ Terminal/log window focused"

            return f"✅ Copied {len(text)} chars"
        except Exception as err:
            return f"❌ Copy failed: {err}"

    # =====================================================
    # SUMMARY
    # =====================================================
    @staticmethod
    async def summarize_clipboard(topic=None):
        try:
            text = pyperclip.paste().strip()
            if not text:
                return "❌ Clipboard empty"
            text = text.replace("\n", " ")
            sentences = [s.strip() for s in text.split(".") if len(s.strip()) > 25]

            if len(sentences) >= 3:
                summary = (f"{sentences[0]}. "
                          f"{sentences[len(sentences)//2]}. "
                          f"{sentences[-1]}.")
            else:
                summary = text[:1000]

            result = ""
            if topic:
                result += f"Topic: {topic}\n\n"
            result += f"Summary:\n{summary}"
            return result
        except Exception as err:
            return f"❌ Summary failed: {err}"

    # =====================================================
    # AUTO SUMMARY
    # =====================================================
    @staticmethod
    async def auto_summarize_page(topic=None):
        try:
            copy_result = await HeartInput.auto_copy()
            if "❌" in copy_result:
                return copy_result
            await asyncio.sleep(0.1)
            return await HeartInput.summarize_clipboard(topic)
        except Exception as err:
            return f"❌ Auto summary failed: {err}"

    # ====================== NEW: ZOOM FEATURES ======================
    @staticmethod
    async def zoom_in(steps=1):
        try:
            for _ in range(steps):
                await HeartInput.run_sync(pyautogui.hotkey, 'ctrl', '+')
                await asyncio.sleep(0.08)
            return f"✅ Zoomed In ({steps} steps)"
        except Exception as err:
            return f"❌ Zoom In failed: {err}"

    @staticmethod
    async def zoom_out(steps=1):
        try:
            for _ in range(steps):
                await HeartInput.run_sync(pyautogui.hotkey, 'ctrl', '-')
                await asyncio.sleep(0.08)
            return f"✅ Zoomed Out ({steps} steps)"
        except Exception as err:
            return f"❌ Zoom Out failed: {err}"

    @staticmethod
    async def zoom_reset():
        try:
            await HeartInput.run_sync(pyautogui.hotkey, 'ctrl', '0')
            return "✅ Zoom Reset to 100%"
        except Exception as err:
            return f"❌ Zoom Reset failed: {err}"

    # ====================== NEW: WINDOW MANAGEMENT ======================
    @staticmethod
    async def minimize_window():
        try:
            await HeartInput.run_sync(pyautogui.hotkey, 'win', 'down')
            return "✅ Window Minimized"
        except Exception:
            return "❌ Minimize failed"

    @staticmethod
    async def maximize_window():
        try:
            await HeartInput.run_sync(pyautogui.hotkey, 'win', 'up')
            return "✅ Window Maximized"
        except Exception:
            return "❌ Maximize failed"

    @staticmethod
    async def close_window():
        try:
            await HeartInput.run_sync(pyautogui.hotkey, 'alt', 'f4')
            return "✅ Window Closed"
        except Exception:
            return "❌ Close failed"

    # =====================================================
    # MASTER CONTROLLER
    # =====================================================
    @staticmethod
    async def control(action, **kwargs):
        try:
            action = str(action).lower().strip()

            aliases = {
                "select_all": "copy",
                "summarize_page": "auto_summarize",
                "read_page": "auto_summarize",
                "scroll_down": "scroll",
                "scroll_up": "scroll",
                "left_click": "click",
                "typing": "type",
            }
            action = aliases.get(action, action)

            print("\n[HEART ACTION]")
            print("ACTION:", action)
            print("WINDOW:", HeartInput.get_active_window())

            # ==================== EXISTING ACTIONS ====================
            if action == "type":
                return await asyncio.wait_for(
                    HeartInput.type_text(
                        text=kwargs.get("text", ""),
                        x=kwargs.get("x"),
                        y=kwargs.get("y"),
                        clear=kwargs.get("clear", False),
                        enter=kwargs.get("enter", False),
                    ), timeout=10
                )

            elif action == "click":
                return await asyncio.wait_for(
                    HeartInput.click(
                        x=kwargs.get("x"),
                        y=kwargs.get("y"),
                        button=kwargs.get("button", "left"),
                        clicks=kwargs.get("clicks", 1),
                    ), timeout=5
                )

            elif action == "move":
                return await asyncio.wait_for(
                    HeartInput.move_mouse(
                        x=kwargs.get("x"),
                        y=kwargs.get("y"),
                        duration=kwargs.get("duration", 0),
                    ), timeout=5
                )

            elif action == "scroll":
                return await asyncio.wait_for(
                    HeartInput.scroll(
                        direction=kwargs.get("direction", "down"),
                        amount=kwargs.get("amount", 700)
                    ), timeout=5
                )

            elif action == "auto_scroll":
                return await asyncio.wait_for(
                    HeartInput.auto_scroll(
                        duration=kwargs.get("duration", 5),
                        speed=kwargs.get("speed", 500)
                    ), timeout=20
                )

            elif action == "copy":
                return await asyncio.wait_for(HeartInput.auto_copy(), timeout=5)

            elif action == "summary":
                return await asyncio.wait_for(
                    HeartInput.summarize_clipboard(kwargs.get("topic")), timeout=5
                )

            elif action == "auto_summarize":
                return await asyncio.wait_for(
                    HeartInput.auto_summarize_page(kwargs.get("topic")), timeout=10
                )

            elif action == "hotkey":
                keys = kwargs.get("keys", [])
                return await asyncio.wait_for(HeartInput.hotkey(*keys), timeout=5)

            elif action == "press":
                return await asyncio.wait_for(
                    HeartInput.press(kwargs.get("key")), timeout=5
                )

            # ==================== NEW FEATURES ====================
            elif action == "zoom_in":
                return await asyncio.wait_for(
                    HeartInput.zoom_in(kwargs.get("steps", 1)), timeout=6
                )

            elif action == "zoom_out":
                return await asyncio.wait_for(
                    HeartInput.zoom_out(kwargs.get("steps", 1)), timeout=6
                )

            elif action == "zoom_reset":
                return await asyncio.wait_for(HeartInput.zoom_reset(), timeout=5)

            elif action == "minimize":
                return await asyncio.wait_for(HeartInput.minimize_window(), timeout=5)

            elif action == "maximize":
                return await asyncio.wait_for(HeartInput.maximize_window(), timeout=5)

            elif action in ["close", "close_window"]:
                return await asyncio.wait_for(HeartInput.close_window(), timeout=5)

            return f"❌ Unknown action: {action}"

        except asyncio.TimeoutError:
            return "❌ Action timeout"
        except Exception as err:
            return f"❌ Control failed: {err}"