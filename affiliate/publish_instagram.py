"""Instagramへ、その日の投稿をリール（15秒動画）で自動投稿する。GitHub Actionsから15分おきに呼ぶ。

- アカウントごとのトークンは環境変数 IG_TOKEN_<アカウントID大文字>（例: IG_TOKEN_BLACK）。無いアカウントは飛ばす
- 公開時間（planner.post_time）を過ぎていて、今日まだ同じ投稿をしていなければ投稿する（重複しない）
- 画像・動画はその場で cards から作る。動画は Instagram の resumable upload で直接送るので、公開URLは要らない
- --dry-run: 投稿せずに、何をするかだけ表示する

API: Instagram API with Instagram Login（graph.instagram.com）
"""
import argparse
import os
import sys
import tempfile
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import httpx

from . import cards, planner, store
from .accounts import ACCOUNTS, PLAN_ANCHOR, PLAN_ANCHOR_WEEK

API = "https://graph.instagram.com/v21.0"
JST = timezone(timedelta(hours=9))


def week_of(day: date) -> tuple:
    """計画の週（開始日・週番号）。PLAN_ANCHOR から7日ごとに区切る。"""
    k = (day - date.fromisoformat(PLAN_ANCHOR)).days // 7
    return date.fromisoformat(PLAN_ANCHOR) + timedelta(days=7 * k), PLAN_ANCHOR_WEEK + k


def todays_row(account_id: str, product: dict, today: date) -> Optional[dict]:
    start, week = week_of(today)
    for r in planner.plan_week(account_id, product, start, week, ready_only=True):
        if r["platform"] == "Instagram" and r["date"].startswith(today.isoformat()):
            return r
    return None


def already_posted(client: httpx.Client, token: str, first_line: str, today: date) -> bool:
    res = client.get(f"{API}/me/media", params={"fields": "caption,timestamp", "limit": 10, "access_token": token})
    res.raise_for_status()
    for m in res.json().get("data", []):
        posted = datetime.strptime(m["timestamp"], "%Y-%m-%dT%H:%M:%S%z").astimezone(JST).date()
        if posted == today and (m.get("caption") or "").split("\n")[0] == first_line:
            return True
    return False


def publish_reel(client: httpx.Client, token: str, video: Path, caption: str) -> str:
    me = client.get(f"{API}/me", params={"fields": "user_id,username", "access_token": token})
    me.raise_for_status()
    user_id = me.json()["user_id"]
    # 1. 入れ物（コンテナ）を作る
    res = client.post(f"{API}/{user_id}/media", data={
        "media_type": "REELS", "upload_type": "resumable", "caption": caption, "access_token": token})
    res.raise_for_status()
    container = res.json()
    # 2. 動画を直接アップロードする
    data = video.read_bytes()
    up = client.post(container["uri"], content=data, headers={
        "Authorization": f"OAuth {token}", "offset": "0", "file_size": str(len(data))}, timeout=300)
    up.raise_for_status()
    # 3. Instagram側の処理が終わるまで待つ
    for _ in range(60):
        st = client.get(f"{API}/{container['id']}", params={"fields": "status_code", "access_token": token})
        st.raise_for_status()
        code = st.json().get("status_code")
        if code == "FINISHED":
            break
        if code == "ERROR":
            raise RuntimeError(f"動画の処理に失敗: {st.json()}")
        time.sleep(10)
    else:
        raise RuntimeError("動画の処理が10分で終わらなかった")
    # 4. 公開する
    pub = client.post(f"{API}/{user_id}/media_publish", data={"creation_id": container["id"], "access_token": token})
    pub.raise_for_status()
    return pub.json()["id"]


def run(dry_run: bool = False, now: Optional[datetime] = None) -> int:
    now = now or datetime.now(JST)
    today = now.date()
    product = store.get()
    failures = 0
    with httpx.Client(timeout=60) as client:
        for aid in ACCOUNTS:
            token = os.environ.get(f"IG_TOKEN_{aid.upper()}")
            if not token:
                continue
            row = todays_row(aid, product, today)
            if not row:
                print(f"[{aid}] 今日の投稿なし")
                continue
            if now.strftime("%H:%M") < row["time"]:
                print(f"[{aid}] まだ公開時間前（{row['time']}）")
                continue
            first_line = row["caption"].split("\n")[0]
            try:
                if already_posted(client, token, first_line, today):
                    print(f"[{aid}] 今日の投稿は済み")
                    continue
                if dry_run:
                    print(f"[{aid}] 投稿予定: {row['type']}／{first_line}")
                    continue
                with tempfile.TemporaryDirectory() as tmp:
                    slides = cards.render_post(row, product, Path(tmp), today.isoformat())
                    video = cards.make_video(slides, Path(tmp) / "reel.mp4", cards.STYLES[aid])
                    media_id = publish_reel(client, token, video, row["caption"])
                print(f"[{aid}] 投稿しました（media_id={media_id}）")
            except Exception as e:  # 1アカウントの失敗で他を止めない
                failures += 1
                print(f"[{aid}] 失敗: {e}", file=sys.stderr)
    return failures


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    sys.exit(1 if run(dry_run=args.dry_run) else 0)
