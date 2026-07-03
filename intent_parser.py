def detect_intent(text: str) -> dict:
    t = text.lower()

    # ===== SYSTEM =====
    if "shutdown" in t:
        return {"category": "system", "action": "shutdown"}

    if "restart" in t:
        return {"category": "system", "action": "restart"}

    if "lock" in t:
        return {"category": "system", "action": "lock"}

    # ===== MEDIA KEYS =====
    if "pause" in t or "resume" in t:
        return {"category": "media", "action": "play_pause"}

    if "next song" in t:
        return {"category": "media", "action": "next"}

    if "previous song" in t:
        return {"category": "media", "action": "previous"}

    # ===== MUSIC SEARCH =====
    if "play" in t and "music" in t:
        return {
            "category": "music",
            "text": t
        }

    if "play song" in t:
        return {
            "category": "music",
            "text": t
        }

    # ===== APPLICATION CONTROL =====
    if t.startswith("open"):
        return {
            "category": "apps",
            "action": "open",
            "name": t.replace("open", "").strip()
        }

    if t.startswith("close"):
        return {
            "category": "apps",
            "action": "close",
            "name": t.replace("close", "").strip()
        }

    # ===== TIME =====
    if "time" in t:
        return {"category": "time"}

    # ===== CODING =====
    if "write code" in t or "code likho" in t:
        return {"category": "coding"}
    # ===== INSTALL APP =====
    if "install" in t:
        return {
            "category": "apps",
            "action": "install",
            "name": t.replace("install", "").strip()
        }

    # ===== UNINSTALL APP =====
    if "uninstall" in t or "remove" in t:
        return {
            "category": "apps",
            "action": "uninstall",
            "name": t.replace("uninstall", "").replace("remove", "").strip()
        }
    if "create file" in t:
        return {"category": "files", "action": "create", "path": "newfile.txt"}

    if "delete file" in t:
        return {"category": "files", "action": "delete", "path": "test.txt"}
    if "merge pdf" in t:
        return {"category": "pdf", "action": "merge"}

    if "summarize pdf" in t:
        return {"category": "pdf", "action": "summarize"}

    # ===== FALLBACK =====
    return {"category": "unknown"}
