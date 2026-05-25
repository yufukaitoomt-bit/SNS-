"""
TikTok Scraper — httpx + yt-dlp のみ（Playwright不使用）
"""

import json
import re
import subprocess
from typing import Dict, List, Optional

import httpx

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
HEADERS = {
    "User-Agent": UA,
    "Accept-Language": "ja-JP,ja;q=0.9,en-US;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Referer": "https://www.tiktok.com/",
}


def _parse_count(text: str) -> int:
    if not text:
        return 0
    t = str(text).strip().replace(",", "")
    try:
        if "万" in t:
            return int(float(t.replace("万", "")) * 10_000)
        if t.upper().endswith("M"):
            return int(float(t[:-1]) * 1_000_000)
        if t.upper().endswith("K"):
            return int(float(t[:-1]) * 1_000)
        return int(float(t))
    except ValueError:
        return 0


def get_follower_count(username: str) -> int:
    try:
        r = httpx.get(
            f"https://www.tiktok.com/@{username}",
            headers=HEADERS,
            follow_redirects=True,
            timeout=12,
        )
        if r.status_code != 200:
            return -1
        m = re.search(r'"followerCount"\s*:\s*(\d+)', r.text)
        if m:
            return int(m.group(1))
        m2 = re.search(r'([\d.,]+[万KM]?)\s*Followers', r.text)
        if m2:
            return _parse_count(m2.group(1))
    except Exception as e:
        print(f"[TikTok] フォロワー取得失敗 @{username}: {e}")
    return -1


def get_user_videos(username: str, max_videos: int = 50) -> List[Dict]:
    try:
        result = subprocess.run(
            [
                "yt-dlp",
                "--dump-json",
                "--flat-playlist",
                f"--playlist-end={max_videos}",
                "--no-warnings",
                f"https://www.tiktok.com/@{username}",
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )
        videos = []
        for line in result.stdout.strip().split("\n"):
            if not line.startswith("{"):
                continue
            try:
                d = json.loads(line)
                videos.append({
                    "id": d.get("id", ""),
                    "title": (d.get("title") or d.get("description") or "")[:120],
                    "play_count": d.get("view_count") or 0,
                    "like_count": d.get("like_count") or 0,
                    "url": d.get("url") or f"https://www.tiktok.com/@{username}/video/{d.get('id','')}",
                })
            except Exception:
                continue
        return videos
    except subprocess.TimeoutExpired:
        print(f"[TikTok] yt-dlp タイムアウト @{username}")
        return []
    except Exception as e:
        print(f"[TikTok] yt-dlp エラー @{username}: {e}")
        return []


def analyze_user(
    username: str,
    viral_threshold: int = 50_000,
    max_videos: int = 50,
) -> Optional[Dict]:
    follower_count = get_follower_count(username)
    videos = get_user_videos(username, max_videos=max_videos)

    if not videos and follower_count < 0:
        return None

    videos.sort(key=lambda v: v["play_count"], reverse=True)
    viral = [v for v in videos if v["play_count"] >= viral_threshold]

    return {
        "username": username,
        "follower_count": follower_count,
        "video_count": len(videos),
        "viral_video_count": len(viral),
        "viral_videos": viral[:10],
        "top_videos": videos[:10],
        "tiktok_url": f"https://www.tiktok.com/@{username}",
    }
