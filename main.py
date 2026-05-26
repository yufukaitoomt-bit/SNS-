import asyncio
import re
from collections import Counter
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from scrapers.tiktok import analyze_user, find_viral_accounts
from scrapers.instagram import InstagramScraper

# ─── パターン分析ロジック ─────────────────────────────────────────
JP_STOP = {"の","に","は","を","が","で","と","た","し","て","い","な","も","こ","れ","あ","そ","る","ん","か","ら","く","さ","っ","つ","わ","よ","ね","から","です","ます","した","ある","いる","ない","する","なの","これ","それ","あれ","この","その","あの","で","も"}

def _tokenize(text: str) -> List[str]:
    text = re.sub(r'https?://\S+', '', text)
    hashtags = re.findall(r'#[\w぀-ヿ一-鿿]+', text)
    body = re.sub(r'#[\w぀-ヿ一-鿿]+', '', text)
    en_words = [w.lower() for w in re.findall(r'[a-zA-Z]{2,}', body)]
    jp_words = re.findall(r'[぀-ヿ一-鿿]{2,6}', body)
    jp_words = [w for w in jp_words if w not in JP_STOP]
    return hashtags + en_words + jp_words

def analyze_patterns(accounts: List[dict]) -> dict:
    all_viral_titles = []
    hook_patterns = []
    account_summary = []
    total_viral = 0

    for acc in accounts:
        viral = acc.get("viral_videos") or []
        total_viral += len(viral)
        titles = [v["title"] for v in viral if v.get("title")]
        all_viral_titles.extend(titles)

        for t in titles[:5]:
            if t and len(t) >= 5:
                hook_patterns.append(t[:20])

        avg_plays = (
            sum(v["play_count"] for v in viral) // len(viral) if viral else 0
        )
        account_summary.append({
            "username": acc["username"],
            "follower_count": acc["follower_count"],
            "viral_video_count": acc["viral_video_count"],
            "avg_viral_plays": avg_plays,
            "top_video_plays": viral[0]["play_count"] if viral else 0,
            "tiktok_url": acc.get("tiktok_url", f"https://www.tiktok.com/@{acc['username']}"),
        })

    all_tokens = []
    all_hashtags = []
    for title in all_viral_titles:
        tokens = _tokenize(title)
        hashtags = [t for t in tokens if t.startswith("#")]
        words = [t for t in tokens if not t.startswith("#")]
        all_tokens.extend(words)
        all_hashtags.extend(hashtags)

    top_keywords = [{"word": w, "count": c} for w, c in Counter(all_tokens).most_common(20)]
    top_hashtags = [{"tag": t, "count": c} for t, c in Counter(all_hashtags).most_common(15)]

    unique_hooks = []
    seen_hooks = set()
    for title in all_viral_titles:
        hook = title[:20] if title else ""
        if hook and hook not in seen_hooks:
            seen_hooks.add(hook)
            unique_hooks.append({"hook": hook, "full": title})
        if len(unique_hooks) >= 12:
            break

    all_plays = []
    for acc in accounts:
        for v in (acc.get("viral_videos") or []):
            all_plays.append(v["play_count"])

    return {
        "account_count": len(accounts),
        "total_viral_videos": total_viral,
        "avg_viral_plays": sum(all_plays) // len(all_plays) if all_plays else 0,
        "top_keywords": top_keywords,
        "top_hashtags": top_hashtags,
        "hook_examples": unique_hooks,
        "account_summary": sorted(account_summary, key=lambda x: x["viral_video_count"], reverse=True),
    }


instagram: Optional[InstagramScraper] = None

app = FastAPI(title="SNS Analyzer")

@app.on_event("startup")
async def startup():
    global instagram
    try:
        instagram = InstagramScraper()
    except Exception as e:
        print(f"Instagram初期化スキップ: {e}")
    print("✅ SNS Analyzer 起動完了")


# ─── リクエストモデル ─────────────────────────────────────────────
class TikTokSearchReq(BaseModel):
    queries: List[str]
    max_followers: int = 3000
    min_viral_videos: int = 3
    viral_threshold: int = 10_000


class TikTokUsersReq(BaseModel):
    usernames: List[str]
    viral_threshold: int = 10_000
    min_viral_videos: int = 0

