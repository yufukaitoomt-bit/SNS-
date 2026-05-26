"""
TikTok Scraper — httpx + yt-dlp ハイブリッド検索
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

USERNAME_RE = re.compile(r'^[a-zA-Z0-9_.]{2,24}$')


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


def _valid_username(uname: str) -> bool:
    if not uname:
        return False
    if not USERNAME_RE.match(uname):
        return False
    # システム・予約名を除外
    if uname.lower() in {"discover", "foryou", "following", "explore", "live", "search", "tag", "music", "user", "video", "trending"}:
        return False
    return True


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


def _extract_usernames_from_html(text: str) -> List[str]:
    """HTMLから複数のパターンでユーザー名を抽出"""
    found = set()
    # uniqueId パターン（TikTokのSIGI_STATE JSON内）
    for uid in re.findall(r'"uniqueId"\s*:\s*"([^"]+)"', text):
        if _valid_username(uid):
            found.add(uid)
    # author.unique_id パターン
    for uid in re.findall(r'"unique_id"\s*:\s*"([^"]+)"', text):
        if _valid_username(uid):
            found.add(uid)
    # /@username/ パターン（リンク内）
    for uid in re.findall(r'/@([a-zA-Z0-9_.]+)[/?"#]', text):
        if _valid_username(uid):
            found.add(uid)
    return list(found)


def _search_yt_dlp(url: str, max_results: int = 30) -> List[str]:
    """yt-dlp で指定URLからユーザー名を取得"""
    found = set()
    try:
        result = subprocess.run(
            [
                "yt-dlp",
                "--dump-json",
                "--flat-playlist",
                f"--playlist-end={max_results}",
                *YT_DLP_OPTS,
                url,
            ],
            capture_output=True,
            text=True,
            timeout=90,
        )
        for line in result.stdout.strip().split("\n"):
            if not line.startswith("{"):
                continue
            try:
                d = json.loads(line)
                uname = (
                    d.get("uploader_id") or d.get("uploader") or
                    d.get("channel_id") or d.get("channel") or ""
                ).lstrip("@").strip()
                if _valid_username(uname):
                    found.add(uname)
            except Exception:
                continue
    except subprocess.TimeoutExpired:
        print(f"[TikTok] yt-dlp タイムアウト: {url}")
    except Exception as e:
        print(f"[TikTok] yt-dlp エラー {url}: {e}")
    return list(found)


def _search_httpx(url: str) -> List[str]:
    """httpx でHTMLを取得しユーザー名を抽出"""
    try:
        r = httpx.get(url, headers=HEADERS, follow_redirects=True, timeout=20)
        if r.status_code == 200:
            return _extract_usernames_from_html(r.text)
    except Exception as e:
        print(f"[TikTok] httpx エラー {url}: {e}")
    return []


def search_users(query: str, max_results: int = 30) -> List[str]:
    """
    1つのクエリ（#付き/なし両対応）から複数の方法で
    ユーザー名を収集して統合
    """
    q = query.lstrip("#").strip()
    if not q:
        return []

    found = set()

    # 方法1: yt-dlp でハッシュタグページ
    tag_url = f"https://www.tiktok.com/tag/{q}"
    yt_tag = _search_yt_dlp(tag_url, max_results)
    found.update(yt_tag)
    print(f"[TikTok] yt-dlp tag/{q}: +{len(yt_tag)}件 (累計{len(found)})")

    # 方法2: httpx でハッシュタグページのHTML
    httpx_tag = _search_httpx(tag_url)
    new_count = len(set(httpx_tag) - found)
    found.update(httpx_tag)
    print(f"[TikTok] httpx tag/{q}: +{new_count}件 (累計{len(found)})")

    # 方法3: httpx で検索ページのHTML
    search_url = f"https://www.tiktok.com/search?q={q}"
    httpx_search = _search_httpx(search_url)
    new_count = len(set(httpx_search) - found)
    found.update(httpx_search)
    print(f"[TikTok] httpx search?q={q}: +{new_count}件 (累計{len(found)})")

    return list(found)


def find_viral_accounts(
    queries: List[str],
    max_followers: int = 3000,
    min_viral_videos: int = 3,
    viral_threshold: int = 10_000,
    **kwargs,  # 後方互換のためis_hashtagを無視
) -> List[Dict]:
    """低フォロワー×バズ動画多数のアカウントを発掘"""
    seen: set = set()
    candidates: List[str] = []

    for query in queries:
        names = search_users(query)
        print(f"[TikTok] '{query}' → {len(names)}件")
        for name in names:
            if name not in seen:
                seen.add(name)
                candidates.append(name)

    print(f"[TikTok] 候補合計 {len(candidates)} 件 → 詳細分析開始...")
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
