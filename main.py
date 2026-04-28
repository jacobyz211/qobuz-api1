import hashlib
import time
import os
import httpx
import uvicorn
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from typing import Optional

load_dotenv()

APP_ID = os.getenv("QOBUZ_APP_ID")
APP_SECRET = os.getenv("QOBUZ_APP_SECRET")
EMAIL = os.getenv("QOBUZ_EMAIL")
PASSWORD_MD5 = os.getenv("QOBUZ_PASSWORD_MD5")
COUNTRY_CODE = os.getenv("COUNTRY_CODE", "US")

BASE = "https://www.qobuz.com/api.json/0.2"

auth_token: Optional[str] = None

app = FastAPI(title="Qobuz API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


async def login():
    global auth_token
    async with httpx.AsyncClient() as client:
        r = await client.post(f"{BASE}/user/login", params={
            "username": EMAIL,
            "password": PASSWORD_MD5,
            "app_id": APP_ID
        })
        if r.status_code != 200:
            raise HTTPException(status_code=401, detail="Qobuz login failed")
        data = r.json()
        auth_token = data["user_auth_token"]


async def get_token() -> str:
    global auth_token
    if not auth_token:
        await login()
    return auth_token


def stream_sig(track_id: str, format_id: int, ts: str) -> str:
    raw = f"trackgetFileUrlformat_id{format_id}intentstreamtrack_id{track_id}{ts}{APP_SECRET}"
    return hashlib.md5(raw.encode()).hexdigest()


@app.get("/")
async def index():
    return {"service": "qobuz-api", "status": "ok"}


@app.get("/search")
async def search(q: str = Query(...), limit: int = 20):
    token = await get_token()
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{BASE}/catalog/search", params={
            "query": q,
            "limit": limit,
            "app_id": APP_ID,
            "user_auth_token": token
        })
        if r.status_code == 401:
            await login()
            token = await get_token()
            r = await client.get(f"{BASE}/catalog/search", params={
                "query": q,
                "limit": limit,
                "app_id": APP_ID,
                "user_auth_token": token
            })
        r.raise_for_status()
        return r.json()


@app.get("/track/{track_id}")
async def get_track(track_id: str):
    token = await get_token()
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{BASE}/track/get", params={
            "track_id": track_id,
            "app_id": APP_ID,
            "user_auth_token": token
        })
        if r.status_code == 401:
            await login()
            token = await get_token()
            r = await client.get(f"{BASE}/track/get", params={
                "track_id": track_id,
                "app_id": APP_ID,
                "user_auth_token": token
            })
        r.raise_for_status()
        return r.json()


@app.get("/stream/{track_id}")
async def stream(
    track_id: str,
    format_id: int = Query(default=27, description="27=HiRes 192kHz, 7=HiRes 96kHz, 6=FLAC 16-bit, 5=MP3 320")
):
    token = await get_token()
    ts = str(int(time.time()))
    sig = stream_sig(track_id, format_id, ts)
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{BASE}/track/getFileUrl", params={
            "track_id": track_id,
            "format_id": format_id,
            "intent": "stream",
            "request_ts": ts,
            "request_sig": sig,
            "app_id": APP_ID,
            "user_auth_token": token
        })
        if r.status_code == 401:
            await login()
            token = await get_token()
            ts = str(int(time.time()))
            sig = stream_sig(track_id, format_id, ts)
            r = await client.get(f"{BASE}/track/getFileUrl", params={
                "track_id": track_id,
                "format_id": format_id,
                "intent": "stream",
                "request_ts": ts,
                "request_sig": sig,
                "app_id": APP_ID,
                "user_auth_token": token
            })
        r.raise_for_status()
        return r.json()


@app.get("/album/{album_id}")
async def get_album(album_id: str):
    token = await get_token()
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{BASE}/album/get", params={
            "album_id": album_id,
            "app_id": APP_ID,
            "user_auth_token": token
        })
        if r.status_code == 401:
            await login()
            token = await get_token()
            r = await client.get(f"{BASE}/album/get", params={
                "album_id": album_id,
                "app_id": APP_ID,
                "user_auth_token": token
            })
        r.raise_for_status()
        return r.json()


@app.get("/artist/{artist_id}")
async def get_artist(artist_id: str, limit: int = 25):
    token = await get_token()
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{BASE}/artist/get", params={
            "artist_id": artist_id,
            "limit": limit,
            "app_id": APP_ID,
            "user_auth_token": token
        })
        if r.status_code == 401:
            await login()
            token = await get_token()
            r = await client.get(f"{BASE}/artist/get", params={
                "artist_id": artist_id,
                "limit": limit,
                "app_id": APP_ID,
                "user_auth_token": token
            })
        r.raise_for_status()
        return r.json()


@app.get("/playlist/{playlist_id}")
async def get_playlist(playlist_id: str):
    token = await get_token()
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{BASE}/playlist/get", params={
            "playlist_id": playlist_id,
            "app_id": APP_ID,
            "user_auth_token": token
        })
        if r.status_code == 401:
            await login()
            token = await get_token()
            r = await client.get(f"{BASE}/playlist/get", params={
                "playlist_id": playlist_id,
                "app_id": APP_ID,
                "user_auth_token": token
            })
        r.raise_for_status()
        return r.json()


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