class UserReq(BaseModel):
    username: str
    viral_threshold: int = 10_000

class PatternAnalysisReq(BaseModel):
    usernames: List[str]
    viral_threshold: int = 10_000

class InstagramSearchReq(BaseModel):
    hashtags: List[str]
    max_followers: int = 3000
    min_viral_posts: int = 5
    viral_threshold: int = 1_000


# ─── TikTok エンドポイント ────────────────────────────────────────
@app.post("/api/tiktok/find-viral")
async def tiktok_find_viral(req: TikTokSearchReq):
    loop = asyncio.get_event_loop()
    results = await loop.run_in_executor(
        None,
        lambda: find_viral_accounts(
            queries=req.queries,
            max_followers=req.max_followers,
            min_viral_videos=req.min_viral_videos,
            viral_threshold=req.viral_threshold,
        ),
    )
    return {"count": len(results), "accounts": results}


@app.post("/api/tiktok/analyze-users")
async def tiktok_analyze_users(req: TikTokUsersReq):
    loop = asyncio.get_event_loop()
    results = []
    for uname in req.usernames:
        uname = uname.strip().lstrip("@")
        if not uname:
            continue
        profile = await loop.run_in_executor(
            None,
            lambda u=uname: analyze_user(u, viral_threshold=req.viral_threshold),
        )
        if profile and profile["viral_video_count"] >= req.min_viral_videos:
            results.append(profile)
        await asyncio.sleep(0.5)

    results.sort(key=lambda x: x["viral_video_count"], reverse=True)
    return {"count": len(results), "accounts": results}


@app.post("/api/tiktok/user")
async def tiktok_user(req: UserReq):
    loop = asyncio.get_event_loop()
    profile = await loop.run_in_executor(
        None,
        lambda: analyze_user(req.username, viral_threshold=req.viral_threshold),
    )
    if not profile:
        raise HTTPException(404, f"@{req.username} のデータを取得できません")
    return profile


@app.post("/api/tiktok/analyze-patterns")
async def tiktok_analyze_patterns(req: PatternAnalysisReq):
    loop = asyncio.get_event_loop()
    accounts = []
    for uname in req.usernames:
        uname = uname.strip().lstrip("@")
        if not uname:
            continue
        profile = await loop.run_in_executor(
            None,
            lambda u=uname: analyze_user(u, viral_threshold=req.viral_threshold, max_videos=50),
        )
        if profile:
            accounts.append(profile)
        await asyncio.sleep(0.8)

    if not accounts:
        raise HTTPException(404, "分析できるアカウントが見つかりませんでした")

    return analyze_patterns(accounts)


# ─── Instagram エンドポイント ─────────────────────────────────────
@app.post("/api/instagram/find-viral")
async def instagram_find_viral(req: InstagramSearchReq):
    if not instagram:
        raise HTTPException(503, "Instagramスクレイパー未起動")
    loop = asyncio.get_event_loop()
    results = await loop.run_in_executor(
        None,
        lambda: instagram.find_viral_accounts(
            hashtags=req.hashtags,
            max_followers=req.max_followers,
            min_viral_posts=req.min_viral_posts,
            viral_threshold=req.viral_threshold,
        ),
    )
    return {"count": len(results), "accounts": results}


@app.post("/api/instagram/user")
async def instagram_user(req: UserReq):
    if not instagram:
        raise HTTPException(503, "Instagramスクレイパー未起動")
    loop = asyncio.get_event_loop()
    profile = await loop.run_in_executor(
        None,
        lambda: instagram.get_user_profile(req.username),
    )
    if not profile:
        raise HTTPException(404, f"@{req.username} のデータを取得できません")
    return profile


# ─── フロントエンド ───────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
async def index():
    return HTML_PAGE


