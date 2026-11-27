#!/usr/bin/env python3
"""スタッフ別「スニーカー以外」販売点数カウント（スマレジ取引履歴CSV）

使い方: python3 count_non_sneaker_by_staff.py <取引履歴CSV> [--from YYYY-MM-DD] [--to YYYY-MM-DD]

想定入力: スマレジ管理画面の取引履歴CSV（60列・取引明細付き・UTF-8 BOM）
除外: 取引区分1以外（ポイント加算/減算/失効）、取消区分1、ショッパー・送料・ラッピング
"""
import csv, sys, io, argparse
from collections import defaultdict

STORE = {"1": "裏原", "3": "大阪南堀江", "6": "原宿明治通り", "8": "名古屋PARCO"}

# 「スニーカー以外」として数える部門
NON_SNEAKER = {
    "フットウェア",            # 靴下・レッグウォーマー
    "アクセサリーズ",          # 靴紐・シュークリップ・ミニバッグ
    "OLDORDER SELECT",        # アパレル（キャップ/フーディ/スウェット等）
    "OverTure select",        # アパレル
    "OVC",                    # アパレル（ヴィンテージフーディ等）
    "Lighter",                # ライター
    "トップス", "ボトムス", "アパレル",
    "MYSTERY BOX", "3D printer accessories",
}
# 部門「その他（売上対象外）」のうち、商品ではないもの＝完全除外
NOT_MERCH = {
    "ショッパーS", "ショッパーL",
    "【OLDORDER】Gift Wrapping",
    "送料（本州・四国）", "送料（沖縄）",
}
# 同部門だが実体は商品（バッグ類）。本集計とは別枠で出す
BAGS = {"Osaka limited Knapsack", "【OLDORDER】ORIGINAL SHOPPINGBAG"}
OTHER_DEPT = {"その他（売上対象外）", "その他(売上対象外)"}


def load(path):
    raw = open(path, "rb").read()
    for enc in ("utf-8-sig", "cp932", "utf-8"):
        try:
            txt = raw.decode(enc); break
        except UnicodeDecodeError:
            continue
    else:
        raise SystemExit(f"{path}: 文字コードを判定できません")
    rdr = csv.reader(io.StringIO(txt))
    hdr = next(rdr)
    return [dict(zip(hdr, r)) for r in rdr if r], hdr, enc


