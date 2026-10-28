"""アフィリエイト投稿ジェネレーターのAPIと画面（/affiliate）。"""
from datetime import date
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel

from . import store
from . import outreach
from .generator import check_claims, generate_week, to_csv, to_markdown
from .library import ALL_PLATFORMS, ANGLES, DEFAULT_PLATFORMS, FORMATS, PERSONAS

router = APIRouter()


class Product(BaseModel):
    id: Optional[str] = None
    brand: str
    name: str
    category: str = "スニーカー"
    price: int = 0
    compare_price: int = 0
    discount: int = 0
    url: str = ""
    celebrity: str = ""
    sole_height: str = ""
    size_tip: str = ""
    tiktok_shop: bool = False
    shop_price: int = 0
    features: List[str] = []
    colors: List[str] = []
    shipping_note: str = ""
    angles: List[str] = []
    hashtags: List[str] = []
    memo: str = ""


class OutreachReq(BaseModel):
    product_id: Optional[str] = None
    commission: Optional[float] = None
    deadline_days: int = 14
    sender: str = ""
    brand_account: str = ""


class GenerateReq(BaseModel):
    product_id: Optional[str] = None
    start: Optional[date] = None
    days: int = 7
    personas: Optional[List[str]] = None
    x_for_all: bool = True
    platforms: Optional[List[str]] = None


def _product(pid: Optional[str]) -> dict:
    try:
        return store.get(pid)
    except KeyError:
        raise HTTPException(404, "商品が見つかりません")


def _generate(req: GenerateReq):
    p = _product(req.product_id)
    return p, generate_week(p, start=req.start, days=req.days, persona_keys=req.personas,
                          x_for_all=req.x_for_all, platforms=req.platforms)


@router.get("/api/affiliate/meta")
async def meta():
    return {
        "angles": {k: v["label"] for k, v in ANGLES.items()},
        "formats": {k: v["label"] for k, v in FORMATS.items()},
        "platforms": ALL_PLATFORMS,
        "default_platforms": DEFAULT_PLATFORMS,
        "personas": {k: {"label": v["label"], "platforms": v["platforms"]} for k, v in PERSONAS.items()},
    }


@router.get("/api/affiliate/products")
async def list_products():
    return store.load()


@router.post("/api/affiliate/products")
async def save_product(p: Product, activate: bool = False):
    ng = check_claims(p.model_dump())
    if ng:
        raise HTTPException(400, f"根拠のない表現は使えません: {'、'.join(ng)}（公式サイトに書いてある事実だけを入れてください）")
    return store.upsert(p.model_dump(), make_active=activate)


@router.post("/api/affiliate/products/{pid}/activate")
async def activate_product(pid: str):
    _product(pid)
    store.set_active(pid)
    return {"active": pid}


@router.delete("/api/affiliate/products/{pid}")
async def delete_product(pid: str):
    store.delete(pid)
    return {"ok": True}


@router.post("/api/affiliate/generate")
async def generate(req: GenerateReq):
    p, posts = _generate(req)
    return {"product": p, "count": len(posts), "posts": posts}


