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

YT_DLP_OPTS = [
    "--no-warnings",
    "--user-agent", UA,
]


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
            timeout=15,
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
                *YT_DLP_OPTS,
                f"https://www.tiktok.com/@{username}",
            ],
            capture_output=True,
            text=True,
            timeout=90,
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
    viral_threshold: int = 10_000,
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


def search_hashtag(hashtag: str, max_results: int = 30) -> List[str]:
    """yt-dlp でハッシュタグページからユーザー名を取得"""
    tag = hashtag.lstrip("#")
    try:
        result = subprocess.run(
            [
                "yt-dlp",
                "--dump-json",
                "--flat-playlist",
                f"--playlist-end={max_results}",
                *YT_DLP_OPTS,
                f"https://www.tiktok.com/tag/{tag}",
            ],
            capture_output=True,
            text=True,
            timeout=90,
        )
        usernames: List[str] = []
        seen: set = set()
        for line in result.stdout.strip().split("\n"):
            if not line.startswith("{"):
                continue
            try:
                d = json.loads(line)
                uname = (
                    d.get("uploader_id") or d.get("uploader") or
                    d.get("channel_id") or d.get("channel") or ""
                ).lstrip("@").strip()
                if uname and uname not in seen and "." not in uname:
                    seen.add(uname)
                    usernames.append(uname)
            except Exception:
                continue
        return usernames
    except subprocess.TimeoutExpired:
        print(f"[TikTok] ハッシュタグ検索タイムアウト #{tag}")
        return []
    except Exception as e:
        print(f"[TikTok] ハッシュタグ検索エラー #{tag}: {e}")
        return []


def search_keyword(keyword: str, max_results: int = 30) -> List[str]:
    """yt-dlp でキーワード検索ページからユーザー名を取得"""
    try:
        result = subprocess.run(
            [
                "yt-dlp",
                "--dump-json",
                "--flat-playlist",
                f"--playlist-end={max_results}",
                *YT_DLP_OPTS,
                f"https://www.tiktok.com/search/video?q={keyword}",
            ],
            capture_output=True,
            text=True,
            timeout=90,
        )
        usernames: List[str] = []
        seen: set = set()
        for line in result.stdout.strip().split("\n"):
            if not line.startswith("{"):
                continue
            try:
                d = json.loads(line)
                uname = (
                    d.get("uploader_id") or d.get("uploader") or
                    d.get("channel_id") or d.get("channel") or ""
                ).lstrip("@").strip()
                if uname and uname not in seen and "." not in uname:
                    seen.add(uname)
                    usernames.append(uname)
            except Exception:
                continue
        return usernames
    except subprocess.TimeoutExpired:
        print(f"[TikTok] キーワード検索タイムアウト: {keyword}")
        return []
    except Exception as e:
        print(f"[TikTok] キーワード検索エラー: {keyword}: {e}")
        return []


def find_viral_accounts(
    queries: List[str],
    max_followers: int = 3000,
    min_viral_videos: int = 3,
    viral_threshold: int = 10_000,
    is_hashtag: bool = True,
) -> List[Dict]:
    """ハッシュタグ/キーワードで候補収集 → 低フォロワー×バズアカウントを発掘"""
    seen: set = set()
    candidates: List[str] = []

    for query in queries:
        names = search_hashtag(query) if is_hashtag else search_keyword(query)
        print(f"[TikTok] {'#' if is_hashtag else ''}{query} → {len(names)}件")
        for name in names:
            if name not in seen:
                seen.add(name)
                candidates.append(name)

    print(f"[TikTok] 候補 {len(candidates)} 件 → 詳細分析開始...")
    results = []

    for uname in candidates:
        profile = analyze_user(uname, viral_threshold=viral_threshold)
        if not profile:
            continue
        followers = profile["follower_count"]
        if followers != -1 and followers > max_followers:
            print(f"  スキップ @{uname} フォロワー{followers:,}")
            continue
        if profile["viral_video_count"] >= min_viral_videos:
            results.append(profile)
            print(
                f"  ✅ @{uname} "
                f"フォロワー{followers:,} "
                f"バズ{profile['viral_video_count']}本"
            )

    results.sort(key=lambda x: x["viral_video_count"], reverse=True)
    return results
