"""
TikTok Scraper — 多段検索（yt-dlp + httpx + JSON深層解析）
"""

import json
import re
import subprocess
import time
from typing import Dict, List, Optional, Set

import httpx

# ─── User-Agent 群 ────────────────────────────────────────────────
UA_DESKTOP = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
UA_MOBILE = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
)
UA_ANDROID = (
    "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36"
)

UAS = [
    ("desktop", UA_DESKTOP),
    ("mobile", UA_MOBILE),
    ("android", UA_ANDROID),
]


def _headers(ua: str) -> dict:
    return {
        "User-Agent": ua,
        "Accept-Language": "ja-JP,ja;q=0.9,en-US;q=0.8",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Referer": "https://www.tiktok.com/",
        "Cache-Control": "no-cache",
    }


HEADERS = _headers(UA_DESKTOP)
YT_DLP_OPTS = ["--no-warnings", "--user-agent", UA_DESKTOP]

USERNAME_RE = re.compile(r"^[a-zA-Z0-9_.]{2,24}$")
RESERVED_NAMES = {
    "discover", "foryou", "following", "explore", "live", "search",
    "tag", "music", "user", "video", "trending", "about", "login",
    "signup", "embed", "share", "challenge", "feedback", "help", "legal",
    "terms", "privacy", "community-guidelines", "creators", "business",
    "ads", "effects", "stickers", "sounds", "media", "static", "node",
    "passport", "verify", "feed", "tiktok", "www", "m", "vm",
}


def _valid_username(uname: str) -> bool:
    if not uname:
        return False
    uname = uname.strip().lstrip("@")
    if not USERNAME_RE.match(uname):
        return False
    if uname.lower() in RESERVED_NAMES:
        return False
    return True


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


# ─── フォロワー数取得（複数UA試行） ───────────────────────────────
def get_follower_count(username: str) -> int:
    for ua_label, ua in UAS:
        try:
            r = httpx.get(
                f"https://www.tiktok.com/@{username}",
                headers=_headers(ua),
                follow_redirects=True,
                timeout=15,
            )
            if r.status_code != 200:
                continue
            m = re.search(r'"followerCount"\s*:\s*(\d+)', r.text)
            if m:
                return int(m.group(1))
            m2 = re.search(r'([\d.,]+[万KM]?)\s*Followers', r.text)
            if m2:
                return _parse_count(m2.group(1))
        except Exception:
            continue
    return -1


# ─── 動画一覧取得 ─────────────────────────────────────────────────
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


# ─── ユーザー名抽出（JSON深層走査 + 正規表現） ───────────────────
def _walk_json_for_usernames(obj, found: Set[str]) -> None:
    """JSON構造を再帰的に探索してユーザー名を収集"""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in ("uniqueId", "unique_id", "authorUniqueId") and isinstance(v, str):
                if _valid_username(v):
                    found.add(v.lstrip("@"))
            elif isinstance(v, (dict, list)):
                _walk_json_for_usernames(v, found)
    elif isinstance(obj, list):
        for item in obj:
            _walk_json_for_usernames(item, found)


def _extract_usernames_from_html(text: str) -> List[str]:
    """HTMLから可能な限り多くのパターンでユーザー名を抽出"""
    found: Set[str] = set()

    # A. __UNIVERSAL_DATA_FOR_REHYDRATION__ (現行TikTok)
    for m in re.finditer(
        r'<script[^>]*id="__UNIVERSAL_DATA_FOR_REHYDRATION__"[^>]*>(.+?)</script>',
        text,
        re.DOTALL,
    ):
        try:
            _walk_json_for_usernames(json.loads(m.group(1)), found)
        except Exception:
            pass

    # B. SIGI_STATE (旧形式)
    for m in re.finditer(
        r'<script[^>]*id="SIGI_STATE"[^>]*>(.+?)</script>',
        text,
        re.DOTALL,
    ):
        try:
            _walk_json_for_usernames(json.loads(m.group(1)), found)
        except Exception:
            pass

    # C. JSON-LD
    for m in re.finditer(
        r'<script[^>]*type="application/ld\+json"[^>]*>(.+?)</script>',
        text,
        re.DOTALL,
    ):
        try:
            _walk_json_for_usernames(json.loads(m.group(1)), found)
        except Exception:
            pass

    # D. 正規表現フォールバック（あらゆるパターン）
    patterns = [
        r'"uniqueId"\s*:\s*"([^"]+)"',
        r'"unique_id"\s*:\s*"([^"]+)"',
        r'"authorUniqueId"\s*:\s*"([^"]+)"',
        r'/@([a-zA-Z0-9_.]+)[/?"#\s]',
        r'href="[^"]*/@([a-zA-Z0-9_.]+)',
        r'tiktok\.com/@([a-zA-Z0-9_.]+)',
    ]
    for pattern in patterns:
        for uid in re.findall(pattern, text):
            if _valid_username(uid):
                found.add(uid.lstrip("@"))

    return list(found)


# ─── yt-dlp 検索 ──────────────────────────────────────────────────
def _search_yt_dlp(url: str, max_results: int = 30) -> List[str]:
    found: Set[str] = set()
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
                # 関連動画のauthorも抽出
                if "entries" in d:
                    _walk_json_for_usernames(d["entries"], found)
            except Exception:
                continue
    except subprocess.TimeoutExpired:
        print(f"[TikTok] yt-dlp タイムアウト: {url}")
    except Exception as e:
        print(f"[TikTok] yt-dlp エラー {url}: {e}")
    return list(found)


