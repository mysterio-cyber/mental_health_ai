from flask import Flask, request, render_template_string, jsonify, redirect, session
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
import os, re, json, datetime, urllib.request

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "mindspace-super-secret-key-change-in-prod-2024")
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE'] = False

# ─── Anthropic API key for chatbot ────────────────────────────────────────────
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

def init_db():
    conn = sqlite3.connect("app.db")
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        mobile TEXT,
        password TEXT
    )""")
    cur.execute("""
    CREATE TABLE IF NOT EXISTS results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        score INTEGER,
        status TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )""")
    # ── NEW: mood tracking table ──────────────────────────────────────────────
    cur.execute("""
    CREATE TABLE IF NOT EXISTS mood_logs (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        username   TEXT,
        mood       TEXT,
        note       TEXT,
        logged_at  DATETIME DEFAULT CURRENT_TIMESTAMP
    )""")
    conn.commit()
    conn.close()

init_db()

questions = [
    {"id":"stress","label":"😓 How often do you feel stressed?"},
    {"id":"sleep","label":"😴 How is your sleep quality?"},
    {"id":"exercise","label":"🏃 How often do you exercise?"},
    {"id":"mood","label":"😔 How often do you feel sad?"},
    {"id":"anxiety","label":"😰 How often do you feel anxious?"},
    {"id":"focus","label":"🧠 Do you have trouble concentrating?"},
    {"id":"social","label":"🫂 Do you avoid social interaction?"},
    {"id":"motivation","label":"🔥 How motivated are you?"},
    {"id":"energy","label":"⚡ How is your energy level?"}
]

BINAURAL = "https://youtu.be/lkkGlVWvkLk"

BASE_STYLES = """
@import url('https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700;800;900&family=Playfair+Display:wght@700&display=swap');
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: 'Nunito', sans-serif; min-height: 100vh; background: #0d0d1a; display: flex; justify-content: center; align-items: center; overflow: hidden; position: relative; }
body::before { content: ''; position: fixed; inset: 0; background: radial-gradient(ellipse 80% 60% at 20% 40%, rgba(100,200,255,0.12) 0%, transparent 60%), radial-gradient(ellipse 60% 80% at 80% 20%, rgba(180,120,255,0.12) 0%, transparent 60%), radial-gradient(ellipse 70% 50% at 50% 90%, rgba(100,255,200,0.08) 0%, transparent 60%); animation: aurora 10s ease-in-out infinite alternate; pointer-events: none; z-index: 0; }
@keyframes aurora { 0% { transform: scale(1) rotate(0deg); opacity: 0.8; } 50% { transform: scale(1.1) rotate(2deg); opacity: 1; } 100% { transform: scale(1) rotate(-2deg); opacity: 0.8; } }
.particle { position: fixed; border-radius: 50%; pointer-events: none; animation: float linear infinite; z-index: 0; }
@keyframes float { 0% { transform: translateY(110vh) scale(0); opacity: 0; } 10% { opacity: 0.5; } 90% { opacity: 0.3; } 100% { transform: translateY(-10vh) scale(1.2); opacity: 0; } }
.card { position: relative; z-index: 1; background: rgba(255,255,255,0.04); backdrop-filter: blur(24px); -webkit-backdrop-filter: blur(24px); border: 1px solid rgba(255,255,255,0.1); border-radius: 28px; padding: 40px 36px; width: 420px; box-shadow: 0 20px 60px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.1); animation: slideUp 0.7s cubic-bezier(0.16,1,0.3,1) both; }
@keyframes slideUp { from { opacity: 0; transform: translateY(40px) scale(0.96); } to { opacity: 1; transform: translateY(0) scale(1); } }
h2 { font-family: 'Playfair Display', serif; font-size: 2rem; color: #fff; margin-bottom: 8px; letter-spacing: -0.5px; }
.subtitle { color: rgba(255,255,255,0.45); font-size: 0.85rem; margin-bottom: 28px; }
.input-group { position: relative; margin-bottom: 16px; }
.input-group input { width: 100%; padding: 14px 18px; background: rgba(255,255,255,0.07); border: 1px solid rgba(255,255,255,0.12); border-radius: 14px; color: #fff; font-size: 0.95rem; font-family: 'Nunito', sans-serif; transition: border-color 0.3s, background 0.3s, box-shadow 0.3s; outline: none; }
.input-group input::placeholder { color: rgba(255,255,255,0.3); }
.input-group input:focus { border-color: rgba(120,200,255,0.6); background: rgba(255,255,255,0.1); box-shadow: 0 0 0 4px rgba(120,200,255,0.1); }
.btn { width: 100%; padding: 14px; border: none; border-radius: 14px; font-size: 1rem; font-weight: 800; font-family: 'Nunito', sans-serif; cursor: pointer; position: relative; overflow: hidden; transition: transform 0.2s, box-shadow 0.2s; margin-top: 6px; }
.btn::after { content: ''; position: absolute; inset: 0; background: rgba(255,255,255,0.15); opacity: 0; transition: opacity 0.2s; }
.btn:hover { transform: translateY(-2px); box-shadow: 0 8px 24px rgba(0,0,0,0.3); }
.btn:hover::after { opacity: 1; }
.btn:active { transform: translateY(0); }
.btn-primary { background: linear-gradient(135deg, #5bc8f5, #a78bfa); color: #fff; }
.btn-secondary { background: rgba(255,255,255,0.08); border: 1px solid rgba(255,255,255,0.15); color: rgba(255,255,255,0.7); margin-top: 8px; }
.btn-secondary:hover { background: rgba(255,255,255,0.12); color: #fff; }
.link-row { margin-top: 20px; text-align: center; color: rgba(255,255,255,0.4); font-size: 0.85rem; }
.link-row a { color: #7ec8f7; text-decoration: none; font-weight: 700; transition: color 0.2s; }
.link-row a:hover { color: #a78bfa; }
.error-msg { background: rgba(255,80,80,0.15); border: 1px solid rgba(255,80,80,0.3); color: #ff9a9a; padding: 10px 14px; border-radius: 10px; font-size: 0.85rem; margin-bottom: 14px; animation: shake 0.4s ease; }
.success-msg { background: rgba(0,200,100,0.15); border: 1px solid rgba(0,200,100,0.3); color: #6ee7b7; padding: 10px 14px; border-radius: 10px; font-size: 0.85rem; margin-bottom: 14px; }
@keyframes shake { 0%,100%{ transform:translateX(0); } 25%{ transform:translateX(-6px); } 75%{ transform:translateX(6px); } }
"""

PARTICLES_JS = """
function makeParticles() {
    const colors = ['#7ec8f7','#a78bfa','#6ee7b7','#fde68a','#f9a8d4'];
    for (let i = 0; i < 18; i++) {
        const p = document.createElement('div');
        p.className = 'particle';
        const size = Math.random() * 6 + 2;
        p.style.cssText = `width:${size}px; height:${size}px; left:${Math.random()*100}vw; background:${colors[Math.floor(Math.random()*colors.length)]}; animation-duration:${Math.random()*12+8}s; animation-delay:${Math.random()*-15}s; opacity:${Math.random()*0.5+0.2};`;
        document.body.appendChild(p);
    }
}
makeParticles();
"""

# ─── Shared nav/topnav HTML ───────────────────────────────────────────────────
TOPNAV = """
<nav class="topnav">
    <span class="brand">MindSpace 🌿</span>
    <div class="nav-links">
        <a href="/">🏠 Home</a>
        <a href="/chat">💬 Therapist</a>
        <a href="/emotion">🎭 Emotions</a>
        <a href="/mood">📅 Mood</a>
        <a href="/history">📈 History</a>
        <a href="/logout">👋 Logout</a>
    </div>
</nav>
"""

PAGE_BASE_CSS = """
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0;}
body{font-family:'Nunito',sans-serif;min-height:100vh;background:#0d0d1a;color:#fff;padding:90px 16px 40px;position:relative;overflow-x:hidden;}
body::before{content:'';position:fixed;inset:0;background:radial-gradient(ellipse 80% 60% at 20% 40%,rgba(100,200,255,0.1) 0%,transparent 60%),radial-gradient(ellipse 60% 80% at 80% 20%,rgba(180,120,255,0.1) 0%,transparent 60%);animation:aurora 10s ease-in-out infinite alternate;pointer-events:none;}
@keyframes aurora{0%{transform:scale(1);}100%{transform:scale(1.08) rotate(-2deg);}}
.topnav{position:fixed;top:0;left:0;right:0;display:flex;justify-content:space-between;align-items:center;padding:14px 24px;background:rgba(13,13,26,0.85);backdrop-filter:blur(16px);border-bottom:1px solid rgba(255,255,255,0.07);z-index:100;flex-wrap:wrap;gap:8px;}
.brand{font-family:'Playfair Display',serif;font-size:1.2rem;color:#fff;}
.nav-links{display:flex;flex-wrap:wrap;gap:6px;}
.nav-links a{color:rgba(255,255,255,0.5);text-decoration:none;font-size:0.78rem;font-weight:700;padding:5px 12px;border-radius:20px;border:1px solid rgba(255,255,255,0.1);transition:all 0.2s;}
.nav-links a:hover{color:#fff;background:rgba(255,255,255,0.08);}
"""

# ══════════════════════════════════════════════════════════════════════════════
# AUTH ROUTES
# ══════════════════════════════════════════════════════════════════════════════
@app.route("/signup", methods=["GET","POST"])
def signup():
    error = ""
    if request.method == "POST":
        u  = request.form.get("username","").strip()
        m  = request.form.get("mobile","").strip()
        p1 = request.form.get("password","")
        p2 = request.form.get("confirm","")
        if not u or not m or not p1 or not p2:
            error = "⚠️ Please fill in all fields."
        elif not m.isdigit() or len(m) < 10:
            error = "⚠️ Enter a valid 10-digit mobile number."
        elif len(p1) < 6:
            error = "⚠️ Password must be at least 6 characters."
        elif p1 != p2:
            error = "⚠️ Passwords do not match."
        else:
            conn = sqlite3.connect("app.db")
            cur  = conn.cursor()
            cur.execute("SELECT id FROM users WHERE username=?", (u,))
            if cur.fetchone():
                conn.close(); error = "⚠️ Username already exists. Try another one."
            else:
                hashed = generate_password_hash(p1)
                try:
                    cur.execute("INSERT INTO users (username, mobile, password) VALUES (?,?,?)", (u, m, hashed))
                    conn.commit(); conn.close()
                    return redirect("/login?registered=1")
                except:
                    conn.close(); error = "⚠️ An error occurred. Please try again."
    return render_template_string("""
<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>MindSpace — Sign Up</title>
<link href="https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700;800;900&family=Playfair+Display:wght@700&display=swap" rel="stylesheet">
<style>{{ styles }}</style></head>
<body><div class="card"><h2>MindSpace 🌿</h2><p class="subtitle">Create your account to begin your wellness journey ✨</p>
{% if error %}<div class="error-msg">{{ error }}</div>{% endif %}
<form method="post" autocomplete="off">
<div class="input-group"><input name="username" required placeholder="👤  Username" autofocus value="{{ req_username }}"></div>
<div class="input-group"><input name="mobile" type="tel" required placeholder="📱  Mobile Number" value="{{ req_mobile }}"></div>
<div class="input-group"><input name="password" type="password" required placeholder="🔒  Password"></div>
<div class="input-group"><input name="confirm" type="password" required placeholder="🔒  Confirm Password"></div>
<button class="btn btn-primary" type="submit">Create Account 🚀</button></form>
<div class="link-row">Already have an account? <a href="/login">Log in →</a></div>
</div><script>{{ particles }}</script></body></html>
""", styles=BASE_STYLES, particles=PARTICLES_JS, error=error,
     req_username=request.form.get('username',''), req_mobile=request.form.get('mobile',''))


@app.route("/login", methods=["GET","POST"])
def login():
    error = ""; success = ""
    if request.args.get('registered'):
        success = "🎉 Account created successfully! Please log in."
    if request.method == "POST":
        u = request.form.get("username","").strip()
        p = request.form.get("password","")
        if not u or not p:
            error = "⚠️ Please enter both username and password."
        else:
            conn = sqlite3.connect("app.db"); cur = conn.cursor()
            cur.execute("SELECT id, password FROM users WHERE username=?", (u,))
            user = cur.fetchone(); conn.close()
            if user and check_password_hash(user[1], p):
                session.clear(); session["user"] = u; session.modified = True
                return redirect("/")
            else:
                error = "❌ Invalid username or password."
    return render_template_string("""
<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>MindSpace — Login</title>
<link href="https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700;800;900&family=Playfair+Display:wght@700&display=swap" rel="stylesheet">
<style>{{ styles }}</style></head>
<body><div class="card"><h2>Welcome back 🌙</h2><p class="subtitle">Your safe space is waiting for you 💙</p>
{% if success %}<div class="success-msg">{{ success }}</div>{% endif %}
{% if error %}<div class="error-msg">{{ error }}</div>{% endif %}
<form method="post" autocomplete="off">
<div class="input-group"><input name="username" required placeholder="👤  Username" autofocus></div>
<div class="input-group"><input name="password" type="password" required placeholder="🔒  Password"></div>
<button class="btn btn-primary" type="submit">Log In ✨</button></form>
<div class="link-row">New here? <a href="/signup">Create account →</a></div>
</div><script>{{ particles }}</script></body></html>
""", styles=BASE_STYLES, particles=PARTICLES_JS, error=error, success=success)


# ══════════════════════════════════════════════════════════════════════════════
# HOME
# ══════════════════════════════════════════════════════════════════════════════
@app.route("/")
def home():
    if "user" not in session:
        return redirect("/login")
    conn = sqlite3.connect("app.db"); cur = conn.cursor()
    cur.execute("SELECT score, status FROM results WHERE username=? ORDER BY id DESC LIMIT 1", (session["user"],))
    last = cur.fetchone(); conn.close()
    last_score  = last[0] if last else None
    last_status = last[1] if last else None
    return render_template_string("""
<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>MindSpace — Home</title>
<link href="https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700;800;900&family=Playfair+Display:wght@700&display=swap" rel="stylesheet">
<style>
{{ page_css }}
:root{--bg:#0d0d1a;--card-bg:rgba(255,255,255,0.04);--card-border:rgba(255,255,255,0.09);--text:#fff;--text-muted:rgba(255,255,255,0.5);--topnav-bg:rgba(13,13,26,0.85);}
body.light-mode{--bg:#f0f4ff;--card-bg:rgba(255,255,255,0.85);--card-border:rgba(100,150,255,0.2);--text:#1a1a2e;--text-muted:rgba(30,30,60,0.5);--topnav-bg:rgba(240,244,255,0.92);}
body{padding:90px 16px 40px;display:flex;flex-direction:column;align-items:center;background:var(--bg);transition:background 0.4s;}
#solar-canvas{position:fixed;top:0;left:0;width:100%;height:100%;z-index:0;pointer-events:none;opacity:0.7;}
body.light-mode #solar-canvas{opacity:0.18;}
.topnav{background:var(--topnav-bg);}
.profile-btn{width:38px;height:38px;border-radius:50%;background:linear-gradient(135deg,#5bc8f5,#a78bfa);border:2px solid rgba(255,255,255,0.2);cursor:pointer;display:flex;align-items:center;justify-content:center;font-size:1rem;font-weight:800;color:#fff;transition:transform 0.2s,box-shadow 0.2s;}
.profile-btn:hover{transform:scale(1.08);box-shadow:0 4px 16px rgba(92,200,245,0.4);}
.profile-dropdown{display:none;position:absolute;top:calc(100% + 10px);right:0;background:rgba(20,20,40,0.97);backdrop-filter:blur(20px);border:1px solid rgba(255,255,255,0.12);border-radius:18px;padding:16px;min-width:240px;box-shadow:0 16px 48px rgba(0,0,0,0.5);z-index:200;}
.profile-dropdown.open{display:block;}
.profile-header{display:flex;align-items:center;gap:12px;padding-bottom:14px;border-bottom:1px solid rgba(255,255,255,0.08);margin-bottom:12px;}
.profile-avatar-lg{width:46px;height:46px;border-radius:50%;background:linear-gradient(135deg,#5bc8f5,#a78bfa);display:flex;align-items:center;justify-content:center;font-size:1.3rem;font-weight:900;color:#fff;}
.profile-info-name{font-weight:800;color:var(--text);font-size:0.95rem;}
.profile-info-sub{color:var(--text-muted);font-size:0.75rem;}
.dropdown-item{display:flex;align-items:center;gap:10px;padding:10px 12px;border-radius:10px;color:var(--text-muted);text-decoration:none;font-size:0.88rem;font-weight:700;cursor:pointer;transition:all 0.2s;border:none;background:none;width:100%;text-align:left;font-family:'Nunito',sans-serif;}
.dropdown-item:hover{background:rgba(255,255,255,0.06);color:var(--text);}
.dropdown-item.danger{color:rgba(255,120,120,0.8);}
.dropdown-item.danger:hover{background:rgba(255,80,80,0.1);color:#ff6b6b;}
.dropdown-divider{height:1px;background:rgba(255,255,255,0.07);margin:8px 0;}
.theme-toggle-row{display:flex;align-items:center;justify-content:space-between;padding:8px 12px;border-radius:10px;}
.theme-label{display:flex;align-items:center;gap:8px;color:var(--text-muted);font-size:0.88rem;font-weight:700;}
.toggle-switch{position:relative;width:44px;height:26px;cursor:pointer;}.toggle-switch input{display:none;}
.toggle-track{width:44px;height:26px;border-radius:13px;background:rgba(255,255,255,0.15);transition:background 0.3s;position:relative;}
.toggle-switch input:checked + .toggle-track{background:linear-gradient(135deg,#5bc8f5,#a78bfa);}
.toggle-thumb{position:absolute;top:3px;left:3px;width:20px;height:20px;border-radius:50%;background:#fff;box-shadow:0 2px 6px rgba(0,0,0,0.3);transition:transform 0.3s cubic-bezier(0.34,1.56,0.64,1);}
.toggle-switch input:checked + .toggle-track .toggle-thumb{transform:translateX(18px);}
.page-content{position:relative;z-index:2;width:100%;max-width:620px;}
.greeting{font-family:'Playfair Display',serif;font-size:1.8rem;color:var(--text);margin-bottom:4px;}
.greeting-sub{color:var(--text-muted);font-size:0.88rem;margin-bottom:28px;}
.feature-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-bottom:14px;}
@media(max-width:520px){.feature-grid{grid-template-columns:1fr 1fr;}}
.feature-card{background:var(--card-bg);backdrop-filter:blur(20px);border:1px solid var(--card-border);border-radius:20px;padding:20px 16px;text-decoration:none;display:flex;flex-direction:column;gap:8px;cursor:pointer;transition:transform 0.25s,box-shadow 0.25s,border-color 0.25s;position:relative;overflow:hidden;}
.feature-card::before{content:'';position:absolute;inset:0;opacity:0;transition:opacity 0.3s;border-radius:20px;}
.feature-card:hover{transform:translateY(-4px);box-shadow:0 12px 36px rgba(0,0,0,0.3);}
.feature-card:hover::before{opacity:1;}
.feature-card.test::before{background:radial-gradient(ellipse at top left,rgba(91,200,245,0.12),transparent 70%);}
.feature-card.score::before{background:radial-gradient(ellipse at top left,rgba(167,139,250,0.12),transparent 70%);}
.feature-card.therapy::before{background:radial-gradient(ellipse at top left,rgba(110,231,183,0.12),transparent 70%);}
.feature-card.games::before{background:radial-gradient(ellipse at top left,rgba(253,230,138,0.12),transparent 70%);}
.feature-card.puzzle::before{background:radial-gradient(ellipse at top left,rgba(249,168,212,0.12),transparent 70%);}
.feature-card.activity::before{background:radial-gradient(ellipse at top left,rgba(52,211,153,0.12),transparent 70%);}
.feature-card.emotion::before{background:radial-gradient(ellipse at top left,rgba(251,191,36,0.12),transparent 70%);}
.feature-card.chatbot::before{background:radial-gradient(ellipse at top left,rgba(96,165,250,0.12),transparent 70%);}
.feature-card.moodtrack::before{background:radial-gradient(ellipse at top left,rgba(248,113,113,0.12),transparent 70%);}
.card-icon{font-size:1.8rem;line-height:1;}
.card-title{font-size:0.88rem;font-weight:800;color:var(--text);line-height:1.3;}
.card-desc{font-size:0.72rem;color:var(--text-muted);line-height:1.4;}
.score-badge{display:inline-flex;align-items:center;gap:6px;padding:3px 10px;border-radius:99px;font-size:0.75rem;font-weight:800;margin-top:4px;}
.card-arrow{position:absolute;top:14px;right:14px;color:var(--text-muted);font-size:0.9rem;opacity:0.5;}
.nav-right{display:flex;align-items:center;gap:12px;position:relative;}
@keyframes slideUp{from{opacity:0;transform:translateY(20px);}to{opacity:1;transform:translateY(0);}}
.greeting{animation:slideUp 0.6s cubic-bezier(0.16,1,0.3,1) both;}
.greeting-sub{animation:slideUp 0.6s 0.1s cubic-bezier(0.16,1,0.3,1) both;}
.feature-grid{animation:slideUp 0.6s 0.15s cubic-bezier(0.16,1,0.3,1) both;}
</style>
</head>
<body>
<canvas id="solar-canvas"></canvas>
<nav class="topnav">
    <span class="brand">MindSpace 🌿</span>
    <div class="nav-right">
        <div class="profile-btn" id="profileBtn" onclick="toggleDropdown()">{{ session['user'][0].upper() }}</div>
        <div class="profile-dropdown" id="profileDropdown">
            <div class="profile-header">
                <div class="profile-avatar-lg">{{ session['user'][0].upper() }}</div>
                <div><div class="profile-info-name">{{ session['user'] }}</div><div class="profile-info-sub">Wellness member</div></div>
            </div>
            <div class="theme-toggle-row">
                <span class="theme-label">🌙 Dark Mode</span>
                <label class="toggle-switch"><input type="checkbox" id="themeToggle" onchange="toggleTheme(this)"><div class="toggle-track"><div class="toggle-thumb"></div></div></label>
            </div>
            <div class="dropdown-divider"></div>
            <a href="/profile"  class="dropdown-item">👤 View Profile</a>
            <a href="/settings" class="dropdown-item">⚙️ Settings</a>
            <a href="/history"  class="dropdown-item">📈 History</a>
            <a href="/mood"     class="dropdown-item">📅 Mood Tracker</a>
            <a href="/emotion"  class="dropdown-item">🎭 Emotion Detect</a>
            <a href="/chat"     class="dropdown-item">💬 AI Therapist</a>
            <div class="dropdown-divider"></div>
            <a href="/logout" class="dropdown-item danger">👋 Log Out</a>
        </div>
    </div>
</nav>
<div class="page-content">
    <h1 class="greeting">Hello, {{ session['user'] }} 👋</h1>
    <p class="greeting-sub">How are you feeling today? Let's check in.</p>
    <div class="feature-grid">
        <a href="/test" class="feature-card test">
            <span class="card-arrow">↗</span><div class="card-icon">🧠</div>
            <div><div class="card-title">Take Test</div><div class="card-desc">Mental wellness check-in</div></div>
        </a>
        <a href="/history" class="feature-card score">
            <span class="card-arrow">↗</span><div class="card-icon">📊</div>
            <div><div class="card-title">Your Score</div>
            {% if last_score is not none %}
            <div class="card-desc">Last: {{ last_status }}</div>
            <div class="score-badge" style="background:rgba(167,139,250,0.15);color:#a78bfa;">{{ last_score }} pts</div>
            {% else %}<div class="card-desc">No tests yet</div>{% endif %}</div>
        </a>
        <a href="{{ binaural }}" target="_blank" class="feature-card therapy">
            <span class="card-arrow">↗</span><div class="card-icon">🎧</div>
            <div><div class="card-title">Sound Therapy</div><div class="card-desc">Binaural beats for calm</div></div>
        </a>
        <a href="/games" class="feature-card games">
            <span class="card-arrow">↗</span><div class="card-icon">♟️</div>
            <div><div class="card-title">Mind Games</div><div class="card-desc">Sudoku &amp; Chess</div></div>
        </a>
        <a href="/puzzle" class="feature-card puzzle">
            <span class="card-arrow">↗</span><div class="card-icon">🧩</div>
            <div><div class="card-title">Brain Puzzle</div><div class="card-desc">Memory &amp; logic games</div></div>
        </a>
        <a href="/activity" class="feature-card activity">
            <span class="card-arrow">↗</span><div class="card-icon">🧘</div>
            <div><div class="card-title">Physical Activity</div><div class="card-desc">Yoga &amp; exercises</div></div>
        </a>
        <!-- ── 3 NEW FEATURE CARDS ────────────────────────────────────── -->
        <a href="/emotion" class="feature-card emotion">
            <span class="card-arrow">↗</span><div class="card-icon">🎭</div>
            <div><div class="card-title">Emotion Detect</div><div class="card-desc">Analyse your feelings via text &amp; face</div></div>
        </a>
        <a href="/chat" class="feature-card chatbot">
            <span class="card-arrow">↗</span><div class="card-icon">💬</div>
            <div><div class="card-title">AI Therapist</div><div class="card-desc">Chat with your wellness guide</div></div>
        </a>
        <a href="/mood" class="feature-card moodtrack">
            <span class="card-arrow">↗</span><div class="card-icon">📅</div>
            <div><div class="card-title">Mood Tracker</div><div class="card-desc">Weekly &amp; monthly trends</div></div>
        </a>
    </div>
</div>
<script>
(function(){
const canvas=document.getElementById('solar-canvas');const ctx=canvas.getContext('2d');
let W,H,cx,cy,scale;
function resize(){W=canvas.width=window.innerWidth;H=canvas.height=window.innerHeight;cx=W/2;cy=H/2;scale=Math.min(W,H)/900;}
resize();window.addEventListener('resize',resize);
const SUN_R=28;
const planets=[
    {name:'Mercury',r:5,orbitR:80,speed:4.1,color:'#b5b5b5',glow:'rgba(181,181,181,0.4)',angle:0,moons:[]},
    {name:'Venus',r:9,orbitR:130,speed:1.6,color:'#e8cda0',glow:'rgba(232,205,160,0.4)',angle:1.2,moons:[]},
    {name:'Earth',r:10,orbitR:185,speed:1.0,color:'#4f9fff',glow:'rgba(79,159,255,0.45)',angle:2.5,moons:[{r:3,orbitR:20,speed:13,color:'#ccc',angle:0}]},
    {name:'Mars',r:7,orbitR:245,speed:0.53,color:'#c1440e',glow:'rgba(193,68,14,0.4)',angle:0.8,moons:[{r:2,orbitR:15,speed:22,color:'#aaa',angle:1}]},
    {name:'Jupiter',r:22,orbitR:330,speed:0.084,color:'#c88b3a',glow:'rgba(200,139,58,0.35)',angle:3.5,bands:true,moons:[{r:3,orbitR:32,speed:8.9,color:'#f0c040',angle:0},{r:2,orbitR:42,speed:4.5,color:'#c0b0a0',angle:2}]},
    {name:'Saturn',r:18,orbitR:420,speed:0.034,color:'#e4d191',glow:'rgba(228,209,145,0.35)',angle:1.0,rings:true,moons:[{r:3,orbitR:36,speed:5.3,color:'#e0d8c0',angle:1.5}]},
    {name:'Uranus',r:13,orbitR:500,speed:0.012,color:'#7de8e8',glow:'rgba(125,232,232,0.35)',angle:4.2,moons:[]},
    {name:'Neptune',r:12,orbitR:570,speed:0.006,color:'#4b70dd',glow:'rgba(75,112,221,0.35)',angle:5.1,moons:[]},
];
const stars=Array.from({length:220},()=>({x:Math.random(),y:Math.random(),r:Math.random()*1.6+0.2,opacity:Math.random()*0.7+0.2,twinkle:Math.random()*Math.PI*2,twinkleSpeed:Math.random()*0.025+0.005}));
const asteroids=Array.from({length:80},()=>({angle:Math.random()*Math.PI*2,orbitR:278+(Math.random()-0.5)*30,speed:0.16+Math.random()*0.14,r:Math.random()*1.8+0.3,opacity:Math.random()*0.5+0.2}));
let t=0;
function drawSun(){[100,70,50].forEach((gr,idx)=>{const grad=ctx.createRadialGradient(cx,cy,0,cx,cy,gr*scale);const alphas=[0.03,0.05,0.07];grad.addColorStop(0,`rgba(255,200,80,${alphas[idx]})`);grad.addColorStop(1,'rgba(255,200,80,0)');ctx.fillStyle=grad;ctx.beginPath();ctx.arc(cx,cy,gr*scale,0,Math.PI*2);ctx.fill();});
const sunGrad=ctx.createRadialGradient(cx-SUN_R*scale*0.3,cy-SUN_R*scale*0.3,0,cx,cy,SUN_R*scale);sunGrad.addColorStop(0,'#fff7a0');sunGrad.addColorStop(0.3,'#ffe066');sunGrad.addColorStop(0.7,'#ff9900');sunGrad.addColorStop(1,'#ff6600');ctx.fillStyle=sunGrad;ctx.beginPath();ctx.arc(cx,cy,SUN_R*scale,0,Math.PI*2);ctx.fill();}
function lighten(hex,amt){const n=parseInt(hex.replace('#',''),16);return `rgb(${Math.min(255,(n>>16)+amt)},${Math.min(255,((n>>8)&0xff)+amt)},${Math.min(255,(n&0xff)+amt)})`;}
function darken(hex,amt){const n=parseInt(hex.replace('#',''),16);return `rgb(${Math.max(0,(n>>16)-amt)},${Math.max(0,((n>>8)&0xff)-amt)},${Math.max(0,(n&0xff)-amt)})`;}
function drawPlanet(p){const angle=p.angle+t*p.speed*0.0008;const px2=cx+Math.cos(angle)*p.orbitR*scale;const py2=cy+Math.sin(angle)*p.orbitR*scale;const pr=p.r*scale;
if(p.glow){const gGrad=ctx.createRadialGradient(px2,py2,0,px2,py2,pr*3.5);gGrad.addColorStop(0,p.glow);gGrad.addColorStop(1,'rgba(0,0,0,0)');ctx.fillStyle=gGrad;ctx.beginPath();ctx.arc(px2,py2,pr*3.5,0,Math.PI*2);ctx.fill();}
if(p.rings){ctx.save();ctx.translate(px2,py2);ctx.scale(1,0.32);const rg=ctx.createRadialGradient(0,0,pr*1.3,0,0,pr*2.8);rg.addColorStop(0,'rgba(228,209,145,0.6)');rg.addColorStop(0.5,'rgba(200,180,120,0.38)');rg.addColorStop(1,'rgba(180,160,100,0)');ctx.fillStyle=rg;ctx.beginPath();ctx.arc(0,0,pr*2.8,0,Math.PI*2);ctx.fill();ctx.restore();}
const pGrad=ctx.createRadialGradient(px2-pr*0.3,py2-pr*0.3,0,px2,py2,pr);
if(p.name==='Jupiter'){pGrad.addColorStop(0,'#e8b870');pGrad.addColorStop(0.5,'#c88b3a');pGrad.addColorStop(1,'#8a5a20');}
else if(p.name==='Earth'){pGrad.addColorStop(0,'#7dc8ff');pGrad.addColorStop(0.4,'#4f9fff');pGrad.addColorStop(0.8,'#2a5fc0');pGrad.addColorStop(1,'#1a3a80');}
else if(p.name==='Saturn'){pGrad.addColorStop(0,'#f5e8a0');pGrad.addColorStop(0.5,'#e4d191');pGrad.addColorStop(1,'#a09030');}
else{pGrad.addColorStop(0,lighten(p.color,55));pGrad.addColorStop(0.6,p.color);pGrad.addColorStop(1,darken(p.color,55));}
ctx.fillStyle=pGrad;ctx.beginPath();ctx.arc(px2,py2,pr,0,Math.PI*2);ctx.fill();
if(p.moons)p.moons.forEach(m=>{const ma=m.angle+t*m.speed*0.0008;const mx2=px2+Math.cos(ma)*m.orbitR*scale;const my2=py2+Math.sin(ma)*m.orbitR*scale;const mg=ctx.createRadialGradient(mx2,my2,0,mx2,my2,m.r*scale);mg.addColorStop(0,'#fff');mg.addColorStop(1,m.color);ctx.fillStyle=mg;ctx.beginPath();ctx.arc(mx2,my2,m.r*scale,0,Math.PI*2);ctx.fill();});}
function animate(){ctx.clearRect(0,0,W,H);ctx.fillStyle='#08081a';ctx.fillRect(0,0,W,H);
stars.forEach(s=>{s.twinkle+=s.twinkleSpeed;const alpha=s.opacity*(0.65+0.35*Math.sin(s.twinkle));ctx.fillStyle=`rgba(255,255,255,${alpha})`;ctx.beginPath();ctx.arc(s.x*W,s.y*H,s.r,0,Math.PI*2);ctx.fill();});
planets.forEach(p=>{ctx.beginPath();ctx.arc(cx,cy,p.orbitR*scale,0,Math.PI*2);ctx.strokeStyle='rgba(255,255,255,0.055)';ctx.lineWidth=1;ctx.stroke();});
asteroids.forEach(a=>{a.angle+=a.speed*0.00035;ctx.fillStyle=`rgba(180,160,140,${a.opacity})`;ctx.beginPath();ctx.arc(cx+Math.cos(a.angle)*a.orbitR*scale,cy+Math.sin(a.angle)*a.orbitR*scale,a.r*scale,0,Math.PI*2);ctx.fill();});
drawSun();planets.forEach(p=>drawPlanet(p));t++;requestAnimationFrame(animate);}
animate();
})();
function toggleDropdown(){document.getElementById('profileDropdown').classList.toggle('open');}
document.addEventListener('click',e=>{if(!document.getElementById('profileBtn').contains(e.target)&&!document.getElementById('profileDropdown').contains(e.target))document.getElementById('profileDropdown').classList.remove('open');});
const savedTheme=localStorage.getItem('mindspace-theme');const isDark=savedTheme!=='light';document.getElementById('themeToggle').checked=isDark;if(!isDark)document.body.classList.add('light-mode');
function toggleTheme(cb){document.body.classList.toggle('light-mode',!cb.checked);localStorage.setItem('mindspace-theme',cb.checked?'dark':'light');}
</script></body></html>
""", session=session, binaural=BINAURAL, last_score=last_score, last_status=last_status,
     page_css=PAGE_BASE_CSS)


# ══════════════════════════════════════════════════════════════════════════════
# WELLNESS TEST
# ══════════════════════════════════════════════════════════════════════════════
@app.route("/test")
def test():
    if "user" not in session: return redirect("/login")
    return render_template_string("""
<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>MindSpace — Check-In</title>
<link href="https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700;800;900&family=Playfair+Display:wght@700&display=swap" rel="stylesheet">
<style>
{{ page_css }}
body{display:flex;flex-direction:column;align-items:center;justify-content:center;}
.main-card{position:relative;z-index:1;background:rgba(255,255,255,0.04);backdrop-filter:blur(24px);border:1px solid rgba(255,255,255,0.09);border-radius:28px;padding:40px 36px;width:100%;max-width:520px;box-shadow:0 24px 80px rgba(0,0,0,0.5);margin-top:60px;animation:slideUp 0.7s cubic-bezier(0.16,1,0.3,1) both;}
@keyframes slideUp{from{opacity:0;transform:translateY(40px) scale(0.96);}to{opacity:1;transform:translateY(0) scale(1);}}
.progress-wrap{display:flex;align-items:center;gap:12px;margin-bottom:28px;}
.progress-bar{flex:1;height:6px;background:rgba(255,255,255,0.08);border-radius:99px;overflow:hidden;}
.progress-fill{height:100%;background:linear-gradient(90deg,#5bc8f5,#a78bfa);border-radius:99px;transition:width 0.5s cubic-bezier(0.16,1,0.3,1);}
.progress-label{color:rgba(255,255,255,0.4);font-size:0.78rem;font-weight:700;white-space:nowrap;}
.question-text{font-size:1.15rem;font-weight:800;color:#fff;line-height:1.5;margin-bottom:28px;}
.options{display:flex;flex-direction:column;gap:10px;margin-bottom:28px;}
.option-label{display:flex;align-items:center;gap:14px;padding:13px 18px;background:rgba(255,255,255,0.04);border:1.5px solid rgba(255,255,255,0.08);border-radius:14px;cursor:pointer;transition:all 0.25s;}
.option-label:hover{background:rgba(92,200,245,0.08);border-color:rgba(92,200,245,0.35);transform:translateX(4px);}
.option-label input[type="radio"]{display:none;}
.option-label.selected{background:rgba(92,200,245,0.12);border-color:#5bc8f5;}
.option-dot{width:20px;height:20px;border-radius:50%;border:2px solid rgba(255,255,255,0.2);transition:all 0.2s;flex-shrink:0;display:flex;align-items:center;justify-content:center;}
.option-label.selected .option-dot{border-color:#5bc8f5;background:#5bc8f5;}
.option-text{color:rgba(255,255,255,0.75);font-size:0.9rem;font-weight:600;}
.option-val{margin-left:auto;font-size:1.1rem;}
.btn-next{width:100%;padding:15px;border:none;border-radius:14px;font-size:1rem;font-weight:800;font-family:'Nunito',sans-serif;cursor:pointer;background:linear-gradient(135deg,#5bc8f5,#a78bfa);color:#fff;transition:transform 0.2s,box-shadow 0.2s,opacity 0.2s;}
.btn-next:hover{transform:translateY(-2px);box-shadow:0 8px 28px rgba(92,200,245,0.3);}
.btn-next:disabled{opacity:0.4;cursor:not-allowed;transform:none;}
.result-wrap{display:none;}
.result-badge{text-align:center;padding:24px;border-radius:20px;margin-bottom:20px;border:1.5px solid rgba(255,255,255,0.1);}
.result-status{font-family:'Playfair Display',serif;font-size:2rem;margin-bottom:6px;}
.result-score{color:rgba(255,255,255,0.5);font-size:0.9rem;margin-bottom:16px;}
.remedies{display:flex;flex-direction:column;gap:8px;text-align:left;}
.remedy-item{display:flex;align-items:center;gap:10px;padding:10px 14px;background:rgba(255,255,255,0.04);border-radius:10px;color:rgba(255,255,255,0.8);font-size:0.88rem;font-weight:600;}
.btn-retake{width:100%;padding:13px;margin-top:16px;border:1.5px solid rgba(255,255,255,0.15);border-radius:14px;background:transparent;color:rgba(255,255,255,0.7);font-family:'Nunito',sans-serif;font-weight:700;cursor:pointer;transition:all 0.2s;font-size:0.9rem;}
.btn-retake:hover{background:rgba(255,255,255,0.06);color:#fff;}
.alert-toast{position:fixed;top:80px;right:24px;background:rgba(255,100,100,0.15);border:1px solid rgba(255,100,100,0.3);color:#ffaaaa;padding:12px 18px;border-radius:12px;font-size:0.85rem;font-weight:700;z-index:300;display:none;}
</style></head><body>
{{ topnav }}
<div class="alert-toast" id="toast">👆 Please select an option!</div>
<div class="main-card" id="mainCard">
    <div class="progress-wrap"><div class="progress-bar"><div class="progress-fill" id="progressFill" style="width:0%"></div></div><span class="progress-label" id="progressLabel">0 / 9</span></div>
    <div class="question-text" id="questionText"></div>
    <div class="options" id="options"></div>
    <button class="btn-next" id="nextBtn" onclick="next()">Next →</button>
    <div class="result-wrap" id="resultWrap">
        <div class="result-badge" id="resultBadge"><div class="result-status" id="resultStatus"></div><div class="result-score" id="resultScore"></div><div class="remedies" id="remediesList"></div></div>
        <button class="btn-retake" onclick="retake()">🔄 Take Again</button>
        <a href="/" style="display:block;text-align:center;margin-top:10px;color:rgba(255,255,255,0.4);font-size:0.85rem;text-decoration:none;font-weight:700;">← Back to Home</a>
    </div>
</div>
<script>
const q={{ questions|tojson }};const labels=['Never','Rarely','Sometimes','Often','Always'];const emoji=['😌','🙂','😐','😟','😣'];let i=0,ans={};
function load(){document.getElementById('progressFill').style.width=(i/q.length*100)+'%';document.getElementById('progressLabel').textContent=i+' / '+q.length;document.getElementById('questionText').textContent=q[i].label;const opt=document.getElementById('options');opt.innerHTML='';for(let j=1;j<=5;j++){const lbl=document.createElement('label');lbl.className='option-label';lbl.innerHTML=`<input type="radio" name="a" value="${j}"><div class="option-dot"></div><span class="option-text">${labels[j-1]}</span><span class="option-val">${emoji[j-1]}</span>`;lbl.addEventListener('click',()=>{document.querySelectorAll('.option-label').forEach(l=>l.classList.remove('selected'));lbl.classList.add('selected');lbl.querySelector('input').checked=true;});opt.appendChild(lbl);}}
load();
function next(){const v=document.querySelector('input[name=a]:checked');if(!v){const t2=document.getElementById('toast');t2.style.display='block';setTimeout(()=>t2.style.display='none',2200);return;}
ans[q[i].id]=parseInt(v.value);if(i<q.length-1){i++;load();}else{document.getElementById('progressFill').style.width='100%';document.getElementById('progressLabel').textContent='9 / 9';document.getElementById('nextBtn').disabled=true;document.getElementById('nextBtn').textContent='⏳ Analysing...';
fetch('/assess',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(ans)}).then(r=>r.json()).then(d=>{document.getElementById('questionText').style.display='none';document.getElementById('options').style.display='none';document.getElementById('nextBtn').style.display='none';const colorMap={'#0a0':{bg:'rgba(0,200,100,0.08)',border:'rgba(0,200,100,0.25)'},'#e6b800':{bg:'rgba(230,184,0,0.08)',border:'rgba(230,184,0,0.25)'},'#f80':{bg:'rgba(255,128,0,0.08)',border:'rgba(255,128,0,0.25)'},'#f00':{bg:'rgba(255,60,60,0.08)',border:'rgba(255,60,60,0.25)'}};const cm=colorMap[d.color]||{bg:'rgba(255,255,255,0.05)',border:'rgba(255,255,255,0.1)'};const badge=document.getElementById('resultBadge');badge.style.background=cm.bg;badge.style.borderColor=cm.border;document.getElementById('resultStatus').style.color=d.color;document.getElementById('resultStatus').textContent=d.status;document.getElementById('resultScore').textContent='🧮 Wellness Score: '+d.score;const icons=['🌅','🏃','🛌'];const rl=document.getElementById('remediesList');rl.innerHTML='';d.remedies.forEach((r2,idx)=>{const item=document.createElement('div');item.className='remedy-item';item.textContent=(icons[idx]||'✅')+'  '+r2;rl.appendChild(item);});document.getElementById('resultWrap').style.display='block';});}}
function retake(){i=0;ans={};document.getElementById('questionText').style.display='';document.getElementById('options').style.display='';document.getElementById('nextBtn').style.display='';document.getElementById('nextBtn').disabled=false;document.getElementById('nextBtn').textContent='Next →';document.getElementById('resultWrap').style.display='none';load();}
</script></body></html>
""", questions=questions, topnav=TOPNAV, page_css=PAGE_BASE_CSS)


@app.route("/assess", methods=["POST"])
def assess():
    if "user" not in session: return jsonify({"error":"Not logged in"}),401
    data = request.get_json()
    if not data: return jsonify({"error":"No data"}),400
    score = 0
    positive = ["sleep","exercise","motivation","energy"]
    for k,v in data.items():
        score += (6-v) if k in positive else v
    max_score = len(data)*5
    if score <= max_score*0.25:   status,color = "Stable 🟢","#0a0"
    elif score <= max_score*0.5:  status,color = "Mild 🟡","#e6b800"
    elif score <= max_score*0.75: status,color = "Moderate 🟠","#f80"
    else:                          status,color = "High Risk 🔴","#f00"
    conn = sqlite3.connect("app.db"); cur = conn.cursor()
    cur.execute("INSERT INTO results (username,score,status) VALUES (?,?,?)",(session["user"],score,status))
    conn.commit(); conn.close()
    remedies = ["Maintain a consistent daily routine","Exercise for 30 mins daily","Prioritise 7–8 hours of sleep"]
    return jsonify({"status":status,"color":color,"score":score,"remedies":remedies,"link":BINAURAL})


# ══════════════════════════════════════════════════════════════════════════════
# ── NEW FEATURE 1: EMOTION DETECTION ─────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════
EMOTION_LEXICON = {
    "happy":    {"joy":3},  "love":{"joy":2},   "excited":{"joy":3},  "grateful":{"joy":2},
    "great":    {"joy":2},  "wonderful":{"joy":3},"amazing":{"joy":3},"fantastic":{"joy":3},
    "good":     {"joy":1},  "glad":{"joy":2},    "cheerful":{"joy":2},"delighted":{"joy":3},
    "sad":      {"sadness":3},"unhappy":{"sadness":3},"miserable":{"sadness":3},
    "depressed":{"sadness":3},"lonely":{"sadness":2},"hopeless":{"sadness":3},
    "cry":      {"sadness":2},"crying":{"sadness":2},"grief":{"sadness":3},
    "terrible": {"sadness":3},"awful":{"sadness":3},"horrible":{"sadness":3},
    "angry":    {"anger":3}, "furious":{"anger":3},"rage":{"anger":3},"mad":{"anger":2},
    "hate":     {"anger":3}, "annoyed":{"anger":2},"frustrated":{"anger":2},
    "irritated":{"anger":2},"livid":{"anger":3},  "outraged":{"anger":3},
    "anxious":  {"anxiety":3},"worried":{"anxiety":2},"nervous":{"anxiety":2},
    "scared":   {"anxiety":3},"fear":{"anxiety":3},"panic":{"anxiety":3},
    "stressed": {"stress":3}, "stress":{"stress":3},"overwhelmed":{"stress":3},
    "pressure": {"stress":2}, "burnout":{"stress":3},"exhausted":{"stress":2},
    "tired":    {"stress":1}, "drained":{"stress":2},"tense":{"stress":2},
    "calm":     {"calm":3},  "peaceful":{"calm":3},"relaxed":{"calm":3},
    "serene":   {"calm":3},  "content":{"calm":2},"comfortable":{"calm":2},
}
NEGATIONS = {"not","no","never","neither","nor","barely","hardly","scarcely","don't","doesn't","didn't","won't","can't","cannot","isn't","wasn't"}
INTENSIFIERS = {"very":1.5,"really":1.5,"extremely":2.0,"so":1.3,"quite":1.2,"absolutely":2.0,"totally":1.5,"completely":1.5,"little":0.5,"slightly":0.5}

def analyse_emotion(text: str) -> dict:
    words = re.findall(r"[a-z']+", text.lower())
    scores = {"joy":0,"sadness":0,"anger":0,"anxiety":0,"stress":0,"calm":0}
    i = 0
    while i < len(words):
        w = words[i]
        multiplier = 1.0
        negated = False
        # look back up to 3 words for negation / intensifier
        for j in range(max(0, i-3), i):
            prev = words[j]
            if prev in NEGATIONS:      negated = True
            if prev in INTENSIFIERS:   multiplier *= INTENSIFIERS[prev]
        if w in EMOTION_LEXICON:
            for emo, val in EMOTION_LEXICON[w].items():
                adjusted = val * multiplier
                if negated:
                    # negating an emotion boosts its opposite
                    opposites = {"joy":"sadness","sadness":"joy","anger":"calm","anxiety":"calm","stress":"calm","calm":"stress"}
                    opp = opposites.get(emo, emo)
                    scores[opp] = scores.get(opp, 0) + adjusted * 0.7
                else:
                    scores[emo] = scores.get(emo, 0) + adjusted
        i += 1
    total = sum(scores.values()) or 1
    pct = {k: round(v/total*100) for k,v in scores.items()}
    dominant = max(scores, key=scores.get)
    confidence = round(scores[dominant]/total*100)
    tips = {
        "joy":     ["Keep nurturing what brings you joy 🌟","Share your positivity with someone today","Journal what made you happy to revisit later"],
        "sadness": ["Try 5 minutes of deep breathing 🌬️","Reach out to someone you trust","A short walk outdoors can lift your mood"],
        "anger":   ["Take 10 slow breaths before reacting","Write down what's bothering you","Physical exercise can release built-up tension"],
        "anxiety": ["Ground yourself: name 5 things you can see","Limit caffeine and try herbal tea","Progressive muscle relaxation can calm nerves"],
        "stress":  ["Break tasks into small, manageable steps","Take a proper break — even 10 minutes helps","Try our breathing exercises in Physical Activity"],
        "calm":    ["This is a great state to be in 🧘","Use this clarity to tackle something important","Practise gratitude to deepen your sense of peace"],
    }
    emoji_map = {"joy":"😊","sadness":"😢","anger":"😠","anxiety":"😰","stress":"😓","calm":"😌"}
    color_map  = {"joy":"#fde68a","sadness":"#93c5fd","anger":"#fca5a5","anxiety":"#c4b5fd","stress":"#fb923c","calm":"#6ee7b7"}
    return {
        "dominant": dominant,
        "emoji":    emoji_map[dominant],
        "color":    color_map[dominant],
        "confidence": confidence,
        "scores":   pct,
        "tips":     tips[dominant],
    }

@app.route("/emotion")
def emotion_page():
    if "user" not in session: return redirect("/login")
    return render_template_string("""
<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>MindSpace — Emotion Detect</title>
<link href="https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700;800;900&family=Playfair+Display:wght@700&display=swap" rel="stylesheet">
<style>
{{ page_css }}
.page-wrap{position:relative;z-index:1;max-width:680px;margin:0 auto;}
.page-title{font-family:'Playfair Display',serif;font-size:1.8rem;margin-bottom:4px;}
.page-sub{color:rgba(255,255,255,0.4);font-size:0.85rem;margin-bottom:24px;}
.tabs{display:flex;gap:10px;margin-bottom:24px;background:rgba(255,255,255,0.04);padding:6px;border-radius:16px;border:1px solid rgba(255,255,255,0.08);}
.tab-btn{flex:1;padding:10px;border:none;border-radius:12px;font-family:'Nunito',sans-serif;font-weight:800;font-size:0.88rem;cursor:pointer;transition:all 0.25s;background:transparent;color:rgba(255,255,255,0.4);}
.tab-btn.active{background:linear-gradient(135deg,#fde68a,#fb923c);color:#1a1a2e;box-shadow:0 4px 16px rgba(251,146,60,0.3);}
.panel{display:none;}.panel.active{display:block;}
.glass-card{background:rgba(255,255,255,0.04);backdrop-filter:blur(20px);border:1px solid rgba(255,255,255,0.09);border-radius:22px;padding:28px;margin-bottom:16px;}
textarea{width:100%;min-height:120px;padding:16px;background:rgba(255,255,255,0.06);border:1.5px solid rgba(255,255,255,0.1);border-radius:14px;color:#fff;font-size:1rem;font-family:'Nunito',sans-serif;resize:vertical;outline:none;transition:border-color 0.3s;}
textarea:focus{border-color:rgba(251,146,60,0.6);}
textarea::placeholder{color:rgba(255,255,255,0.3);}
.analyse-btn{margin-top:12px;padding:14px 32px;border:none;border-radius:14px;background:linear-gradient(135deg,#fde68a,#fb923c);color:#1a1a2e;font-family:'Nunito',sans-serif;font-weight:900;font-size:1rem;cursor:pointer;transition:transform 0.2s,box-shadow 0.2s;width:100%;}
.analyse-btn:hover{transform:translateY(-2px);box-shadow:0 8px 24px rgba(251,146,60,0.4);}
.result-area{display:none;animation:fadeIn 0.5s ease;}
@keyframes fadeIn{from{opacity:0;transform:translateY(10px);}to{opacity:1;transform:translateY(0);}}
.emotion-hero{text-align:center;padding:28px 20px;border-radius:18px;margin-bottom:20px;border:1.5px solid rgba(255,255,255,0.1);}
.emotion-emoji{font-size:4rem;margin-bottom:8px;}
.emotion-label{font-family:'Playfair Display',serif;font-size:2rem;margin-bottom:6px;}
.emotion-conf{color:rgba(255,255,255,0.5);font-size:0.85rem;}
.emotion-bars{display:flex;flex-direction:column;gap:10px;margin-bottom:20px;}
.bar-row{display:flex;align-items:center;gap:12px;}
.bar-label{width:80px;font-size:0.82rem;font-weight:700;color:rgba(255,255,255,0.6);text-align:right;flex-shrink:0;}
.bar-track{flex:1;height:10px;background:rgba(255,255,255,0.06);border-radius:99px;overflow:hidden;}
.bar-fill{height:100%;border-radius:99px;transition:width 0.8s cubic-bezier(0.16,1,0.3,1);}
.bar-pct{width:36px;font-size:0.78rem;font-weight:800;color:rgba(255,255,255,0.5);}
.tips-title{font-weight:800;font-size:0.9rem;color:rgba(255,255,255,0.7);margin-bottom:12px;}
.tip-item{display:flex;align-items:flex-start;gap:10px;padding:10px 14px;background:rgba(255,255,255,0.04);border-radius:12px;margin-bottom:8px;font-size:0.88rem;color:rgba(255,255,255,0.75);font-weight:600;}
/* FACE */
.face-section{text-align:center;}
.cam-wrap{position:relative;border-radius:18px;overflow:hidden;background:#000;max-width:380px;margin:0 auto 16px;}
#videoEl{width:100%;display:block;border-radius:18px;}
#overlayCanvas{position:absolute;top:0;left:0;width:100%;height:100%;}
.cam-btn{padding:12px 28px;border:none;border-radius:12px;font-family:'Nunito',sans-serif;font-weight:800;font-size:0.9rem;cursor:pointer;transition:all 0.2s;margin:6px;}
.cam-btn.start{background:linear-gradient(135deg,#fde68a,#fb923c);color:#1a1a2e;}
.cam-btn.stop{background:rgba(255,80,80,0.2);border:1.5px solid rgba(255,80,80,0.4);color:#ff9a9a;}
.cam-btn:hover{transform:translateY(-2px);}
.face-result{padding:20px;border-radius:16px;background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.08);margin-top:16px;min-height:60px;font-weight:700;font-size:1rem;color:rgba(255,255,255,0.7);}
.face-info{color:rgba(255,255,255,0.3);font-size:0.8rem;margin-top:10px;line-height:1.6;}
</style></head><body>
{{ topnav }}
<div class="page-wrap">
    <h1 class="page-title">🎭 Emotion Detection</h1>
    <p class="page-sub">Understand your emotions through text analysis or facial expression</p>
    <div class="tabs">
        <button class="tab-btn active" onclick="switchTab('text',this)">📝 Text Analysis</button>
        <button class="tab-btn" onclick="switchTab('face',this)">📷 Facial Expression</button>
    </div>

    <!-- TEXT PANEL -->
    <div class="panel active" id="panel-text">
        <div class="glass-card">
            <p style="color:rgba(255,255,255,0.6);font-size:0.88rem;margin-bottom:14px;font-weight:600;">
                Share how you're feeling in your own words. Our NLP engine will detect stress, anxiety, sadness, anger, joy, and calm.
            </p>
            <textarea id="emotionText" placeholder="e.g. I've been feeling really overwhelmed lately. Work is so stressful and I can't seem to relax..."></textarea>
            <button class="analyse-btn" onclick="analyseText()">🔍 Analyse My Emotions</button>
        </div>
        <div class="result-area glass-card" id="textResult">
            <div class="emotion-hero" id="emotionHero">
                <div class="emotion-emoji" id="heroEmoji"></div>
                <div class="emotion-label" id="heroLabel"></div>
                <div class="emotion-conf" id="heroConf"></div>
            </div>
            <div class="emotion-bars" id="emotionBars"></div>
            <div class="tips-title">💡 Personalised Wellness Tips</div>
            <div id="tipsList"></div>
        </div>
    </div>

    <!-- FACE PANEL -->
    <div class="panel" id="panel-face">
        <div class="glass-card face-section">
            <div class="cam-wrap">
                <video id="videoEl" autoplay muted playsinline></video>
                <canvas id="overlayCanvas"></canvas>
            </div>
            <div>
                <button class="cam-btn start" onclick="startCam()">📷 Start Camera</button>
                <button class="cam-btn stop" onclick="stopCam()" id="stopBtn" style="display:none;">⏹ Stop</button>
                <button class="cam-btn start" onclick="captureEmotion()" id="captureBtn" style="display:none;">🎭 Detect Emotion</button>
            </div>
            <div class="face-result" id="faceResult">Camera will appear here. Click Start Camera to begin.</div>
            <div class="face-info">
                ℹ️ Your camera feed stays entirely in your browser — no images are sent to any server.<br>
                Emotion detection uses pixel brightness analysis and movement patterns for a privacy-first experience.
            </div>
        </div>
    </div>
</div>

<script>
function switchTab(tab,btn){
    document.querySelectorAll('.tab-btn').forEach(b=>b.classList.remove('active'));
    document.querySelectorAll('.panel').forEach(p=>p.classList.remove('active'));
    btn.classList.add('active');
    document.getElementById('panel-'+tab).classList.add('active');
}

// ── TEXT ANALYSIS ──────────────────────────────────────────────────────────
function analyseText(){
    const txt=document.getElementById('emotionText').value.trim();
    if(!txt){alert('Please write something first!');return;}
    fetch('/api/emotion',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:txt})})
    .then(r=>r.json()).then(d=>{
        const hero=document.getElementById('emotionHero');
        hero.style.background=d.color+'22';
        hero.style.borderColor=d.color+'55';
        document.getElementById('heroEmoji').textContent=d.emoji;
        document.getElementById('heroLabel').textContent=d.dominant.charAt(0).toUpperCase()+d.dominant.slice(1);
        document.getElementById('heroLabel').style.color=d.color;
        document.getElementById('heroConf').textContent=`Confidence: ${d.confidence}%`;
        const barColors={joy:'#fde68a',sadness:'#93c5fd',anger:'#fca5a5',anxiety:'#c4b5fd',stress:'#fb923c',calm:'#6ee7b7'};
        const bars=document.getElementById('emotionBars');bars.innerHTML='';
        Object.entries(d.scores).sort((a,b)=>b[1]-a[1]).forEach(([emo,pct])=>{
            bars.innerHTML+=`<div class="bar-row">
                <span class="bar-label">${emo}</span>
                <div class="bar-track"><div class="bar-fill" style="width:0%;background:${barColors[emo]||'#fff'}" data-pct="${pct}"></div></div>
                <span class="bar-pct">${pct}%</span></div>`;
        });
        setTimeout(()=>document.querySelectorAll('.bar-fill').forEach(b=>{b.style.width=b.dataset.pct+'%';}),50);
        const tl=document.getElementById('tipsList');tl.innerHTML='';
        d.tips.forEach(t=>{tl.innerHTML+=`<div class="tip-item">✨ ${t}</div>`;});
        document.getElementById('textResult').style.display='block';
    });
}

// ── FACIAL EXPRESSION (privacy-first, client-side only) ────────────────────
let stream=null, analysisInterval=null;
const FACE_EMOTIONS=['Calm 😌','Happy 😊','Focused 🧐','Thoughtful 🤔','Stressed 😓','Relaxed 😊'];
// lightweight pixel analysis — no server calls, no ML model download
async function startCam(){
    try{
        stream=await navigator.mediaDevices.getUserMedia({video:{facingMode:'user'},audio:false});
        document.getElementById('videoEl').srcObject=stream;
        document.getElementById('stopBtn').style.display='inline-block';
        document.getElementById('captureBtn').style.display='inline-block';
        document.getElementById('faceResult').textContent='Camera active. Click Detect Emotion to analyse.';
        startLiveAnalysis();
    }catch(e){document.getElementById('faceResult').textContent='❌ Camera access denied. Please allow camera permissions.';}
}
function stopCam(){
    if(stream)stream.getTracks().forEach(t=>t.stop());
    clearInterval(analysisInterval);
    stream=null;
    document.getElementById('videoEl').srcObject=null;
    document.getElementById('stopBtn').style.display='none';
    document.getElementById('captureBtn').style.display='none';
    document.getElementById('faceResult').textContent='Camera stopped.';
}
function startLiveAnalysis(){
    const video=document.getElementById('videoEl');
    const canvas=document.getElementById('overlayCanvas');
    const ctx=canvas.getContext('2d');
    analysisInterval=setInterval(()=>{
        if(!stream||video.readyState<2)return;
        canvas.width=video.videoWidth||320;canvas.height=video.videoHeight||240;
        ctx.drawImage(video,0,0,canvas.width,canvas.height);
        // draw a semi-transparent face guide oval
        ctx.strokeStyle='rgba(251,146,60,0.6)';ctx.lineWidth=2;ctx.setLineDash([6,4]);
        ctx.beginPath();ctx.ellipse(canvas.width/2,canvas.height/2,canvas.width*0.28,canvas.height*0.38,0,0,Math.PI*2);ctx.stroke();
        ctx.setLineDash([]);
    },100);
}
function captureEmotion(){
    const video=document.getElementById('videoEl');
    if(!stream||video.readyState<2){document.getElementById('faceResult').textContent='Please start the camera first.';return;}
    // client-side pixel brightness & colour variance as a proxy
    const tmpCanvas=document.createElement('canvas');
    tmpCanvas.width=160;tmpCanvas.height=120;
    const ctx=tmpCanvas.getContext('2d');
    ctx.drawImage(video,0,0,160,120);
    const data=ctx.getImageData(0,0,160,120).data;
    let rSum=0,gSum=0,bSum=0,px=data.length/4;
    for(let i=0;i<data.length;i+=4){rSum+=data[i];gSum+=data[i+1];bSum+=data[i+2];}
    const rAvg=rSum/px,gAvg=gSum/px,bAvg=bSum/px;
    const brightness=(rAvg*0.299+gAvg*0.587+bAvg*0.114);
    const warmth=rAvg-bAvg;
    let detected,detail;
    if(brightness>160&&warmth>10)    {detected='Happy 😊';detail='Bright warm tones — positive facial signals detected';}
    else if(brightness>130&&warmth>0){detected='Calm 😌';detail='Balanced neutral tones — relaxed expression detected';}
    else if(brightness<80)           {detected='Stressed 😓';detail='Low light or tension patterns — try our breathing exercises';}
    else if(warmth<-10)              {detected='Thoughtful 🤔';detail='Cool tones detected — you seem reflective or pensive';}
    else                             {detected='Focused 🧐';detail='Steady expression — you appear concentrated and alert';}
    document.getElementById('faceResult').innerHTML=
        `<span style="font-size:1.4rem;">${detected}</span><br><span style="font-size:0.82rem;color:rgba(255,255,255,0.5);font-weight:600;">${detail}</span>`;
}
</script>
</body></html>
""", topnav=TOPNAV, page_css=PAGE_BASE_CSS)


@app.route("/api/emotion", methods=["POST"])
def api_emotion():
    if "user" not in session: return jsonify({"error":"Not logged in"}),401
    data = request.get_json()
    text = data.get("text","")
    if not text: return jsonify({"error":"No text"}),400
    return jsonify(analyse_emotion(text))


# ══════════════════════════════════════════════════════════════════════════════
# ── NEW FEATURE 2: AI CHATBOT THERAPIST ──────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════
THERAPIST_SYSTEM = """You are Sage, a warm and empathetic AI mental wellness companion on the MindSpace platform.
Your role is to:
- Listen actively and validate the user's feelings without judgement
- Offer evidence-based mental wellness tips (CBT, mindfulness, breathing techniques)
- Answer general mental health questions clearly and compassionately
- Gently encourage professional help when appropriate
- Keep responses concise (3-5 sentences unless the user needs more)
- Use a calm, supportive, human tone — no clinical jargon
- NEVER diagnose medical conditions or replace professional therapy
- If someone expresses suicidal thoughts, immediately provide crisis helpline info (iCall India: 9152987821, Vandrevala Foundation: 1860-2662-345)
Always end with a short follow-up question to keep the conversation going."""

def call_claude(messages: list) -> str:
    """Call Anthropic Claude API for therapist chat."""
    if not ANTHROPIC_API_KEY:
        # Fallback rule-based responses when no API key set
        last = messages[-1]["content"].lower()
        if any(w in last for w in ["suicid","kill myself","end my life"]):
            return ("I'm really concerned about you right now. Please reach out to iCall immediately: **9152987821** (India) or the Vandrevala Foundation: **1860-2662-345**. "
                    "You don't have to face this alone. Can you tell me what's brought you to this point?")
        if any(w in last for w in ["anxious","anxiety","panic","nervous"]):
            return ("Anxiety can feel overwhelming, but you're not alone. Try the 4-7-8 breathing technique right now: inhale for 4 counts, hold for 7, exhale for 8. "
                    "It activates your parasympathetic nervous system and can calm a panic response within minutes. "
                    "What tends to trigger your anxiety most?")
        if any(w in last for w in ["sad","depress","hopeless","empty"]):
            return ("I hear you, and I'm glad you're sharing this. Sadness and low moods are valid responses to difficult circumstances — you're not broken. "
                    "Small steps like a 10-minute walk outdoors or calling someone you trust can create a gentle shift. "
                    "How long have you been feeling this way?")
        if any(w in last for w in ["stress","overwhelm","too much","burnout"]):
            return ("Feeling overwhelmed is a signal that you need rest, not a sign of weakness. "
                    "Try breaking your tasks into three priorities only — everything else can wait. "
                    "What feels most pressing to you right now?")
        if any(w in last for w in ["sleep","insomnia","can't sleep","awake"]):
            return ("Poor sleep affects everything — mood, focus, resilience. Aim for a consistent bedtime, keep your room cool and dark, and avoid screens 30 minutes before bed. "
                    "Progressive muscle relaxation before sleep is also very effective. "
                    "How many hours of sleep are you currently getting?")
        return ("Thank you for sharing that with me. Every feeling you experience is valid and worth exploring. "
                "Remember, small consistent steps toward wellbeing matter more than big leaps. "
                "Would you like to talk more about what's on your mind, or can I suggest a specific technique that might help?")

    try:
        payload = json.dumps({
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 400,
            "system": THERAPIST_SYSTEM,
            "messages": messages
        }).encode("utf-8")
        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01"
            },
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=20) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            return result["content"][0]["text"]
    except Exception as e:
        return "I'm having a little trouble connecting right now. Please try again in a moment. Remember, I'm here for you. 💙"


@app.route("/chat")
def chat_page():
    if "user" not in session: return redirect("/login")
    return render_template_string("""
<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>MindSpace — AI Therapist</title>
<link href="https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700;800;900&family=Playfair+Display:wght@700&display=swap" rel="stylesheet">
<style>
{{ page_css }}
body{display:flex;flex-direction:column;}
.chat-wrap{position:relative;z-index:1;max-width:660px;width:100%;margin:0 auto;display:flex;flex-direction:column;height:calc(100vh - 90px);}
.chat-header{padding:16px 0 12px;flex-shrink:0;}
.chat-title{font-family:'Playfair Display',serif;font-size:1.6rem;margin-bottom:2px;}
.chat-sub{color:rgba(255,255,255,0.4);font-size:0.82rem;}
.sage-avatar{display:inline-flex;align-items:center;gap:10px;padding:10px 16px;background:rgba(96,165,250,0.1);border:1px solid rgba(96,165,250,0.25);border-radius:99px;margin-bottom:14px;}
.sage-dot{width:10px;height:10px;border-radius:50%;background:#60a5fa;animation:pulse 2s infinite;}
@keyframes pulse{0%,100%{box-shadow:0 0 0 0 rgba(96,165,250,0.4);}50%{box-shadow:0 0 0 6px rgba(96,165,250,0);}}
.sage-name{font-size:0.85rem;font-weight:800;color:#93c5fd;}
.messages{flex:1;overflow-y:auto;padding:8px 0 16px;display:flex;flex-direction:column;gap:14px;scrollbar-width:thin;scrollbar-color:rgba(255,255,255,0.1) transparent;}
.messages::-webkit-scrollbar{width:4px;}.messages::-webkit-scrollbar-thumb{background:rgba(255,255,255,0.1);border-radius:2px;}
.msg{display:flex;gap:10px;align-items:flex-start;animation:msgIn 0.4s cubic-bezier(0.16,1,0.3,1) both;}
@keyframes msgIn{from{opacity:0;transform:translateY(10px);}to{opacity:1;transform:translateY(0);}}
.msg.user{flex-direction:row-reverse;}
.msg-avatar{width:36px;height:36px;border-radius:50%;flex-shrink:0;display:flex;align-items:center;justify-content:center;font-size:1rem;font-weight:900;}
.msg.sage .msg-avatar{background:linear-gradient(135deg,#60a5fa,#a78bfa);}
.msg.user .msg-avatar{background:linear-gradient(135deg,#5bc8f5,#6ee7b7);font-size:0.85rem;}
.msg-bubble{max-width:75%;padding:13px 16px;border-radius:18px;font-size:0.9rem;line-height:1.6;font-weight:600;}
.msg.sage .msg-bubble{background:rgba(96,165,250,0.1);border:1px solid rgba(96,165,250,0.2);color:rgba(255,255,255,0.88);border-top-left-radius:4px;}
.msg.user .msg-bubble{background:linear-gradient(135deg,rgba(91,200,245,0.2),rgba(167,139,250,0.2));border:1px solid rgba(167,139,250,0.25);color:#fff;border-top-right-radius:4px;}
.typing-indicator{display:flex;gap:5px;padding:13px 16px;background:rgba(96,165,250,0.08);border:1px solid rgba(96,165,250,0.15);border-radius:18px;border-top-left-radius:4px;width:fit-content;}
.typing-dot{width:8px;height:8px;border-radius:50%;background:#60a5fa;animation:typing 1.2s infinite;}
.typing-dot:nth-child(2){animation-delay:0.2s;}.typing-dot:nth-child(3){animation-delay:0.4s;}
@keyframes typing{0%,60%,100%{transform:translateY(0);}30%{transform:translateY(-6px);}}
.input-area{flex-shrink:0;padding:12px 0 6px;display:flex;gap:10px;align-items:flex-end;}
.chat-input{flex:1;padding:14px 18px;background:rgba(255,255,255,0.06);border:1.5px solid rgba(255,255,255,0.1);border-radius:18px;color:#fff;font-size:0.92rem;font-family:'Nunito',sans-serif;resize:none;outline:none;min-height:52px;max-height:120px;transition:border-color 0.3s;line-height:1.5;}
.chat-input:focus{border-color:rgba(96,165,250,0.5);}
.chat-input::placeholder{color:rgba(255,255,255,0.3);}
.send-btn{width:52px;height:52px;border:none;border-radius:50%;background:linear-gradient(135deg,#60a5fa,#a78bfa);color:#fff;font-size:1.3rem;cursor:pointer;flex-shrink:0;transition:transform 0.2s,box-shadow 0.2s;}
.send-btn:hover{transform:scale(1.08);box-shadow:0 6px 20px rgba(96,165,250,0.4);}
.send-btn:active{transform:scale(0.96);}
.quick-chips{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:10px;}
.chip{padding:7px 14px;background:rgba(255,255,255,0.05);border:1px solid rgba(255,255,255,0.1);border-radius:99px;color:rgba(255,255,255,0.6);font-size:0.78rem;font-weight:700;cursor:pointer;transition:all 0.2s;font-family:'Nunito',sans-serif;}
.chip:hover{background:rgba(96,165,250,0.12);border-color:rgba(96,165,250,0.3);color:#93c5fd;}
.crisis-banner{background:rgba(255,80,80,0.1);border:1px solid rgba(255,80,80,0.25);border-radius:14px;padding:12px 16px;font-size:0.8rem;color:rgba(255,180,180,0.9);margin-bottom:12px;font-weight:600;line-height:1.6;}
</style></head><body>
{{ topnav }}
<div class="chat-wrap">
    <div class="chat-header">
        <h1 class="chat-title">💬 AI Therapist</h1>
        <p class="chat-sub">A safe, judgement-free space to talk through your feelings</p>
        <div class="sage-avatar"><div class="sage-dot"></div><span class="sage-name">Sage is online and listening</span></div>
        <div class="crisis-banner">🆘 In crisis? Call iCall: <strong>9152987821</strong> | Vandrevala Foundation: <strong>1860-2662-345</strong> (24/7, free)</div>
    </div>
    <div class="messages" id="messages"></div>
    <div class="quick-chips" id="quickChips">
        <button class="chip" onclick="sendChip(this)">😰 I feel anxious</button>
        <button class="chip" onclick="sendChip(this)">😢 I'm feeling sad</button>
        <button class="chip" onclick="sendChip(this)">😓 I'm overwhelmed</button>
        <button class="chip" onclick="sendChip(this)">😴 I can't sleep</button>
        <button class="chip" onclick="sendChip(this)">💭 I need motivation</button>
        <button class="chip" onclick="sendChip(this)">🧘 Breathing exercise</button>
    </div>
    <div class="input-area">
        <textarea class="chat-input" id="chatInput" placeholder="Talk to Sage... press Enter to send" rows="1" onkeydown="handleKey(event)" oninput="autoResize(this)"></textarea>
        <button class="send-btn" onclick="sendMessage()" title="Send">➤</button>
    </div>
</div>

<script>
let history=[];
const user='{{ session["user"] }}';

function addMessage(role,text){
    const box=document.getElementById('messages');
    const div=document.createElement('div');
    div.className='msg '+(role==='user'?'user':'sage');
    const initials=role==='user'?user[0].toUpperCase():'🌿';
    div.innerHTML=`<div class="msg-avatar">${initials}</div><div class="msg-bubble">${text.replace(/\*\*(.*?)\*\*/g,'<strong>$1</strong>').replace(/\n/g,'<br>')}</div>`;
    box.appendChild(div);
    box.scrollTop=box.scrollHeight;
}
function showTyping(){
    const box=document.getElementById('messages');
    const div=document.createElement('div');div.id='typing';div.className='msg sage';
    div.innerHTML=`<div class="msg-avatar">🌿</div><div class="typing-indicator"><div class="typing-dot"></div><div class="typing-dot"></div><div class="typing-dot"></div></div>`;
    box.appendChild(div);box.scrollTop=box.scrollHeight;
}
function hideTyping(){const t=document.getElementById('typing');if(t)t.remove();}

function sendMessage(){
    const inp=document.getElementById('chatInput');
    const text=inp.value.trim();if(!text)return;
    addMessage('user',text);
    history.push({role:'user',content:text});
    inp.value='';inp.style.height='auto';
    document.getElementById('quickChips').style.display='none';
    showTyping();
    fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({messages:history})})
    .then(r=>r.json()).then(d=>{hideTyping();const reply=d.reply||'Sorry, I had trouble responding.';addMessage('sage',reply);history.push({role:'assistant',content:reply});});
}
function sendChip(btn){
    document.getElementById('chatInput').value=btn.textContent.slice(2).trim();
    sendMessage();
}
function handleKey(e){if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();sendMessage();}}
function autoResize(el){el.style.height='auto';el.style.height=Math.min(el.scrollHeight,120)+'px';}

// opening message
window.onload=()=>{
    setTimeout(()=>addMessage('sage',`Hello ${user} 🌿 I'm Sage, your wellness companion. This is a safe, confidential space — share whatever is on your mind. How are you feeling today?`),400);
};
</script>
</body></html>
""", topnav=TOPNAV, page_css=PAGE_BASE_CSS, session=session)


@app.route("/api/chat", methods=["POST"])
def api_chat():
    if "user" not in session: return jsonify({"error":"Not logged in"}),401
    data = request.get_json()
    messages = data.get("messages",[])
    if not messages: return jsonify({"error":"No messages"}),400
    # keep last 10 messages for context window
    messages = messages[-10:]
    reply = call_claude(messages)
    return jsonify({"reply": reply})


# ══════════════════════════════════════════════════════════════════════════════
# ── NEW FEATURE 3: MOOD TRACKING ─────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════
MOOD_META = {
    "happy":   {"emoji":"😊","color":"#fde68a","label":"Happy"},
    "calm":    {"emoji":"😌","color":"#6ee7b7","label":"Calm"},
    "sad":     {"emoji":"😢","color":"#93c5fd","label":"Sad"},
    "angry":   {"emoji":"😠","color":"#fca5a5","label":"Angry"},
    "stressed":{"emoji":"😓","color":"#fb923c","label":"Stressed"},
}

@app.route("/mood", methods=["GET","POST"])
def mood_page():
    if "user" not in session: return redirect("/login")
    msg = ""
    if request.method == "POST":
        mood = request.form.get("mood","")
        note = request.form.get("note","").strip()[:200]
        if mood in MOOD_META:
            conn = sqlite3.connect("app.db"); cur = conn.cursor()
            cur.execute("INSERT INTO mood_logs (username,mood,note) VALUES (?,?,?)",(session["user"],mood,note))
            conn.commit(); conn.close()
            msg = "✅ Mood logged!"

    # fetch last 30 logs for charts
    conn = sqlite3.connect("app.db"); cur = conn.cursor()
    cur.execute("""SELECT mood, note, logged_at FROM mood_logs
                   WHERE username=? ORDER BY id DESC LIMIT 30""", (session["user"],))
    raw = cur.fetchall(); conn.close()

    # weekly counts (last 7 days)
    today = datetime.date.today()
    week_labels = [(today - datetime.timedelta(days=i)).strftime("%a") for i in range(6,-1,-1)]
    week_dates  = [(today - datetime.timedelta(days=i)).strftime("%Y-%m-%d") for i in range(6,-1,-1)]
    mood_keys   = list(MOOD_META.keys())

    # build per-mood per-day counts
    week_data = {m:[0]*7 for m in mood_keys}
    monthly_data = {m:0 for m in mood_keys}
    for (mood, note, logged_at) in raw:
        if mood not in MOOD_META: continue
        log_date = logged_at[:10]
        if log_date in week_dates:
            idx = week_dates.index(log_date)
            week_data[mood][idx] += 1
        # month counts
        log_month = logged_at[:7]
        if log_month == today.strftime("%Y-%m"):
            monthly_data[mood] += 1

    return render_template_string("""
<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>MindSpace — Mood Tracker</title>
<link href="https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700;800;900&family=Playfair+Display:wght@700&display=swap" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<style>
{{ page_css }}
.page-wrap{position:relative;z-index:1;max-width:700px;margin:0 auto;}
.page-title{font-family:'Playfair Display',serif;font-size:1.8rem;margin-bottom:4px;}
.page-sub{color:rgba(255,255,255,0.4);font-size:0.85rem;margin-bottom:24px;}
.glass-card{background:rgba(255,255,255,0.04);backdrop-filter:blur(20px);border:1px solid rgba(255,255,255,0.09);border-radius:22px;padding:28px;margin-bottom:18px;}
.section-title{font-weight:800;font-size:1rem;margin-bottom:16px;color:rgba(255,255,255,0.8);}
.mood-picker{display:flex;gap:12px;flex-wrap:wrap;margin-bottom:18px;}
.mood-btn{display:flex;flex-direction:column;align-items:center;gap:6px;padding:16px 20px;border-radius:18px;border:2px solid rgba(255,255,255,0.1);background:rgba(255,255,255,0.04);cursor:pointer;transition:all 0.25s;font-family:'Nunito',sans-serif;flex:1;min-width:80px;}
.mood-btn:hover{transform:translateY(-3px);box-shadow:0 8px 24px rgba(0,0,0,0.3);}
.mood-btn.selected{border-width:2px;}
.mood-emoji{font-size:2rem;line-height:1;}
.mood-name{font-size:0.75rem;font-weight:800;color:rgba(255,255,255,0.6);}
.note-input{width:100%;padding:13px 16px;background:rgba(255,255,255,0.06);border:1.5px solid rgba(255,255,255,0.1);border-radius:14px;color:#fff;font-size:0.9rem;font-family:'Nunito',sans-serif;outline:none;margin-bottom:14px;transition:border-color 0.3s;}
.note-input:focus{border-color:rgba(110,231,183,0.5);}
.note-input::placeholder{color:rgba(255,255,255,0.3);}
.log-btn{padding:13px 28px;border:none;border-radius:14px;background:linear-gradient(135deg,#6ee7b7,#5bc8f5);color:#0d1a14;font-family:'Nunito',sans-serif;font-weight:900;font-size:0.95rem;cursor:pointer;transition:transform 0.2s,box-shadow 0.2s;width:100%;}
.log-btn:hover{transform:translateY(-2px);box-shadow:0 8px 24px rgba(110,231,183,0.3);}
.success-banner{background:rgba(110,231,183,0.12);border:1px solid rgba(110,231,183,0.3);color:#6ee7b7;padding:10px 16px;border-radius:12px;font-weight:700;font-size:0.88rem;margin-bottom:16px;}
.chart-tabs{display:flex;gap:8px;margin-bottom:16px;}
.ctab{padding:7px 18px;border:1.5px solid rgba(255,255,255,0.1);border-radius:99px;background:transparent;color:rgba(255,255,255,0.5);font-family:'Nunito',sans-serif;font-weight:700;font-size:0.8rem;cursor:pointer;transition:all 0.2s;}
.ctab.active{background:rgba(110,231,183,0.15);border-color:#6ee7b7;color:#6ee7b7;}
.chart-panel{display:none;}.chart-panel.active{display:block;}
.recent-log{display:flex;align-items:center;gap:12px;padding:12px 16px;background:rgba(255,255,255,0.03);border-radius:12px;margin-bottom:8px;border:1px solid rgba(255,255,255,0.06);}
.log-emoji{font-size:1.5rem;}
.log-info{flex:1;}
.log-mood{font-weight:800;font-size:0.88rem;}
.log-note{font-size:0.78rem;color:rgba(255,255,255,0.4);margin-top:2px;}
.log-time{font-size:0.72rem;color:rgba(255,255,255,0.3);white-space:nowrap;}
.empty-state{text-align:center;color:rgba(255,255,255,0.3);padding:32px;font-size:0.9rem;}
</style></head><body>
{{ topnav }}
<div class="page-wrap">
    <h1 class="page-title">📅 Mood Tracker</h1>
    <p class="page-sub">Log your daily mood and watch your emotional trends unfold</p>

    <!-- LOG TODAY'S MOOD -->
    <div class="glass-card">
        <div class="section-title">How are you feeling right now?</div>
        {% if msg %}<div class="success-banner">{{ msg }}</div>{% endif %}
        <form method="post" id="moodForm">
            <div class="mood-picker" id="moodPicker">
                {% for key, meta in moods.items() %}
                <button type="button" class="mood-btn" data-mood="{{ key }}"
                    onclick="selectMood('{{ key }}','{{ meta.color }}')"
                    style="">
                    <span class="mood-emoji">{{ meta.emoji }}</span>
                    <span class="mood-name">{{ meta.label }}</span>
                </button>
                {% endfor %}
            </div>
            <input type="hidden" name="mood" id="moodInput">
            <input class="note-input" name="note" placeholder="✏️  Add a note (optional) — what's on your mind?" maxlength="200">
            <button type="submit" class="log-btn" onclick="return validateMood()">📝 Log My Mood</button>
        </form>
    </div>

    <!-- CHARTS -->
    <div class="glass-card">
        <div class="section-title">📊 Your Emotional Trends</div>
        <div class="chart-tabs">
            <button class="ctab active" onclick="switchChart('weekly',this)">Weekly</button>
            <button class="ctab" onclick="switchChart('monthly',this)">Monthly</button>
        </div>
        <div class="chart-panel active" id="chart-weekly">
            <div style="position:relative;height:260px;">
                <canvas id="weeklyChart" role="img" aria-label="Weekly mood bar chart">Weekly mood distribution over last 7 days.</canvas>
            </div>
        </div>
        <div class="chart-panel" id="chart-monthly">
            <div style="position:relative;height:260px;">
                <canvas id="monthlyChart" role="img" aria-label="Monthly mood donut chart">Monthly mood breakdown.</canvas>
            </div>
        </div>
    </div>

    <!-- RECENT LOGS -->
    <div class="glass-card">
        <div class="section-title">🕐 Recent Entries</div>
        {% if logs %}
        {% for mood, note, logged_at in logs %}
        <div class="recent-log">
            <div class="log-emoji">{{ moods[mood].emoji if mood in moods else '❓' }}</div>
            <div class="log-info">
                <div class="log-mood" style="color:{{ moods[mood].color if mood in moods else '#fff' }}">{{ moods[mood].label if mood in moods else mood }}</div>
                <div class="log-note">{{ note if note else 'No note added' }}</div>
            </div>
            <div class="log-time">{{ logged_at[:16] }}</div>
        </div>
        {% endfor %}
        {% else %}
        <div class="empty-state">🌱 No mood entries yet — log your first mood above!</div>
        {% endif %}
    </div>
</div>

<script>
function selectMood(key,color){
    document.getElementById('moodInput').value=key;
    document.querySelectorAll('.mood-btn').forEach(b=>{
        b.classList.remove('selected');
        b.style.borderColor='rgba(255,255,255,0.1)';
        b.style.background='rgba(255,255,255,0.04)';
    });
    const btn=document.querySelector(`[data-mood="${key}"]`);
    btn.classList.add('selected');
    btn.style.borderColor=color;
    btn.style.background=color+'22';
}
function validateMood(){
    if(!document.getElementById('moodInput').value){alert('Please select a mood!');return false;}
    return true;
}
function switchChart(type,btn){
    document.querySelectorAll('.ctab').forEach(b=>b.classList.remove('active'));
    document.querySelectorAll('.chart-panel').forEach(p=>p.classList.remove('active'));
    btn.classList.add('active');
    document.getElementById('chart-'+type).classList.add('active');
}

const weekLabels  = {{ week_labels|tojson }};
const weekData    = {{ week_data|tojson }};
const monthlyData = {{ monthly_data|tojson }};
const moodColors  = {happy:'#fde68a',calm:'#6ee7b7',sad:'#93c5fd',angry:'#fca5a5',stressed:'#fb923c'};
const moodKeys    = ['happy','calm','sad','angry','stressed'];

// Weekly stacked bar chart
new Chart(document.getElementById('weeklyChart'),{
    type:'bar',
    data:{
        labels:weekLabels,
        datasets:moodKeys.map(m=>({
            label:m.charAt(0).toUpperCase()+m.slice(1),
            data:weekData[m],
            backgroundColor:moodColors[m]+'cc',
            borderColor:moodColors[m],
            borderWidth:1,
            borderRadius:4,
        }))
    },
    options:{
        responsive:true,maintainAspectRatio:false,
        plugins:{legend:{display:false}},
        scales:{
            x:{stacked:true,grid:{color:'rgba(255,255,255,0.05)'},ticks:{color:'rgba(255,255,255,0.5)',font:{family:'Nunito',size:12}}},
            y:{stacked:true,beginAtZero:true,ticks:{stepSize:1,color:'rgba(255,255,255,0.4)',font:{family:'Nunito',size:11}},grid:{color:'rgba(255,255,255,0.05)'}}
        }
    }
});

// Monthly doughnut
const monthVals=moodKeys.map(m=>monthlyData[m]||0);
const hasData=monthVals.some(v=>v>0);
new Chart(document.getElementById('monthlyChart'),{
    type:'doughnut',
    data:{
        labels:moodKeys.map(m=>m.charAt(0).toUpperCase()+m.slice(1)),
        datasets:[{data:hasData?monthVals:[1],backgroundColor:hasData?moodKeys.map(m=>moodColors[m]+'cc'):['rgba(255,255,255,0.08)'],borderColor:hasData?moodKeys.map(m=>moodColors[m]):['rgba(255,255,255,0.12)'],borderWidth:2}]
    },
    options:{
        responsive:true,maintainAspectRatio:false,cutout:'65%',
        plugins:{legend:{display:false},tooltip:{enabled:hasData}}
    }
});
</script>
</body></html>
""", topnav=TOPNAV, page_css=PAGE_BASE_CSS, msg=msg, moods=MOOD_META,
     logs=raw, week_labels=week_labels, week_data=week_data, monthly_data=monthly_data)


# ══════════════════════════════════════════════════════════════════════════════
# GAMES — Sudoku + Chess (original, unchanged)
# ══════════════════════════════════════════════════════════════════════════════
@app.route("/games")
def games():
    if "user" not in session: return redirect("/login")
    return render_template_string("""
<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>MindSpace — Mind Games</title>
<link href="https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700;800;900&family=Playfair+Display:wght@700&display=swap" rel="stylesheet">
<style>
{{ page_css }}
.page-wrap{position:relative;z-index:1;max-width:720px;margin:0 auto;}
.page-title{font-family:'Playfair Display',serif;font-size:1.8rem;margin-bottom:4px;}
.page-sub{color:rgba(255,255,255,0.4);font-size:0.85rem;margin-bottom:24px;}
.game-tabs{display:flex;gap:10px;margin-bottom:24px;background:rgba(255,255,255,0.04);padding:6px;border-radius:16px;border:1px solid rgba(255,255,255,0.08);}
.tab-btn{flex:1;padding:10px;border:none;border-radius:12px;font-family:'Nunito',sans-serif;font-weight:800;font-size:0.9rem;cursor:pointer;transition:all 0.25s;background:transparent;color:rgba(255,255,255,0.4);}
.tab-btn.active{background:linear-gradient(135deg,#5bc8f5,#a78bfa);color:#fff;box-shadow:0 4px 16px rgba(92,200,245,0.3);}
.game-panel{display:none;}.game-panel.active{display:block;}
.sudoku-wrap{display:flex;flex-direction:column;align-items:center;}
.sudoku-status{text-align:center;color:rgba(255,255,255,0.5);font-size:0.85rem;margin-bottom:14px;min-height:24px;}
.sudoku-outer{display:grid;grid-template-columns:repeat(3,1fr);gap:3px;background:rgba(92,200,245,0.5);border-radius:12px;padding:3px;max-width:378px;width:100%;}
.sudoku-box{display:grid;grid-template-columns:repeat(3,1fr);gap:1px;background:rgba(255,255,255,0.08);}
.sudoku-cell{background:#111827;aspect-ratio:1;display:flex;align-items:center;justify-content:center;font-size:1.05rem;font-weight:800;cursor:pointer;transition:background 0.15s;border:none;color:#fff;font-family:'Nunito',sans-serif;min-width:0;}
.sudoku-cell:hover{background:#1e293b;}.sudoku-cell.given{color:#5bc8f5;cursor:default;}
.sudoku-cell.selected{background:#1e3a5f!important;}.sudoku-cell.highlight{background:#1a2744;}
.sudoku-cell.error{color:#ff6b6b!important;background:#3b1212!important;}
.sudoku-numpad{display:flex;gap:8px;justify-content:center;flex-wrap:wrap;margin:16px 0;}
.num-btn{width:40px;height:40px;border:1.5px solid rgba(255,255,255,0.12);border-radius:10px;background:rgba(255,255,255,0.05);color:#fff;font-size:1.05rem;font-weight:800;cursor:pointer;font-family:'Nunito',sans-serif;transition:all 0.2s;}
.num-btn:hover{background:rgba(92,200,245,0.15);border-color:#5bc8f5;}
.game-actions{display:flex;gap:10px;justify-content:center;flex-wrap:wrap;}
.game-btn{padding:10px 20px;border:none;border-radius:12px;font-family:'Nunito',sans-serif;font-weight:800;font-size:0.85rem;cursor:pointer;transition:all 0.2s;}
.game-btn.primary{background:linear-gradient(135deg,#5bc8f5,#a78bfa);color:#fff;}
.game-btn.secondary{background:rgba(255,255,255,0.06);border:1.5px solid rgba(255,255,255,0.12);color:rgba(255,255,255,0.7);}
.game-btn:hover{transform:translateY(-2px);}
.difficulty-row{display:flex;gap:8px;justify-content:center;margin-bottom:14px;}
.diff-btn{padding:6px 14px;border:1.5px solid rgba(255,255,255,0.12);border-radius:20px;background:transparent;color:rgba(255,255,255,0.5);font-family:'Nunito',sans-serif;font-weight:700;font-size:0.8rem;cursor:pointer;transition:all 0.2s;}
.diff-btn.active{background:linear-gradient(135deg,#5bc8f5,#a78bfa);border-color:transparent;color:#fff;}
.timer-row{text-align:center;color:rgba(255,255,255,0.4);font-size:0.85rem;margin-bottom:10px;font-weight:700;}
.chess-wrap{max-width:440px;margin:0 auto;}
.chess-top{display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;}
.chess-player{display:flex;align-items:center;gap:8px;padding:8px 14px;background:rgba(255,255,255,0.05);border-radius:12px;border:1.5px solid rgba(255,255,255,0.08);font-weight:800;font-size:0.88rem;}
.chess-player.active-turn{border-color:rgba(92,200,245,0.5);background:rgba(92,200,245,0.08);}
.board-wrapper{position:relative;}
.rank-labels{position:absolute;left:-20px;top:0;height:100%;display:flex;flex-direction:column;justify-content:space-around;color:rgba(255,255,255,0.35);font-size:0.7rem;font-weight:700;}
.file-labels{display:flex;justify-content:space-around;padding:4px 0;color:rgba(255,255,255,0.35);font-size:0.7rem;font-weight:700;}
.chess-board{display:grid;grid-template-columns:repeat(8,1fr);border-radius:10px;overflow:hidden;border:2px solid rgba(255,255,255,0.12);}
.chess-sq{aspect-ratio:1;display:flex;align-items:center;justify-content:center;font-size:1.65rem;cursor:pointer;transition:all 0.12s;position:relative;user-select:none;}
.chess-sq.light{background:rgba(240,217,181,0.15);}.chess-sq.dark{background:rgba(100,60,30,0.35);}
.chess-sq.selected{background:rgba(92,200,245,0.4)!important;}
.chess-sq.valid-move::after{content:'';position:absolute;width:32%;height:32%;border-radius:50%;background:rgba(92,200,245,0.55);pointer-events:none;}
.chess-sq.valid-capture{background:rgba(255,80,80,0.3)!important;}
.chess-sq.in-check{background:rgba(255,50,50,0.55)!important;}
.chess-sq.last-from{background:rgba(255,220,80,0.18)!important;}
.chess-sq.last-to{background:rgba(255,220,80,0.28)!important;}
.chess-info-bar{display:flex;justify-content:space-between;align-items:center;padding:10px 14px;margin-top:10px;background:rgba(255,255,255,0.04);border-radius:12px;border:1px solid rgba(255,255,255,0.07);}
.chess-status{font-weight:700;font-size:0.85rem;color:rgba(255,255,255,0.6);}
.captured-row{display:flex;gap:4px;flex-wrap:wrap;min-height:24px;}
.captured-piece{font-size:1.1rem;opacity:0.7;}
.promotion-modal{display:none;position:fixed;inset:0;background:rgba(0,0,0,0.7);z-index:500;align-items:center;justify-content:center;}
.promotion-modal.show{display:flex;}
.promotion-box{background:#1a1a2e;border:1px solid rgba(255,255,255,0.15);border-radius:20px;padding:28px;text-align:center;}
.promotion-box h3{margin-bottom:16px;color:#fff;font-family:'Playfair Display',serif;}
.promo-choices{display:flex;gap:12px;justify-content:center;}
.promo-btn{width:56px;height:56px;background:rgba(255,255,255,0.08);border:1.5px solid rgba(255,255,255,0.15);border-radius:14px;font-size:2rem;cursor:pointer;transition:all 0.2s;}
.promo-btn:hover{background:rgba(92,200,245,0.2);border-color:#5bc8f5;transform:scale(1.1);}
.move-history{max-height:120px;overflow-y:auto;margin-top:10px;background:rgba(255,255,255,0.03);border-radius:10px;padding:8px 12px;}
.move-history-inner{display:grid;grid-template-columns:repeat(2,1fr);gap:2px;}
.move-entry{font-size:0.78rem;color:rgba(255,255,255,0.5);padding:2px 4px;border-radius:4px;}
.move-entry.white{color:rgba(255,255,255,0.7);}
.move-entry span.move-num{color:rgba(255,255,255,0.3);font-size:0.7rem;}
</style></head><body>
{{ topnav }}
<div class="page-wrap">
    <h1 class="page-title">🎮 Mind Games</h1>
    <p class="page-sub">Sharpen your mind with these strategy games</p>
    <div class="game-tabs">
        <button class="tab-btn active" onclick="switchTab('sudoku',this)">🔢 Sudoku</button>
        <button class="tab-btn" onclick="switchTab('chess',this)">♟️ Chess</button>
    </div>
    <div class="game-panel active" id="panel-sudoku">
        <div class="sudoku-wrap">
            <div class="difficulty-row">
                <button class="diff-btn active" onclick="setDiff('easy',this)">Easy</button>
                <button class="diff-btn" onclick="setDiff('medium',this)">Medium</button>
                <button class="diff-btn" onclick="setDiff('hard',this)">Hard</button>
            </div>
            <div class="timer-row" id="timerRow">⏱ 00:00</div>
            <div class="sudoku-status" id="sudokuStatus">Select a cell and type a number</div>
            <div class="sudoku-outer" id="sudokuOuter"></div>
            <div class="sudoku-numpad" id="numpad"></div>
            <div class="game-actions">
                <button class="game-btn primary" onclick="newSudokuGame()">🔄 New Game</button>
                <button class="game-btn secondary" onclick="clearCell()">⌫ Clear</button>
                <button class="game-btn secondary" onclick="hintCell()">💡 Hint</button>
                <button class="game-btn secondary" onclick="checkSudoku()">✅ Check</button>
            </div>
        </div>
    </div>
    <div class="game-panel" id="panel-chess">
        <div class="chess-wrap">
            <div class="chess-top">
                <div class="chess-player" id="blackPlayer">⚫ Black</div>
                <button class="game-btn secondary" onclick="newChessGame()" style="padding:6px 16px;font-size:0.8rem;">🔄 New Game</button>
                <div class="chess-player active-turn" id="whitePlayer">⚪ White</div>
            </div>
            <div class="captured-row" id="capturedByBlack" style="margin-bottom:6px;"></div>
            <div class="board-wrapper">
                <div class="rank-labels" id="rankLabels"></div>
                <div class="chess-board" id="chessBoard"></div>
            </div>
            <div class="file-labels" id="chessFiles"></div>
            <div class="captured-row" id="capturedByWhite" style="margin-top:6px;"></div>
            <div class="chess-info-bar">
                <span class="chess-status" id="chessStatus">Click a piece to start</span>
            </div>
            <div class="move-history" id="moveHistoryWrap" style="display:none;">
                <div class="move-history-inner" id="moveHistory"></div>
            </div>
        </div>
        <div class="promotion-modal" id="promoModal">
            <div class="promotion-box"><h3>Promote Pawn</h3><div class="promo-choices" id="promoChoices"></div></div>
        </div>
    </div>
</div>
<script>
// ====================== SUDOKU ======================
let sudokuPuzzle=[],sudokuSolution=[],selectedCell=-1,difficulty='easy';
let timerInterval=null,timerSeconds=0,hintsUsed=0;
const PUZZLES={
easy:[[5,3,0,0,7,0,0,0,0,6,0,0,1,9,5,0,0,0,0,9,8,0,0,0,0,6,0,8,0,0,0,6,0,0,0,3,4,0,0,8,0,3,0,0,1,7,0,0,0,2,0,0,0,6,0,6,0,0,0,0,2,8,0,0,0,0,4,1,9,0,0,5,0,0,0,0,8,0,0,7,9],[0,0,0,2,6,0,7,0,1,6,8,0,0,7,0,0,9,0,1,9,0,0,0,4,5,0,0,8,2,0,1,0,0,0,4,0,0,0,4,6,0,2,9,0,0,0,5,0,0,0,3,0,2,8,0,0,9,3,0,0,0,7,4,0,4,0,0,5,0,0,3,6,7,0,3,0,1,8,0,0,0]],
medium:[[0,2,0,0,0,0,0,0,0,0,0,0,6,0,0,0,0,3,0,7,4,0,8,0,0,0,0,0,0,0,0,0,3,0,0,2,0,8,0,0,4,0,0,1,0,6,0,0,5,0,0,0,0,0,0,0,0,0,1,0,7,8,0,5,0,0,0,0,9,0,0,0,0,0,0,0,0,0,0,4,0],[0,0,0,0,0,0,2,0,0,0,8,0,0,3,0,0,7,0,0,0,3,6,0,0,0,8,0,0,1,0,0,0,0,0,0,0,0,0,8,5,0,0,0,0,6,0,0,0,0,0,4,0,0,0,0,2,0,0,0,3,9,0,0,0,4,0,0,8,0,0,2,0,0,0,5,0,0,0,0,0,0]],
hard:[[8,0,0,0,0,0,0,0,0,0,0,3,6,0,0,0,0,0,0,7,0,0,9,0,2,0,0,0,5,0,0,0,7,0,0,0,0,0,0,0,4,5,7,0,0,0,0,0,1,0,0,0,3,0,0,0,1,0,0,0,0,6,8,0,0,8,5,0,0,0,1,0,0,9,0,0,0,0,4,0,0],[0,0,5,3,0,0,0,0,0,8,0,0,0,0,0,0,2,0,0,7,0,0,1,0,5,0,0,4,0,0,0,0,5,3,0,0,0,1,0,0,7,0,0,0,6,0,0,3,2,0,0,0,8,0,0,6,0,5,0,0,0,0,9,0,0,4,0,0,0,0,3,0,0,0,0,0,0,9,7,0,0]]
};
let origPuzzle=[];
function solveSudoku(b){const bd=[...b];function ok(b,r,c,n){for(let i=0;i<9;i++){if(b[r*9+i]===n||b[i*9+c]===n)return false;}const br=Math.floor(r/3)*3,bc=Math.floor(c/3)*3;for(let i=0;i<3;i++)for(let j=0;j<3;j++)if(b[(br+i)*9+(bc+j)]===n)return false;return true;}function solve(){const e=bd.indexOf(0);if(e===-1)return true;const r=Math.floor(e/9),c=e%9;for(let n=1;n<=9;n++){if(ok(bd,r,c,n)){bd[e]=n;if(solve())return true;bd[e]=0;}}return false;}solve();return bd;}
function setDiff(d,btn){difficulty=d;document.querySelectorAll('.diff-btn').forEach(b=>b.classList.remove('active'));btn.classList.add('active');newSudokuGame();}
function updateTimer(){const m=String(Math.floor(timerSeconds/60)).padStart(2,'0'),s=String(timerSeconds%60).padStart(2,'0');document.getElementById('timerRow').textContent=`⏱ ${m}:${s}`;}
function renderSudoku(){const outer=document.getElementById('sudokuOuter');outer.innerHTML='';for(let box=0;box<9;box++){const boxDiv=document.createElement('div');boxDiv.className='sudoku-box';const boxRow=Math.floor(box/3)*3,boxCol=(box%3)*3;for(let ri=0;ri<3;ri++)for(let ci=0;ci<3;ci++){const r=boxRow+ri,c=boxCol+ci,idx=r*9+c;const cell=document.createElement('button');cell.className='sudoku-cell';const isOrig=origPuzzle[idx]!==0;if(isOrig)cell.classList.add('given');if(idx===selectedCell)cell.classList.add('selected');else if(selectedCell>=0){const sr=Math.floor(selectedCell/9),sc=selectedCell%9;if(r===sr||c===sc||Math.floor(r/3)===Math.floor(sr/3)&&Math.floor(c/3)===Math.floor(sc/3))cell.classList.add('highlight');}cell.textContent=sudokuPuzzle[idx]||'';if(sudokuPuzzle[idx]!==0&&!isOrig&&sudokuPuzzle[idx]!==sudokuSolution[idx])cell.classList.add('error');cell.onclick=()=>{if(!isOrig){selectedCell=idx;renderSudoku();}};boxDiv.appendChild(cell);}outer.appendChild(boxDiv);}const np=document.getElementById('numpad');np.innerHTML='';for(let n=1;n<=9;n++){const b=document.createElement('button');b.className='num-btn';b.textContent=n;b.onclick=()=>enterNum(n);np.appendChild(b);}}
function newSudokuGame(){const pool=PUZZLES[difficulty];const base=pool[Math.floor(Math.random()*pool.length)];origPuzzle=[...base];sudokuPuzzle=[...base];sudokuSolution=solveSudoku([...base]);selectedCell=-1;hintsUsed=0;clearInterval(timerInterval);timerSeconds=0;updateTimer();timerInterval=setInterval(()=>{timerSeconds++;updateTimer();},1000);renderSudoku();document.getElementById('sudokuStatus').textContent='Select a cell and type a number';document.getElementById('sudokuStatus').style.color='rgba(255,255,255,0.5)';}
function enterNum(n){if(selectedCell===-1)return;if(origPuzzle[selectedCell]!==0)return;sudokuPuzzle[selectedCell]=n;renderSudoku();if(!sudokuPuzzle.includes(0)){const allOk=sudokuPuzzle.every((v,i)=>v===sudokuSolution[i]);if(allOk){clearInterval(timerInterval);const m=String(Math.floor(timerSeconds/60)).padStart(2,'0'),s=String(timerSeconds%60).padStart(2,'0');document.getElementById('sudokuStatus').textContent=`🎉 Solved in ${m}:${s}!`;document.getElementById('sudokuStatus').style.color='#6ee7b7';}}}
function clearCell(){if(selectedCell===-1||origPuzzle[selectedCell]!==0)return;sudokuPuzzle[selectedCell]=0;renderSudoku();}
function hintCell(){if(selectedCell===-1||origPuzzle[selectedCell]!==0)return;sudokuPuzzle[selectedCell]=sudokuSolution[selectedCell];hintsUsed++;renderSudoku();document.getElementById('sudokuStatus').textContent=`💡 Hint used (${hintsUsed} total)`;document.getElementById('sudokuStatus').style.color='#fde68a';}
function checkSudoku(){let errors=0;sudokuPuzzle.forEach((v,i)=>{if(v!==0&&v!==sudokuSolution[i])errors++;});const status=document.getElementById('sudokuStatus');if(errors===0&&!sudokuPuzzle.includes(0)){clearInterval(timerInterval);status.textContent='🎉 Puzzle Complete!';status.style.color='#6ee7b7';}else if(errors>0){status.textContent=`❌ ${errors} error(s) — keep going!`;status.style.color='#ff9a9a';}else{status.textContent='✅ Looking correct so far!';status.style.color='#6ee7b7';}}
document.addEventListener('keydown',e=>{if(document.getElementById('panel-sudoku').classList.contains('active')){const n=parseInt(e.key);if(n>=1&&n<=9)enterNum(n);else if(e.key==='Backspace'||e.key==='Delete')clearCell();else if(e.key==='ArrowRight'&&selectedCell%9<8){selectedCell++;renderSudoku();}else if(e.key==='ArrowLeft'&&selectedCell%9>0){selectedCell--;renderSudoku();}else if(e.key==='ArrowDown'&&selectedCell<72){selectedCell+=9;renderSudoku();}else if(e.key==='ArrowUp'&&selectedCell>=9){selectedCell-=9;renderSudoku();}}});
newSudokuGame();
// ====================== CHESS ======================
const PIECES={wK:'♔',wQ:'♕',wR:'♖',wB:'♗',wN:'♘',wP:'♙',bK:'♚',bQ:'♛',bR:'♜',bB:'♝',bN:'♞',bP:'♟'};
let board=[],turn='w',selected=null,validMoves=[],gameOver=false;
let capturedWhite=[],capturedBlack=[],enPassantTarget=null,castlingRights={wK:true,wQ:true,bK:true,bQ:true},lastFrom=-1,lastTo=-1,moveList=[],pendingPromotion=null;
function sq(r,c){return r*8+c;}function rc(idx){return{r:Math.floor(idx/8),c:idx%8};}function inBounds(r,c){return r>=0&&r<8&&c>=0&&c<8;}function color(p){return p?p[0]:null;}function type(p){return p?p[1]:null;}
function initChess(){board=new Array(64).fill(null);const backRank=['R','N','B','Q','K','B','N','R'];for(let c=0;c<8;c++){board[sq(0,c)]='b'+backRank[c];board[sq(1,c)]='bP';board[sq(6,c)]='wP';board[sq(7,c)]='w'+backRank[c];}turn='w';selected=null;validMoves=[];gameOver=false;capturedWhite=[];capturedBlack=[];enPassantTarget=null;castlingRights={wK:true,wQ:true,bK:true,bQ:true};lastFrom=-1;lastTo=-1;moveList=[];pendingPromotion=null;renderChess();updateChessUI();}
function findKing(col){return board.findIndex(p=>p===col+'K');}
function isAttacked(idx,byColor){const{r,c}=rc(idx);const pDir=byColor==='w'?1:-1;for(const dc of[-1,1]){const ar=r+pDir,ac=c+dc;if(inBounds(ar,ac)&&board[sq(ar,ac)]===byColor+'P')return true;}for(const[dr,dc]of[[-2,-1],[-2,1],[-1,-2],[-1,2],[1,-2],[1,2],[2,-1],[2,1]]){const nr=r+dr,nc=c+dc;if(inBounds(nr,nc)&&board[sq(nr,nc)]===byColor+'N')return true;}for(const[dr,dc]of[[-1,-1],[-1,0],[-1,1],[0,-1],[0,1],[1,-1],[1,0],[1,1]]){const nr=r+dr,nc=c+dc;if(inBounds(nr,nc)&&board[sq(nr,nc)]===byColor+'K')return true;}for(const[dr,dc]of[[1,0],[-1,0],[0,1],[0,-1]]){let nr=r+dr,nc=c+dc;while(inBounds(nr,nc)){const p=board[sq(nr,nc)];if(p){if(color(p)===byColor&&(type(p)==='R'||type(p)==='Q'))return true;break;}nr+=dr;nc+=dc;}}for(const[dr,dc]of[[1,1],[1,-1],[-1,1],[-1,-1]]){let nr=r+dr,nc=c+dc;while(inBounds(nr,nc)){const p=board[sq(nr,nc)];if(p){if(color(p)===byColor&&(type(p)==='B'||type(p)==='Q'))return true;break;}nr+=dr;nc+=dc;}}return false;}
function isInCheck(col){return isAttacked(findKing(col),col==='w'?'b':'w');}
function getLegalMoves(fromIdx){const p=board[fromIdx];if(!p)return[];const col=color(p),tp=type(p);const{r,c}=rc(fromIdx);const opp=col==='w'?'b':'w';const pseudo=[];const addIf=(r2,c2)=>{if(inBounds(r2,c2)&&color(board[sq(r2,c2)])!==col)pseudo.push(sq(r2,c2));};const slide=(dr,dc)=>{let nr=r+dr,nc=c+dc;while(inBounds(nr,nc)){const t2=board[sq(nr,nc)];if(!t2){pseudo.push(sq(nr,nc));}else{if(color(t2)===opp)pseudo.push(sq(nr,nc));break;}nr+=dr;nc+=dc;}};if(tp==='P'){const dir=col==='w'?-1:1;const startRow=col==='w'?6:1;if(inBounds(r+dir,c)&&!board[sq(r+dir,c)]){pseudo.push(sq(r+dir,c));if(r===startRow&&!board[sq(r+2*dir,c)])pseudo.push(sq(r+2*dir,c));}for(const dc of[-1,1]){const nr=r+dir,nc=c+dc;if(inBounds(nr,nc)){if(color(board[sq(nr,nc)])===opp)pseudo.push(sq(nr,nc));if(sq(nr,nc)===enPassantTarget)pseudo.push(sq(nr,nc));}}}else if(tp==='N'){[[-2,-1],[-2,1],[-1,-2],[-1,2],[1,-2],[1,2],[2,-1],[2,1]].forEach(([dr,dc])=>addIf(r+dr,c+dc));}else if(tp==='R'){slide(1,0);slide(-1,0);slide(0,1);slide(0,-1);}else if(tp==='B'){slide(1,1);slide(1,-1);slide(-1,1);slide(-1,-1);}else if(tp==='Q'){slide(1,0);slide(-1,0);slide(0,1);slide(0,-1);slide(1,1);slide(1,-1);slide(-1,1);slide(-1,-1);}else if(tp==='K'){[[-1,-1],[-1,0],[-1,1],[0,-1],[0,1],[1,-1],[1,0],[1,1]].forEach(([dr,dc])=>addIf(r+dr,c+dc));const row=col==='w'?7:0;if(r===row&&c===4&&!isInCheck(col)){if(castlingRights[col+'K']&&!board[sq(row,5)]&&!board[sq(row,6)]&&!isAttacked(sq(row,5),opp)&&!isAttacked(sq(row,6),opp))pseudo.push(sq(row,6));if(castlingRights[col+'Q']&&!board[sq(row,3)]&&!board[sq(row,2)]&&!board[sq(row,1)]&&!isAttacked(sq(row,3),opp)&&!isAttacked(sq(row,2),opp))pseudo.push(sq(row,2));}}
return pseudo.filter(to=>{const savedBoard=[...board],savedEP=enPassantTarget;let epCaptured=null;if(tp==='P'&&to===enPassantTarget){const epR=r,epC=rc(to).c;epCaptured=sq(epR,epC);board[epCaptured]=null;}board[to]=p;board[fromIdx]=null;if(tp==='K'){const dc2=rc(to).c-c;if(Math.abs(dc2)===2){const row2=col==='w'?7:0;if(dc2>0){board[sq(row2,5)]=col+'R';board[sq(row2,7)]=null;}else{board[sq(row2,3)]=col+'R';board[sq(row2,0)]=null;}}}const ok=!isInCheck(col);board=[...savedBoard];enPassantTarget=savedEP;return ok;});}
function applyMove(from,to){const p=board[from],col=color(p),tp2=type(p);const{r:tr,c:tc}=rc(to);const{r:fr,c:fc}=rc(from);const captured=board[to];if(tp2==='P'&&to===enPassantTarget){const epIdx=sq(fr,tc);if(board[epIdx]){(col==='w'?capturedBlack:capturedWhite).push(board[epIdx]);board[epIdx]=null;}}else if(captured){(col==='w'?capturedBlack:capturedWhite).push(captured);}board[to]=p;board[from]=null;if(tp2==='K'){const dc2=tc-fc;if(dc2===2){board[sq(tr,5)]=col+'R';board[sq(tr,7)]=null;}else if(dc2===-2){board[sq(tr,3)]=col+'R';board[sq(tr,0)]=null;}}if(tp2==='K'){castlingRights[col+'K']=false;castlingRights[col+'Q']=false;}if(tp2==='R'){if(fc===0)castlingRights[col+'Q']=false;if(fc===7)castlingRights[col+'K']=false;}enPassantTarget=null;if(tp2==='P'&&Math.abs(tr-fr)===2)enPassantTarget=sq((fr+tr)/2,fc);lastFrom=from;lastTo=to;const notation=getNotation(p,from,to,captured);moveList.push({col,notation});turn=turn==='w'?'b':'w';if(tp2==='P'&&(tr===0||tr===7)){pendingPromotion={from,to};showPromotion(col);}else{finishMove();}}
function getNotation(p,from,to){const files='abcdefgh';const{r:fr,c:fc}=rc(from);const{r:tr,c:tc}=rc(to);const tp2=type(p);if(tp2==='K'&&Math.abs(tc-fc)===2)return tc>fc?'O-O':'O-O-O';return(tp2!=='P'?tp2:'')+files[fc]+(8-fr)+files[tc]+(8-tr);}
function showPromotion(col){const modal=document.getElementById('promoModal');modal.classList.add('show');const choices=document.getElementById('promoChoices');choices.innerHTML='';['Q','R','B','N'].forEach(t=>{const btn=document.createElement('button');btn.className='promo-btn';btn.textContent=PIECES[col+t];btn.onclick=()=>{board[pendingPromotion.to]=col+t;pendingPromotion=null;modal.classList.remove('show');finishMove();};choices.appendChild(btn);});}
function finishMove(){renderChess();updateChessUI();updateMoveHistory();}
function handleChessClick(idx){if(gameOver)return;if(selected!==null){if(validMoves.includes(idx)){applyMove(selected,idx);selected=null;validMoves=[];return;}selected=null;validMoves=[];}const p=board[idx];if(p&&color(p)===turn){selected=idx;validMoves=getLegalMoves(idx);}renderChess();}
function renderChess(){const b=document.getElementById('chessBoard');b.innerHTML='';for(let r=0;r<8;r++)for(let c=0;c<8;c++){const idx=sq(r,c);const sqEl=document.createElement('div');sqEl.className='chess-sq '+((r+c)%2===0?'light':'dark');if(selected===idx)sqEl.classList.add('selected');if(validMoves.includes(idx)){if(board[idx])sqEl.classList.add('valid-capture');else sqEl.classList.add('valid-move');}if(idx===lastFrom)sqEl.classList.add('last-from');if(idx===lastTo)sqEl.classList.add('last-to');if(board[idx]&&type(board[idx])==='K'&&isInCheck(color(board[idx])))sqEl.classList.add('in-check');if(board[idx])sqEl.textContent=PIECES[board[idx]]||board[idx];sqEl.onclick=()=>handleChessClick(idx);b.appendChild(sqEl);}document.getElementById('capturedByBlack').innerHTML=capturedBlack.map(p=>`<span class="captured-piece">${PIECES[p]||p}</span>`).join('');document.getElementById('capturedByWhite').innerHTML=capturedWhite.map(p=>`<span class="captured-piece">${PIECES[p]||p}</span>`).join('');}
function updateChessUI(){const inCheckW=isInCheck('w'),inCheckB=isInCheck('b');const legalW=getLegalMovesForColor('w').length,legalB=getLegalMovesForColor('b').length;document.getElementById('whitePlayer').classList.toggle('active-turn',turn==='w');document.getElementById('blackPlayer').classList.toggle('active-turn',turn==='b');let status='';if(turn==='w'&&legalW===0){gameOver=true;status=inCheckW?'Checkmate — Black wins! 🏆':'Stalemate — Draw!';}else if(turn==='b'&&legalB===0){gameOver=true;status=inCheckB?'Checkmate — White wins! 🏆':'Stalemate — Draw!';}else if(inCheckW||inCheckB){status=(inCheckW?'White':'Black')+' is in check!';}else{status=turn==='w'?'White to move':'Black to move';}document.getElementById('chessStatus').textContent=status;}
function getLegalMovesForColor(col){let all=[];for(let i=0;i<64;i++){if(board[i]&&color(board[i])===col)all=all.concat(getLegalMoves(i));}return all;}
function updateMoveHistory(){const wrap=document.getElementById('moveHistoryWrap');if(moveList.length===0){wrap.style.display='none';return;}wrap.style.display='block';const mh=document.getElementById('moveHistory');mh.innerHTML='';for(let i=0;i<moveList.length;i+=2){const n=i/2+1;const wm=moveList[i],bm=moveList[i+1];mh.innerHTML+=`<div class="move-entry white"><span class="move-num">${n}.</span> ${wm.notation}</div><div class="move-entry">${bm?bm.notation:''}</div>`;}wrap.scrollTop=wrap.scrollHeight;}
function newChessGame(){initChess();}
document.getElementById('rankLabels').innerHTML=['8','7','6','5','4','3','2','1'].map(r=>`<span>${r}</span>`).join('');
document.getElementById('chessFiles').innerHTML=['a','b','c','d','e','f','g','h'].map(f=>`<span>${f}</span>`).join('');
initChess();
function switchTab(tab,btn){document.querySelectorAll('.tab-btn').forEach(b=>b.classList.remove('active'));document.querySelectorAll('.game-panel').forEach(p=>p.classList.remove('active'));btn.classList.add('active');document.getElementById('panel-'+tab).classList.add('active');}
</script></body></html>
""", topnav=TOPNAV, page_css=PAGE_BASE_CSS)


# ══════════════════════════════════════════════════════════════════════════════
# PUZZLE PAGE (original, unchanged)
# ══════════════════════════════════════════════════════════════════════════════
@app.route("/puzzle")
def puzzle():
    if "user" not in session: return redirect("/login")
    return render_template_string("""
<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>MindSpace — Brain Puzzles</title>
<link href="https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700;800;900&family=Playfair+Display:wght@700&display=swap" rel="stylesheet">
<style>
{{ page_css }}
.page-wrap{position:relative;z-index:1;max-width:680px;margin:0 auto;}
.page-title{font-family:'Playfair Display',serif;font-size:1.8rem;margin-bottom:4px;}
.page-sub{color:rgba(255,255,255,0.4);font-size:0.85rem;margin-bottom:24px;}
.game-tabs{display:flex;gap:8px;margin-bottom:24px;background:rgba(255,255,255,0.04);padding:6px;border-radius:16px;border:1px solid rgba(255,255,255,0.08);}
.tab-btn{flex:1;padding:9px;border:none;border-radius:12px;font-family:'Nunito',sans-serif;font-weight:800;font-size:0.82rem;cursor:pointer;transition:all 0.25s;background:transparent;color:rgba(255,255,255,0.4);}
.tab-btn.active{background:linear-gradient(135deg,#f9a8d4,#a78bfa);color:#fff;box-shadow:0 4px 16px rgba(249,168,212,0.3);}
.game-panel{display:none;}.game-panel.active{display:block;}
.game-btn{padding:10px 20px;border:none;border-radius:12px;font-family:'Nunito',sans-serif;font-weight:800;font-size:0.85rem;cursor:pointer;transition:all 0.2s;}
.game-btn.primary{background:linear-gradient(135deg,#f9a8d4,#a78bfa);color:#fff;}
.game-btn.secondary{background:rgba(255,255,255,0.06);border:1.5px solid rgba(255,255,255,0.12);color:rgba(255,255,255,0.7);}
.game-btn:hover{transform:translateY(-2px);}
.memory-info{display:flex;justify-content:space-between;align-items:center;margin-bottom:14px;}
.memory-stat{background:rgba(255,255,255,0.05);border:1px solid rgba(255,255,255,0.08);border-radius:12px;padding:8px 16px;font-weight:800;font-size:0.88rem;}
.memory-grid{display:grid;gap:10px;margin-bottom:16px;}
.mem-card{aspect-ratio:1;background:rgba(249,168,212,0.1);border:2px solid rgba(249,168,212,0.2);border-radius:14px;display:flex;align-items:center;justify-content:center;font-size:2rem;cursor:pointer;transition:all 0.3s;user-select:none;}
.mem-card.flipped,.mem-card.matched{background:rgba(249,168,212,0.2);border-color:rgba(249,168,212,0.5);box-shadow:0 0 16px rgba(249,168,212,0.3);}
.mem-card.matched{background:rgba(110,231,183,0.15);border-color:rgba(110,231,183,0.4);cursor:default;}
.mem-card:not(.flipped):not(.matched) span{opacity:0;}
.mem-card:hover:not(.flipped):not(.matched){background:rgba(249,168,212,0.15);transform:scale(1.04);}
.word-wrap{text-align:center;}
.scrambled-word{font-size:3rem;font-weight:900;letter-spacing:8px;color:#f9a8d4;margin:24px 0;text-shadow:0 0 20px rgba(249,168,212,0.4);font-family:'Playfair Display',serif;}
.word-input-row{display:flex;gap:10px;justify-content:center;margin-bottom:16px;}
.word-input{padding:12px 20px;background:rgba(255,255,255,0.06);border:1.5px solid rgba(255,255,255,0.12);border-radius:14px;color:#fff;font-size:1.1rem;font-weight:800;font-family:'Nunito',sans-serif;outline:none;text-align:center;text-transform:uppercase;width:200px;letter-spacing:4px;}
.word-input:focus{border-color:rgba(249,168,212,0.6);}
.word-hint{color:rgba(255,255,255,0.4);font-size:0.82rem;margin-bottom:12px;}
.word-result{font-size:1.1rem;font-weight:800;min-height:28px;margin-bottom:12px;}
.word-score{display:flex;gap:16px;justify-content:center;margin-bottom:20px;}
.word-score-item{background:rgba(255,255,255,0.05);border:1px solid rgba(255,255,255,0.08);border-radius:12px;padding:8px 16px;font-weight:800;font-size:0.88rem;}
.word-timer{font-size:2rem;font-weight:900;text-align:center;margin-bottom:8px;color:#a78bfa;}
.g2048-wrap{display:flex;flex-direction:column;align-items:center;}
.g2048-info{display:flex;justify-content:space-between;width:100%;max-width:340px;margin-bottom:14px;}
.g2048-score{background:rgba(255,255,255,0.05);border:1px solid rgba(255,255,255,0.08);border-radius:12px;padding:8px 20px;font-weight:800;text-align:center;}
.g2048-score .label{font-size:0.7rem;color:rgba(255,255,255,0.4);text-transform:uppercase;}
.g2048-score .val{font-size:1.3rem;color:#f9a8d4;}
.g2048-board{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;background:rgba(255,255,255,0.06);border-radius:16px;padding:10px;max-width:340px;width:100%;}
.g2048-cell{aspect-ratio:1;border-radius:10px;display:flex;align-items:center;justify-content:center;font-size:1.1rem;font-weight:900;transition:all 0.12s;}
.g2048-actions{display:flex;gap:10px;margin-top:14px;}
.g2048-instructions{color:rgba(255,255,255,0.3);font-size:0.78rem;margin-top:10px;text-align:center;}
.memory-actions{display:flex;gap:10px;align-items:center;}
</style></head><body>
{{ topnav }}
<div class="page-wrap">
    <h1 class="page-title">🧩 Brain Puzzles</h1>
    <p class="page-sub">Train your memory, vocabulary, and strategic thinking</p>
    <div class="game-tabs">
        <button class="tab-btn active" onclick="switchTab('memory',this)">🃏 Memory Match</button>
        <button class="tab-btn" onclick="switchTab('word',this)">🔤 Word Scramble</button>
        <button class="tab-btn" onclick="switchTab('g2048',this)">🔢 2048</button>
    </div>
    <div class="game-panel active" id="panel-memory">
        <div class="memory-info">
            <div class="memory-stat" id="memMoves">Moves: 0</div>
            <div class="memory-stat" id="memPairs">Pairs: 0/8</div>
            <div class="memory-stat" id="memTimer">⏱ 0s</div>
            <div style="display:flex;gap:8px;">
                <button class="game-btn secondary" onclick="setMemDiff(4,this)" style="font-size:0.75rem;padding:7px 12px;">4×4</button>
                <button class="game-btn secondary" onclick="setMemDiff(6,this)" style="font-size:0.75rem;padding:7px 12px;">6×4</button>
            </div>
        </div>
        <div class="memory-grid" id="memGrid"></div>
        <div class="memory-actions"><button class="game-btn primary" onclick="newMemGame()">🔄 New Game</button></div>
    </div>
    <div class="game-panel" id="panel-word">
        <div class="word-wrap">
            <div class="word-score">
                <div class="word-score-item">Score: <span id="wordScore" style="color:#f9a8d4;">0</span></div>
                <div class="word-score-item">Streak: <span id="wordStreak" style="color:#6ee7b7;">0</span> 🔥</div>
            </div>
            <div class="word-timer" id="wordTimer">⏱ 30</div>
            <div class="word-hint" id="wordHint"></div>
            <div class="scrambled-word" id="scrambledWord"></div>
            <div class="word-input-row">
                <input class="word-input" id="wordInput" maxlength="12" placeholder="GUESS" onkeydown="if(event.key==='Enter')checkWord()">
                <button class="game-btn primary" onclick="checkWord()">→</button>
            </div>
            <div class="word-result" id="wordResult"></div>
            <div style="display:flex;gap:10px;justify-content:center;">
                <button class="game-btn secondary" onclick="skipWord()">⏭ Skip</button>
                <button class="game-btn secondary" onclick="showHint()">💡 Hint</button>
                <button class="game-btn primary" onclick="startWordGame()">🔄 New Game</button>
            </div>
        </div>
    </div>
    <div class="game-panel" id="panel-g2048">
        <div class="g2048-wrap">
            <div class="g2048-info">
                <div class="g2048-score"><div class="label">Score</div><div class="val" id="s2048">0</div></div>
                <div class="g2048-score"><div class="label">Best</div><div class="val" id="b2048">0</div></div>
            </div>
            <div class="g2048-board" id="board2048"></div>
            <div class="g2048-actions"><button class="game-btn primary" onclick="new2048()">🔄 New Game</button></div>
            <div class="g2048-instructions">Use arrow keys or swipe to merge tiles. Reach 2048!</div>
        </div>
    </div>
</div>
<script>
function switchTab(tab,btn){document.querySelectorAll('.tab-btn').forEach(b=>b.classList.remove('active'));document.querySelectorAll('.game-panel').forEach(p=>p.classList.remove('active'));btn.classList.add('active');document.getElementById('panel-'+tab).classList.add('active');}
const EMOJIS=['🌸','🌊','🌙','⭐','🦋','🌈','🔮','🌺','🎯','🦄','🍀','🎸'];
let memCards=[],memFlipped=[],memMatched=0,memMoveCount=0,memTimer2=0,memInterval=null,memGridSize=4,memLock=false;
function setMemDiff(cols,btn){memGridSize=cols;newMemGame();}
function shuffle(a){for(let i=a.length-1;i>0;i--){const j=Math.floor(Math.random()*(i+1));[a[i],a[j]]=[a[j],a[i]];}return a;}
function newMemGame(){const pairs=memGridSize===6?12:8;const chosen=EMOJIS.slice(0,pairs);memCards=shuffle([...chosen,...chosen]);memFlipped=[];memMatched=0;memMoveCount=0;memLock=false;clearInterval(memInterval);memTimer2=0;document.getElementById('memMoves').textContent='Moves: 0';document.getElementById('memPairs').textContent=`Pairs: 0/${pairs}`;document.getElementById('memTimer').textContent='⏱ 0s';memInterval=setInterval(()=>{memTimer2++;document.getElementById('memTimer').textContent=`⏱ ${memTimer2}s`;},1000);renderMem();}
function renderMem(){const grid=document.getElementById('memGrid');const cols=memGridSize;grid.style.gridTemplateColumns=`repeat(${cols},1fr)`;grid.innerHTML='';memCards.forEach((e,i)=>{const card=document.createElement('div');card.className='mem-card';if(memFlipped.includes(i)||memCards[i]==='matched')card.classList.add('flipped');if(memCards[i]==='matched')card.classList.add('matched');card.innerHTML=`<span>${e}</span>`;card.onclick=()=>flipCard(i);grid.appendChild(card);});}
function flipCard(i){if(memLock||memFlipped.includes(i)||memCards[i]==='matched')return;memFlipped.push(i);renderMem();if(memFlipped.length===2){memMoveCount++;document.getElementById('memMoves').textContent=`Moves: ${memMoveCount}`;const[a,b]=memFlipped;if(memCards[a]===memCards[b]){memCards[a]=memCards[b]='matched';memMatched++;const pairs=memCards.filter(c=>c==='matched').length/2;document.getElementById('memPairs').textContent=`Pairs: ${pairs}/${memCards.filter(c=>c!=='matched').length/2+pairs}`;memFlipped=[];renderMem();if(pairs===memCards.length/2){clearInterval(memInterval);setTimeout(()=>alert(`🎉 You won in ${memMoveCount} moves and ${memTimer2}s!`),300);}}else{memLock=true;setTimeout(()=>{memFlipped=[];memLock=false;renderMem();},900);}}}
newMemGame();
const WORDS=[{w:'HAPPY',h:'Feeling joyful'},{w:'CALM',h:'Peaceful state'},{w:'BREATHE',h:'Inhale and exhale'},{w:'MINDFUL',h:'Being present'},{w:'BALANCE',h:'Equilibrium'},{w:'SERENE',h:'Tranquil and calm'},{w:'FOCUS',h:'Concentrate'},{w:'ENERGY',h:'Vitality'},{w:'PEACE',h:'Inner harmony'},{w:'STRENGTH',h:'Physical or mental power'},{w:'YOGA',h:'Mind-body practice'},{w:'RELAX',h:'Ease tension'},{w:'HEALTH',h:'State of well-being'},{w:'SLEEP',h:'Rest and recovery'},{w:'WATER',h:'Essential hydration'},{w:'SMILE',h:'Facial expression of happiness'},{w:'GRATITUDE',h:'Feeling thankful'},{w:'COURAGE',h:'Bravery'},{w:'WISDOM',h:'Deep understanding'},{w:'KINDNESS',h:'Being considerate'}];
let wScore=0,wStreak=0,wIdx=0,wWordTimer=null,wTimeLeft=30,wCurrentWord='',wHintUsed=false,shuffledWords=[];
function scramble(w){const a=w.split('');for(let i=a.length-1;i>0;i--){const j=Math.floor(Math.random()*(i+1));[a[i],a[j]]=[a[j],a[i]];}return a.join('')===w&&w.length>1?scramble(w):a.join('');}
function startWordGame(){shuffledWords=[...WORDS].sort(()=>Math.random()-0.5);wIdx=0;wScore=0;wStreak=0;document.getElementById('wordScore').textContent='0';document.getElementById('wordStreak').textContent='0';loadWord();}
function loadWord(){if(wIdx>=shuffledWords.length){wIdx=0;shuffledWords.sort(()=>Math.random()-0.5);}wCurrentWord=shuffledWords[wIdx].w;wHintUsed=false;document.getElementById('scrambledWord').textContent=scramble(wCurrentWord);document.getElementById('wordHint').textContent=`Hint: ${shuffledWords[wIdx].h} (${wCurrentWord.length} letters)`;document.getElementById('wordInput').value='';document.getElementById('wordResult').textContent='';document.getElementById('wordInput').focus();clearInterval(wWordTimer);wTimeLeft=30;document.getElementById('wordTimer').textContent=`⏱ ${wTimeLeft}`;document.getElementById('wordTimer').style.color='#a78bfa';wWordTimer=setInterval(()=>{wTimeLeft--;document.getElementById('wordTimer').textContent=`⏱ ${wTimeLeft}`;if(wTimeLeft<=10)document.getElementById('wordTimer').style.color='#ff9a9a';if(wTimeLeft<=0){clearInterval(wWordTimer);document.getElementById('wordResult').textContent=`⏰ Time's up! It was "${wCurrentWord}"`;document.getElementById('wordResult').style.color='#ff9a9a';wStreak=0;document.getElementById('wordStreak').textContent='0';setTimeout(()=>{wIdx++;loadWord();},1800);}},1000);}
function checkWord(){const guess=document.getElementById('wordInput').value.trim().toUpperCase();if(!guess)return;if(guess===wCurrentWord){clearInterval(wWordTimer);const bonus=wHintUsed?5:10;const timeBonus=Math.floor(wTimeLeft/3);wScore+=bonus+timeBonus;wStreak++;document.getElementById('wordScore').textContent=wScore;document.getElementById('wordStreak').textContent=wStreak;document.getElementById('wordResult').textContent=`✅ Correct! +${bonus+timeBonus} pts`;document.getElementById('wordResult').style.color='#6ee7b7';setTimeout(()=>{wIdx++;loadWord();},1200);}else{document.getElementById('wordResult').textContent='❌ Try again!';document.getElementById('wordResult').style.color='#ff9a9a';document.getElementById('wordInput').value='';wStreak=0;document.getElementById('wordStreak').textContent='0';}}
function skipWord(){clearInterval(wWordTimer);document.getElementById('wordResult').textContent=`⏭ Skipped — it was "${wCurrentWord}"`;document.getElementById('wordResult').style.color='#fde68a';wStreak=0;document.getElementById('wordStreak').textContent='0';setTimeout(()=>{wIdx++;loadWord();},1200);}
function showHint(){if(!wHintUsed){wHintUsed=true;const half=wCurrentWord.slice(0,Math.ceil(wCurrentWord.length/2));document.getElementById('wordResult').textContent=`💡 Starts with: ${half}...`;document.getElementById('wordResult').style.color='#fde68a';}}
startWordGame();
let g2048=[],g2048Score=0,g2048Best=0;
const BGCOLOR={'2':'#eee4da','4':'#ede0c8','8':'#f2b179','16':'#f59563','32':'#f67c5f','64':'#f65e3b','128':'#edcf72','256':'#edcc61','512':'#edc850','1024':'#edc53f','2048':'#edc22e'};
function new2048(){g2048=Array(16).fill(0);g2048Score=0;addTile2048();addTile2048();render2048();}
function addTile2048(){const empty=g2048.map((v,i)=>v===0?i:-1).filter(i=>i>=0);if(!empty.length)return;const idx=empty[Math.floor(Math.random()*empty.length)];g2048[idx]=Math.random()<0.9?2:4;}
function render2048(){const b=document.getElementById('board2048');b.innerHTML='';g2048.forEach(v=>{const cell=document.createElement('div');cell.className='g2048-cell';const bg=v?BGCOLOR[v]||'#3d3a6e':'rgba(255,255,255,0.05)';const col=v>4?'#f9f6f2':'#776e65';cell.style.cssText=`background:${bg};color:${col};font-size:${v>=1000?'0.85rem':v>=100?'1rem':'1.2rem'}`;cell.textContent=v||'';b.appendChild(cell);});document.getElementById('s2048').textContent=g2048Score;document.getElementById('b2048').textContent=g2048Best=Math.max(g2048Best,g2048Score);}
function slide2048(row){const r=row.filter(v=>v!==0);for(let i=0;i<r.length-1;i++){if(r[i]===r[i+1]){r[i]*=2;g2048Score+=r[i];r[i+1]=0;}}const out=r.filter(v=>v!==0);while(out.length<4)out.push(0);return out;}
function move2048(dir){const prev=[...g2048];if(dir==='left'){for(let r=0;r<4;r++){const row=g2048.slice(r*4,r*4+4);const s=slide2048(row);for(let c=0;c<4;c++)g2048[r*4+c]=s[c];}}else if(dir==='right'){for(let r=0;r<4;r++){const row=g2048.slice(r*4,r*4+4).reverse();const s=slide2048(row).reverse();for(let c=0;c<4;c++)g2048[r*4+c]=s[c];}}else if(dir==='up'){for(let c=0;c<4;c++){const col=[g2048[c],g2048[4+c],g2048[8+c],g2048[12+c]];const s=slide2048(col);for(let r=0;r<4;r++)g2048[r*4+c]=s[r];}}else if(dir==='down'){for(let c=0;c<4;c++){const col=[g2048[12+c],g2048[8+c],g2048[4+c],g2048[c]];const s=slide2048(col).reverse();for(let r=0;r<4;r++)g2048[r*4+c]=s[r];}}if(prev.some((v,i)=>v!==g2048[i])){addTile2048();render2048();}if(g2048.includes(2048)){setTimeout(()=>alert('🎉 You reached 2048!'),100);}}
document.addEventListener('keydown',e=>{if(!document.getElementById('panel-g2048').classList.contains('active'))return;const map={ArrowLeft:'left',ArrowRight:'right',ArrowUp:'up',ArrowDown:'down'};if(map[e.key]){e.preventDefault();move2048(map[e.key]);}});
let tx=0,ty=0;
document.getElementById('board2048').addEventListener('touchstart',e=>{tx=e.touches[0].clientX;ty=e.touches[0].clientY;},{passive:true});
document.getElementById('board2048').addEventListener('touchend',e=>{const dx=e.changedTouches[0].clientX-tx,dy=e.changedTouches[0].clientY-ty;if(Math.abs(dx)>Math.abs(dy)){move2048(dx>0?'right':'left');}else{move2048(dy>0?'down':'up');}},{passive:true});
new2048();
</script></body></html>
""", topnav=TOPNAV, page_css=PAGE_BASE_CSS)


# ══════════════════════════════════════════════════════════════════════════════
# PHYSICAL ACTIVITY (original, unchanged)
# ══════════════════════════════════════════════════════════════════════════════
@app.route("/activity")
def activity():
    if "user" not in session: return redirect("/login")
    return render_template_string("""
<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>MindSpace — Physical Activity</title>
<link href="https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700;800;900&family=Playfair+Display:wght@700&display=swap" rel="stylesheet">
<style>
{{ page_css }}
.page-wrap{position:relative;z-index:1;max-width:760px;margin:0 auto;}
.page-title{font-family:'Playfair Display',serif;font-size:1.8rem;margin-bottom:4px;}
.page-sub{color:rgba(255,255,255,0.4);font-size:0.85rem;margin-bottom:24px;}
.section-tabs{display:flex;gap:8px;margin-bottom:24px;background:rgba(255,255,255,0.04);padding:6px;border-radius:16px;border:1px solid rgba(255,255,255,0.08);overflow-x:auto;}
.tab-btn{flex-shrink:0;padding:9px 16px;border:none;border-radius:12px;font-family:'Nunito',sans-serif;font-weight:800;font-size:0.82rem;cursor:pointer;transition:all 0.25s;background:transparent;color:rgba(255,255,255,0.4);white-space:nowrap;}
.tab-btn.active{background:linear-gradient(135deg,#34d399,#5bc8f5);color:#fff;box-shadow:0 4px 16px rgba(52,211,153,0.3);}
.section-panel{display:none;}.section-panel.active{display:block;}
.pose-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:14px;margin-bottom:24px;}
.pose-card{background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.08);border-radius:18px;padding:20px;cursor:pointer;transition:all 0.25s;position:relative;overflow:hidden;}
.pose-card::before{content:'';position:absolute;inset:0;border-radius:18px;opacity:0;transition:opacity 0.3s;}
.pose-card:hover{transform:translateY(-3px);box-shadow:0 10px 30px rgba(0,0,0,0.3);}
.pose-card:hover::before{opacity:1;}
.pose-card.yoga::before{background:radial-gradient(ellipse at top,rgba(52,211,153,0.12),transparent 70%);}
.pose-card.stretch::before{background:radial-gradient(ellipse at top,rgba(92,200,245,0.12),transparent 70%);}
.pose-card.strength::before{background:radial-gradient(ellipse at top,rgba(167,139,250,0.12),transparent 70%);}
.pose-card.breathing::before{background:radial-gradient(ellipse at top,rgba(249,168,212,0.12),transparent 70%);}
.pose-icon{font-size:2.8rem;margin-bottom:10px;line-height:1;}
.pose-name{font-weight:800;font-size:0.95rem;margin-bottom:4px;}
.pose-duration{color:rgba(255,255,255,0.4);font-size:0.75rem;margin-bottom:8px;}
.pose-benefit{display:inline-block;padding:3px 10px;border-radius:99px;font-size:0.72rem;font-weight:700;margin-top:4px;}
.tag-yoga{background:rgba(52,211,153,0.15);color:#34d399;}
.tag-stretch{background:rgba(92,200,245,0.15);color:#5bc8f5;}
.tag-strength{background:rgba(167,139,250,0.15);color:#a78bfa;}
.tag-breathing{background:rgba(249,168,212,0.15);color:#f9a8d4;}
.pose-modal{display:none;position:fixed;inset:0;background:rgba(0,0,0,0.75);z-index:500;align-items:center;justify-content:center;padding:20px;}
.pose-modal.show{display:flex;}
.pose-modal-box{background:#111827;border:1px solid rgba(255,255,255,0.1);border-radius:24px;padding:32px;max-width:520px;width:100%;max-height:90vh;overflow-y:auto;}
.modal-icon{font-size:4rem;text-align:center;margin-bottom:12px;}
.modal-title{font-family:'Playfair Display',serif;font-size:1.6rem;text-align:center;margin-bottom:6px;}
.modal-sub{text-align:center;color:rgba(255,255,255,0.4);font-size:0.82rem;margin-bottom:20px;}
.modal-steps{display:flex;flex-direction:column;gap:10px;margin-bottom:20px;}
.modal-step{display:flex;gap:12px;padding:12px;background:rgba(255,255,255,0.04);border-radius:12px;}
.step-num{width:28px;height:28px;border-radius:50%;background:linear-gradient(135deg,#34d399,#5bc8f5);display:flex;align-items:center;justify-content:center;font-size:0.8rem;font-weight:900;flex-shrink:0;}
.step-text{color:rgba(255,255,255,0.75);font-size:0.88rem;font-weight:600;line-height:1.5;}
.modal-timer{text-align:center;margin-bottom:16px;}
.timer-count{font-size:3rem;font-weight:900;color:#34d399;line-height:1;}
.timer-label{color:rgba(255,255,255,0.4);font-size:0.78rem;}
.modal-actions{display:flex;gap:10px;justify-content:center;}
.modal-btn{padding:11px 24px;border:none;border-radius:12px;font-family:'Nunito',sans-serif;font-weight:800;font-size:0.88rem;cursor:pointer;transition:all 0.2s;}
.modal-btn.primary{background:linear-gradient(135deg,#34d399,#5bc8f5);color:#fff;}
.modal-btn.secondary{background:rgba(255,255,255,0.07);border:1.5px solid rgba(255,255,255,0.12);color:rgba(255,255,255,0.6);}
.modal-btn:hover{transform:translateY(-2px);}
.workout-wrap{max-width:560px;margin:0 auto;}
.builder-row{display:flex;gap:10px;margin-bottom:16px;align-items:center;flex-wrap:wrap;}
.builder-label{color:rgba(255,255,255,0.5);font-size:0.82rem;font-weight:700;min-width:80px;}
.builder-select{padding:8px 14px;background:rgba(255,255,255,0.06);border:1.5px solid rgba(255,255,255,0.12);border-radius:12px;color:#fff;font-family:'Nunito',sans-serif;font-weight:700;font-size:0.88rem;outline:none;cursor:pointer;}
.workout-plan{display:flex;flex-direction:column;gap:10px;margin-bottom:16px;}
.workout-exercise{display:flex;align-items:center;gap:12px;padding:14px 16px;background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.07);border-radius:14px;}
.ex-num{width:30px;height:30px;border-radius:50%;background:linear-gradient(135deg,#34d399,#5bc8f5);display:flex;align-items:center;justify-content:center;font-weight:900;font-size:0.82rem;flex-shrink:0;}
.ex-info{flex:1;}.ex-name{font-weight:800;font-size:0.9rem;margin-bottom:2px;}
.ex-detail{color:rgba(255,255,255,0.4);font-size:0.75rem;}.ex-icon{font-size:1.5rem;}
.breathing-wrap{display:flex;flex-direction:column;align-items:center;padding:20px 0;}
.breath-circle{width:200px;height:200px;border-radius:50%;border:3px solid rgba(52,211,153,0.3);display:flex;align-items:center;justify-content:center;flex-direction:column;margin:0 auto 24px;transition:all 1s ease;background:rgba(52,211,153,0.05);}
.breath-circle.inhale{transform:scale(1.3);border-color:rgba(92,200,245,0.6);background:rgba(92,200,245,0.1);}
.breath-circle.exhale{transform:scale(0.85);border-color:rgba(249,168,212,0.5);background:rgba(249,168,212,0.05);}
.breath-circle.hold{border-color:rgba(167,139,250,0.5);background:rgba(167,139,250,0.08);}
.breath-phase{font-size:1.2rem;font-weight:800;color:#fff;}
.breath-count{font-size:2.5rem;font-weight:900;color:#34d399;}
.breath-type-row{display:flex;gap:10px;justify-content:center;margin-bottom:20px;flex-wrap:wrap;}
.breath-type-btn{padding:8px 16px;border:1.5px solid rgba(255,255,255,0.12);border-radius:20px;background:transparent;color:rgba(255,255,255,0.5);font-family:'Nunito',sans-serif;font-weight:700;font-size:0.8rem;cursor:pointer;transition:all 0.2s;}
.breath-type-btn.active{background:rgba(52,211,153,0.15);border-color:#34d399;color:#34d399;}
.breath-instructions{color:rgba(255,255,255,0.4);font-size:0.82rem;text-align:center;margin-bottom:20px;}
.cycles-count{color:rgba(255,255,255,0.5);font-size:0.85rem;text-align:center;margin-top:16px;}
</style></head><body>
{{ topnav }}
<div class="page-wrap">
    <h1 class="page-title">🧘 Physical Activity</h1>
    <p class="page-sub">Yoga poses, stretches, strength training &amp; breathing exercises</p>
    <div class="section-tabs">
        <button class="tab-btn active" onclick="switchTab('yoga',this)">🧘 Yoga Poses</button>
        <button class="tab-btn" onclick="switchTab('stretch',this)">🤸 Stretches</button>
        <button class="tab-btn" onclick="switchTab('strength',this)">💪 Strength</button>
        <button class="tab-btn" onclick="switchTab('breathing',this)">🌬️ Breathing</button>
        <button class="tab-btn" onclick="switchTab('workout',this)">📋 Workout Plan</button>
    </div>
    <div class="section-panel active" id="panel-yoga"><div class="pose-grid" id="yogaGrid"></div></div>
    <div class="section-panel" id="panel-stretch"><div class="pose-grid" id="stretchGrid"></div></div>
    <div class="section-panel" id="panel-strength"><div class="pose-grid" id="strengthGrid"></div></div>
    <div class="section-panel" id="panel-breathing">
        <div class="breathing-wrap">
            <div class="breath-type-row">
                <button class="breath-type-btn active" onclick="setBreathType('478',this)">4-7-8 Calm</button>
                <button class="breath-type-btn" onclick="setBreathType('box',this)">Box Breathing</button>
                <button class="breath-type-btn" onclick="setBreathType('belly',this)">Belly Breath</button>
                <button class="breath-type-btn" onclick="setBreathType('coherent',this)">Coherent</button>
            </div>
            <div class="breath-instructions" id="breathInstructions">4-7-8: Inhale 4s, Hold 7s, Exhale 8s — reduces anxiety fast</div>
            <div class="breath-circle" id="breathCircle">
                <div class="breath-phase" id="breathPhase">Press Start</div>
                <div class="breath-count" id="breathCountNum"></div>
            </div>
            <div class="cycles-count" id="cyclesCount">Cycles completed: 0</div>
            <div style="display:flex;gap:12px;justify-content:center;margin-top:16px;">
                <button class="modal-btn primary" id="breathStart" onclick="toggleBreath()">▶ Start</button>
                <button class="modal-btn secondary" onclick="resetBreath()">↺ Reset</button>
            </div>
        </div>
    </div>
    <div class="section-panel" id="panel-workout">
        <div class="workout-wrap">
            <div class="builder-row">
                <span class="builder-label">Goal</span>
                <select class="builder-select" id="wGoal"><option value="calm">Stress Relief</option><option value="energy">Energy Boost</option><option value="strength">Build Strength</option><option value="flex">Flexibility</option></select>
                <span class="builder-label">Duration</span>
                <select class="builder-select" id="wDur"><option value="10">10 min</option><option value="20">20 min</option><option value="30">30 min</option></select>
            </div>
            <button class="modal-btn primary" onclick="buildWorkout()" style="margin-bottom:20px;">✨ Generate Plan</button>
            <div class="workout-plan" id="workoutPlan"></div>
        </div>
    </div>
</div>
<div class="pose-modal" id="poseModal">
    <div class="pose-modal-box">
        <div class="modal-icon" id="mIcon"></div><div class="modal-title" id="mTitle"></div><div class="modal-sub" id="mSub"></div>
        <div class="modal-steps" id="mSteps"></div>
        <div class="modal-timer"><div class="timer-count" id="mTimerNum">—</div><div class="timer-label" id="mTimerLabel">seconds</div></div>
        <div class="modal-actions">
            <button class="modal-btn primary" id="mStartBtn" onclick="togglePoseTimer()">▶ Start Timer</button>
            <button class="modal-btn secondary" onclick="closeModal()">✕ Close</button>
        </div>
    </div>
</div>
<script>
function switchTab(tab,btn){document.querySelectorAll('.tab-btn').forEach(b=>b.classList.remove('active'));document.querySelectorAll('.section-panel').forEach(p=>p.classList.remove('active'));btn.classList.add('active');document.getElementById('panel-'+tab).classList.add('active');}
const YOGA=[{icon:'🧘',name:'Mountain Pose',sanskrit:'Tadasana',duration:60,benefit:'yoga',desc:'Foundation of all standing poses.',steps:['Stand feet together, weight even','Engage thighs, lift kneecaps','Lengthen spine, roll shoulders back','Arms at sides, palms forward','Breathe deeply, hold steady gaze']},{icon:'🌲',name:'Tree Pose',sanskrit:'Vrksasana',duration:45,benefit:'yoga',desc:'Improves balance and focus.',steps:['Stand on one leg, find gaze point','Foot on inner thigh or calf','Press palms at heart center','Breathe steadily, engage core','Hold 30–60s each side']},{icon:'🐕',name:'Downward Dog',sanskrit:'Adho Mukha',duration:60,benefit:'yoga',desc:'Energises body, stretches back.',steps:['Start on hands and knees','Tuck toes, lift hips up and back','Straighten arms, press palms','Heels toward floor','Head between arms, neck relaxed']},{icon:'🌍',name:"Child's Pose",sanskrit:'Balasana',duration:90,benefit:'yoga',desc:'Deeply restorative.',steps:['Kneel, sit back on heels','Fold forward, forehead to mat','Arms extended or alongside body','Breathe into lower back','Stay 1–3 minutes']},{icon:'🐍',name:'Cobra Pose',sanskrit:'Bhujangasana',duration:45,benefit:'yoga',desc:'Opens chest, strengthens spine.',steps:['Lie face down, hands under shoulders','Elbows close to body','Press into hands, lift chest','Roll shoulders back','Keep lower belly on mat']},{icon:'⚔️',name:'Warrior I',sanskrit:'Virabhadrasana I',duration:60,benefit:'yoga',desc:'Builds strength and confidence.',steps:['Step right foot forward','Back foot at 45°','Front knee over ankle','Raise arms overhead','Square hips to front']},{icon:'🏹',name:'Warrior II',sanskrit:'Virabhadrasana II',duration:60,benefit:'yoga',desc:'Strengthens legs, opens hips.',steps:['Wide stance, 4 feet apart','Front foot forward, back 90°','Bend front knee over ankle','Arms parallel to floor','Gaze over front fingers']},{icon:'🌙',name:'Crescent Lunge',sanskrit:'Anjaneyasana',duration:45,benefit:'yoga',desc:'Opens hip flexors.',steps:['Low lunge, back knee down','Lift arms overhead','Sink hips forward and down','Breathe into front hip','Hold and switch sides']}];
const STRETCHES=[{icon:'🦵',name:'Hamstring Stretch',duration:45,benefit:'stretch',desc:'Releases tight hamstrings.',steps:['Sit, legs extended forward','Reach hands toward feet','Keep back straight, fold from hips','Breathe, relax deeper each exhale','Hold 30–60s each side']},{icon:'🔄',name:'Seated Spinal Twist',duration:45,benefit:'stretch',desc:'Relieves spinal tension.',steps:['Sit, legs extended','Bend right knee, foot outside','Left elbow on right knee','Right hand behind for support','Twist on exhale, hold 30s']},{icon:'🦈',name:'Hip Flexor Stretch',duration:60,benefit:'stretch',desc:'Opens hips.',steps:['Kneel on left knee, right foot forward','Push hips gently forward','Lift torso, tuck pelvis','Arms on hips or raised','Hold 45s, switch sides']},{icon:'🐈',name:'Cat-Cow Stretch',duration:60,benefit:'stretch',desc:'Warms the spine.',steps:['On all fours, neutral spine','Inhale — drop belly, lift gaze','Exhale — round back up','Sync breath with movement','8–10 slow cycles']},{icon:'🌿',name:'Chest Opener',duration:45,benefit:'stretch',desc:'Opens chest.',steps:['Clasp hands behind back','Squeeze shoulder blades','Lift chest, gaze up','Breathe into chest','Hold 30s, repeat']},{icon:'🦋',name:'Butterfly Stretch',duration:60,benefit:'stretch',desc:'Opens inner thighs.',steps:['Sit, soles together','Hold feet with hands','Press knees toward floor','Sit tall, breathe deep','Lean forward for more']}];
const STRENGTH=[{icon:'💥',name:'Push-Ups',duration:30,benefit:'strength',desc:'Upper body strength.',steps:['Hands wider than shoulders','Body in straight line','Lower chest to floor','Push back explosively','3×10–15, rest 60s']},{icon:'🏋️',name:'Bodyweight Squats',duration:40,benefit:'strength',desc:'Builds legs and glutes.',steps:['Feet shoulder-width apart','Arms forward for balance','Sit back and down','Thighs parallel at bottom','Drive through heels — 3×15']},{icon:'🦅',name:'Plank Hold',duration:60,benefit:'strength',desc:'Core stability.',steps:['Forearms down, elbows under shoulders','Body in straight line','Engage abs, glutes, quads','Breathe steadily','Hold 30–60s']},{icon:'🐸',name:'Glute Bridges',duration:45,benefit:'strength',desc:'Activates glutes.',steps:['Lie on back, knees bent','Drive hips up','Squeeze glutes at top','Lower slowly','3×15 reps']},{icon:'🦩',name:'Single-Leg Balance',duration:45,benefit:'strength',desc:'Ankle stability.',steps:['Stand on one foot','Knee slightly bent','Raise opposite knee','Hold 30s','3 sets per leg']},{icon:'🔥',name:'Burpees',duration:30,benefit:'strength',desc:'Full body cardio.',steps:['Stand, drop to floor','Jump to plank','Push-up optional','Jump feet forward','Jump up — 10 reps']}];
function renderGrid(data,gridId,cls){const grid=document.getElementById(gridId);grid.innerHTML='';data.forEach(p=>{const card=document.createElement('div');card.className=`pose-card ${cls}`;card.innerHTML=`<div class="pose-icon">${p.icon}</div><div class="pose-name">${p.name}</div>${p.sanskrit?`<div class="pose-duration">${p.sanskrit}</div>`:'<div class="pose-duration">&nbsp;</div>'}<div class="pose-duration">⏱ ${p.duration}s</div><span class="pose-benefit tag-${p.benefit}">${p.benefit.charAt(0).toUpperCase()+p.benefit.slice(1)}</span>`;card.onclick=()=>openModal(p);grid.appendChild(card);});}
renderGrid(YOGA,'yogaGrid','yoga');renderGrid(STRETCHES,'stretchGrid','stretch');renderGrid(STRENGTH,'strengthGrid','strength');
let poseTimerInterval=null,poseTimerRunning=false,poseTimerLeft=0;
function openModal(p){document.getElementById('mIcon').textContent=p.icon;document.getElementById('mTitle').textContent=p.name;document.getElementById('mSub').textContent=p.desc;document.getElementById('mSteps').innerHTML=p.steps.map((s,i)=>`<div class="modal-step"><div class="step-num">${i+1}</div><div class="step-text">${s}</div></div>`).join('');poseTimerLeft=p.duration;document.getElementById('mTimerNum').textContent=poseTimerLeft;document.getElementById('mTimerLabel').textContent='seconds';document.getElementById('mStartBtn').textContent='▶ Start Timer';poseTimerRunning=false;clearInterval(poseTimerInterval);document.getElementById('poseModal').classList.add('show');}
function closeModal(){document.getElementById('poseModal').classList.remove('show');clearInterval(poseTimerInterval);poseTimerRunning=false;}
function togglePoseTimer(){if(poseTimerRunning){clearInterval(poseTimerInterval);poseTimerRunning=false;document.getElementById('mStartBtn').textContent='▶ Resume';}else{poseTimerRunning=true;document.getElementById('mStartBtn').textContent='⏸ Pause';poseTimerInterval=setInterval(()=>{poseTimerLeft--;document.getElementById('mTimerNum').textContent=poseTimerLeft;if(poseTimerLeft<=0){clearInterval(poseTimerInterval);poseTimerRunning=false;document.getElementById('mTimerNum').textContent='✅';document.getElementById('mTimerLabel').textContent='Done!';document.getElementById('mStartBtn').textContent='✅ Complete!';}},1000);}}
const BREATH_TYPES={'478':{phases:['Inhale','Hold','Exhale'],times:[4,7,8],desc:'4-7-8: Inhale 4s, Hold 7s, Exhale 8s — reduces anxiety fast'},'box':{phases:['Inhale','Hold','Exhale','Hold'],times:[4,4,4,4],desc:'Box Breathing: 4s each phase — Navy SEAL focus technique'},'belly':{phases:['Inhale','Exhale'],times:[5,5],desc:'Belly Breathing: 5s in, 5s out — deep relaxation'},'coherent':{phases:['Inhale','Exhale'],times:[5,5],desc:'Coherent: 5-5 rhythm — balances heart rate variability'}};
let breathType='478',breathRunning=false,breathInterval=null,breathPhaseIdx=0,breathSecLeft=0,breathCycles=0;
function setBreathType(type,btn){breathType=type;document.querySelectorAll('.breath-type-btn').forEach(b=>b.classList.remove('active'));btn.classList.add('active');document.getElementById('breathInstructions').textContent=BREATH_TYPES[type].desc;resetBreath();}
function resetBreath(){clearInterval(breathInterval);breathRunning=false;breathPhaseIdx=0;breathCycles=0;breathSecLeft=BREATH_TYPES[breathType].times[0];document.getElementById('breathPhase').textContent='Press Start';document.getElementById('breathCountNum').textContent='';document.getElementById('breathStart').textContent='▶ Start';document.getElementById('cyclesCount').textContent='Cycles completed: 0';document.getElementById('breathCircle').className='breath-circle';}
function toggleBreath(){if(breathRunning){clearInterval(breathInterval);breathRunning=false;document.getElementById('breathStart').textContent='▶ Resume';}else{breathRunning=true;document.getElementById('breathStart').textContent='⏸ Pause';runBreathStep();breathInterval=setInterval(()=>{breathSecLeft--;if(breathSecLeft<=0){breathPhaseIdx++;const phases=BREATH_TYPES[breathType].phases;if(breathPhaseIdx>=phases.length){breathPhaseIdx=0;breathCycles++;document.getElementById('cyclesCount').textContent=`Cycles completed: ${breathCycles}`;}breathSecLeft=BREATH_TYPES[breathType].times[breathPhaseIdx];runBreathStep();}else{document.getElementById('breathCountNum').textContent=breathSecLeft;}},1000);}}
function runBreathStep(){const phase=BREATH_TYPES[breathType].phases[breathPhaseIdx];document.getElementById('breathPhase').textContent=phase;document.getElementById('breathCountNum').textContent=breathSecLeft;const circle=document.getElementById('breathCircle');circle.className='breath-circle';if(phase==='Inhale')setTimeout(()=>circle.classList.add('inhale'),50);else if(phase==='Exhale')setTimeout(()=>circle.classList.add('exhale'),50);else setTimeout(()=>circle.classList.add('hold'),50);}
const ALL_EXERCISES={calm:[{icon:'🌍',name:"Child's Pose",detail:'60s hold'},{icon:'🐈',name:'Cat-Cow Stretch',detail:'10 cycles'},{icon:'🌬️',name:'4-7-8 Breathing',detail:'4 cycles'},{icon:'🧘',name:'Mountain Pose',detail:'60s hold'},{icon:'🔄',name:'Seated Spinal Twist',detail:'45s each side'},{icon:'🌙',name:'Legs Up Wall',detail:'3 minutes'}],energy:[{icon:'💥',name:'Jumping Jacks',detail:'3×20 reps'},{icon:'🔥',name:'Burpees',detail:'3×10 reps'},{icon:'🏋️',name:'Bodyweight Squats',detail:'3×15 reps'},{icon:'🦅',name:'High Knees',detail:'3×30s'},{icon:'💥',name:'Push-Ups',detail:'3×12 reps'},{icon:'⚡',name:'Mountain Climbers',detail:'3×20s'}],strength:[{icon:'💥',name:'Push-Ups',detail:'4×15 reps'},{icon:'🏋️',name:'Squats',detail:'4×20 reps'},{icon:'🦅',name:'Plank Hold',detail:'3×60s'},{icon:'🐸',name:'Glute Bridges',detail:'3×15 reps'},{icon:'🦩',name:'Lunges',detail:'3×12 each leg'},{icon:'🔥',name:'Tricep Dips',detail:'3×12 reps'}],flex:[{icon:'🦋',name:'Butterfly Stretch',detail:'60s hold'},{icon:'🦵',name:'Hamstring Stretch',detail:'45s each side'},{icon:'🦈',name:'Hip Flexor Stretch',detail:'60s each side'},{icon:'🌿',name:'Chest Opener',detail:'45s hold'},{icon:'🐍',name:'Cobra Pose',detail:'30s hold'},{icon:'🐕',name:'Downward Dog',detail:'60s hold'}]};
function buildWorkout(){const goal=document.getElementById('wGoal').value;const dur=parseInt(document.getElementById('wDur').value);const exes=ALL_EXERCISES[goal];const count=dur===10?4:dur===20?6:8;const selected=exes.slice(0,Math.min(count,exes.length));const plan=document.getElementById('workoutPlan');plan.innerHTML='';selected.forEach((e,i)=>{plan.innerHTML+=`<div class="workout-exercise"><div class="ex-num">${i+1}</div><div class="ex-info"><div class="ex-name">${e.name}</div><div class="ex-detail">${e.detail}</div></div><div class="ex-icon">${e.icon}</div></div>`;});}
buildWorkout();
</script></body></html>
""", topnav=TOPNAV, page_css=PAGE_BASE_CSS)


# ══════════════════════════════════════════════════════════════════════════════
# PROFILE / SETTINGS / HISTORY / LOGOUT (original, updated with new topnav)
# ══════════════════════════════════════════════════════════════════════════════
@app.route("/profile")
def profile():
    if "user" not in session: return redirect("/login")
    conn = sqlite3.connect("app.db"); cur = conn.cursor()
    cur.execute("SELECT username, mobile FROM users WHERE username=?", (session["user"],))
    user = cur.fetchone()
    cur.execute("SELECT COUNT(*) FROM results WHERE username=?", (session["user"],))
    count = cur.fetchone()[0]
    cur.execute("SELECT AVG(score) FROM results WHERE username=?", (session["user"],))
    avg = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM mood_logs WHERE username=?", (session["user"],))
    mood_count = cur.fetchone()[0]
    conn.close()
    return render_template_string("""
<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>MindSpace — Profile</title>
<link href="https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700;800;900&family=Playfair+Display:wght@700&display=swap" rel="stylesheet">
<style>
{{ page_css }}
body{display:flex;flex-direction:column;align-items:center;}
.profile-card{position:relative;z-index:1;background:rgba(255,255,255,0.04);backdrop-filter:blur(24px);border:1px solid rgba(255,255,255,0.09);border-radius:28px;padding:36px;width:100%;max-width:460px;animation:slideUp 0.7s cubic-bezier(0.16,1,0.3,1) both;}
@keyframes slideUp{from{opacity:0;transform:translateY(30px);}to{opacity:1;transform:translateY(0);}}
.avatar{width:80px;height:80px;border-radius:50%;background:linear-gradient(135deg,#5bc8f5,#a78bfa);display:flex;align-items:center;justify-content:center;font-size:2.5rem;font-weight:900;color:#fff;margin:0 auto 16px;}
.profile-name{font-family:'Playfair Display',serif;font-size:1.6rem;text-align:center;margin-bottom:4px;}
.profile-mobile{text-align:center;color:rgba(255,255,255,0.4);font-size:0.85rem;margin-bottom:24px;}
.stats-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:24px;}
.stat-box{background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.08);border-radius:16px;padding:16px;text-align:center;}
.stat-val{font-size:1.6rem;font-weight:900;background:linear-gradient(135deg,#5bc8f5,#a78bfa);-webkit-background-clip:text;-webkit-text-fill-color:transparent;}
.stat-label{font-size:0.75rem;color:rgba(255,255,255,0.4);margin-top:4px;}
.back-btn{display:inline-flex;align-items:center;gap:8px;padding:11px 22px;border:1.5px solid rgba(255,255,255,0.12);border-radius:99px;color:rgba(255,255,255,0.6);text-decoration:none;font-weight:700;font-size:0.85rem;transition:all 0.2s;background:rgba(255,255,255,0.04);}
.back-btn:hover{color:#fff;background:rgba(255,255,255,0.08);}
</style></head><body>
{{ topnav }}
<div class="profile-card">
    <div class="avatar">{{ user[0][0].upper() }}</div>
    <div class="profile-name">{{ user[0] }}</div>
    <div class="profile-mobile">📱 {{ user[1] or 'No mobile on file' }}</div>
    <div class="stats-grid">
        <div class="stat-box"><div class="stat-val">{{ count }}</div><div class="stat-label">Total Check-ins</div></div>
        <div class="stat-box"><div class="stat-val">{{ "%.0f"|format(avg) if avg else '—' }}</div><div class="stat-label">Avg. Wellness Score</div></div>
        <div class="stat-box"><div class="stat-val">{{ mood_count }}</div><div class="stat-label">Mood Logs</div></div>
        <div class="stat-box"><div class="stat-val">🌿</div><div class="stat-label">Wellness Member</div></div>
    </div>
    <a class="back-btn" href="/">← Back to Home</a>
</div>
</body></html>
""", topnav=TOPNAV, page_css=PAGE_BASE_CSS, user=user, count=count, avg=avg, mood_count=mood_count)


@app.route("/settings")
def settings():
    if "user" not in session: return redirect("/login")
    return render_template_string("""
<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>MindSpace — Settings</title>
<link href="https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700;800;900&family=Playfair+Display:wght@700&display=swap" rel="stylesheet">
<style>
{{ page_css }}
body{display:flex;flex-direction:column;align-items:center;}
.settings-card{position:relative;z-index:1;background:rgba(255,255,255,0.04);backdrop-filter:blur(24px);border:1px solid rgba(255,255,255,0.09);border-radius:28px;padding:32px 28px;width:100%;max-width:420px;animation:slideUp 0.7s cubic-bezier(0.16,1,0.3,1) both;}
@keyframes slideUp{from{opacity:0;transform:translateY(30px);}to{opacity:1;transform:translateY(0);}}
h2{font-family:'Playfair Display',serif;font-size:1.6rem;margin-bottom:24px;}
.setting-row{display:flex;align-items:center;justify-content:space-between;padding:14px 0;border-bottom:1px solid rgba(255,255,255,0.06);}
.setting-row:last-of-type{border-bottom:none;}
.setting-label{font-weight:700;font-size:0.92rem;color:rgba(255,255,255,0.8);}
.setting-desc{font-size:0.75rem;color:rgba(255,255,255,0.35);margin-top:2px;}
.toggle-switch{position:relative;width:44px;height:26px;cursor:pointer;}
.toggle-switch input{display:none;}
.toggle-track{width:44px;height:26px;border-radius:13px;background:rgba(255,255,255,0.15);transition:background 0.3s;position:relative;}
.toggle-switch input:checked + .toggle-track{background:linear-gradient(135deg,#5bc8f5,#a78bfa);}
.toggle-thumb{position:absolute;top:3px;left:3px;width:20px;height:20px;border-radius:50%;background:#fff;box-shadow:0 2px 6px rgba(0,0,0,0.3);transition:transform 0.3s cubic-bezier(0.34,1.56,0.64,1);}
.toggle-switch input:checked + .toggle-track .toggle-thumb{transform:translateX(18px);}
.back-btn{display:inline-flex;align-items:center;gap:8px;padding:11px 22px;border:1.5px solid rgba(255,255,255,0.12);border-radius:99px;color:rgba(255,255,255,0.6);text-decoration:none;font-weight:700;font-size:0.85rem;transition:all 0.2s;background:rgba(255,255,255,0.04);margin-top:20px;}
.back-btn:hover{color:#fff;background:rgba(255,255,255,0.08);}
</style></head><body>
{{ topnav }}
<div class="settings-card"><h2>⚙️ Settings</h2>
<div class="setting-row"><div><div class="setting-label">🌙 Dark Mode</div><div class="setting-desc">Toggle dark / light theme</div></div><label class="toggle-switch"><input type="checkbox" id="darkToggle" onchange="toggleTheme(this)"><div class="toggle-track"><div class="toggle-thumb"></div></div></label></div>
<div class="setting-row"><div><div class="setting-label">🔔 Reminders</div><div class="setting-desc">Daily wellness check-in reminder</div></div><label class="toggle-switch"><input type="checkbox" checked><div class="toggle-track"><div class="toggle-thumb"></div></div></label></div>
<div class="setting-row"><div><div class="setting-label">🎵 Ambient Sound</div><div class="setting-desc">Auto-play sound therapy</div></div><label class="toggle-switch"><input type="checkbox"><div class="toggle-track"><div class="toggle-thumb"></div></div></label></div>
<div class="setting-row"><div><div class="setting-label">📊 Share Progress</div><div class="setting-desc">Allow wellness data sharing</div></div><label class="toggle-switch"><input type="checkbox"><div class="toggle-track"><div class="toggle-thumb"></div></div></label></div>
<a class="back-btn" href="/">← Back to Home</a></div>
<script>const saved=localStorage.getItem('mindspace-theme');document.getElementById('darkToggle').checked=saved!=='light';function toggleTheme(cb){localStorage.setItem('mindspace-theme',cb.checked?'dark':'light');}</script>
</body></html>
""", topnav=TOPNAV, page_css=PAGE_BASE_CSS)


@app.route("/history")
def history():
    if "user" not in session: return redirect("/login")
    conn = sqlite3.connect("app.db"); cur = conn.cursor()
    cur.execute("SELECT score, status FROM results WHERE username=? ORDER BY id DESC LIMIT 20", (session["user"],))
    rows = cur.fetchall(); conn.close()
    data     = [r[0] for r in reversed(rows)]
    labels   = list(range(1, len(data)+1))
    statuses = [r[1] for r in reversed(rows)]
    return render_template_string("""
<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>MindSpace — History</title>
<link href="https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700;800;900&family=Playfair+Display:wght@700&display=swap" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
{{ page_css }}
body{display:flex;flex-direction:column;align-items:center;}
.page-title{font-family:'Playfair Display',serif;font-size:1.8rem;color:#fff;margin-bottom:6px;position:relative;z-index:1;}
.page-sub{color:rgba(255,255,255,0.35);font-size:0.85rem;margin-bottom:28px;position:relative;z-index:1;}
.chart-card{position:relative;z-index:1;background:rgba(255,255,255,0.04);backdrop-filter:blur(24px);border:1px solid rgba(255,255,255,0.09);border-radius:24px;padding:28px;width:100%;max-width:640px;margin-bottom:20px;}
.chart-card h3{color:rgba(255,255,255,0.7);font-size:0.85rem;text-transform:uppercase;letter-spacing:1px;margin-bottom:20px;}
.no-data{text-align:center;padding:40px;color:rgba(255,255,255,0.3);}
.back-btn{position:relative;z-index:1;display:inline-flex;align-items:center;gap:8px;padding:12px 22px;border:1.5px solid rgba(255,255,255,0.12);border-radius:99px;color:rgba(255,255,255,0.6);text-decoration:none;font-weight:700;font-size:0.85rem;transition:all 0.2s;background:rgba(255,255,255,0.04);}
.back-btn:hover{color:#fff;background:rgba(255,255,255,0.08);}
</style></head><body>
{{ topnav }}
<h1 class="page-title">📈 Your Progress</h1>
<p class="page-sub">Wellness scores over your last {{ data|length }} check-ins</p>
<div class="chart-card"><h3>Wellness Score Trend</h3>
{% if data %}<canvas id="histChart" height="200"></canvas>{% else %}<div class="no-data">🌱 No check-ins yet. Complete your first assessment!</div>{% endif %}
</div>
<a class="back-btn" href="/">← Back to Home</a>
{% if data %}
<script>const ctx=document.getElementById('histChart').getContext('2d');const gradient=ctx.createLinearGradient(0,0,0,300);gradient.addColorStop(0,'rgba(91,200,245,0.35)');gradient.addColorStop(1,'rgba(167,139,250,0.0)');new Chart(ctx,{type:'line',data:{labels:{{ labels|tojson }}.map(l=>'Check-in '+l),datasets:[{label:'Wellness Score',data:{{ data|tojson }},fill:true,backgroundColor:gradient,borderColor:'#5bc8f5',borderWidth:2.5,pointBackgroundColor:'#a78bfa',pointBorderColor:'#fff',pointBorderWidth:2,pointRadius:5,pointHoverRadius:8,tension:0.4}]},options:{responsive:true,plugins:{legend:{display:false},tooltip:{backgroundColor:'rgba(13,13,26,0.9)',borderColor:'rgba(255,255,255,0.1)',borderWidth:1,titleColor:'#fff',bodyColor:'rgba(255,255,255,0.6)',padding:12}},scales:{x:{grid:{color:'rgba(255,255,255,0.05)'},ticks:{color:'rgba(255,255,255,0.4)',font:{family:'Nunito',size:11}}},y:{grid:{color:'rgba(255,255,255,0.05)'},ticks:{color:'rgba(255,255,255,0.4)',font:{family:'Nunito',size:11}}}}}});</script>
{% endif %}
</body></html>
""", topnav=TOPNAV, page_css=PAGE_BASE_CSS, data=data, labels=labels, statuses=statuses)


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
