import keyboard


def handle_media(action: str) -> str:
    """
    Control media playback:
    play | pause | play_pause | next | previous
    """

    action = action.lower().strip()

    if action in ["play", "pause", "play_pause"]:
        keyboard.send("play/pause media")
        return "Media play/pause kiya gaya."

    elif action == "next":
        keyboard.send("next track")
        return "Next song chala diya."

    elif action == "previous":
        keyboard.send("previous track")
        return "Previous song chala diya."

    else:
        return "Media command samajh nahi aaya."
