from livekit.agents.llm import function_tool
from livekit.agents import RunContext
import time
import pyautogui
import pygetwindow as gw
import asyncio

# =========================================================
# SAFETY CONFIG
# =========================================================
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.4


# =========================================================
# HEART TOOLS CLASS - LIVEKIT READY
# =========================================================
class HeartTools:

    def _activate_whatsapp(self) -> bool:
        """Internal helper to reliably focus WhatsApp window"""
        try:
            possible_titles = ["WhatsApp", "WhatsApp Desktop"]
            for title in possible_titles:
                windows = gw.getWindowsWithTitle(title)
                if windows:
                    win = windows[0]
                    if win.isMinimized:
                        win.restore()
                    win.activate()
                    time.sleep(1.3)
                    try:
                        win.maximize()
                    except:
                        pass
                    return True
            return False
        except:
            return False

    # =====================================================
    # MAIN FUNCTION - RECOMMENDED
    # =====================================================
    @function_tool(
        name="send_whatsapp_desktop",
        description="""Send a message using WhatsApp Desktop application.
        It will open WhatsApp if not opened, search for the contact, and send the message.
        Contact name should be exactly as saved in WhatsApp (e.g. Mummy, Jaan, Amit, Boss)."""
    )
    async def send_whatsapp_desktop(
            self,
            context: RunContext,
            contact_name: str,
            message: str
    ) -> str:
        """Send message via WhatsApp Desktop"""
        _ = context  # Required by LiveKit

        try:
            def _perform_send():
                # Step 1: Ensure WhatsApp is open and focused
                if not self._activate_whatsapp():
                    # Fallback: Open via Windows Search
                    pyautogui.hotkey('win', 's')
                    time.sleep(1.2)
                    pyautogui.write('whatsapp')
                    time.sleep(1.0)
                    pyautogui.press('enter')
                    time.sleep(6.5)  # Wait for app to load

                self._activate_whatsapp()
                time.sleep(2.5)

                # Step 2: Open search bar and clear it
                pyautogui.hotkey('ctrl', 'f')
                time.sleep(1.0)
                pyautogui.hotkey('ctrl', 'a')
                pyautogui.press('backspace')
                time.sleep(0.7)

                # Step 3: Type contact name
                pyautogui.write(contact_name)
                time.sleep(2.8)

                # Step 4: Select first result
                pyautogui.press('down')
                time.sleep(0.8)
                pyautogui.press('enter')
                time.sleep(2.5)

                # Step 5: Type and send message
                pyautogui.write(message)
                time.sleep(0.8)
                pyautogui.press('enter')
                time.sleep(1.2)

                return True, f"Message sent successfully to '{contact_name}'"

            # Run GUI automation in a separate thread (non-blocking)
            success, result_msg = await asyncio.to_thread(_perform_send)

            if success:
                return f"✅ {result_msg}"
            else:
                return f"❌ {result_msg}"

        except Exception as e:
            return f"❌ Failed to send WhatsApp message: {str(e)}\nMake sure WhatsApp Desktop is installed and your phone is linked."

    # =====================================================
    # INDIVIDUAL FUNCTIONS (Optional)
    # =====================================================
    @function_tool
    async def open_whatsapp(self) -> tuple[bool, str]:
        """Open WhatsApp Desktop"""
        try:
            def _open():
                if not self._activate_whatsapp():
                    pyautogui.hotkey('win', 's')
                    time.sleep(1.2)
                    pyautogui.write('whatsapp')
                    time.sleep(1)
                    pyautogui.press('enter')
                    time.sleep(6)
                self._activate_whatsapp()
                time.sleep(2)
                return True, "WhatsApp opened successfully"

            return await asyncio.to_thread(_open)
        except Exception as e:
            return False, f"Failed to open WhatsApp: {str(e)}"

    @function_tool
    async def send_message(self, message: str) -> tuple[bool, str]:
        """Send message to currently active chat"""
        try:
            def _send():
                if not self._activate_whatsapp():
                    return False, "Could not activate WhatsApp"
                pyautogui.write(message)
                time.sleep(0.7)
                pyautogui.press('enter')
                time.sleep(1)
                return True, "Message sent"

            return await asyncio.to_thread(_send)
        except Exception as e:
            return False, f"Failed to send message: {str(e)}"


# ====================== FOR TESTING ======================
if __name__ == "__main__":
    tools = HeartTools()
    print("🧪 Testing WhatsApp Desktop Tool...\n")

    contact = input("Enter contact name: ")
    message = "Hello! This is a test message from LiveKit automation."

    # Run async function in sync test
    import asyncio

    result = asyncio.run(tools.send_whatsapp_desktop(None, contact, message))
    print(result)