# ─── httpx 検索（複数UA試行） ─────────────────────────────────────
def _search_httpx(url: str) -> List[str]:
    """各UAで試行して最も多くの結果が取れたものを採用"""
    best: List[str] = []
    for ua_label, ua in UAS:
        try:
            r = httpx.get(
                url,
                headers=_headers(ua),
                follow_redirects=True,
                timeout=20,
            )
            if r.status_code == 200:
                names = _extract_usernames_from_html(r.text)
                if len(names) > len(best):
                    best = names
                if len(best) >= 10:
                    break  # 十分取れたら次のURLへ
            time.sleep(0.3)
        except Exception:
            continue
    return best


# ─── 検索エンジン経由フォールバック ───────────────────────────────
def _search_via_search_engine(query: str, engine_url: str) -> List[str]:
    """検索エンジン経由でTikTokのユーザーページを探す"""
    found: Set[str] = set()
    for ua_label, ua in UAS:
        try:
            r = httpx.get(
                engine_url,
                headers=_headers(ua),
                follow_redirects=True,
                timeout=20,
            )
            if r.status_code == 200:
                # tiktok.com/@username を全部抽出
                for uid in re.findall(
                    r'tiktok\.com/@([a-zA-Z0-9_.]+)', r.text
                ):
                    if _valid_username(uid):
                        found.add(uid)
                if found:
                    break
            time.sleep(0.3)
        except Exception:
            continue
    return list(found)


def _search_duckduckgo(query: str) -> List[str]:
    q = httpx.QueryParams({"q": f'site:tiktok.com "{query}"'})
    return _search_via_search_engine(
        query, f"https://html.duckduckgo.com/html/?{q}"
    )


def _search_bing(query: str) -> List[str]:
    q = httpx.QueryParams({"q": f'site:tiktok.com "{query}"'})
    return _search_via_search_engine(
        query, f"https://www.bing.com/search?{q}"
    )


def _search_google(query: str) -> List[str]:
    q = httpx.QueryParams({"q": f'site:tiktok.com "{query}"'})
    return _search_via_search_engine(
        query, f"https://www.google.com/search?{q}"
    )


# ─── メイン検索関数 ───────────────────────────────────────────────
def search_users(query: str, max_results: int = 30) -> List[str]:
    """
    1つのクエリ（#付き/なし両対応）から複数の方法を駆使して
    ユーザー名を収集
    """
    q = query.lstrip("#").strip()
    if not q:
        return []

    found: Set[str] = set()

    # 試行するURLパターン
    url_candidates = [
        ("tag", f"https://www.tiktok.com/tag/{q}"),
        ("discover", f"https://www.tiktok.com/discover/{q}"),
        ("search-video", f"https://www.tiktok.com/search/video?q={q}"),
        ("search-user", f"https://www.tiktok.com/search/user?q={q}"),
        ("search", f"https://www.tiktok.com/search?q={q}"),
    ]

    # 1. yt-dlp でタグページ + discoverページ
    for label, url in url_candidates[:2]:
        names = _search_yt_dlp(url, max_results)
        before = len(found)
        found.update(names)
        if len(found) > before:
            print(f"[TikTok] yt-dlp {label}: +{len(found) - before}件 (累計{len(found)})")

    # 2. httpx で全URLを試行
    for label, url in url_candidates:
        names = _search_httpx(url)
        before = len(found)
        found.update(names)
        if len(found) > before:
            print(f"[TikTok] httpx {label}: +{len(found) - before}件 (累計{len(found)})")

    # 3. TikTokから直接取れない場合は検索エンジン経由
    if len(found) < 5:
        print(f"[TikTok] 直接検索 {len(found)}件のみ → 検索エンジン経由で補完")
        for engine_name, engine_fn in [
            ("DuckDuckGo", _search_duckduckgo),
            ("Bing", _search_bing),
            ("Google", _search_google),
        ]:
            names = engine_fn(q)
            before = len(found)
            found.update(names)
            if len(found) > before:
                print(
                    f"[TikTok] {engine_name}: +{len(found) - before}件 "
                    f"(累計{len(found)})"
                )
            if len(found) >= 20:
                break

    print(f"[TikTok] '{query}' → 最終 {len(found)} 件のユニークユーザー")
    return list(found)


# ─── バズアカウント発掘 ───────────────────────────────────────────
def find_viral_accounts(
    queries: List[str],
    max_followers: int = 3000,
    min_viral_videos: int = 3,
    viral_threshold: int = 10_000,
    **kwargs,
) -> List[Dict]:
    """検索ワードから低フォロワー×バズ動画多数のアカウントを発掘"""
    seen: Set[str] = set()
    candidates: List[str] = []

    for query in queries:
        names = search_users(query)
        for name in names:
            if name not in seen:
                seen.add(name)
                candidates.append(name)
        time.sleep(0.5)

    print(f"[TikTok] 候補合計 {len(candidates)} 件 → 詳細分析開始...")
    results = []

    for uname in candidates:
        profile = analyze_user(uname, viral_threshold=viral_threshold)
        if not profile:
            continue
        followers = profile["follower_count"]
        if followers != -1 and followers > max_followers:
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