@router.post("/api/affiliate/export.csv")
async def export_csv(req: GenerateReq):
    p, posts = _generate(req)
    return Response(to_csv(posts), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="{p["id"]}.csv"'})


@router.post("/api/affiliate/export.md")
async def export_md(req: GenerateReq):
    p, posts = _generate(req)
    return Response(to_markdown(p, posts), media_type="text/markdown; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="{p["id"]}.md"'})


@router.post("/api/affiliate/outreach")
async def outreach_kit(req: OutreachReq):
    p = _product(req.product_id)
    return outreach.build(p, req.commission, req.deadline_days, req.sender, req.brand_account)


@router.get("/api/affiliate/tracker.csv")
async def tracker():
    return Response(outreach.tracker_csv(), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": 'attachment; filename="creator_tracker.csv"'})


@router.get("/affiliate", response_class=HTMLResponse)
async def page():
    return PAGE


PAGE = """<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>アフィリエイト投稿 — SNS Analyzer</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#0f0f0f;color:#f0f0f0;min-height:100vh}
header{background:#1a1a1a;border-bottom:1px solid #2a2a2a;padding:14px 24px;display:flex;align-items:center;gap:10px}
header h1{font-size:17px;font-weight:700}
header a{color:#888;font-size:12px;margin-left:auto;text-decoration:none}
.badge{background:#fe2c55;color:#fff;font-size:11px;padding:2px 8px;border-radius:20px;font-weight:600}
main{max-width:1000px;margin:0 auto;padding:28px 16px}
.card{background:#1a1a1a;border:1px solid #2a2a2a;border-radius:12px;padding:20px;margin-bottom:14px}
.card h2{font-size:13px;font-weight:700;color:#888;margin-bottom:14px;letter-spacing:.5px}
.tip{font-size:12px;color:#888;margin-bottom:12px;padding:10px 12px;background:#111;border-radius:8px;border-left:3px solid #fe2c55;line-height:1.6}
.form-row{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:10px}
@media(max-width:640px){.form-row{grid-template-columns:1fr}}
.form-group{display:flex;flex-direction:column;gap:5px}
label{font-size:11px;color:#888;font-weight:600}
input,textarea,select{background:#0f0f0f;border:1px solid #333;color:#f0f0f0;padding:9px 11px;border-radius:7px;font-size:13px;width:100%;outline:none}
input:focus,textarea:focus,select:focus{border-color:#fe2c55}
textarea{resize:vertical;min-height:60px;font-size:12px}
.checks{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:10px}
.checks label{display:flex;align-items:center;gap:5px;background:#111;border:1px solid #333;border-radius:20px;padding:5px 11px;font-size:12px;color:#ccc;cursor:pointer;font-weight:500}
.checks input{width:auto}
.btns{display:flex;gap:8px;flex-wrap:wrap;margin-top:6px}
button{padding:10px 16px;border-radius:8px;border:none;background:#2a2a2a;color:#f0f0f0;font-size:13px;font-weight:700;cursor:pointer}
button.run{background:#fe2c55;color:#fff;flex:1}
.status{margin-top:10px;font-size:12px;color:#888;min-height:18px}
.warn{color:#f0c040}
.day{font-size:14px;font-weight:800;margin:22px 0 8px;color:#fe2c55}
.post{background:#1a1a1a;border:1px solid #2a2a2a;border-radius:10px;padding:14px;margin-bottom:10px}
.meta{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:8px}
.chip{font-size:11px;padding:2px 8px;border-radius:20px;background:#2a2a2a;color:#ccc}
.chip.p{background:#fe2c55;color:#fff}
pre{white-space:pre-wrap;background:#0f0f0f;border:1px solid #2a2a2a;border-radius:8px;padding:10px;font-size:12px;line-height:1.6;margin-top:6px;font-family:inherit}
.copy{font-size:11px;padding:4px 10px;margin-top:6px}
.sub{font-size:11px;color:#666;margin-top:8px}
</style>
</head>
<body>
<header>
  <h1>アフィリエイト投稿ジェネレーター</h1><span class="badge">週次</span>
  <a href="/">← SNS Analyzer</a>
</header>
<main>
  <div class="card">
    <h2>① 今週売る商品</h2>
    <div class="tip">商品を選ぶか「新規」で登録 → 訴求軸にチェック → 保存。<b>訴求軸の一番上にチェックした軸が「主軸」</b>になり、全キャラの投稿に必ず混ざります（例: 韓国系で売りたい商品は「韓国系・K-POP」を主軸に）。URLが発行されたら入れて保存するだけで全投稿に反映されます。</div>
    <div class="form-row">
      <div class="form-group"><label>商品</label><select id="sel" onchange="loadForm()"></select></div>
      <div class="form-group"><label>&nbsp;</label><button onclick="newForm()">＋ 新規商品</button></div>
    </div>
    <div class="form-row">
      <div class="form-group"><label>ブランド</label><input id="brand"></div>
      <div class="form-group"><label>商品名</label><input id="name"></div>
    </div>
    <div class="form-row">
      <div class="form-group"><label>カテゴリ（スニーカー / サンダル / バッグ等）</label><input id="category"></div>
      <div class="form-group"><label>着用している有名人（本人発信などで確認できた場合のみ）</label><input id="celebrity"></div>
    </div>
    <div class="form-row">
      <div class="form-group"><label>公式価格（税込・円）</label><input id="price" type="number"></div>
      <div class="form-group"><label>他店価格（公式より高い場合のみ。投稿日に要確認）</label><input id="compare_price" type="number"></div>
    </div>
    <div class="form-row">
      <div class="form-group"><label>アフィリエイトURL</label><input id="url" placeholder="発行されたら貼る"></div>
      <div class="form-group"><label>リンク経由の割引額（円・確定したら入力。0＝なし）</label><input id="discount" type="number" placeholder="例: 500"></div>
    </div>
    <div class="form-row">
      <div class="form-group"><label>特徴（公式サイトに書いてある事実のみ・1行1つ）</label><textarea id="features" placeholder="例: 男女兼用"></textarea></div>
      <div class="form-group"><label>カラー（1行1つ）</label><textarea id="colors"></textarea></div>
    </div>
    <div class="form-row">
      <div class="form-group"><label>ソールの高さ（公式表記。例: 5.5cm）</label><input id="sole_height"></div>
      <div class="form-group"><label>公式のサイズ案内（例: ワンサイズ上推奨）</label><input id="size_tip"></div>
    </div>
    <div class="form-row">
      <div class="form-group"><label>配送などの注意書き（公式サイト購入時）</label><input id="shipping_note"></div>
      <div class="form-group"><label>追加ハッシュタグ（スペース区切り・#不要）</label><input id="hashtags"></div>
    </div>
    <div class="checks"><label><input type="checkbox" id="tiktok_shop">TikTok Shopに出店している（TikTok投稿は🛒商品リンクで売る）</label></div>
    <div class="form-group" style="margin-bottom:10px"><label>TikTok Shopでの価格（公式サイトと違う場合だけ・円）</label><input id="shop_price" type="number"></div>
    <label>訴求軸（チェック順＝優先順。最初が主軸）</label>
    <div class="checks" id="angles"></div>
    <div class="form-group" style="margin-bottom:10px"><label>メモ</label><input id="memo"></div>
    <div class="btns">
      <button class="run" onclick="saveProduct()">保存して今週の商品にする</button>
      <button onclick="delProduct()">削除</button>
    </div>
    <div class="status" id="p-status"></div>
  </div>

  <div class="card">
    <h2>② 1週間分を生成</h2>
    <div class="form-row">
      <div class="form-group"><label>開始日（空欄＝次の月曜）</label><input id="start" type="date"></div>
      <div class="form-group"><label>日数</label><input id="days" type="number" value="7" min="1" max="31"></div>
    </div>
    <label>媒体（既定: TikTok と X）</label>
    <div class="checks" id="platforms"></div>
    <label>キャラ（アカウント）</label>
    <div class="checks" id="personas"></div>
    <div class="checks"><label><input type="checkbox" id="xall" checked>動画キャラのX版も作る</label></div>
    <div class="btns">
      <button class="run" onclick="gen()">生成する</button>
      <button onclick="dl('csv')">CSVダウンロード</button>
      <button onclick="dl('md')">Markdownダウンロード</button>
    </div>
    <div class="status" id="g-status"></div>
  </div>
  <div class="card">
    <h2>③ クリエイター依頼セット（TikTok Shop・商品送付あり）</h2>
    <div class="tip">DM文面と依頼書を、今の商品データから作ります。報酬率が空欄なら【未定】と入ります。依頼書の「使っていただける事実」は商品の特徴・ソール高さ・サイズ案内から入ります（公式の事実だけ）。</div>
    <div class="form-row">
      <div class="form-group"><label>報酬率（%）</label><input id="commission" type="number" step="0.5" placeholder="例: 12"></div>
      <div class="form-group"><label>投稿期限（届いてから◯日）</label><input id="deadline" type="number" value="14"></div>
    </div>
    <div class="form-row">
      <div class="form-group"><label>担当者名</label><input id="sender"></div>
      <div class="form-group"><label>ブランドのTikTokアカウント</label><input id="brand_account" placeholder="@old.order_japan.staff"></div>
    </div>
    <div class="btns">
      <button class="run" onclick="kit()">依頼セットを作る</button>
      <button onclick="location.href='/api/affiliate/tracker.csv'">管理表CSV</button>
    </div>
    <div id="kit"></div>
  </div>
  <div id="out"></div>
</main>
<script>
let META={},DATA={},angleOrder=[];
const $=id=>document.getElementById(id);
const esc=s=>String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const lines=s=>s.split('\\n').map(x=>x.trim()).filter(Boolean);

async function init(){
  META=await (await fetch('/api/affiliate/meta')).json();
  $('platforms').innerHTML=META.platforms.map(p=>`<label><input type="checkbox" value="${esc(p)}" ${META.default_platforms.includes(p)?'checked':''}>${esc(p)}</label>`).join('');
  $('personas').innerHTML=Object.entries(META.personas).map(([k,v])=>`<label><input type="checkbox" value="${k}" checked>${k} ${esc(v.label)}（${v.platforms.join('/')}）</label>`).join('');
  await reload();
}
async function reload(sel){
  DATA=await (await fetch('/api/affiliate/products')).json();
  $('sel').innerHTML=DATA.products.map(p=>`<option value="${p.id}">${p.id===DATA.active?'★ ':''}${esc(p.brand)} ${esc(p.name)}</option>`).join('');
  $('sel').value=sel||DATA.active||'';
  loadForm();
}
function renderAngles(selected){
  angleOrder=[...selected];
  $('angles').innerHTML=Object.entries(META.angles).map(([k,l])=>{
    const i=angleOrder.indexOf(k);
    return `<label><input type="checkbox" value="${k}" ${i>=0?'checked':''} onchange="toggleAngle('${k}',this.checked)">${i===0?'⭐ ':i>0?(i+1)+'. ':''}${esc(l)}</label>`;
  }).join('');
}
function toggleAngle(k,on){
  angleOrder=angleOrder.filter(a=>a!==k); if(on)angleOrder.push(k); renderAngles(angleOrder);
}
function fill(p){
  for(const k of ['brand','name','category','celebrity','price','compare_price','discount','shop_price','sole_height','size_tip','url','shipping_note','memo'])$(k).value=p[k]??'';
  $('tiktok_shop').checked=!!p.tiktok_shop;
  $('features').value=(p.features||[]).join('\\n');
  $('colors').value=(p.colors||[]).join('\\n');
  $('hashtags').value=(p.hashtags||[]).join(' ');
  renderAngles(p.angles||[]);
  $('p-status').innerHTML=p.url?'':'<span class="warn">⚠️ URL未設定（投稿文には【URL未設定】と入ります）</span>';
}
function loadForm(){const p=DATA.products.find(x=>x.id===$('sel').value); fill(p||{category:'スニーカー'}); $('sel').dataset.editing=p?p.id:'';}
function newForm(){$('sel').dataset.editing=''; fill({category:'スニーカー'});}
async function saveProduct(){
  const body={id:$('sel').dataset.editing||null,brand:$('brand').value.trim(),name:$('name').value.trim(),category:$('category').value.trim()||'スニーカー',
    celebrity:$('celebrity').value.trim(),sole_height:$('sole_height').value.trim(),size_tip:$('size_tip').value.trim(),tiktok_shop:$('tiktok_shop').checked,price:+$('price').value||0,compare_price:+$('compare_price').value||0,discount:+$('discount').value||0,shop_price:+$('shop_price').value||0,url:$('url').value.trim(),
    features:lines($('features').value),colors:lines($('colors').value),shipping_note:$('shipping_note').value.trim(),
    hashtags:$('hashtags').value.split(/\\s+/).map(t=>t.replace(/^#/,'')).filter(Boolean),angles:angleOrder,memo:$('memo').value.trim()};
  if(!body.brand||!body.name)return alert('ブランドと商品名は必須です');
  const r=await fetch('/api/affiliate/products?activate=true',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
  const p=await r.json(); if(!r.ok){$('p-status').innerHTML='<span class="warn">'+esc(p.detail)+'</span>';return;}
  await reload(p.id); $('p-status').innerHTML+=' ✅ 保存しました（今週の商品に設定）';
}
async function delProduct(){
  const id=$('sel').dataset.editing; if(!id||!confirm('この商品を削除しますか？'))return;
  await fetch('/api/affiliate/products/'+id,{method:'DELETE'}); await reload();
}
function req(){
  return {product_id:$('sel').value||null,start:$('start').value||null,days:+$('days').value||7,
    personas:[...$('personas').querySelectorAll('input:checked')].map(i=>i.value),x_for_all:$('xall').checked,
    platforms:[...$('platforms').querySelectorAll('input:checked')].map(i=>i.value)};
}
async function gen(){
  $('g-status').textContent='生成中...';
  const r=await fetch('/api/affiliate/generate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(req())});
  if(!r.ok){$('g-status').textContent='エラー: '+(await r.json()).detail;return;}
  const d=await r.json(); $('g-status').textContent=`✅ ${d.count}件生成`+(d.product.url?'':'（URL未設定）');
  let day='',html='';
  d.posts.forEach((p,i)=>{
    if(p.date!==day){day=p.date;html+=`<div class="day">${esc(day)}</div>`;}
    html+=`<div class="post"><div class="meta"><span class="chip p">${p.persona} ${esc(p.persona_label)}</span><span class="chip">${esc(p.platform)}</span><span class="chip">${esc(p.angle)}</span><span class="chip">${esc(p.format)}</span></div>`
      +(p.script?`<div class="sub">台本</div><pre id="s${i}">${esc(p.script)}</pre><button class="copy" onclick="cp('s${i}')">台本をコピー</button>`:'')
      +`<div class="sub">投稿文</div><pre id="c${i}">${esc(p.caption)}</pre><button class="copy" onclick="cp('c${i}')">投稿文をコピー</button>`
      +(p.disclosure?`<div class="sub warn">☑️ ${esc(p.disclosure)}</div>`:'')+`</div>`;
  });
  $('out').innerHTML=html;
}
async function kit(){
  const r=await fetch('/api/affiliate/outreach',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({
    product_id:$('sel').value||null,commission:+$('commission').value||null,deadline_days:+$('deadline').value||14,
    sender:$('sender').value.trim(),brand_account:$('brand_account').value.trim()})});
  const k=await r.json();
  const parts=[['① 最初のDM','dm_first'],['② 返信がないとき（5日後に1回だけ）','dm_followup'],['③ OKをもらったら','dm_accepted'],['④ 依頼書（③と一緒に送る）','brief']];
  $('kit').innerHTML=parts.map(([t,key])=>`<div class="sub">${t}</div><pre id="k_${key}">${esc(k[key])}</pre><button class="copy" onclick="cp('k_${key}')">コピー</button>`).join('');
}
function cp(id){navigator.clipboard.writeText($(id).textContent);}
async function dl(kind){
  const r=await fetch('/api/affiliate/export.'+kind,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(req())});
  const b=await r.blob(),a=document.createElement('a');
  a.href=URL.createObjectURL(b); a.download=(($('sel').value)||'posts')+'.'+kind; a.click();
}
init();
</script>
</body>
</html>
"""
