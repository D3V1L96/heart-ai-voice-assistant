
import os
import webbrowser
import subprocess

from mood_engine import detect_mood


SPOTIFY_PATH = os.path.expandvars(
    r"C:\Users\%USERNAME%\AppData\Roaming\Spotify\Spotify.exe"
)

MOOD_PLAYLISTS = {
    "sad": "sad lofi hindi",
    "happy": "party remix",
    "angry": "workout rap",
    "relaxed": "chill lofi",
    "neutral": "lofi music"
}


def handle_music(text: str) -> str:
    """
    Play music on Spotify or YouTube based on mood or keywords.
    """

    text = text.lower().strip()

    mood = detect_mood(text)
    query = MOOD_PLAYLISTS.get(mood, "music")

    # 🎵 Spotify
    if "spotify" in text:
        if os.path.exists(SPOTIFY_PATH):
            subprocess.Popen(SPOTIFY_PATH)
            webbrowser.open(
                f"https://open.spotify.com/search/{query}"
            )
            return "Spotify par music chala rahi hoon."
        else:
            webbrowser.open(
                f"https://www.youtube.com/results?search_query={query}"
            )
            return "Spotify install nahi hai, YouTube par chala rahi hoon."

    # ▶ YouTube
    if "youtube" in text:
        webbrowser.open(
            f"https://www.youtube.com/results?search_query={query}"
        )
        return "YouTube par music chala rahi hoon."

    # 🎧 Default fallback
    webbrowser.open(
        f"https://www.youtube.com/results?search_query={query}"
    )
    return "Music chala rahi hoon."
