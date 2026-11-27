#!/usr/bin/env python3
"""11/1-11/26 スタッフ別「スニーカー以外」販売点数カウント

使い方:  python3 count_non_sneaker_by_staff.py <取引明細CSV> [<CSV2> ...]

スマレジの取引履歴CSV（明細あり）を想定。列名は自動判定する。
ラッピング（その他（売上対象外））は除外。
"""
import csv, sys, io, re
from collections import defaultdict

FROM_DATE, TO_DATE = "2026-11-01", "2026-11-26"

# 非スニーカー部門（既存データ 7/16-10/17 の実績から）
NON_SNEAKER = {
    "アクセサリーズ", "アパレル", "トップス", "ボトムス",
    "OLDORDER SELECT", "MYSTERY BOX", "3D printer accessories",
}
# 集計から完全に除外（商品ではない）
EXCLUDE = {"その他（売上対象外）", "その他(売上対象外)"}
EXCLUDE_NAME_RE = re.compile(r"gift\s*wrapping|ラッピング|ギフト包装", re.I)

ALIASES = {
    "date":  ["取引日", "取引日時", "売上日", "日付", "日時", "取引年月日"],
    "store": ["店舗名", "店舗", "店舗コード", "店"],
    "staff": ["担当者名", "担当者", "スタッフ名", "スタッフ", "販売員", "担当スタッフ"],
    "dept":  ["部門名", "部門", "カテゴリ", "カテゴリー"],
    "name":  ["商品名", "商品", "品名"],
    "qty":   ["数量", "販売点数", "個数", "点数", "売上数量"],
}

def pick(fields, keys):
    norm = {(f or "").strip().lstrip("﻿"): f for f in fields}
    for k in keys:
        if k in norm:
            return norm[k]
    for k in keys:                      # 部分一致フォールバック
        for f in norm:
            if k and k in f:
                return norm[f]
    return None

def read_rows(path):
    raw = open(path, "rb").read()
    for enc in ("utf-8-sig", "cp932", "utf-8"):
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise SystemExit(f"{path}: 文字コードを判定できません")
    rdr = csv.DictReader(io.StringIO(text), skipinitialspace=True)
    return list(rdr), (rdr.fieldnames or []), enc

def norm_date(v):
    m = re.search(r"(\d{4})[-/年](\d{1,2})[-/月](\d{1,2})", v or "")
    return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}" if m else None

def main(paths):
    by_staff = defaultdict(lambda: defaultdict(int))   # (店, 担当者) -> 部門 -> 点数
    by_item  = defaultdict(int)
    sneaker  = defaultdict(int)
    unknown_depts, skipped, total_rows = defaultdict(int), 0, 0

    for path in paths:
        rows, fields, enc = read_rows(path)
        cols = {k: pick(fields, v) for k, v in ALIASES.items()}
        print(f"[{path}] {enc} / {len(rows)}行")
        for k, v in cols.items():
            print(f"    {k:6} -> {v!r}")
        missing = [k for k in ("date", "staff", "qty") if not cols[k]]
        if missing:
            print(f"  !! 必須列が見つかりません: {missing}\n     ヘッダー: {fields}")
            continue
        print()

        for r in rows:
            total_rows += 1
            nm = (r.get(cols["name"]) or "").strip() if cols["name"] else ""
            if nm == "合計":
                continue
            d = norm_date(r.get(cols["date"], ""))
            if not d or not (FROM_DATE <= d <= TO_DATE):
                skipped += 1
                continue
            dept = (r.get(cols["dept"]) or "").strip() if cols["dept"] else ""
            if dept in EXCLUDE or EXCLUDE_NAME_RE.search(nm):
                continue
            try:
                q = int(float((r.get(cols["qty"]) or "0").replace(",", "")))
            except ValueError:
                q = 0
            if q <= 0:
                continue
            store = (r.get(cols["store"]) or "-").strip() if cols["store"] else "-"
            staff = (r.get(cols["staff"]) or "(未設定)").strip() or "(未設定)"

            if dept in NON_SNEAKER:
                by_staff[(store, staff)][dept] += q
                by_item[(dept, nm)] += q
            else:
                sneaker[(store, staff)] += q
                if dept and dept not in NON_SNEAKER:
                    unknown_depts[dept] += q

    print("=" * 78)
    print(f"■ スニーカー以外の販売点数（{FROM_DATE}〜{TO_DATE}・ラッピング除外）")
    print("=" * 78)
    print(f"{'店':14} {'担当者':14} {'非スニーカー':>10} {'スニーカー':>10} {'構成比':>8}")
    rank = sorted(by_staff.items(), key=lambda x: -sum(x[1].values()))
    tot_n = tot_s = 0
    for (store, staff), depts in rank:
        n = sum(depts.values()); s = sneaker.get((store, staff), 0)
        tot_n += n; tot_s += s
        share = f"{n/(n+s)*100:.1f}%" if (n + s) else "-"
        print(f"{store:14} {staff:14} {n:>10} {s:>10} {share:>8}")
    for key, s in sorted(sneaker.items(), key=lambda x: -x[1]):
        if key not in by_staff:
            tot_s += s
            print(f"{key[0]:14} {key[1]:14} {0:>10} {s:>10} {'0.0%':>8}")
    print("-" * 78)
    sh = f"{tot_n/(tot_n+tot_s)*100:.1f}%" if (tot_n + tot_s) else "-"
    print(f"{'合計':14} {'':14} {tot_n:>10} {tot_s:>10} {sh:>8}")

    print(f"\n■ 部門別")
    agg = defaultdict(int)
    for depts in by_staff.values():
        for d, q in depts.items():
            agg[d] += q
    for d, q in sorted(agg.items(), key=lambda x: -x[1]):
        print(f"  {d:28} {q:>5}")

    print(f"\n■ 商品別")
    for (d, nm), q in sorted(by_item.items(), key=lambda x: -x[1]):
        print(f"  {d:22} | {nm[:48]:50} {q:>4}")

    if unknown_depts:
        print(f"\n■ スニーカー側に入れた部門（確認用。非スニーカーならリストに追加）")
        for d, q in sorted(unknown_depts.items(), key=lambda x: -x[1])[:40]:
            print(f"  {d:28} {q:>5}")
    print(f"\n(読込{total_rows}行 / 期間外{skipped}行)")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    main(sys.argv[1:])
