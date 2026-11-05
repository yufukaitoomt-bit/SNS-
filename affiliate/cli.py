"""コマンドラインで週次の投稿カレンダーを出力する。

例:
  python -m affiliate.cli list
  python -m affiliate.cli week                       # 今週の商品(active)で生成 → out/ に保存
  python -m affiliate.cli week --product oldorder-turbo-gt --start 2026-10-19 --personas A,D,E
  python -m affiliate.cli set-url oldorder-turbo-gt https://...   # URL発行後に1回だけ
  python -m affiliate.cli set-discount oldorder-turbo-gt 500      # リンク特典が確定したら
  python -m affiliate.cli activate oldorder-turbo-gt              # 今週売る商品を切り替え
  python -m affiliate.cli outreach --commission 12 --sender 山田     # クリエイター依頼セット
  python -m affiliate.cli plan --start 2026-11-09                   # テーマ別アカウント9つの1週間分
"""
import argparse
from datetime import date, timedelta
from pathlib import Path

from . import store
from . import outreach, planner
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
    w.add_argument("--pr-text", action="store_true", help="ラベルが付く投稿にも本文に【PR】を入れる")
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
    o.add_argument("--perk", action="append", default=[], help="売れた人向けの特典（複数可）")
    o.add_argument("--out", default="out")
    pl = sub.add_parser("plan")
    pl.add_argument("--product")
    pl.add_argument("--start", help="開始日 YYYY-MM-DD（省略時は次の月曜）")
    pl.add_argument("--week", type=int, default=0, help="何週目か（お手入れ回などの周期に使う）")
    pl.add_argument("--accounts", help="例: black,kstreet（省略時は全部）")
    pl.add_argument("--out", default="out")
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
        kit = outreach.build(p, args.commission, args.deadline, args.sender, args.brand_account, args.perk)
        out = Path(args.out)
        out.mkdir(exist_ok=True)
        (out / f"{p['id']}_outreach.md").write_text(outreach.to_markdown(p, kit), encoding="utf-8")
        (out / "creator_tracker.csv").write_text(outreach.tracker_csv(), encoding="utf-8")
        print(f"✅ {out / (p['id'] + '_outreach.md')} / creator_tracker.csv")
    elif args.cmd == "plan":
        p = store.get(args.product)
        if args.start:
            start = date.fromisoformat(args.start)
        else:
            today = date.today()
            start = today + timedelta(days=(7 - today.weekday()) % 7 or 7)
        ids = args.accounts.split(",") if args.accounts else list(planner.ACCOUNTS)
        rows = planner.plan_all(p, start, args.week, ids)
        out = Path(args.out)
        out.mkdir(exist_ok=True)
        (out / f"plan_{start.isoformat()}.csv").write_text(planner.to_csv(rows), encoding="utf-8")
        for aid in ids:
            (out / f"{aid}_{start.isoformat()}.md").write_text(planner.to_markdown(aid, rows), encoding="utf-8")
        print(f"✅ {len(ids)}アカウント・{len(rows)}件 → {out}/")
    elif args.cmd == "week":
        p = store.get(args.product)
        start = date.fromisoformat(args.start) if args.start else None
        personas = args.personas.split(",") if args.personas else None
        posts = generate_week(p, start=start, days=args.days, persona_keys=personas, x_for_all=not args.no_x, pr_text=args.pr_text,
                             platforms=args.platforms.split(",") if args.platforms else None)
        out = Path(args.out)
        out.mkdir(exist_ok=True)
        stem = f"{p['id']}_{posts[0]['date'][:10]}" if posts else p["id"]
        (out / f"{stem}.csv").write_text(to_csv(posts), encoding="utf-8")
        (out / f"{stem}.md").write_text(to_markdown(p, posts), encoding="utf-8")
        print(f"✅ {len(posts)}件生成 → {out / stem}.csv / .md")


if __name__ == "__main__":
    main()
