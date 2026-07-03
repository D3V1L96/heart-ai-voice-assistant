import subprocess
import time
import pyautogui
from livekit.agents.llm import function

# -------------------------
# OPEN WHATSAPP
# -------------------------

def open_whatsapp():
    subprocess.Popen("whatsapp:")
    time.sleep(10)

# -------------------------
# SEARCH CONTACT
# -------------------------

def search_contact(name: str):
    pyautogui.hotkey("ctrl", "f")
    time.sleep(1)
    pyautogui.write(name)
    time.sleep(2)
    pyautogui.press("enter")
    time.sleep(2)

# -------------------------
# SEND MESSAGE
# -------------------------

def send_message(contact: str, message: str):
    open_whatsapp()
    search_contact(contact)
    pyautogui.write(message)
    time.sleep(1)
    pyautogui.press("enter")
    return f"Sir, {contact} ko message bhej diya."

# -------------------------
# MAIN HANDLER
# -------------------------

@function
async def handle_whatsapp(intent: dict):
    contact = intent.get("contact")
    message = intent.get("message")

    if not contact:
        return "Sir, contact name batao."

    if not message:
        return "Sir, kya message bhejna hai?"

    return send_message(contact, message)
