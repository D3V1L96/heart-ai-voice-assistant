
import os


def handle_system(action: str) -> str:
    """
    action: shutdown | restart | lock
    """

    action = action.lower().strip()

    if action == "shutdown":
        os.system("shutdown /s /t 1")
        return "System shutdown ho raha hai."

    elif action == "restart":
        os.system("shutdown /r /t 1")
        return "System restart ho raha hai."

    elif action == "lock":
        os.system("rundll32.exe user32.dll,LockWorkStation")
        return "System lock kar diya gaya hai."

    else:
        return "System command samajh nahi aaya."
