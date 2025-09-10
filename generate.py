import os
import requests
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("API_KEY")   # make sure it's set in .env

BASE_URL = "https://api.elevenlabs.io/v1/music"

def generate_music_from_prompt(prompt: str, output_file: str = "generated_music.mp3") -> str | None:
    headers = {
        "xi-api-key": API_KEY,
        "Content-Type": "application/json"
    }

    payload = {
        "prompt": prompt,
        "music_length_ms": 30_000,   # milliseconds
        "model_id": "music_v1"
    }

    params = {
        "output_format": "mp3_44100_128"
    }

    resp = requests.post(BASE_URL, headers=headers, params=params, json=payload, stream=True)

    if resp.status_code != 200:
        try:
            return f"Error: {resp.status_code} - {resp.json()}"
        except:
            return f"Error: {resp.status_code} - {resp.text}"

    # Check if response is audio
    if resp.headers.get("Content-Type", "").startswith("audio/"):
        with open(output_file, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        return output_file

    # Otherwise return JSON error/debug info
    try:
        return f"API returned JSON instead of audio: {resp.json()}"
    except:
        return None
