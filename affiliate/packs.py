"""予約投稿用の素材パック。アカウント×SNS×日付ごとに、画像・動画・本文・公開時間を1フォルダにまとめる。

out/packs/<週>/<アカウント>/<SNS>/<日付>_<時間>/ に
  - 1.png 2.png 3.png（画像）／video.mp4（TikTok・YouTube用）
  - caption.txt（本文。そのままコピーして貼る）
  - 設定.txt（広告表示の設定・公開時間）
TikTok Studio・Xの予約画面に、フォルダの中身をそのまま入れれば済むようにする。
"""
import shutil
from pathlib import Path
from typing import List

VIDEO_PLATFORMS = {"TikTok", "YouTube"}


def build(rows: List[dict], cards_dir: Path, out_dir: Path) -> int:
    """rows: planner.plan_all の結果。cards_dir: cards.render_week の出力先（<アカウント>/<日付>_N.png）。"""
    n = 0
    for r in rows:
        day = r["date"][:10]
        src = cards_dir / r["account"]
        folder = out_dir / r["account"] / r["platform"] / f"{day}_{r['time'].replace(':', '')}"
        folder.mkdir(parents=True, exist_ok=True)
        for i in (1, 2, 3):
            img = src / f"{day}_{i}.png"
            if img.exists():
                shutil.copy(img, folder / f"{i}.png")
        video = src / f"{day}.mp4"
        if r["platform"] in VIDEO_PLATFORMS and video.exists():
            shutil.copy(video, folder / "video.mp4")
        (folder / "caption.txt").write_text(r["caption"] + "\n", encoding="utf-8")
        setting = [f"公開日時: {r['date']} {r['time']}", f"アカウント: {r['account_name']}", f"投稿の型: {r['type']}"]
        if r["disclosure"]:
            setting.append(f"広告表示: {r['disclosure']}")
        (folder / "設定.txt").write_text("\n".join(setting) + "\n", encoding="utf-8")
        n += 1
    return n
