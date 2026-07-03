# whatsapp_file_sender.py
# Separate tool for sending files via Desktop WhatsApp with full drive scanning

import os
import time
import pyautogui


def scan_all_drives_for_file(file_name: str) -> str:
    """
    Scan all installed drives to find the file.
    Returns full path if found, else error message.
    """
    drives = []
    for d in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
        drive_path = f"{d}:\\"
        if os.path.exists(drive_path):
            drives.append(drive_path)

    if not drives:
        return "No drives found on this system."

    print(f"Scanning drives: {', '.join(drives)}")

    found_paths = []
    for drive in drives:
        for root, dirs, files in os.walk(drive):
            if file_name in files:
                full_path = os.path.join(root, file_name)
                found_paths.append(full_path)
                print(f"Found: {full_path}")

    if not found_paths:
        return f"File '{file_name}' not found on any drive."

    if len(found_paths) == 1:
        return found_paths[0]  # single file → use this

    # Multiple files → return list for user to choose
    paths_str = "\n".join([f"{i + 1}. {p}" for i, p in enumerate(found_paths)])
    return f"Multiple files found:\n{paths_str}\nWhich one to send? (reply with number)"


def send_file_via_desktop_whatsapp(contact_name: str, file_path: str) -> str:
    """
    Send the file using Desktop WhatsApp automation.
    """
    try:
        # Open WhatsApp Desktop
        pyautogui.hotkey('win', 's')
        time.sleep(1)
        pyautogui.write('whatsapp')
        time.sleep(1)
        pyautogui.press('enter')
        time.sleep(8)  # Wait for full open

        # Search contact
        pyautogui.hotkey('ctrl', 'f')
        time.sleep(1.5)
        pyautogui.write(contact_name)
        time.sleep(3)
        pyautogui.press('enter')
        time.sleep(5)  # chat open

        # Attach → Document
        pyautogui.moveTo(800, 1050)  # Adjust: paperclip icon
        time.sleep(0.8)
        pyautogui.click()
        time.sleep(1.5)

        pyautogui.moveTo(800, 900)  # Adjust: Document option
        time.sleep(0.8)
        pyautogui.click()
        time.sleep(3)

        # Type file path
        pyautogui.write(file_path)
        time.sleep(2)
        pyautogui.press('enter')
        time.sleep(4)

        # Send
        pyautogui.moveTo(1400, 1050)  # Adjust: Send button
        time.sleep(0.8)
        pyautogui.click()
        time.sleep(2)

        return f"File sent to {contact_name} successfully! 📤"

    except Exception as e:
        return f"Send failed: {str(e)}\nTips:\n- WhatsApp Desktop must be open & linked\n- Screen visible\n- Run as admin\n- Adjust coordinates if needed"


# Example usage (for testing this file alone)
if __name__ == "__main__":
    file_name = input("Enter file name to search & send: ")
    contact = input("Enter contact name: ")

    path_result = scan_all_drives_for_file(file_name)

    if "Multiple files found" in path_result:
        print(path_result)
        choice = int(input("Enter number: ")) - 1
        path_result = path_result.split("\n")[choice + 1].split(". ", 1)[1]  # extract path

    elif "not found" in path_result:
        print(path_result)
    else:
        print(f"Found: {path_result}")
        result = send_file_via_desktop_whatsapp(contact, path_result)
        print(result)
