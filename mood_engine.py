def detect_mood(text: str) -> str:
    t = text.lower()

    if any(word in t for word in ["sad", "udasi", "dukhi", "tut gaya", "mood kharab"]):
        return "sad"

    if any(word in t for word in ["khush", "happy", "masti", "mazedaar", "mast"]):
        return "happy"

    if any(word in t for word in ["gussa", "naraz", "bhadka hua", "angry"]):
        return "angry"

    if any(word in t for word in ["thanda", "shant", "calm", "relaxed", "aaraam"]):
        return "relaxed"

    if any(word in t for word in ["dar", "fear", "darr lag raha", "scared"]):
        return "fear"

    return "neutral"
