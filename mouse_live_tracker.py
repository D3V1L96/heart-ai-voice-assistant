import os
import shutil
import time
from datetime import datetime
from typing import Tuple

import pyautogui


class WhatsAppDesktopAutomation:
    """Clean, robust, and production-ready WhatsApp Desktop automation."""

    def __init__(self, delay: float = 0.8):
        pyautogui.FAILSAFE = True
        self.delay = delay
        self.whatsapp_title = "WhatsApp"

    # ====================== BACKUP ======================
    def _create_backup(self, full_path: str) -> Tuple[bool, str]:
        """Create timestamped backup before modification."""
        if not os.path.exists(full_path):
            return False, "No backup needed (file did not exist)"

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base, ext = os.path.splitext(full_path)
        backup_path = f"{base}_backup_{timestamp}{ext}"

        try:
            shutil.copy2(full_path, backup_path)
            if os.path.exists(backup_path) and os.path.getsize(backup_path) > 0:
                return True, f"Backup created: {os.path.basename(backup_path)}"
            return False, "Backup verification failed"
        except Exception as e:
            return False, f"Backup failed: {str(e)}"

    # ====================== HELPERS ======================
    def _open_whatsapp(self) -> bool:
        """Open WhatsApp Desktop and bring it to front."""
        try:
            # Search and open via Windows Start
            pyautogui.hotkey('win', 's')
            time.sleep(0.8)
            pyautogui.write('whatsapp')
            time.sleep(0.7)
            pyautogui.press('enter')
            time.sleep(4.5)  # Wait for launch

            # Bring window to front
            self._bring_to_front()
            return True
        except Exception:
            return False

    def _bring_to_front(self) -> bool:
        """Maximize and activate WhatsApp window."""
        try:
            import pygetwindow as gw
            windows = gw.getWindowsWithTitle(self.whatsapp_title)
            for win in windows:
                if win.title.strip():
                    if win.isMinimized:
                        win.restore()
                    win.activate()
                    time.sleep(0.6)
                    win.maximize()
                    time.sleep(1.2)
                    return True
            return False
        except ImportError:
            # Fallback
            pyautogui.hotkey('alt', 'tab')
            time.sleep(1.0)
            return True
        except Exception:
            return False

    def _search_and_open_contact(self, contact_name: str) -> bool:
        """Search and open contact/chat."""
        try:
            # Focus search
            pyautogui.hotkey('ctrl', 'f')
            time.sleep(self.delay)

            # Clear previous text
            pyautogui.hotkey('ctrl', 'a')
            pyautogui.press('backspace')
            time.sleep(0.4)

            pyautogui.write(contact_name, interval=0.05)
            time.sleep(2.0)

            pyautogui.press('enter')
            time.sleep(2.5)
            return True
        except Exception:
            return False

    def _send_message(self, message: str) -> bool:
        """Type and send the message."""
        try:
            pyautogui.write(message, interval=0.03)
            time.sleep(0.7)
            pyautogui.press('enter')
            time.sleep(1.0)
            return True
        except Exception:
            return False

    # ====================== MAIN FUNCTION ======================
    @function_tool(
        name="send_whatsapp_desktop",
        description="""
        Send message via Desktop WhatsApp app.
        WhatsApp Desktop must be installed and phone linked.
        """
    )
    async def send_whatsapp_desktop(
        self,
        context,
        contact_name: str,
        message: str
    ) -> str:

        _ = context  # Unused context

        # Validation
        contact_name = contact_name.strip()
        message = message.strip()

        if not contact_name:
            return "Error: Contact name cannot be empty."
        if not message:
            return "Error: Message cannot be empty."

        try:
            # Open WhatsApp
            if not self._open_whatsapp():
                return "Failed to open WhatsApp Desktop. Please make sure it is installed."

            # Search & open contact
            if not self._search_and_open_contact(contact_name):
                return f"Could not find contact: {contact_name}"

            # Send message
            if not self._send_message(message):
                return "Failed to send the message."

            return (
                f"✅ Message sent successfully!\n\n"
                f"Contact: {contact_name}\n"
                f"Message: {message}"
            )

        except pyautogui.FailSafeException:
            return "❌ Automation stopped by user (mouse moved to corner)."
        except Exception as e:
            return f"❌ WhatsApp automation failed: {str(e)}\n\nMake sure WhatsApp Desktop is visible and linked."


# For direct testing
if __name__ == "__main__":
    wa = WhatsAppDesktopAutomation(delay=0.75)
    result = wa.send_whatsapp_desktop(None, "Test Contact", "Hi, this is a test from automation!")
    print(result)