def col(hdr, idx):
    return hdr[idx - 1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv")
    ap.add_argument("--from", dest="d_from", default="2026-11-01")
    ap.add_argument("--to", dest="d_to", default="2026-11-26")
    a = ap.parse_args()

    rows, hdr, enc = load(a.csv)
    if len(hdr) < 60:
        raise SystemExit(f"列数が{len(hdr)}しかありません。取引明細付きのCSVが必要です。\nヘッダー: {hdr}")
    C = {k: col(hdr, i) for k, i in dict(
        kind=3, cancel=4, store=26, staff_id=36, staff=37,
        dt=2, line=45, code=47, name=48, qty=54, amt=57, dept=60).items()}

    ns = defaultdict(lambda: defaultdict(int))   # (店,担当) -> 部門 -> 点数
    sn = defaultdict(int)                        # (店,担当) -> スニーカー点数
    item = defaultdict(int)
    bags = defaultdict(int)
    unknown = defaultdict(int)
    returns, dropped_kind, out_of_range, total = 0, 0, 0, 0

    for r in rows:
        total += 1
        if r[C["kind"]] != "1":
            dropped_kind += 1; continue
        if r[C["cancel"]] == "1":
            continue
        d = (r[C["dt"]] or "")[:10].replace("/", "-")
        if not (a.d_from <= d <= a.d_to):
            out_of_range += 1; continue
        try:
            q = int(float(r[C["qty"]] or 0))
        except ValueError:
            q = 0
        if r[C["line"]] == "2":                  # 返品行は減算
            q = -abs(q); returns += 1
        if q == 0:
            continue

        dept = (r[C["dept"]] or "").strip()
        name = (r[C["name"]] or "").strip()
        store = STORE.get((r[C["store"]] or "").strip(), f"店舗ID{r[C['store']]}")
        staff = (r[C["staff"]] or "").strip() or "(未設定)"

        if dept in OTHER_DEPT:
            if name in NOT_MERCH:
                continue
            if name in BAGS:
                bags[(store, staff, name)] += q
                continue
            unknown[(dept, name)] += q
            continue
        if not dept:
            unknown[("(部門空欄)", name)] += q
            continue

        if dept in NON_SNEAKER:
            ns[(store, staff)][dept] += q
            item[(dept, name)] += q
        else:
            sn[(store, staff)] += q

    W = 86
    print("=" * W)
    print(f"■ スニーカー以外の販売点数　{a.d_from} 〜 {a.d_to}（ラッピング・ショッパー・送料は除外）")
    print("=" * W)
    print(f"{'店':12} {'担当者':14} {'非スニーカー':>10} {'スニーカー':>10} {'計':>7} {'非スニ比率':>9}")
    print("-" * W)
    keys = set(ns) | set(sn)
    tn = ts = 0
    for k in sorted(keys, key=lambda x: (-sum(ns[x].values()), -sn[x])):
        n, s = sum(ns[k].values()), sn[k]
        tn += n; ts += s
        sh = f"{n/(n+s)*100:.1f}%" if (n + s) else "-"
        print(f"{k[0]:12} {k[1]:14} {n:>10} {s:>10} {n+s:>7} {sh:>9}")
    print("-" * W)
    sh = f"{tn/(tn+ts)*100:.1f}%" if (tn + ts) else "-"
    print(f"{'合計':12} {'':14} {tn:>10} {ts:>10} {tn+ts:>7} {sh:>9}")

    print(f"\n■ 店別")
    st = defaultdict(lambda: [0, 0])
    for k in keys:
        st[k[0]][0] += sum(ns[k].values()); st[k[0]][1] += sn[k]
    for s_, (n, sv) in sorted(st.items(), key=lambda x: -x[1][0]):
        r_ = f"{n/(n+sv)*100:.1f}%" if (n + sv) else "-"
        print(f"  {s_:14} 非スニーカー {n:>4} / スニーカー {sv:>4} / 比率 {r_:>7}")

    print(f"\n■ 部門別（非スニーカー）")
    agg = defaultdict(int)
    for v in ns.values():
        for d_, q in v.items():
            agg[d_] += q
    for d_, q in sorted(agg.items(), key=lambda x: -x[1]):
        print(f"  {d_:26} {q:>4}")

    print(f"\n■ 商品別（非スニーカー）")
    for (d_, nm), q in sorted(item.items(), key=lambda x: -x[1]):
        print(f"  {q:>4}  [{d_}] {nm[:54]}")

    if bags:
        print(f"\n■ 別枠：部門「その他（売上対象外）」にあるが商品のもの（含めるか要判断）")
        bs = defaultdict(int)
        for (s_, st_, nm), q in bags.items():
            bs[nm] += q
        for nm, q in sorted(bs.items(), key=lambda x: -x[1]):
            print(f"  {q:>4}  {nm}")
        print(f"  → 合計 {sum(bs.values())}点。含めると非スニーカーは {tn + sum(bs.values())}点")
        print(f"\n  担当者別の内訳")
        for (s_, st_, nm), q in sorted(bags.items(), key=lambda x: -x[1]):
            print(f"    {s_:12} {st_:14} {nm[:34]:36} {q:>4}")

    if unknown:
        print(f"\n■ 判定できなかった商品（確認用）")
        for (d_, nm), q in sorted(unknown.items(), key=lambda x: -x[1]):
            print(f"  {q:>4}  [{d_}] {nm[:54]}")

    print(f"\n(全{total}行 / 通常取引以外を除外{dropped_kind}行 / 期間外{out_of_range}行 / 返品{returns}行)")


if __name__ == "__main__":
    main()