HTML_PAGE = """<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>SNS Analyzer — NEW PRIME</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#0f0f0f;color:#f0f0f0;min-height:100vh}
header{background:#1a1a1a;border-bottom:1px solid #2a2a2a;padding:14px 24px;display:flex;align-items:center;gap:10px}
header h1{font-size:17px;font-weight:700}
.badge{background:#fe2c55;color:#fff;font-size:11px;padding:2px 8px;border-radius:20px;font-weight:600}
.badge.ig{background:linear-gradient(135deg,#f09433,#dc2743,#bc1888)}
main{max-width:1000px;margin:0 auto;padding:28px 16px}
.tabs{display:flex;gap:4px;margin-bottom:20px;flex-wrap:wrap}
.tab{padding:8px 18px;border-radius:8px;border:none;cursor:pointer;font-size:13px;font-weight:600;background:#1a1a1a;color:#888;transition:all .2s}
.tab.active{background:#fe2c55;color:#fff}
.panel{display:none}.panel.active{display:block}
.card{background:#1a1a1a;border:1px solid #2a2a2a;border-radius:12px;padding:20px;margin-bottom:14px}
.card h2{font-size:13px;font-weight:700;color:#888;margin-bottom:14px;text-transform:uppercase;letter-spacing:.5px}
.tip{font-size:12px;color:#666;margin-bottom:12px;padding:10px 12px;background:#111;border-radius:8px;border-left:3px solid #fe2c55}
.form-row{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:10px}
.form-group{display:flex;flex-direction:column;gap:5px}
label{font-size:11px;color:#888;font-weight:600;text-transform:uppercase;letter-spacing:.3px}
input,textarea{background:#0f0f0f;border:1px solid #333;color:#f0f0f0;padding:9px 11px;border-radius:7px;font-size:13px;width:100%;outline:none;transition:border .2s}
input:focus,textarea:focus{border-color:#fe2c55}
textarea{resize:vertical;min-height:90px;font-family:monospace;font-size:12px}
button.run{width:100%;padding:11px;border-radius:8px;border:none;background:#fe2c55;color:#fff;font-size:14px;font-weight:700;cursor:pointer;margin-top:6px;transition:opacity .2s}
button.run:disabled{opacity:.35;cursor:not-allowed}
.status{margin-top:10px;font-size:12px;color:#888;min-height:18px}
.status.running{color:#f0c040}.status.done{color:#40d080}.status.error{color:#ff6060}
.results{margin-top:20px}
.rc{background:#1a1a1a;border:1px solid #2a2a2a;border-radius:10px;padding:14px;margin-bottom:10px}
.rh{display:flex;align-items:flex-start;justify-content:space-between;margin-bottom:10px}
.username a{color:#f0f0f0;text-decoration:none;font-weight:700;font-size:15px}
.username a:hover{color:#fe2c55}
.nickname{color:#888;font-size:12px;margin-top:2px}
.metrics{display:flex;gap:14px;flex-wrap:wrap;margin:10px 0}
.metric{text-align:center}
.metric-val{font-size:17px;font-weight:800;color:#fe2c55}
.metric-label{font-size:10px;color:#555;margin-top:1px}
.vbadge{background:#fe2c55;color:#fff;padding:3px 10px;border-radius:20px;font-size:12px;font-weight:700;white-space:nowrap}
.vlist{margin-top:8px}
.vi{display:flex;justify-content:space-between;align-items:center;padding:5px 0;border-bottom:1px solid #222;font-size:12px}
.vi:last-child{border-bottom:none}
.vi-desc{color:#bbb;flex:1;margin-right:10px;overflow:hidden;white-space:nowrap;text-overflow:ellipsis}
.vi-plays{color:#fe2c55;font-weight:700;white-space:nowrap}
.no-results{text-align:center;color:#444;padding:40px;font-size:13px}
.spinner{display:inline-block;width:13px;height:13px;border:2px solid #444;border-top-color:#fe2c55;border-radius:50%;animation:spin .7s linear infinite;margin-right:5px;vertical-align:middle}
@keyframes spin{to{transform:rotate(360deg)}}
</style>
</head>
<body>
<header>
  <h1>SNS Analyzer</h1>
  <span class="badge">TikTok</span>
  <span class="badge ig">Instagram</span>
</header>
<main>
  <div class="tabs">
    <button class="tab active" onclick="sw('tt-auto')">TikTok 自動発掘</button>
    <button class="tab" onclick="sw('tt-manual')">TikTok 手動分析</button>
    <button class="tab" onclick="sw('tt-pattern')">🔥 バズパターン分析</button>
    <button class="tab" onclick="sw('tt-user')">TikTok ユーザー調査</button>
    <button class="tab" onclick="sw('ig-auto')">Instagram 発掘</button>
    <button class="tab" onclick="sw('ig-user')">Instagram ユーザー調査</button>
  </div>

  <!-- TikTok 自動発掘 -->
  <div id="panel-tt-auto" class="panel active">
    <div class="card">
      <h2>TikTok — キーワード/ハッシュタグで自動発掘</h2>
      <div class="tip">💡 キーワード単体でも `#` 付きでもOK。タグページ・検索ページの両方から候補を収集します。結果が出ない場合はバズ判定の再生数を下げてください。</div>
      <div class="form-group" style="margin-bottom:10px">
        <label>検索ワード（1行1件、#付きでもOK）</label>
        <textarea id="tt-queries" placeholder="ファッション&#10;#営業バイト&#10;大学生 稼ぐ&#10;#代理店求人"></textarea>
      </div>
      <div class="form-row">
        <div class="form-group"><label>最大フォロワー数</label><input type="number" id="tt-max-f" value="3000"></div>
        <div class="form-group"><label>最小バズ動画数</label><input type="number" id="tt-min-v" value="3"></div>
        <div class="form-group"><label>バズ判定（再生数以上）</label><input type="number" id="tt-threshold" value="10000"></div>
      </div>
      <button class="run" id="tt-auto-btn" onclick="runAutoSearch()">🔍 発掘スタート</button>
      <div class="status" id="tt-auto-status"></div>
    </div>
    <div id="tt-auto-results" class="results"></div>
  </div>

  <!-- TikTok 手動分析 -->
  <div id="panel-tt-manual" class="panel">
    <div class="card">
      <h2>TikTok — ユーザー名リスト一括分析</h2>
      <div class="tip">💡 TikTokで手動検索して見つけた @ユーザー名を貼り付けると、フォロワー数・バズ動画数を一括取得します。</div>
      <div class="form-group" style="margin-bottom:10px">
        <label>ユーザー名（1行1件、@不要）</label>
        <textarea id="tt-manual-users" placeholder="username1&#10;username2&#10;username3"></textarea>
      </div>
      <div class="form-row">
        <div class="form-group"><label>バズ判定（再生数以上）</label><input type="number" id="tt-manual-threshold" value="10000"></div>
        <div class="form-group"><label>最小バズ動画数（0=全表示）</label><input type="number" id="tt-manual-min" value="0"></div>
      </div>
      <button class="run" id="tt-manual-btn" onclick="runManualAnalysis()">📊 一括分析</button>
      <div class="status" id="tt-manual-status"></div>
    </div>
    <div id="tt-manual-results" class="results"></div>
  </div>

  <!-- バズパターン分析 -->
  <div id="panel-tt-pattern" class="panel">
    <div class="card">
      <h2>バズパターン分析 — 複数アカウントの共通点を抽出</h2>
      <div class="tip">💡 手動分析で見つけたアカウント名を貼り付けると、バズ動画に共通するキーワード・ハッシュタグ・フックを自動分析します。</div>
      <div class="form-group" style="margin-bottom:10px">
        <label>分析するアカウント（1行1件、@不要）</label>
        <textarea id="pt-users" placeholder="username1&#10;username2&#10;username3&#10;username4&#10;username5" style="min-height:120px"></textarea>
      </div>
      <div class="form-row">
        <div class="form-group"><label>バズ判定（再生数以上）</label><input type="number" id="pt-threshold" value="10000"></div>
      </div>
      <button class="run" id="pt-btn" onclick="runPatternAnalysis()">🔍 パターン分析スタート</button>
      <div class="status" id="pt-status"></div>
    </div>
    <div id="pt-results" class="results"></div>
  </div>

  <!-- TikTok ユーザー個別調査 -->
  <div id="panel-tt-user" class="panel">
    <div class="card">
      <h2>TikTok — ユーザー個別調査</h2>
      <div class="form-group" style="margin-bottom:10px">
        <label>ユーザー名（@なし）</label>
        <input type="text" id="tt-single-user" placeholder="username">
      </div>
      <div class="form-row">
        <div class="form-group"><label>バズ判定（再生数以上）</label><input type="number" id="tt-single-threshold" value="10000"></div>
      </div>
      <button class="run" id="tt-user-btn" onclick="runUserSearch()">📊 調査する</button>
      <div class="status" id="tt-user-status"></div>
    </div>
    <div id="tt-user-results" class="results"></div>
  </div>

  <!-- Instagram 自動発掘 -->
  <div id="panel-ig-auto" class="panel">
    <div class="card">
      <h2>Instagram — ハッシュタグで自動発掘</h2>
      <div class="form-group" style="margin-bottom:10px">
        <label>ハッシュタグ（1行1件、#不要）</label>
        <textarea id="ig-tags" placeholder="営業バイト&#10;大学生副業&#10;歩合&#10;稼ぐ"></textarea>
      </div>
      <div class="form-row">
        <div class="form-group"><label>最大フォロワー数</label><input type="number" id="ig-max-f" value="3000"></div>
        <div class="form-group"><label>最小バズ投稿数</label><input type="number" id="ig-min-v" value="3"></div>
        <div class="form-group"><label>バズ判定（いいね以上）</label><input type="number" id="ig-threshold" value="1000"></div>
      </div>
      <button class="run" id="ig-auto-btn" onclick="runIgSearch()">🔍 発掘スタート</button>
      <div class="status" id="ig-auto-status"></div>
    </div>
    <div id="ig-auto-results" class="results"></div>
  </div>

  <!-- Instagram ユーザー個別調査 -->
  <div id="panel-ig-user" class="panel">
    <div class="card">
      <h2>Instagram — ユーザー個別調査</h2>
      <div class="form-group" style="margin-bottom:10px">
        <label>ユーザー名（@なし）</label>
        <input type="text" id="ig-single-user" placeholder="username">
      </div>
      <button class="run" id="ig-user-btn" onclick="runIgUser()">📊 調査する</button>
      <div class="status" id="ig-user-status"></div>
    </div>
    <div id="ig-user-results" class="results"></div>
  </div>
</main>

<script>
const TABS = ['tt-auto','tt-manual','tt-pattern','tt-user','ig-auto','ig-user'];

function sw(name){
  document.querySelectorAll('.tab').forEach((t,i)=>t.classList.toggle('active',TABS[i]===name));
  document.querySelectorAll('.panel').forEach(p=>p.classList.remove('active'));
  document.getElementById('panel-'+name).classList.add('active');
}
function fmt(n){
  if(!n||n<0)return '?';
  if(n>=1e6)return(n/1e6).toFixed(1)+'M';
  if(n>=1e4)return Math.round(n/1e4)+'万';
  if(n>=1e3)return(n/1e3).toFixed(1)+'K';
  return n.toLocaleString();
}
function setStatus(id,msg,type=''){
  const el=document.getElementById(id);
  el.className='status '+type;
  el.innerHTML=type==='running'?`<span class="spinner"></span>${msg}`:msg;
}

function renderTT(accounts, containerId){
  const el=document.getElementById(containerId);
  if(!accounts.length){el.innerHTML='<div class="no-results">該当アカウントなし。条件を緩めるか別のキーワードで試してください。</div>';return;}
  el.innerHTML=accounts.map(a=>`
    <div class="rc">
      <div class="rh">
        <div>
          <div class="username">
            <a href="${a.tiktok_url}" target="_blank">@${a.username}</a>
          </div>
        </div>
        <span class="vbadge">🔥 バズ${a.viral_video_count}本</span>
      </div>
      <div class="metrics">
        <div class="metric"><div class="metric-val">${fmt(a.follower_count)}</div><div class="metric-label">フォロワー</div></div>
        <div class="metric"><div class="metric-val">${a.video_count}</div><div class="metric-label">動画数</div></div>
        <div class="metric"><div class="metric-val">${a.viral_video_count}</div><div class="metric-label">バズ動画</div></div>
      </div>
      <div class="vlist">
        ${(a.viral_videos||a.top_videos||[]).slice(0,5).map(v=>`
          <div class="vi">
            <span class="vi-desc">${v.title||'(タイトルなし)'}</span>
            <span class="vi-plays">▶ ${fmt(v.play_count)}</span>
          </div>`).join('')}
      </div>
    </div>`).join('');
}

function renderIG(accounts, containerId){
  const el=document.getElementById(containerId);
  if(!accounts.length){el.innerHTML='<div class="no-results">該当アカウントなし。</div>';return;}
  el.innerHTML=accounts.map(a=>`
    <div class="rc">
      <div class="rh">
        <div>
          <div class="username"><a href="https://www.instagram.com/${a.username}/" target="_blank">@${a.username}</a></div>
          <div class="nickname">${a.full_name||''}</div>
        </div>
        <span class="vbadge" style="background:linear-gradient(135deg,#f09433,#bc1888)">🔥 バズ${a.viral_post_count}件</span>
      </div>
      <div class="metrics">
        <div class="metric"><div class="metric-val">${fmt(a.follower_count)}</div><div class="metric-label">フォロワー</div></div>
        <div class="metric"><div class="metric-val">${a.post_count}</div><div class="metric-label">投稿数</div></div>
        <div class="metric"><div class="metric-val">${a.viral_post_count}</div><div class="metric-label">バズ投稿</div></div>
      </div>
      ${a.bio?`<div style="font-size:11px;color:#666;margin-bottom:8px">${a.bio}</div>`:''}
      <div class="vlist">
        ${(a.viral_posts||[]).slice(0,5).map(v=>`
          <div class="vi">
            <span class="vi-desc"><a href="${v.url}" target="_blank" style="color:#bbb;text-decoration:none">${v.caption||'(キャプションなし)'}</a></span>
            <span class="vi-plays">❤ ${fmt(v.likes)}</span>
          </div>`).join('')}
      </div>
    </div>`).join('');
}

async function runAutoSearch(){
  const queries=document.getElementById('tt-queries').value.split('\\n').map(s=>s.trim()).filter(Boolean);
  if(!queries.length)return alert('キーワードを入力してください');
  const btn=document.getElementById('tt-auto-btn');
  btn.disabled=true;
  setStatus('tt-auto-status','yt-dlpで検索中... 数分かかります','running');
  document.getElementById('tt-auto-results').innerHTML='';
  try{
    const res=await fetch('/api/tiktok/find-viral',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({
      queries,
      max_followers:+document.getElementById('tt-max-f').value,
      min_viral_videos:+document.getElementById('tt-min-v').value,
      viral_threshold:+document.getElementById('tt-threshold').value,
    })});
    const data=await res.json();
    if(data.count===0){
      setStatus('tt-auto-status','該当なし。バズ判定の再生数を下げる / 最小バズ動画数を0にする / フォロワー上限を上げる で再試行してください','done');
    }else{
      setStatus('tt-auto-status',`✅ 完了 — ${data.count}件発見`,'done');
    }
    renderTT(data.accounts||[],'tt-auto-results');
  }catch(e){setStatus('tt-auto-status','エラー: '+e.message,'error');}
  finally{btn.disabled=false;}
}

async function runManualAnalysis(){
  const usernames=document.getElementById('tt-manual-users').value.split('\\n').map(s=>s.trim().replace(/^@/,'')).filter(Boolean);
  if(!usernames.length)return alert('ユーザー名を入力してください');
  const btn=document.getElementById('tt-manual-btn');
  btn.disabled=true;
  setStatus('tt-manual-status',`${usernames.length}件を分析中...`,'running');
  document.getElementById('tt-manual-results').innerHTML='';
  try{
    const res=await fetch('/api/tiktok/analyze-users',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({
      usernames,
      viral_threshold:+document.getElementById('tt-manual-threshold').value,
      min_viral_videos:+document.getElementById('tt-manual-min').value,
    })});
    const data=await res.json();
    setStatus('tt-manual-status',`✅ 完了 — ${data.count}件分析済み`,'done');
    renderTT(data.accounts||[],'tt-manual-results');
  }catch(e){setStatus('tt-manual-status','エラー: '+e.message,'error');}
  finally{btn.disabled=false;}
}

async function runUserSearch(){
  const u=document.getElementById('tt-single-user').value.trim();
  if(!u)return alert('ユーザー名を入力してください');
  const btn=document.getElementById('tt-user-btn');
  btn.disabled=true;
  setStatus('tt-user-status','取得中...','running');
  document.getElementById('tt-user-results').innerHTML='';
  try{
    const res=await fetch('/api/tiktok/user',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:u.replace(/^@/,''),viral_threshold:+document.getElementById('tt-single-threshold').value})});
    if(!res.ok)throw new Error((await res.json()).detail);
    const a=await res.json();
    setStatus('tt-user-status','✅ 取得完了','done');
    renderTT([a],'tt-user-results');
  }catch(e){setStatus('tt-user-status','エラー: '+e.message,'error');}
  finally{btn.disabled=false;}
}

async function runPatternAnalysis(){
  const usernames=document.getElementById('pt-users').value.split('\\n').map(s=>s.trim().replace(/^@/,'')).filter(Boolean);
  if(!usernames.length)return alert('アカウント名を入力してください');
  const btn=document.getElementById('pt-btn');
  btn.disabled=true;
  setStatus('pt-status',`${usernames.length}アカウントのバズ動画を収集・分析中...`,'running');
  document.getElementById('pt-results').innerHTML='';
  try{
    const res=await fetch('/api/tiktok/analyze-patterns',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({
      usernames,
      viral_threshold:+document.getElementById('pt-threshold').value,
    })});
    if(!res.ok)throw new Error((await res.json()).detail);
    const d=await res.json();
    setStatus('pt-status',`✅ 完了 — ${d.account_count}アカウント / バズ動画${d.total_viral_videos}本を分析`,'done');
    renderPattern(d,'pt-results');
  }catch(e){setStatus('pt-status','エラー: '+e.message,'error');}
  finally{btn.disabled=false;}
}

function renderPattern(d, containerId){
  const el=document.getElementById(containerId);
  const fmtPlays = n => n>=1e6?(n/1e6).toFixed(1)+'M':n>=1e4?Math.round(n/1e4)+'万':n>=1e3?(n/1e3).toFixed(1)+'K':n.toLocaleString();

  el.innerHTML=`
    <div class="rc" style="border-color:#fe2c55">
      <div style="display:flex;gap:24px;flex-wrap:wrap;padding:4px 0">
        <div class="metric"><div class="metric-val">${d.account_count}</div><div class="metric-label">分析アカウント数</div></div>
        <div class="metric"><div class="metric-val">${d.total_viral_videos}</div><div class="metric-label">バズ動画合計</div></div>
        <div class="metric"><div class="metric-val">${fmtPlays(d.avg_viral_plays)}</div><div class="metric-label">平均バズ再生数</div></div>
      </div>
    </div>

    <div class="rc">
      <div style="font-size:12px;font-weight:700;color:#888;margin-bottom:12px;text-transform:uppercase;letter-spacing:.5px">アカウント別比較</div>
      <div style="overflow-x:auto">
        <table style="width:100%;border-collapse:collapse;font-size:12px">
          <thead>
            <tr style="color:#666;border-bottom:1px solid #2a2a2a">
              <th style="text-align:left;padding:6px 8px">アカウント</th>
              <th style="text-align:right;padding:6px 8px">フォロワー</th>
              <th style="text-align:right;padding:6px 8px">バズ動画</th>
              <th style="text-align:right;padding:6px 8px">平均再生</th>
              <th style="text-align:right;padding:6px 8px">最高再生</th>
            </tr>
          </thead>
          <tbody>
            ${d.account_summary.map(a=>`
              <tr style="border-bottom:1px solid #1f1f1f">
                <td style="padding:7px 8px"><a href="${a.tiktok_url}" target="_blank" style="color:#fe2c55;text-decoration:none;font-weight:600">@${a.username}</a></td>
                <td style="text-align:right;padding:7px 8px;color:#bbb">${fmtPlays(a.follower_count)}</td>
                <td style="text-align:right;padding:7px 8px;color:#fe2c55;font-weight:700">${a.viral_video_count}本</td>
                <td style="text-align:right;padding:7px 8px;color:#bbb">${fmtPlays(a.avg_viral_plays)}</td>
                <td style="text-align:right;padding:7px 8px;color:#bbb">${fmtPlays(a.top_video_plays)}</td>
              </tr>`).join('')}
          </tbody>
        </table>
      </div>
    </div>

    <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:12px">
      <div class="rc">
        <div style="font-size:12px;font-weight:700;color:#888;margin-bottom:12px;text-transform:uppercase;letter-spacing:.5px">よく使われるキーワード</div>
        ${d.top_keywords.length ? d.top_keywords.map((k,i)=>`
          <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px">
            <span style="color:#555;font-size:11px;width:18px;text-align:right">${i+1}</span>
            <div style="flex:1;background:#111;border-radius:4px;overflow:hidden">
              <div style="background:linear-gradient(90deg,#3a0010,#0f0f0f);width:${Math.min(100,k.count*8)}%;height:22px;display:flex;align-items:center;padding:0 8px">
                <span style="font-size:13px;color:#f0f0f0;white-space:nowrap">${k.word}</span>
              </div>
            </div>
            <span style="color:#fe2c55;font-weight:700;font-size:12px;white-space:nowrap">${k.count}回</span>
          </div>`).join('') : '<div style="color:#444;font-size:12px">データなし</div>'}
      </div>
      <div class="rc">
        <div style="font-size:12px;font-weight:700;color:#888;margin-bottom:12px;text-transform:uppercase;letter-spacing:.5px">よく使われるハッシュタグ</div>
        ${d.top_hashtags.length ? d.top_hashtags.map((t,i)=>`
          <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px">
            <span style="color:#555;font-size:11px;width:18px;text-align:right">${i+1}</span>
            <span style="flex:1;font-size:13px;color:#60b0ff">${t.tag}</span>
            <span style="color:#fe2c55;font-weight:700;font-size:12px">${t.count}回</span>
          </div>`).join('') : '<div style="color:#444;font-size:12px">ハッシュタグなし</div>'}
      </div>
    </div>

    <div class="rc">
      <div style="font-size:12px;font-weight:700;color:#888;margin-bottom:12px;text-transform:uppercase;letter-spacing:.5px">バズ動画の冒頭パターン（フック例）</div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px">
        ${d.hook_examples.map(h=>`
          <div style="background:#111;border-radius:8px;padding:10px 12px;border-left:3px solid #fe2c55">
            <div style="font-size:13px;color:#f0f0f0;margin-bottom:4px">${h.hook}${h.full.length>20?'…':''}</div>
            ${h.full.length>20?`<div style="font-size:11px;color:#555;overflow:hidden;white-space:nowrap;text-overflow:ellipsis">${h.full}</div>`:''}
          </div>`).join('')}
      </div>
    </div>
  `;
}

async function runIgSearch(){
  const hashtags=document.getElementById('ig-tags').value.split('\\n').map(s=>s.trim().replace(/^#/,'')).filter(Boolean);
  if(!hashtags.length)return alert('ハッシュタグを入力してください');
  const btn=document.getElementById('ig-auto-btn');
  btn.disabled=true;
  setStatus('ig-auto-status','検索・分析中...','running');
  document.getElementById('ig-auto-results').innerHTML='';
  try{
    const res=await fetch('/api/instagram/find-viral',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({
      hashtags,
      max_followers:+document.getElementById('ig-max-f').value,
      min_viral_posts:+document.getElementById('ig-min-v').value,
      viral_threshold:+document.getElementById('ig-threshold').value,
    })});
    const data=await res.json();
    setStatus('ig-auto-status',`✅ 完了 — ${data.count}件発見`,'done');
    renderIG(data.accounts||[],'ig-auto-results');
  }catch(e){setStatus('ig-auto-status','エラー: '+e.message,'error');}
  finally{btn.disabled=false;}
}

async function runIgUser(){
  const u=document.getElementById('ig-single-user').value.trim();
  if(!u)return alert('ユーザー名を入力してください');
  const btn=document.getElementById('ig-user-btn');
  btn.disabled=true;
  setStatus('ig-user-status','取得中...','running');
  document.getElementById('ig-user-results').innerHTML='';
  try{
    const res=await fetch('/api/instagram/user',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:u.replace(/^@/,'')})});
    if(!res.ok)throw new Error((await res.json()).detail);
    const a=await res.json();
    setStatus('ig-user-status','✅ 取得完了','done');
    renderIG([a],'ig-user-results');
  }catch(e){setStatus('ig-user-status','エラー: '+e.message,'error');}
  finally{btn.disabled=false;}
}
</script>
</body>
</html>
"""
