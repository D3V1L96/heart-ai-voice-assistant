import os
from datetime import datetime
import pytz
from serpapi import GoogleSearch
from dotenv import load_dotenv

# ───────────────────────────────────────────────
#  1. Load environment variables
# ───────────────────────────────────────────────

# Try to load from .env.local (most common name in your project)
success = load_dotenv(".env.local")

# Fallback: also try the more standard name .env
if not success:
    success = load_dotenv(".env")

# ───────────────────────────────────────────────
#  2. Get API key + immediate debug output
# ───────────────────────────────────────────────

API_KEY = os.getenv("SERPAPI_API_KEY")

print("═══════════════════════════════════════════════")
print("          DEBUG INFORMATION (do not remove yet)")
print("═══════════════════════════════════════════════")
print(f"Current working directory : {os.getcwd()}")
print(f".env.local exists?        : {os.path.exists('.env.local')}")
print(f".env exists?              : {os.path.exists('.env')}")
print(f"python-dotenv loaded file : {'successfully' if success else 'NOT found'}")
print(f"SERPAPI_API_KEY value     : {API_KEY!r}")
print("═══════════════════════════════════════════════\n")

# ───────────────────────────────────────────────
#  Functions
# ───────────────────────────────────────────────

def get_current_datetime(timezone_str="Asia/Kolkata") -> str:
    tz = pytz.timezone(timezone_str)
    now = datetime.now(tz)
    date_str = now.strftime("%d %B %Y")
    time_str = now.strftime("%I:%M %p")
    return f"Aaj ki taareekh hai {date_str} aur waqt hai {time_str}."


def search_google_with_sources(query: str, num_results: int = 3) -> str:
    if not API_KEY:
        return (
            "Search API key configured nahi hai.\n\n"
            "Possible reasons & fixes:\n"
            "  • File .env.local (or .env) is missing or in wrong folder\n"
            "  • File contains wrong format → should be exactly:\n"
            "    SERPAPI_API_KEY=1f693f5d4665b1344fad47eb010d0222f1ef0e94241fb63ce4a84b1b685b3431\n"
            "    (no quotes, no spaces around =)\n"
            "  • PyCharm / terminal was not restarted after creating .env file\n"
            "  • You are using the wrong package (must be google-search-results)\n\n"
            "Run the script again and look at the DEBUG block above."
        )

    params = {
        "engine": "google",
        "q": query,
        "api_key": API_KEY,
        "num": num_results,
    }

    try:
        search = GoogleSearch(params)
        results = search.get_dict()

        if "error" in results:
            return f"SerpApi returned an error:\n{results['error']}"

        organic = results.get("organic_results", [])
        if not organic:
            return "Koi organic results nahi mile."

        lines = []
        for i, item in enumerate(organic[:num_results], 1):
            title   = item.get("title",   "—")
            snippet = item.get("snippet", "—")
            link    = item.get("link",    "—")
            lines.append(f"{i}. {title}")
            lines.append(f"   {snippet}")
            lines.append(f"   Source: {link}")
            lines.append("")

        lines.append("Aap upar diye gaye links par click karke asli source check kar sakte hain.")
        return "\n".join(lines)

    except Exception as e:
        return f"Exception during search: {type(e).__name__}: {e}"


async def handle_search_query(user_query: str) -> str:
    datetime_info = get_current_datetime()
    search_results = search_google_with_sources(user_query)
    return f"{datetime_info}\n\nSearch results for \"{user_query}\":\n\n{search_results}"


# ───────────────────────────────────────────────
#  Main (for direct running)
# ───────────────────────────────────────────────

if __name__ == "__main__":
    import asyncio

    query = "heart AI assistant features"
    # query = "best places to visit in Himachal Pradesh"

    result = asyncio.run(handle_search_query(query))
    print(result)