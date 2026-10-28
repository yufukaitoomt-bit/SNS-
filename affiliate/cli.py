"""コマンドラインで週次の投稿カレンダーを出力する。

例:
  python -m affiliate.cli list
  python -m affiliate.cli week                       # 今週の商品(active)で生成 → out/ に保存
  python -m affiliate.cli week --product oldorder-turbo-gt --start 2026-10-19 --personas A,D,E
  python -m affiliate.cli set-url oldorder-turbo-gt https://...   # URL発行後に1回だけ
  python -m affiliate.cli set-discount oldorder-turbo-gt 500      # リンク特典が確定したら
  python -m affiliate.cli activate oldorder-turbo-gt              # 今週売る商品を切り替え
  python -m affiliate.cli outreach --commission 12 --sender 山田     # クリエイター依頼セット
"""
import argparse
from datetime import date
from pathlib import Path

from . import store
from . import outreach
from .generator import generate_week, to_csv, to_markdown


def main():
    ap = argparse.ArgumentParser(prog="affiliate")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list")
    w = sub.add_parser("week")
    w.add_argument("--product")
    w.add_argument("--start", help="開始日 YYYY-MM-DD（省略時は次の月曜）")
    w.add_argument("--days", type=int, default=7)
    w.add_argument("--personas", help="例: A,B,E（省略時は全員）")
    w.add_argument("--platforms", help="例: TikTok,X（省略時は TikTok と X）")
    w.add_argument("--no-x", action="store_true", help="動画キャラのX版を作らない")
    w.add_argument("--out", default="out")
    u = sub.add_parser("set-url")
    u.add_argument("product")
    u.add_argument("url")
    dc = sub.add_parser("set-discount")
    dc.add_argument("product")
    dc.add_argument("yen", type=int)
    o = sub.add_parser("outreach")
    o.add_argument("--product")
    o.add_argument("--commission", type=float, help="報酬率(%%)")
    o.add_argument("--deadline", type=int, default=14)
    o.add_argument("--sender", default="")
    o.add_argument("--brand-account", default="")
    o.add_argument("--out", default="out")
    a = sub.add_parser("activate")
    a.add_argument("product")
    args = ap.parse_args()

    if args.cmd == "list":
        data = store.load()
        for p in data["products"]:
            mark = "★" if p["id"] == data.get("active") else " "
            print(f"{mark} {p['id']:<28} {p['brand']} {p['name']}  ¥{p.get('price') or 0:,}  URL:{'あり' if p.get('url') else '未設定'}")
    elif args.cmd == "set-url":
        p = store.get(args.product)
        p["url"] = args.url
        store.upsert(p)
        print(f"✅ {p['name']} のURLを設定しました")
    elif args.cmd == "set-discount":
        p = store.get(args.product)
        p["discount"] = args.yen
        store.upsert(p)
        print(f"✅ {p['name']} のリンク特典を ¥{args.yen:,} オフに設定しました")
    elif args.cmd == "activate":
        store.set_active(args.product)
        print(f"✅ 今週の商品: {args.product}")
    elif args.cmd == "outreach":
        p = store.get(args.product)
        kit = outreach.build(p, args.commission, args.deadline, args.sender, args.brand_account)
        out = Path(args.out)
        out.mkdir(exist_ok=True)
        (out / f"{p['id']}_outreach.md").write_text(outreach.to_markdown(p, kit), encoding="utf-8")
        (out / "creator_tracker.csv").write_text(outreach.tracker_csv(), encoding="utf-8")
        print(f"✅ {out / (p['id'] + '_outreach.md')} / creator_tracker.csv")
    elif args.cmd == "week":
        p = store.get(args.product)
        start = date.fromisoformat(args.start) if args.start else None
        personas = args.personas.split(",") if args.personas else None
        posts = generate_week(p, start=start, days=args.days, persona_keys=personas, x_for_all=not args.no_x,
                             platforms=args.platforms.split(",") if args.platforms else None)
        out = Path(args.out)
        out.mkdir(exist_ok=True)
        stem = f"{p['id']}_{posts[0]['date'][:10]}" if posts else p["id"]
        (out / f"{stem}.csv").write_text(to_csv(posts), encoding="utf-8")
        (out / f"{stem}.md").write_text(to_markdown(p, posts), encoding="utf-8")
        print(f"✅ {len(posts)}件生成 → {out / stem}.csv / .md")


if __name__ == "__main__":
    main()
