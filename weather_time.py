
import os
import aiohttp
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("a69a65c46bf547aff0e7165ca485d9c6")
BASE_URL = "https://api.openweathermap.org/data/2.5/weather"


# ----------------------------
# TIME
# ----------------------------

def get_time():
    now = datetime.now()
    return now.strftime("%H:%M")


def get_date():
    today = datetime.now()
    return today.strftime("%d %B %Y")


# ----------------------------
# WEATHER
# ----------------------------

async def fetch_weather(city: str) -> str:
    if not API_KEY:
        return "OpenWeather API key set nahi hai."

    params = {
        "q": city,
        "appid": API_KEY,
        "units": "metric",
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(BASE_URL, params=params) as resp:
            if resp.status != 200:
                return "City ka weather nahi mil paaya."
            data = await resp.json()

    weather_desc = data["weather"][0]["description"]
    temp = data["main"]["temp"]
    humidity = data["main"]["humidity"]

    return (
        f"{city} ka mausam {weather_desc} hai. "
        f"Temperature {temp}°C aur humidity {humidity}% hai."
    )


# ----------------------------
# HANDLER (Router Entry)
# ----------------------------

async def handle_time(text: str) -> str:
    text = text.lower()

    if "time" in text:
        return f"Abhi time hai {get_time()}"

    if "date" in text:
        return f"Aaj ki date hai {get_date()}"

    if "weather" in text:
        city = extract_city(text)
        return await fetch_weather(city)

    return "Aap time, date ya weather pooch sakte hain."


# ----------------------------
# CITY EXTRACTOR
# ----------------------------

def extract_city(text: str) -> str:
    words = text.split()
    ignore = ["weather", "in", "at", "ka", "hai", "tell", "me"]

    for w in words:
        if w not in ignore and len(w) > 2:
            return w.capitalize()

    return "Delhi"
