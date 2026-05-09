from flask import Flask, request, render_template_string, jsonify, redirect, session
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
import os, json, datetime, random, urllib.request, urllib.error

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "mindspace-super-secret-key-change-in-prod-2024")
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE'] = False

# ── OpenAI API key (set via environment variable OPENAI_API_KEY) ──────────────
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")

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
    cur.execute("""
    CREATE TABLE IF NOT EXISTS mood_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        mood TEXT,
        note TEXT,
        intensity INTEGER DEFAULT 3,
        logged_at DATETIME DEFAULT CURRENT_TIMESTAMP
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

# ─────────────────────────────────────────────
# AUTH ROUTES
# ─────────────────────────────────────────────

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
            existing = cur.fetchone()
            if existing:
                conn.close()
                error = "⚠️ Username already exists. Try another one."
            else:
                hashed = generate_password_hash(p1)
                try:
                    cur.execute("INSERT INTO users (username, mobile, password) VALUES (?,?,?)", (u, m, hashed))
                    conn.commit()
                    conn.close()
                    return redirect("/login?registered=1")
                except Exception:
                    conn.close()
                    error = "⚠️ An error occurred. Please try again."
    return render_template_string("""
<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>MindSpace — Sign Up</title><style>{{ styles }}</style></head>
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
    error = ""
    success = ""
    if request.args.get('registered'):
        success = "🎉 Account created successfully! Please log in."
    if request.method == "POST":
        u = request.form.get("username","").strip()
        p = request.form.get("password","")
        if not u or not p:
            error = "⚠️ Please enter both username and password."
        else:
            conn = sqlite3.connect("app.db")
            cur  = conn.cursor()
            cur.execute("SELECT id, password FROM users WHERE username=?", (u,))
            user = cur.fetchone()
            conn.close()
            if user and check_password_hash(user[1], p):
                session.clear()
                session["user"] = u
                session.modified = True
                return redirect("/")
            else:
                error = "❌ Invalid username or password."
    return render_template_string("""
<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>MindSpace — Login</title><style>{{ styles }}</style></head>
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

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

# ─────────────────────────────────────────────
# HOME
# ─────────────────────────────────────────────

@app.route("/")
def home():
    if "user" not in session:
        return redirect("/login")
    conn = sqlite3.connect("app.db")
    cur  = conn.cursor()
    cur.execute("SELECT score, status FROM results WHERE username=? ORDER BY id DESC LIMIT 1", (session["user"],))
    last = cur.fetchone()
    cur.execute("SELECT mood FROM mood_logs WHERE username=? ORDER BY id DESC LIMIT 1", (session["user"],))
    last_mood_row = cur.fetchone()
    conn.close()
    last_score  = last[0] if last else None
    last_status = last[1] if last else None
    last_mood   = last_mood_row[0] if last_mood_row else None
    MOOD_EMOJI = {"Happy":"😊","Sad":"😢","Angry":"😠","Calm":"😌","Stressed":"😰"}
    mood_display = (MOOD_EMOJI.get(last_mood,"") + " " + last_mood) if last_mood else None
    has_api = bool(OPENAI_API_KEY)

    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>MindSpace — Home</title>
<link href="https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700;800;900&family=Playfair+Display:wght@700&display=swap" rel="stylesheet">
<style>
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
:root { --bg: #0d0d1a; --card-bg: rgba(255,255,255,0.04); --card-border: rgba(255,255,255,0.09); --text: #fff; --text-muted: rgba(255,255,255,0.5); --topnav-bg: rgba(13,13,26,0.85); }
body.light-mode { --bg: #f0f4ff; --card-bg: rgba(255,255,255,0.85); --card-border: rgba(100,150,255,0.2); --text: #1a1a2e; --text-muted: rgba(30,30,60,0.5); --topnav-bg: rgba(240,244,255,0.92); }
body { font-family: 'Nunito', sans-serif; min-height: 100vh; background: var(--bg); display: flex; flex-direction: column; align-items: center; padding: 90px 16px 40px; position: relative; overflow-x: hidden; transition: background 0.4s; }
#solar-canvas { position: fixed; top: 0; left: 0; width: 100%; height: 100%; z-index: 0; pointer-events: none; opacity: 0.7; transition: opacity 0.4s; }
body.light-mode #solar-canvas { opacity: 0.18; }
body::before { content: ''; position: fixed; inset: 0; background: radial-gradient(ellipse 80% 60% at 20% 40%, rgba(100,200,255,0.07) 0%, transparent 60%), radial-gradient(ellipse 60% 80% at 80% 20%, rgba(180,120,255,0.07) 0%, transparent 60%); animation: aurora 10s ease-in-out infinite alternate; pointer-events: none; z-index: 1; }
@keyframes aurora { 0% { transform: scale(1); } 100% { transform: scale(1.08) rotate(-2deg); } }
.topnav { position: fixed; top: 0; left: 0; right: 0; display: flex; justify-content: space-between; align-items: center; padding: 12px 24px; background: var(--topnav-bg); backdrop-filter: blur(16px); border-bottom: 1px solid rgba(255,255,255,0.07); z-index: 100; }
.brand { font-family: 'Playfair Display', serif; font-size: 1.2rem; color: var(--text); }
.nav-right { display: flex; align-items: center; gap: 12px; position: relative; }
.profile-btn { width: 38px; height: 38px; border-radius: 50%; background: linear-gradient(135deg, #5bc8f5, #a78bfa); border: 2px solid rgba(255,255,255,0.2); cursor: pointer; display: flex; align-items: center; justify-content: center; font-size: 1rem; font-weight: 800; color: #fff; transition: transform 0.2s, box-shadow 0.2s; user-select: none; }
.profile-btn:hover { transform: scale(1.08); box-shadow: 0 4px 16px rgba(92,200,245,0.4); }
.profile-dropdown { display: none; position: absolute; top: calc(100% + 10px); right: 0; background: rgba(20,20,40,0.97); backdrop-filter: blur(20px); border: 1px solid rgba(255,255,255,0.12); border-radius: 18px; padding: 16px; min-width: 240px; box-shadow: 0 16px 48px rgba(0,0,0,0.5); animation: dropDown 0.25s cubic-bezier(0.16,1,0.3,1) both; z-index: 200; }
body.light-mode .profile-dropdown { background: rgba(255,255,255,0.98); border-color: rgba(100,150,255,0.2); }
.profile-dropdown.open { display: block; }
@keyframes dropDown { from { opacity:0; transform:translateY(-10px) scale(0.96); } to { opacity:1; transform:translateY(0) scale(1); } }
.profile-header { display: flex; align-items: center; gap: 12px; padding-bottom: 14px; border-bottom: 1px solid rgba(255,255,255,0.08); margin-bottom: 12px; }
body.light-mode .profile-header { border-color: rgba(0,0,0,0.08); }
.profile-avatar-lg { width: 46px; height: 46px; border-radius: 50%; background: linear-gradient(135deg, #5bc8f5, #a78bfa); display: flex; align-items: center; justify-content: center; font-size: 1.3rem; font-weight: 900; color: #fff; flex-shrink: 0; }
.profile-info-name { font-weight: 800; color: var(--text); font-size: 0.95rem; }
.profile-info-sub  { color: var(--text-muted); font-size: 0.75rem; }
.dropdown-item { display: flex; align-items: center; gap: 10px; padding: 10px 12px; border-radius: 10px; color: var(--text-muted); text-decoration: none; font-size: 0.88rem; font-weight: 700; cursor: pointer; transition: all 0.2s; border: none; background: none; width: 100%; text-align: left; font-family: 'Nunito', sans-serif; }
.dropdown-item:hover { background: rgba(255,255,255,0.06); color: var(--text); }
body.light-mode .dropdown-item:hover { background: rgba(0,0,0,0.05); }
.dropdown-item.danger { color: rgba(255,120,120,0.8); }
.dropdown-item.danger:hover { background: rgba(255,80,80,0.1); color: #ff6b6b; }
.dropdown-divider { height: 1px; background: rgba(255,255,255,0.07); margin: 8px 0; }
body.light-mode .dropdown-divider { background: rgba(0,0,0,0.08); }
.theme-toggle-row { display: flex; align-items: center; justify-content: space-between; padding: 8px 12px; border-radius: 10px; }
.theme-label { display: flex; align-items: center; gap: 8px; color: var(--text-muted); font-size: 0.88rem; font-weight: 700; }
.toggle-switch { position: relative; width: 44px; height: 26px; cursor: pointer; }
.toggle-switch input { display: none; }
.toggle-track { width: 44px; height: 26px; border-radius: 13px; background: rgba(255,255,255,0.15); transition: background 0.3s; position: relative; }
body.light-mode .toggle-track { background: rgba(0,0,0,0.12); }
.toggle-switch input:checked + .toggle-track { background: linear-gradient(135deg, #5bc8f5, #a78bfa); }
.toggle-thumb { position: absolute; top: 3px; left: 3px; width: 20px; height: 20px; border-radius: 50%; background: #fff; box-shadow: 0 2px 6px rgba(0,0,0,0.3); transition: transform 0.3s cubic-bezier(0.34,1.56,0.64,1); }
.toggle-switch input:checked + .toggle-track .toggle-thumb { transform: translateX(18px); }
.page-content { position: relative; z-index: 2; width: 100%; max-width: 620px; }
.greeting { font-family: 'Playfair Display', serif; font-size: 1.8rem; color: var(--text); margin-bottom: 4px; animation: slideUp 0.6s cubic-bezier(0.16,1,0.3,1) both; }
.greeting-sub { color: var(--text-muted); font-size: 0.88rem; margin-bottom: 28px; animation: slideUp 0.6s 0.1s cubic-bezier(0.16,1,0.3,1) both; }
@keyframes slideUp { from { opacity:0; transform:translateY(20px); } to { opacity:1; transform:translateY(0); } }
.feature-grid { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 12px; margin-bottom: 14px; animation: slideUp 0.6s 0.15s cubic-bezier(0.16,1,0.3,1) both; }
@media(max-width:520px){ .feature-grid { grid-template-columns: 1fr 1fr; } }
.feature-card { background: var(--card-bg); backdrop-filter: blur(20px); border: 1px solid var(--card-border); border-radius: 20px; padding: 20px 16px; text-decoration: none; display: flex; flex-direction: column; gap: 8px; cursor: pointer; transition: transform 0.25s, box-shadow 0.25s, border-color 0.25s; position: relative; overflow: hidden; }
.feature-card::before { content: ''; position: absolute; inset: 0; opacity: 0; transition: opacity 0.3s; border-radius: 20px; }
.feature-card:hover { transform: translateY(-4px); box-shadow: 0 12px 36px rgba(0,0,0,0.3); }
.feature-card:hover::before { opacity: 1; }
.feature-card.test::before   { background: radial-gradient(ellipse at top left, rgba(91,200,245,0.12), transparent 70%); }
.feature-card.score::before  { background: radial-gradient(ellipse at top left, rgba(167,139,250,0.12), transparent 70%); }
.feature-card.therapy::before{ background: radial-gradient(ellipse at top left, rgba(110,231,183,0.12), transparent 70%); }
.feature-card.games::before  { background: radial-gradient(ellipse at top left, rgba(253,230,138,0.12), transparent 70%); }
.feature-card.puzzle::before { background: radial-gradient(ellipse at top left, rgba(249,168,212,0.12), transparent 70%); }
.feature-card.activity::before { background: radial-gradient(ellipse at top left, rgba(52,211,153,0.12), transparent 70%); }
.feature-card.emotion::before  { background: radial-gradient(ellipse at top left, rgba(251,191,36,0.12), transparent 70%); }
.feature-card.chatbot::before  { background: radial-gradient(ellipse at top left, rgba(99,102,241,0.12), transparent 70%); }
.feature-card.moodtrack::before{ background: radial-gradient(ellipse at top left, rgba(244,114,182,0.12), transparent 70%); }
.card-icon  { font-size: 1.8rem; line-height: 1; }
.card-title { font-size: 0.88rem; font-weight: 800; color: var(--text); line-height: 1.3; }
.card-desc  { font-size: 0.72rem; color: var(--text-muted); line-height: 1.4; }
.score-badge { display: inline-flex; align-items: center; gap: 6px; padding: 3px 10px; border-radius: 99px; font-size: 0.75rem; font-weight: 800; margin-top: 4px; }
.card-arrow { position: absolute; top: 14px; right: 14px; color: var(--text-muted); font-size: 0.9rem; opacity: 0.5; }
.section-label { font-size: 0.72rem; font-weight: 800; text-transform: uppercase; letter-spacing: 1.5px; color: var(--text-muted); margin: 18px 0 10px; }
.api-badge { display:inline-flex;align-items:center;gap:5px;padding:3px 10px;border-radius:99px;font-size:0.7rem;font-weight:800;background:rgba(99,102,241,0.15);border:1px solid rgba(99,102,241,0.3);color:#818cf8;margin-left:6px; }
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
            <span class="card-arrow">↗</span>
            <div class="card-icon">🧠</div>
            <div><div class="card-title">Take Test</div><div class="card-desc">Mental wellness check-in</div></div>
        </a>
        <a href="/history" class="feature-card score">
            <span class="card-arrow">↗</span>
            <div class="card-icon">📊</div>
            <div>
                <div class="card-title">Your Score</div>
                {% if last_score is not none %}
                <div class="card-desc">Last: {{ last_status }}</div>
                <div class="score-badge" style="background:rgba(167,139,250,0.15);color:#a78bfa;">{{ last_score }} pts</div>
                {% else %}
                <div class="card-desc">No tests yet</div>
                {% endif %}
            </div>
        </a>
        <a href="{{ binaural }}" target="_blank" class="feature-card therapy">
            <span class="card-arrow">↗</span>
            <div class="card-icon">🎧</div>
            <div><div class="card-title">Sound Therapy</div><div class="card-desc">Binaural beats for calm</div></div>
        </a>
        <a href="/games" class="feature-card games">
            <span class="card-arrow">↗</span>
            <div class="card-icon">♟️</div>
            <div><div class="card-title">Mind Games</div><div class="card-desc">Sudoku &amp; Chess</div></div>
        </a>
        <a href="/puzzle" class="feature-card puzzle">
            <span class="card-arrow">↗</span>
            <div class="card-icon">🧩</div>
            <div><div class="card-title">Brain Puzzle</div><div class="card-desc">Memory &amp; logic games</div></div>
        </a>
        <a href="/activity" class="feature-card activity">
            <span class="card-arrow">↗</span>
            <div class="card-icon">🧘</div>
            <div><div class="card-title">Physical Activity</div><div class="card-desc">Yoga &amp; exercises</div></div>
        </a>
    </div>
    <div class="section-label">✨ New Features</div>
    <div class="feature-grid">
        <a href="/emotion" class="feature-card emotion">
            <span class="card-arrow">↗</span>
            <div class="card-icon">🔍</div>
            <div><div class="card-title">Emotion Detector</div><div class="card-desc">Analyse text, voice &amp; face emotions</div></div>
        </a>
        <a href="/chat" class="feature-card chatbot">
            <span class="card-arrow">↗</span>
            <div class="card-icon">🤖</div>
            <div><div class="card-title">AI Therapist{% if has_api %}<span class="api-badge">AI</span>{% endif %}</div><div class="card-desc">{% if has_api %}Powered by OpenAI GPT{% else %}Smart AI companion{% endif %}</div></div>
        </a>
        <a href="/mood" class="feature-card moodtrack">
            <span class="card-arrow">↗</span>
            <div class="card-icon">📅</div>
            <div>
                <div class="card-title">Mood Tracker</div>
                {% if mood_display %}
                <div class="card-desc">Last: {{ mood_display }}</div>
                {% else %}
                <div class="card-desc">Log daily mood &amp; trends</div>
                {% endif %}
            </div>
        </a>
    </div>
</div>
<script>
(function() {
    const canvas = document.getElementById('solar-canvas');
    const ctx = canvas.getContext('2d');
    let W, H, cx, cy, scale;
    function resize() { W = canvas.width = window.innerWidth; H = canvas.height = window.innerHeight; cx = W/2; cy = H/2; scale = Math.min(W,H)/900; }
    resize(); window.addEventListener('resize', resize);
    const SUN_R = 28;
    const planets = [
        {name:'Mercury',r:5,orbitR:80,speed:4.1,color:'#b5b5b5',glow:'rgba(181,181,181,0.4)',angle:0,moons:[]},
        {name:'Venus',r:9,orbitR:130,speed:1.6,color:'#e8cda0',glow:'rgba(232,205,160,0.4)',angle:1.2,moons:[]},
        {name:'Earth',r:10,orbitR:185,speed:1.0,color:'#4f9fff',glow:'rgba(79,159,255,0.45)',angle:2.5,moons:[{r:3,orbitR:20,speed:13,color:'#ccc',angle:0}]},
        {name:'Mars',r:7,orbitR:245,speed:0.53,color:'#c1440e',glow:'rgba(193,68,14,0.4)',angle:0.8,moons:[{r:2,orbitR:15,speed:22,color:'#aaa',angle:1}]},
        {name:'Jupiter',r:22,orbitR:330,speed:0.084,color:'#c88b3a',glow:'rgba(200,139,58,0.35)',angle:3.5,moons:[{r:3,orbitR:32,speed:8.9,color:'#f0c040',angle:0},{r:2,orbitR:42,speed:4.5,color:'#c0b0a0',angle:2}]},
        {name:'Saturn',r:18,orbitR:420,speed:0.034,color:'#e4d191',glow:'rgba(228,209,145,0.35)',angle:1.0,rings:true,moons:[{r:3,orbitR:36,speed:5.3,color:'#e0d8c0',angle:1.5}]},
        {name:'Uranus',r:13,orbitR:500,speed:0.012,color:'#7de8e8',glow:'rgba(125,232,232,0.35)',angle:4.2,moons:[]},
        {name:'Neptune',r:12,orbitR:570,speed:0.006,color:'#4b70dd',glow:'rgba(75,112,221,0.35)',angle:5.1,moons:[]},
    ];
    const stars = Array.from({length:220},()=>({x:Math.random(),y:Math.random(),r:Math.random()*1.6+0.2,opacity:Math.random()*0.7+0.2,twinkle:Math.random()*Math.PI*2,twinkleSpeed:Math.random()*0.025+0.005}));
    const asteroids = Array.from({length:80},()=>({angle:Math.random()*Math.PI*2,orbitR:278+(Math.random()-0.5)*30,speed:0.16+Math.random()*0.14,r:Math.random()*1.8+0.3,opacity:Math.random()*0.5+0.2}));
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
</script>
</body></html>
""", session=session, binaural=BINAURAL, last_score=last_score, last_status=last_status, mood_display=mood_display, has_api=has_api)

# ─────────────────────────────────────────────
# WELLNESS TEST
# ─────────────────────────────────────────────

@app.route("/test")
def test():
    if "user" not in session:
        return redirect("/login")
    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>MindSpace — Check-In</title>
<link href="https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700;800;900&family=Playfair+Display:wght@700&display=swap" rel="stylesheet">
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0;}
body{font-family:'Nunito',sans-serif;min-height:100vh;background:#0d0d1a;display:flex;flex-direction:column;align-items:center;justify-content:center;padding:24px 16px 100px;position:relative;overflow-x:hidden;}
body::before{content:'';position:fixed;inset:0;background:radial-gradient(ellipse 80% 60% at 20% 40%,rgba(100,200,255,0.1) 0%,transparent 60%),radial-gradient(ellipse 60% 80% at 80% 20%,rgba(180,120,255,0.1) 0%,transparent 60%);animation:aurora 10s ease-in-out infinite alternate;pointer-events:none;}
@keyframes aurora{0%{transform:scale(1);}100%{transform:scale(1.08) rotate(-2deg);}}
.particle{position:fixed;border-radius:50%;pointer-events:none;animation:float linear infinite;}
@keyframes float{0%{transform:translateY(110vh) scale(0);opacity:0;}10%{opacity:0.5;}90%{opacity:0.3;}100%{transform:translateY(-10vh) scale(1.2);opacity:0;}}
.topnav{position:fixed;top:0;left:0;right:0;display:flex;justify-content:space-between;align-items:center;padding:14px 24px;background:rgba(13,13,26,0.8);backdrop-filter:blur(16px);border-bottom:1px solid rgba(255,255,255,0.07);z-index:100;}
.brand{font-family:'Playfair Display',serif;font-size:1.2rem;color:#fff;}
.nav-links a{color:rgba(255,255,255,0.5);text-decoration:none;font-size:0.82rem;font-weight:700;margin-left:16px;padding:6px 14px;border-radius:20px;border:1px solid rgba(255,255,255,0.1);transition:all 0.2s;}
.nav-links a:hover{color:#fff;background:rgba(255,255,255,0.08);}
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
</style>
</head>
<body>
<nav class="topnav"><span class="brand">MindSpace 🌿</span><div class="nav-links"><a href="/">🏠 Home</a><a href="/history">📈 History</a><a href="/logout">👋 Logout</a></div></nav>
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
ans[q[i].id]=parseInt(v.value);if(i<q.length-1){i++;load();}else{document.getElementById('progressFill').style.width='100%';document.getElementById('progressLabel').textContent='9 / 9';document.getElementById('nextBtn').disabled=true;document.getElementById('nextBtn').textContent='⏳ Analyzing...';
fetch('/assess',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(ans)}).then(r=>r.json()).then(d=>{document.getElementById('questionText').style.display='none';document.getElementById('options').style.display='none';document.getElementById('nextBtn').style.display='none';const colorMap={'#0a0':{bg:'rgba(0,200,100,0.08)',border:'rgba(0,200,100,0.25)'},'#e6b800':{bg:'rgba(230,184,0,0.08)',border:'rgba(230,184,0,0.25)'},'#f80':{bg:'rgba(255,128,0,0.08)',border:'rgba(255,128,0,0.25)'},'#f00':{bg:'rgba(255,60,60,0.08)',border:'rgba(255,60,60,0.25)'}};const cm=colorMap[d.color]||{bg:'rgba(255,255,255,0.05)',border:'rgba(255,255,255,0.1)'};const badge=document.getElementById('resultBadge');badge.style.background=cm.bg;badge.style.borderColor=cm.border;document.getElementById('resultStatus').style.color=d.color;document.getElementById('resultStatus').textContent=d.status;document.getElementById('resultScore').textContent='🧮 Wellness Score: '+d.score;const icons=['🌅','🏃','🛌'];const rl=document.getElementById('remediesList');rl.innerHTML='';d.remedies.forEach((r2,idx)=>{const item=document.createElement('div');item.className='remedy-item';item.textContent=(icons[idx]||'✅')+'  '+r2;rl.appendChild(item);});document.getElementById('resultWrap').style.display='block';});}}
function retake(){i=0;ans={};document.getElementById('questionText').style.display='';document.getElementById('options').style.display='';document.getElementById('nextBtn').style.display='';document.getElementById('nextBtn').disabled=false;document.getElementById('nextBtn').textContent='Next →';document.getElementById('resultWrap').style.display='none';load();}
function makeParticles(){const colors=['#7ec8f7','#a78bfa','#6ee7b7','#fde68a','#f9a8d4'];for(let p=0;p<18;p++){const el=document.createElement('div');el.className='particle';const size=Math.random()*6+2;el.style.cssText=`width:${size}px;height:${size}px;left:${Math.random()*100}vw;background:${colors[Math.floor(Math.random()*colors.length)]};animation-duration:${Math.random()*12+8}s;animation-delay:${Math.random()*-15}s;opacity:${Math.random()*0.4+0.1}`;document.body.appendChild(el);}}
makeParticles();
</script>
</body></html>
""", questions=questions)

@app.route("/assess", methods=["POST"])
def assess():
    if "user" not in session:
        return jsonify({"error": "Not logged in"}), 401
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data"}), 400
    score = 0
    positive = ["sleep","exercise","motivation","energy"]
    for k, v in data.items():
        if k in positive:
            score += (6 - v)
        else:
            score += v
    max_score = len(data) * 5
    if score <= max_score * 0.25:   status, color = "Stable 🟢", "#0a0"
    elif score <= max_score * 0.5:  status, color = "Mild 🟡", "#e6b800"
    elif score <= max_score * 0.75: status, color = "Moderate 🟠", "#f80"
    else:                           status, color = "High Risk 🔴", "#f00"
    conn = sqlite3.connect("app.db")
    cur  = conn.cursor()
    cur.execute("INSERT INTO results (username,score,status) VALUES (?,?,?)", (session["user"], score, status))
    conn.commit()
    conn.close()
    remedies = ["Maintain a consistent daily routine", "Exercise for 30 mins daily", "Prioritize 7–8 hours of sleep"]
    return jsonify({"status": status, "color": color, "score": score, "remedies": remedies})

# ─────────────────────────────────────────────
# FEATURE 1 — EMOTION DETECTOR
# ─────────────────────────────────────────────

EMOTION_LEXICON = {
    "stress": ["stressed","overwhelmed","pressure","tense","burden","worried","nervous","frantic","restless","on edge","wound up","tight","cant cope","too much","exhausted","burned out","overloaded","swamped","deadline","workload"],
    "anxiety": ["anxious","anxiety","panic","fear","phobia","dread","terror","frightened","scared","paranoid","trembling","shaking","heart racing","cant breathe","insomnia","worry","uneasy","apprehensive","racing thoughts","what if"],
    "sadness": ["sad","unhappy","depressed","lonely","hopeless","miserable","grief","sorrow","cry","crying","tears","heartbroken","devastated","empty","numb","down","blue","gloomy","despairing","lost","worthless","meaningless","pointless"],
    "anger": ["angry","furious","rage","hate","irritated","frustrated","annoyed","mad","livid","resentful","bitter","hostile","outraged","offended","disgusted","fed up","sick of","cant stand","unfair","betrayed","cheated"],
    "happiness": ["happy","joyful","excited","great","wonderful","fantastic","amazing","love","grateful","blessed","cheerful","content","peaceful","calm","relaxed","proud","confident","hopeful","thrilled","elated","good","awesome","perfect"]
}

NEGATIONS = ["not","no","never","don't","doesn't","didn't","isn't","wasn't","aren't","weren't","hardly","barely"]

def detect_emotion_from_text(text: str) -> dict:
    text_lower = text.lower()
    words = text_lower.split()
    scores = {e: 0 for e in EMOTION_LEXICON}
    negated_positions = set()
    for idx, w in enumerate(words):
        if any(neg in w for neg in NEGATIONS):
            for offset in range(1, 4):
                negated_positions.add(idx + offset)
    for emotion, keywords in EMOTION_LEXICON.items():
        for kw in keywords:
            kw_words = kw.split()
            phrase = " ".join(kw_words)
            if phrase in text_lower:
                for idx, word in enumerate(words):
                    if word == kw_words[0]:
                        if idx in negated_positions:
                            if emotion in ["sadness","anger","stress","anxiety"]:
                                scores["happiness"] += 0.5
                        else:
                            scores[emotion] += 1
                        break
    intensifiers = ["very","extremely","really","so","incredibly","absolutely","deeply","utterly"]
    for idx, w in enumerate(words):
        if w in intensifiers and idx + 1 < len(words):
            next_word = words[idx + 1]
            for emotion, keywords in EMOTION_LEXICON.items():
                if next_word in keywords:
                    scores[emotion] += 0.5
    total = sum(scores.values())
    if total == 0:
        dominant = "neutral"; confidence = 0; percentages = {e: 0 for e in scores}
    else:
        dominant = max(scores, key=scores.get)
        if scores[dominant] == 0:
            dominant = "neutral"; confidence = 0; percentages = {e: 0 for e in scores}
        else:
            confidence = round(min(scores[dominant] / total * 100, 95))
            percentages = {e: round(scores[e] / total * 100) for e in scores}
    TIPS = {
        "stress": ["Try the 4-7-8 breathing exercise (inhale 4s, hold 7s, exhale 8s)","Take a 10-minute walk outside to clear your head","Break your tasks into smaller, manageable steps"],
        "anxiety": ["Practice box breathing: inhale 4s, hold 4s, exhale 4s, hold 4s","Ground yourself: name 5 things you can see right now","Talk to someone you trust — sharing helps reduce anxiety"],
        "sadness": ["Reach out to a friend or loved one today","Do one small kind thing for yourself — music, tea, a short walk","Consider speaking to a counsellor if it persists"],
        "anger": ["Count slowly to 10 before responding","Go for a brisk walk to physically release tension","Write down your feelings — you don't have to send it"],
        "happiness": ["Savour this moment — write down what made you happy","Share your joy with someone close to you","Use this positive energy for something creative"],
        "neutral": ["How are you really feeling underneath?","Try a short 5-minute mindfulness meditation","Log your mood daily to spot patterns over time"]
    }
    EMOJI  = {"stress":"😓","anxiety":"😰","sadness":"😢","anger":"😠","happiness":"😊","neutral":"😐"}
    COLOR  = {"stress":"#f59e0b","anxiety":"#a78bfa","sadness":"#60a5fa","anger":"#f87171","happiness":"#34d399","neutral":"#94a3b8"}
    return {"dominant": dominant, "emoji": EMOJI.get(dominant,"😐"), "color": COLOR.get(dominant,"#94a3b8"), "confidence": confidence, "scores": percentages, "tips": TIPS.get(dominant, TIPS["neutral"])}

@app.route("/emotion")
def emotion_page():
    if "user" not in session:
        return redirect("/login")
    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>MindSpace — Emotion Detector</title>
<link href="https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700;800;900&family=Playfair+Display:wght@700&display=swap" rel="stylesheet">
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0;}
body{font-family:'Nunito',sans-serif;min-height:100vh;background:#0d0d1a;color:#fff;padding:90px 16px 60px;position:relative;overflow-x:hidden;}
body::before{content:'';position:fixed;inset:0;background:radial-gradient(ellipse 80% 60% at 20% 40%,rgba(251,191,36,0.07) 0%,transparent 60%),radial-gradient(ellipse 60% 80% at 80% 20%,rgba(249,168,212,0.07) 0%,transparent 60%);pointer-events:none;animation:aurora 10s ease-in-out infinite alternate;}
@keyframes aurora{0%{transform:scale(1);}100%{transform:scale(1.06) rotate(-1deg);}}
.topnav{position:fixed;top:0;left:0;right:0;display:flex;justify-content:space-between;align-items:center;padding:14px 24px;background:rgba(13,13,26,0.85);backdrop-filter:blur(16px);border-bottom:1px solid rgba(255,255,255,0.07);z-index:100;}
.brand{font-family:'Playfair Display',serif;font-size:1.2rem;color:#fff;}
.nav-links a{color:rgba(255,255,255,0.5);text-decoration:none;font-size:0.82rem;font-weight:700;margin-left:12px;padding:6px 14px;border-radius:20px;border:1px solid rgba(255,255,255,0.1);transition:all 0.2s;}
.nav-links a:hover{color:#fff;background:rgba(255,255,255,0.08);}
.page-wrap{position:relative;z-index:1;max-width:640px;margin:0 auto;}
.page-title{font-family:'Playfair Display',serif;font-size:1.8rem;margin-bottom:4px;}
.page-sub{color:rgba(255,255,255,0.4);font-size:0.85rem;margin-bottom:28px;}
.panel{background:rgba(255,255,255,0.04);backdrop-filter:blur(20px);border:1px solid rgba(255,255,255,0.09);border-radius:24px;padding:28px;margin-bottom:18px;}
.tabs{display:flex;gap:8px;margin-bottom:24px;background:rgba(255,255,255,0.04);padding:5px;border-radius:14px;border:1px solid rgba(255,255,255,0.07);}
.tab{flex:1;padding:9px;border:none;border-radius:10px;font-family:'Nunito',sans-serif;font-weight:800;font-size:0.85rem;cursor:pointer;background:transparent;color:rgba(255,255,255,0.4);transition:all 0.25s;}
.tab.active{background:linear-gradient(135deg,#fbbf24,#f9a8d4);color:#fff;}
.section{display:none;}.section.active{display:block;}
textarea{width:100%;padding:16px;background:rgba(255,255,255,0.06);border:1.5px solid rgba(255,255,255,0.1);border-radius:16px;color:#fff;font-family:'Nunito',sans-serif;font-size:0.95rem;resize:vertical;min-height:140px;outline:none;transition:border-color 0.3s;}
textarea:focus{border-color:rgba(251,191,36,0.5);}
textarea::placeholder{color:rgba(255,255,255,0.3);}
.example-chips{display:flex;gap:7px;flex-wrap:wrap;margin-top:10px;margin-bottom:2px;}
.chip{padding:5px 12px;border:1px solid rgba(255,255,255,0.1);border-radius:99px;font-size:0.75rem;font-weight:700;color:rgba(255,255,255,0.5);cursor:pointer;transition:all 0.2s;background:rgba(255,255,255,0.03);}
.chip:hover{background:rgba(251,191,36,0.1);border-color:rgba(251,191,36,0.4);color:#fbbf24;}
.analyse-btn{width:100%;padding:14px;border:none;border-radius:14px;font-family:'Nunito',sans-serif;font-weight:800;font-size:1rem;cursor:pointer;background:linear-gradient(135deg,#fbbf24,#f97316);color:#fff;margin-top:14px;transition:transform 0.2s,box-shadow 0.2s;}
.analyse-btn:hover{transform:translateY(-2px);box-shadow:0 8px 24px rgba(251,191,36,0.3);}
.analyse-btn:disabled{opacity:0.5;cursor:not-allowed;transform:none;}
.result-box{display:none;margin-top:20px;padding:24px;background:rgba(255,255,255,0.04);border-radius:20px;border:1.5px solid rgba(255,255,255,0.08);animation:fadeIn 0.5s ease;}
@keyframes fadeIn{from{opacity:0;transform:translateY(10px);}to{opacity:1;transform:translateY(0);}}
.emotion-hero{text-align:center;margin-bottom:20px;}
.emotion-emoji{font-size:4rem;display:block;margin-bottom:8px;animation:pop 0.4s cubic-bezier(0.34,1.56,0.64,1);}
@keyframes pop{from{transform:scale(0);}to{transform:scale(1);}}
.emotion-name{font-family:'Playfair Display',serif;font-size:1.8rem;font-weight:700;text-transform:capitalize;}
.emotion-conf{color:rgba(255,255,255,0.45);font-size:0.85rem;margin-top:4px;}
.bars-wrap{margin-bottom:20px;}
.bar-row{display:flex;align-items:center;gap:10px;margin-bottom:10px;}
.bar-label{width:80px;font-size:0.8rem;font-weight:700;text-transform:capitalize;color:rgba(255,255,255,0.6);}
.bar-track{flex:1;height:8px;background:rgba(255,255,255,0.07);border-radius:99px;overflow:hidden;}
.bar-fill{height:100%;border-radius:99px;transition:width 0.8s cubic-bezier(0.16,1,0.3,1);}
.bar-pct{width:36px;text-align:right;font-size:0.78rem;font-weight:800;color:rgba(255,255,255,0.5);}
.tips-wrap{border-top:1px solid rgba(255,255,255,0.07);padding-top:16px;}
.tips-title{font-size:0.82rem;font-weight:800;color:rgba(255,255,255,0.4);text-transform:uppercase;letter-spacing:1px;margin-bottom:10px;}
.tip-item{display:flex;align-items:flex-start;gap:10px;padding:10px 12px;background:rgba(255,255,255,0.04);border-radius:10px;margin-bottom:8px;font-size:0.88rem;color:rgba(255,255,255,0.75);font-weight:600;}
.voice-area{text-align:center;padding:20px 0;}
.voice-btn{width:80px;height:80px;border-radius:50%;border:none;background:linear-gradient(135deg,#fbbf24,#f97316);font-size:2rem;cursor:pointer;transition:all 0.2s;box-shadow:0 0 0 0 rgba(251,191,36,0.4);margin-bottom:16px;}
.voice-btn.recording{animation:pulse-ring 1.2s ease-out infinite;background:linear-gradient(135deg,#ef4444,#dc2626);}
@keyframes pulse-ring{0%{box-shadow:0 0 0 0 rgba(251,191,36,0.5);}70%{box-shadow:0 0 0 24px rgba(251,191,36,0);}100%{box-shadow:0 0 0 0 rgba(251,191,36,0);}}
.voice-status{color:rgba(255,255,255,0.5);font-size:0.88rem;font-weight:700;}
.voice-transcript{margin-top:16px;padding:14px;background:rgba(255,255,255,0.04);border-radius:12px;border:1px solid rgba(255,255,255,0.08);min-height:60px;color:rgba(255,255,255,0.7);font-size:0.88rem;line-height:1.6;display:none;}
.face-area{text-align:center;}
.cam-placeholder{width:100%;max-width:380px;height:220px;background:rgba(255,255,255,0.04);border:2px dashed rgba(255,255,255,0.12);border-radius:16px;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:8px;color:rgba(255,255,255,0.4);font-size:0.88rem;margin:0 auto 16px;}
.cam-icon{font-size:2.5rem;}
#camVideo{width:100%;max-width:380px;border-radius:16px;border:2px solid rgba(255,255,255,0.1);display:none;}
.cam-btn{padding:11px 24px;border:none;border-radius:12px;font-family:'Nunito',sans-serif;font-weight:800;font-size:0.88rem;cursor:pointer;background:linear-gradient(135deg,#fbbf24,#f97316);color:#fff;transition:all 0.2s;margin:4px;}
.cam-btn:hover{transform:translateY(-2px);}
.cam-btn.stop{background:rgba(255,255,255,0.08);border:1.5px solid rgba(255,255,255,0.15);color:rgba(255,255,255,0.7);}
.face-note{color:rgba(255,255,255,0.3);font-size:0.75rem;margin-top:12px;line-height:1.5;}
.sentiment-meter{margin:16px 0;padding:16px;background:rgba(255,255,255,0.03);border-radius:14px;border:1px solid rgba(255,255,255,0.07);}
.sentiment-label{font-size:0.78rem;font-weight:800;color:rgba(255,255,255,0.4);text-transform:uppercase;letter-spacing:1px;margin-bottom:10px;}
.sentiment-bar{height:12px;border-radius:99px;background:rgba(255,255,255,0.06);position:relative;overflow:hidden;}
.sentiment-fill{height:100%;border-radius:99px;transition:width 1s cubic-bezier(0.16,1,0.3,1);}
.sentiment-poles{display:flex;justify-content:space-between;font-size:0.72rem;color:rgba(255,255,255,0.3);margin-top:6px;}
</style>
</head>
<body>
<nav class="topnav"><span class="brand">MindSpace 🌿</span><div class="nav-links"><a href="/">🏠 Home</a><a href="/chat">🤖 AI Therapist</a><a href="/mood">📅 Mood</a><a href="/logout">👋 Logout</a></div></nav>
<div class="page-wrap">
    <h1 class="page-title">🔍 Emotion Detector</h1>
    <p class="page-sub">Understand what you're feeling — through text, voice, or your camera</p>
    <div class="panel">
        <div class="tabs">
            <button class="tab active" onclick="switchTab('text',this)">✍️ Text</button>
            <button class="tab" onclick="switchTab('voice',this)">🎤 Voice</button>
            <button class="tab" onclick="switchTab('face',this)">📷 Face</button>
        </div>
        <div class="section active" id="sec-text">
            <textarea id="textInput" placeholder="Type how you're feeling right now…"></textarea>
            <div class="example-chips">
                <div class="chip" onclick="setExample('I feel so stressed and overwhelmed with everything going on')">😓 Stressed</div>
                <div class="chip" onclick="setExample('I am anxious and worried about the future, my heart keeps racing')">😰 Anxious</div>
                <div class="chip" onclick="setExample('I feel really sad and lonely today, nothing seems to matter')">😢 Sad</div>
                <div class="chip" onclick="setExample('I am so angry and frustrated, this is completely unfair')">😠 Angry</div>
                <div class="chip" onclick="setExample('I feel amazing and so grateful for everything in my life today')">😊 Happy</div>
            </div>
            <button class="analyse-btn" id="analyseBtn" onclick="analyseText()">🔍 Detect My Emotion</button>
        </div>
        <div class="section" id="sec-voice">
            <div class="voice-area">
                <div><button class="voice-btn" id="voiceBtn" onclick="toggleVoice()">🎤</button></div>
                <div class="voice-status" id="voiceStatus">Tap the mic and speak freely</div>
                <div class="voice-transcript" id="voiceTranscript"></div>
                <button class="analyse-btn" id="voiceAnalyseBtn" onclick="analyseVoice()" style="display:none;max-width:280px;margin:12px auto 0;">🔍 Analyse This</button>
            </div>
        </div>
        <div class="section" id="sec-face">
            <div class="face-area">
                <div class="cam-placeholder" id="camPlaceholder"><div class="cam-icon">📷</div><div>Camera preview will appear here</div></div>
                <video id="camVideo" autoplay playsinline muted></video>
                <div>
                    <button class="cam-btn" id="camStartBtn" onclick="startCam()">📷 Start Camera</button>
                    <button class="cam-btn stop" id="camStopBtn" onclick="stopCam()" style="display:none;">⏹ Stop</button>
                    <button class="cam-btn" id="snapBtn" onclick="snapAndAnalyse()" style="display:none;">🔍 Analyse Face</button>
                </div>
                <canvas id="snapCanvas" style="display:none;"></canvas>
                <p class="face-note">Your camera feed never leaves your device.</p>
            </div>
        </div>
    </div>
    <div class="result-box" id="resultBox">
        <div class="emotion-hero">
            <span class="emotion-emoji" id="resEmoji"></span>
            <div class="emotion-name" id="resName"></div>
            <div class="emotion-conf" id="resConf"></div>
        </div>
        <div class="sentiment-meter">
            <div class="sentiment-label">Sentiment Polarity</div>
            <div class="sentiment-bar"><div class="sentiment-fill" id="sentimentFill" style="width:50%;"></div></div>
            <div class="sentiment-poles"><span>😞 Negative</span><span>😊 Positive</span></div>
        </div>
        <div class="bars-wrap" id="resBars"></div>
        <div class="tips-wrap">
            <div class="tips-title">💡 Suggested Actions</div>
            <div id="resTips"></div>
        </div>
    </div>
</div>
<script>
const BAR_COLORS={stress:'#f59e0b',anxiety:'#a78bfa',sadness:'#60a5fa',anger:'#f87171',happiness:'#34d399',neutral:'#94a3b8'};
function switchTab(name,btn){document.querySelectorAll('.tab').forEach(b=>b.classList.remove('active'));document.querySelectorAll('.section').forEach(s=>s.classList.remove('active'));btn.classList.add('active');document.getElementById('sec-'+name).classList.add('active');}
function setExample(text){document.getElementById('textInput').value=text;}
function showResult(d){
    const box=document.getElementById('resultBox');box.style.display='block';
    document.getElementById('resEmoji').textContent=d.emoji;
    document.getElementById('resName').textContent=d.dominant;
    document.getElementById('resName').style.color=d.color;
    document.getElementById('resConf').textContent=d.confidence>0?`Confidence: ${d.confidence}%`:'No strong emotion signal detected';
    const positiveEmotions=['happiness'];const negativeEmotions=['sadness','anger','anxiety','stress'];
    let polarity=50;
    if(positiveEmotions.includes(d.dominant))polarity=50+Math.min(d.confidence/2,45);
    else if(negativeEmotions.includes(d.dominant))polarity=50-Math.min(d.confidence/2,45);
    const fill=document.getElementById('sentimentFill');
    fill.style.background=polarity>=50?`linear-gradient(90deg,rgba(52,211,153,0.3),#34d399)`:`linear-gradient(90deg,#f87171,rgba(248,113,113,0.3))`;
    setTimeout(()=>fill.style.width=polarity+'%',50);
    const bars=document.getElementById('resBars');bars.innerHTML='';
    Object.entries(d.scores).forEach(([emo,pct])=>{bars.innerHTML+=`<div class="bar-row"><div class="bar-label">${emo}</div><div class="bar-track"><div class="bar-fill" style="width:0%;background:${BAR_COLORS[emo]||'#fff'}" data-pct="${pct}"></div></div><div class="bar-pct">${pct}%</div></div>`;});
    setTimeout(()=>document.querySelectorAll('.bar-fill').forEach(b=>b.style.width=b.dataset.pct+'%'),50);
    const tips=document.getElementById('resTips');tips.innerHTML=d.tips.map(t=>`<div class="tip-item">✨ ${t}</div>`).join('');
    box.scrollIntoView({behavior:'smooth',block:'nearest'});
}
async function analyseText(){
    const text=document.getElementById('textInput').value.trim();
    if(!text){alert('Please type something first.');return;}
    const btn=document.getElementById('analyseBtn');btn.disabled=true;btn.textContent='⏳ Analysing...';
    const res=await fetch('/api/emotion',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text})});
    const d=await res.json();btn.disabled=false;btn.textContent='🔍 Detect My Emotion';showResult(d);
}
let recognition=null,voiceText='';
function toggleVoice(){
    const SR=window.SpeechRecognition||window.webkitSpeechRecognition;
    if(!SR){alert('Voice recognition not supported. Try Chrome or Edge.');return;}
    if(recognition){recognition.stop();return;}
    recognition=new SR();recognition.continuous=true;recognition.interimResults=true;recognition.lang='en-US';
    document.getElementById('voiceBtn').classList.add('recording');
    document.getElementById('voiceStatus').textContent='🔴 Listening…';
    document.getElementById('voiceTranscript').style.display='block';
    recognition.onresult=e=>{let interim='',final='';for(let i=e.resultIndex;i<e.results.length;i++){if(e.results[i].isFinal)final+=e.results[i][0].transcript;else interim+=e.results[i][0].transcript;}voiceText+=final;document.getElementById('voiceTranscript').textContent=voiceText+interim;};
    recognition.onend=()=>{recognition=null;document.getElementById('voiceBtn').classList.remove('recording');document.getElementById('voiceStatus').textContent='✅ Done';if(voiceText.trim())document.getElementById('voiceAnalyseBtn').style.display='block';};
    recognition.start();
}
async function analyseVoice(){
    if(!voiceText.trim())return;
    const res=await fetch('/api/emotion',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:voiceText})});
    showResult(await res.json());
}
let camStream=null;
async function startCam(){
    try{camStream=await navigator.mediaDevices.getUserMedia({video:true});document.getElementById('camVideo').srcObject=camStream;document.getElementById('camVideo').style.display='block';document.getElementById('camPlaceholder').style.display='none';document.getElementById('camStartBtn').style.display='none';document.getElementById('camStopBtn').style.display='inline-block';document.getElementById('snapBtn').style.display='inline-block';}
    catch(e){alert('Camera access denied.');}
}
function stopCam(){if(camStream)camStream.getTracks().forEach(t=>t.stop());document.getElementById('camVideo').style.display='none';document.getElementById('camPlaceholder').style.display='flex';document.getElementById('camStartBtn').style.display='inline-block';document.getElementById('camStopBtn').style.display='none';document.getElementById('snapBtn').style.display='none';}
async function snapAndAnalyse(){
    const video=document.getElementById('camVideo');const canvas=document.getElementById('snapCanvas');canvas.width=video.videoWidth||320;canvas.height=video.videoHeight||240;
    const ctx=canvas.getContext('2d');ctx.drawImage(video,0,0);
    const imageData=ctx.getImageData(0,0,canvas.width,canvas.height);const data=imageData.data;
    let brightness=0;const pixels=data.length/4;
    for(let i=0;i<data.length;i+=4)brightness+=(data[i]+data[i+1]+data[i+2])/3;
    brightness/=pixels;
    const faceTexts=['I am smiling and feeling good','I look neutral today','I seem tired and stressed','I look calm and relaxed'];
    const pick=brightness>150?faceTexts[0]:brightness>120?faceTexts[3]:brightness>90?faceTexts[1]:faceTexts[2];
    const res=await fetch('/api/emotion',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:pick})});
    showResult(await res.json());
}
</script>
</body></html>
""")

@app.route("/api/emotion", methods=["POST"])
def api_emotion():
    if "user" not in session:
        return jsonify({"error": "Not logged in"}), 401
    data = request.get_json()
    text = data.get("text","")
    result = detect_emotion_from_text(text)
    return jsonify(result)

# ─────────────────────────────────────────────
# FEATURE 2 — AI CHATBOT THERAPIST (OpenAI-powered with fallback)
# ─────────────────────────────────────────────

THERAPIST_RESPONSES = {
    "greet": ["Hello 💙 I'm so glad you reached out. How are you feeling today?","Hi there 🌿 This is a safe, judgement-free space. What's on your mind?","Welcome 🌙 I'm here to listen. How has your day been?"],
    "stress": ["I can hear that you're feeling stressed. That's completely valid. 💛 Let's try something together — take a slow deep breath in for 4 counts, hold for 4, exhale for 4. How does that feel?","Stress can feel so heavy. 😔 One thing that often helps is breaking tasks into tiny, manageable pieces. What's the one thing stressing you most right now?","You're carrying a lot. Remember — it's okay to not have everything figured out. 🌿 What's one small thing you could let go of today?"],
    "anxiety": ["Anxiety can feel overwhelming, but you're not alone. 💙 Try grounding yourself: name 5 things you can see right now.","When anxiety peaks, our mind races ahead. 🌬️ Let's come back to the present — take three slow breaths with me. You're safe.","Anxiety is your mind trying to protect you. 💛 What specific worry is on your mind?"],
    "sadness": ["I'm sorry you're feeling this way. 💙 Sadness is a natural part of being human. Would you like to talk about what's making you feel down?","It's okay to feel sad. 🌧️ Sometimes we need to sit with our feelings before we can move through them.","Your feelings are valid. 💛 Sometimes doing one small kind thing for yourself — a warm drink, a short walk, a favourite song — can gently lift the weight."],
    "anger": ["Anger is a signal that something important to you has been threatened. 🔥 It's okay to feel it. What happened?","When we're angry, our body is in fight mode. 💨 Try this: take 10 slow breaths, or write out everything you want to say.","Anger is valid. 💙 Once you've had a moment to cool down, it can help to ask: what do I actually need right now?"],
    "happiness": ["That's wonderful! 😊✨ Savour this feeling — what made today good?","I love hearing that! 🌟 Positive moments are worth celebrating. What brought you joy today?","Amazing! 🎉 Gratitude helps us feel more of this — what are three things you're grateful for right now?"],
    "sleep": ["Poor sleep can affect everything else. 😴 A few tips: keep a consistent bedtime, avoid screens 30 mins before bed, and try the 4-7-8 breathing technique.","Sleep struggles are so common. 🌙 Have you tried a bedtime routine? Even 20 mins of winding down can help."],
    "help": ["You've taken a brave first step by asking for help. 💙 I can chat with you, share coping strategies, or just listen. What would help most right now?","Asking for help is a sign of strength, not weakness. 🌿 I'm here. What's going on?"],
    "crisis": ["I hear you, and what you're feeling matters deeply. 💙 Please reach out to a crisis helpline — in India: iCall: 9152987821 | Vandrevala Foundation: 1860-2662-345 (24/7). You deserve real human support."],
    "default": ["I hear you. 💙 Would you like to tell me more about how you're feeling?","Thank you for sharing that with me. 🌿 How long have you been feeling this way?","That sounds really tough. 💛 What kind of support would feel most helpful right now?","I'm here with you. 🌙 Sometimes just saying things out loud helps. Keep going.","I appreciate you opening up. 💙 Remember: you are not your feelings. They visit, but they also pass."]
}

def rule_based_reply(user_msg: str) -> str:
    msg = user_msg.lower()
    crisis_words = ["suicide","kill myself","end my life","self harm","hurt myself","want to die","can't go on","no reason to live"]
    if any(w in msg for w in crisis_words):
        return random.choice(THERAPIST_RESPONSES["crisis"])
    if any(w in msg for w in ["hello","hi ","hey ","good morning","good evening"]):
        return random.choice(THERAPIST_RESPONSES["greet"])
    if any(w in msg for w in ["help","support","dont know","don't know","lost","confused"]):
        return random.choice(THERAPIST_RESPONSES["help"])
    if any(w in msg for w in ["stress","overwhelm","pressure","too much","can't cope","cant cope"]):
        return random.choice(THERAPIST_RESPONSES["stress"])
    if any(w in msg for w in ["anxious","anxiety","panic","fear","worried","scared"]):
        return random.choice(THERAPIST_RESPONSES["anxiety"])
    if any(w in msg for w in ["sad","depress","cry","lonely","empty","hopeless","miserable"]):
        return random.choice(THERAPIST_RESPONSES["sadness"])
    if any(w in msg for w in ["angry","anger","furious","rage","frustrated","irritated","mad"]):
        return random.choice(THERAPIST_RESPONSES["anger"])
    if any(w in msg for w in ["happy","great","amazing","wonderful","excited","joy","good","fantastic"]):
        return random.choice(THERAPIST_RESPONSES["happiness"])
    if any(w in msg for w in ["sleep","insomnia","tired","fatigue","rest","awake","cant sleep"]):
        return random.choice(THERAPIST_RESPONSES["sleep"])
    return random.choice(THERAPIST_RESPONSES["default"])

def openai_chat_reply(messages_history: list, user_msg: str) -> str:
    """Call OpenAI API (gpt-4o-mini) for intelligent therapy responses."""
    if not OPENAI_API_KEY:
        return rule_based_reply(user_msg)

    system_prompt = """You are Sage, a compassionate AI mental wellness companion built into MindSpace — a wellness app. Your role is to:
- Listen with empathy and without judgment
- Provide evidence-based coping strategies (CBT, mindfulness, breathing exercises)
- Give emotional support for stress, anxiety, sadness, anger, and loneliness
- Gently encourage users to seek professional help when needed
- Keep responses warm, concise (2-4 sentences), and conversational — use emojis sparingly but naturally
- NEVER diagnose, prescribe, or replace professional therapy
- If someone expresses suicidal ideation, immediately provide Indian crisis helplines: iCall 9152987821, Vandrevala Foundation 1860-2662-345
- Always respond in first person as Sage

Important: Keep responses short and supportive, not lecture-like."""

    api_messages = [{"role": "system", "content": system_prompt}]
    for m in messages_history[-8:]:
        role = m.get("role", "user")
        if role == "bot":
            role = "assistant"
        api_messages.append({"role": role, "content": m.get("content", "")})
    api_messages.append({"role": "user", "content": user_msg})

    payload = json.dumps({
        "model": "gpt-4o-mini",
        "max_tokens": 300,
        "temperature": 0.8,
        "messages": api_messages
    }).encode("utf-8")

    try:
        req = urllib.request.Request(
            "https://api.openai.com/v1/chat/completions",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {OPENAI_API_KEY}"
            },
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            return result["choices"][0]["message"]["content"].strip()
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="ignore")
        print(f"OpenAI HTTP Error {e.code}: {body}")
        return rule_based_reply(user_msg)
    except Exception as ex:
        print(f"OpenAI error: {ex}")
        return rule_based_reply(user_msg)

@app.route("/chat")
def chat_page():
    if "user" not in session:
        return redirect("/login")
    has_api = bool(OPENAI_API_KEY)
    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>MindSpace — AI Therapist</title>
<link href="https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700;800;900&family=Playfair+Display:wght@700&display=swap" rel="stylesheet">
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0;}
body{font-family:'Nunito',sans-serif;height:100vh;background:#0d0d1a;color:#fff;display:flex;flex-direction:column;overflow:hidden;position:relative;}
body::before{content:'';position:fixed;inset:0;background:radial-gradient(ellipse 80% 60% at 20% 40%,rgba(99,102,241,0.08) 0%,transparent 60%),radial-gradient(ellipse 60% 80% at 80% 20%,rgba(167,139,250,0.08) 0%,transparent 60%);pointer-events:none;z-index:0;}
.topnav{position:relative;z-index:10;display:flex;justify-content:space-between;align-items:center;padding:14px 24px;background:rgba(13,13,26,0.95);backdrop-filter:blur(16px);border-bottom:1px solid rgba(255,255,255,0.07);flex-shrink:0;}
.brand{font-family:'Playfair Display',serif;font-size:1.2rem;color:#fff;}
.nav-links a{color:rgba(255,255,255,0.5);text-decoration:none;font-size:0.82rem;font-weight:700;margin-left:12px;padding:6px 14px;border-radius:20px;border:1px solid rgba(255,255,255,0.1);transition:all 0.2s;}
.nav-links a:hover{color:#fff;background:rgba(255,255,255,0.08);}
.chat-header{position:relative;z-index:5;display:flex;align-items:center;gap:14px;padding:16px 24px;background:rgba(255,255,255,0.03);border-bottom:1px solid rgba(255,255,255,0.06);flex-shrink:0;}
.bot-avatar{width:46px;height:46px;border-radius:50%;background:linear-gradient(135deg,#6366f1,#a78bfa);display:flex;align-items:center;justify-content:center;font-size:1.4rem;flex-shrink:0;box-shadow:0 0 20px rgba(99,102,241,0.4);}
.bot-name{font-weight:800;font-size:1rem;}
.bot-status{font-size:0.75rem;color:rgba(255,255,255,0.4);display:flex;align-items:center;gap:6px;}
.status-dot{width:8px;height:8px;border-radius:50%;background:#34d399;animation:blink 2s ease-in-out infinite;}
@keyframes blink{0%,100%{opacity:1;}50%{opacity:0.4;}}
.ai-badge{display:inline-flex;align-items:center;gap:4px;padding:2px 8px;border-radius:99px;font-size:0.65rem;font-weight:800;background:rgba(99,102,241,0.2);border:1px solid rgba(99,102,241,0.4);color:#818cf8;margin-left:8px;}
.disclaimer{font-size:0.72rem;color:rgba(255,255,255,0.25);margin-left:auto;max-width:240px;text-align:right;line-height:1.4;}
.messages{flex:1;overflow-y:auto;padding:20px 20px 10px;display:flex;flex-direction:column;gap:14px;position:relative;z-index:2;}
.messages::-webkit-scrollbar{width:4px;}
.messages::-webkit-scrollbar-thumb{background:rgba(255,255,255,0.1);border-radius:99px;}
.msg{max-width:75%;display:flex;flex-direction:column;gap:4px;animation:msgIn 0.3s cubic-bezier(0.16,1,0.3,1);}
@keyframes msgIn{from{opacity:0;transform:translateY(10px);}to{opacity:1;transform:translateY(0);}}
.msg.bot{align-self:flex-start;}
.msg.user{align-self:flex-end;}
.bubble{padding:13px 17px;border-radius:18px;font-size:0.92rem;line-height:1.6;font-weight:600;}
.msg.bot .bubble{background:rgba(99,102,241,0.15);border:1px solid rgba(99,102,241,0.25);border-bottom-left-radius:4px;color:rgba(255,255,255,0.9);}
.msg.user .bubble{background:linear-gradient(135deg,rgba(92,200,245,0.2),rgba(167,139,250,0.2));border:1px solid rgba(167,139,250,0.3);border-bottom-right-radius:4px;color:#fff;}
.msg-time{font-size:0.7rem;color:rgba(255,255,255,0.25);padding:0 4px;}
.msg.user .msg-time{text-align:right;}
.typing-bubble{background:rgba(99,102,241,0.12);border:1px solid rgba(99,102,241,0.2);border-radius:18px;border-bottom-left-radius:4px;padding:14px 18px;display:inline-flex;gap:5px;align-items:center;}
.typing-dot{width:7px;height:7px;background:#a78bfa;border-radius:50%;animation:typingBounce 1.2s ease-in-out infinite;}
.typing-dot:nth-child(2){animation-delay:0.2s;}
.typing-dot:nth-child(3){animation-delay:0.4s;}
@keyframes typingBounce{0%,100%{transform:translateY(0);}50%{transform:translateY(-6px);}}
.quick-replies{display:flex;gap:8px;flex-wrap:wrap;padding:0 20px 10px;position:relative;z-index:2;}
.qr-btn{padding:7px 14px;border:1px solid rgba(255,255,255,0.12);border-radius:99px;background:rgba(255,255,255,0.04);color:rgba(255,255,255,0.6);font-family:'Nunito',sans-serif;font-size:0.78rem;font-weight:700;cursor:pointer;transition:all 0.2s;white-space:nowrap;}
.qr-btn:hover{background:rgba(99,102,241,0.15);border-color:rgba(99,102,241,0.4);color:#fff;}
.input-row{position:relative;z-index:5;display:flex;gap:10px;padding:14px 20px 20px;background:rgba(13,13,26,0.9);border-top:1px solid rgba(255,255,255,0.06);flex-shrink:0;}
.chat-input{flex:1;padding:13px 18px;background:rgba(255,255,255,0.06);border:1.5px solid rgba(255,255,255,0.1);border-radius:99px;color:#fff;font-family:'Nunito',sans-serif;font-size:0.92rem;outline:none;transition:border-color 0.3s;}
.chat-input:focus{border-color:rgba(99,102,241,0.5);}
.chat-input::placeholder{color:rgba(255,255,255,0.3);}
.send-btn{width:46px;height:46px;border-radius:50%;border:none;background:linear-gradient(135deg,#6366f1,#a78bfa);color:#fff;font-size:1.2rem;cursor:pointer;transition:transform 0.2s,box-shadow 0.2s;flex-shrink:0;display:flex;align-items:center;justify-content:center;}
.send-btn:hover{transform:scale(1.1);box-shadow:0 4px 16px rgba(99,102,241,0.4);}
.api-note{font-size:0.7rem;text-align:center;color:rgba(255,255,255,0.2);padding:4px 0 0;}
</style>
</head>
<body>
<nav class="topnav"><span class="brand">MindSpace 🌿</span><div class="nav-links"><a href="/">🏠 Home</a><a href="/emotion">🔍 Emotions</a><a href="/logout">👋 Logout</a></div></nav>
<div class="chat-header">
    <div class="bot-avatar">🤖</div>
    <div>
        <div class="bot-name">Sage — Your AI Companion{% if has_api %}<span class="ai-badge">✦ GPT-4o</span>{% endif %}</div>
        <div class="bot-status"><span class="status-dot"></span> Always here for you</div>
    </div>
    <div class="disclaimer">Not a substitute for professional therapy. For emergencies call iCall: 9152987821</div>
</div>
<div class="messages" id="messages"></div>
<div class="quick-replies" id="quickReplies">
    <button class="qr-btn" onclick="quickSend('I feel stressed today')">😓 I feel stressed</button>
    <button class="qr-btn" onclick="quickSend('I have anxiety')">😰 I have anxiety</button>
    <button class="qr-btn" onclick="quickSend('I feel sad and lonely')">😢 I feel sad</button>
    <button class="qr-btn" onclick="quickSend('I am angry about something')">😠 I feel angry</button>
    <button class="qr-btn" onclick="quickSend('I cannot sleep well')">😴 Sleep issues</button>
    <button class="qr-btn" onclick="quickSend('I need some help')">🙏 I need help</button>
</div>
{% if not has_api %}
<div class="api-note">⚠️ Set OPENAI_API_KEY env variable for full AI responses — using smart fallback now</div>
{% endif %}
<div class="input-row">
    <input class="chat-input" id="chatInput" placeholder="Share what's on your mind…" onkeydown="if(event.key==='Enter'&&!event.shiftKey){event.preventDefault();sendMsg();}">
    <button class="send-btn" onclick="sendMsg()">➤</button>
</div>
<script>
const messagesEl=document.getElementById('messages');
let chatHistory=[];
function nowTime(){const d=new Date();return d.getHours().toString().padStart(2,'0')+':'+d.getMinutes().toString().padStart(2,'0');}
function addMsg(text,role){
    const div=document.createElement('div');div.className='msg '+role;
    div.innerHTML=`<div class="bubble">${text.replace(/\\n/g,'<br>')}</div><div class="msg-time">${nowTime()}</div>`;
    messagesEl.appendChild(div);messagesEl.scrollTop=messagesEl.scrollHeight;
    chatHistory.push({role:role==='bot'?'assistant':'user',content:text});
}
function showTyping(){const div=document.createElement('div');div.className='msg bot';div.id='typing';div.innerHTML=`<div class="typing-bubble"><div class="typing-dot"></div><div class="typing-dot"></div><div class="typing-dot"></div></div>`;messagesEl.appendChild(div);messagesEl.scrollTop=messagesEl.scrollHeight;}
function removeTyping(){const t=document.getElementById('typing');if(t)t.remove();}
let isSending=false;
async function sendMsg(){
    if(isSending)return;
    const input=document.getElementById('chatInput');const text=input.value.trim();if(!text)return;
    isSending=true;input.value='';document.getElementById('quickReplies').style.display='none';
    addMsg(text,'user');showTyping();
    try{
        const res=await fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:text,history:chatHistory.slice(-12)})});
        const d=await res.json();removeTyping();addMsg(d.reply,'bot');
    }catch(e){removeTyping();addMsg('Sorry, I had trouble connecting. Please try again. 💙','bot');}
    isSending=false;
}
function quickSend(text){document.getElementById('chatInput').value=text;sendMsg();}
setTimeout(()=>{addMsg('Hello {{ session["user"] }} 💙 I\\'m Sage, your compassionate AI companion. This is a safe, judgement-free space. How are you feeling today?','bot');},400);
</script>
</body></html>
""", has_api=has_api)

@app.route("/api/chat", methods=["POST"])
def api_chat():
    if "user" not in session:
        return jsonify({"error": "Not logged in"}), 401
    data = request.get_json()
    msg = data.get("message","").strip()
    history = data.get("history", [])
    if not msg:
        return jsonify({"reply": "I'm here. What would you like to share? 💙"})
    reply = openai_chat_reply(history, msg)
    return jsonify({"reply": reply})

# ─────────────────────────────────────────────
# FEATURE 3 — MOOD TRACKER
# ─────────────────────────────────────────────

MOOD_META = {
    "Happy":   {"emoji":"😊","color":"#34d399","bg":"rgba(52,211,153,0.15)","border":"rgba(52,211,153,0.35)"},
    "Calm":    {"emoji":"😌","color":"#60a5fa","bg":"rgba(96,165,250,0.15)","border":"rgba(96,165,250,0.35)"},
    "Sad":     {"emoji":"😢","color":"#818cf8","bg":"rgba(129,140,248,0.15)","border":"rgba(129,140,248,0.35)"},
    "Angry":   {"emoji":"😠","color":"#f87171","bg":"rgba(248,113,113,0.15)","border":"rgba(248,113,113,0.35)"},
    "Stressed":{"emoji":"😰","color":"#fbbf24","bg":"rgba(251,191,36,0.15)","border":"rgba(251,191,36,0.35)"},
}

@app.route("/mood", methods=["GET","POST"])
def mood_page():
    if "user" not in session:
        return redirect("/login")
    saved = False
    if request.method == "POST":
        mood      = request.form.get("mood","")
        note      = request.form.get("note","").strip()[:300]
        intensity = int(request.form.get("intensity","3"))
        if mood in MOOD_META:
            conn = sqlite3.connect("app.db")
            cur  = conn.cursor()
            cur.execute("INSERT INTO mood_logs (username,mood,note,intensity) VALUES (?,?,?,?)", (session["user"], mood, note, intensity))
            conn.commit()
            conn.close()
            saved = True
    conn = sqlite3.connect("app.db")
    cur  = conn.cursor()
    cur.execute("""SELECT mood, intensity, note, date(logged_at) as d, strftime('%H:%M', logged_at) as tm
                   FROM mood_logs WHERE username=? ORDER BY id DESC LIMIT 60""", (session["user"],))
    rows = cur.fetchall()
    conn.close()
    today = datetime.date.today()
    week_labels = []
    week_data   = {m: [] for m in MOOD_META}
    for i in range(6,-1,-1):
        d = today - datetime.timedelta(days=i)
        week_labels.append(d.strftime("%a"))
        day_str = str(d)
        day_rows = [r for r in rows if r[3] == day_str]
        counts = {m: 0 for m in MOOD_META}
        for r in day_rows:
            if r[0] in counts:
                counts[r[0]] += 1
        for m in MOOD_META:
            week_data[m].append(counts[m])
    month_counts = {m: 0 for m in MOOD_META}
    for r in rows:
        if r[0] in month_counts:
            month_counts[r[0]] += 1
    recent = rows[:12]
    streak = 0
    for i in range(60):
        d = today - datetime.timedelta(days=i)
        if any(r[3] == str(d) for r in rows):
            streak += 1
        else:
            break

    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>MindSpace — Mood Tracker</title>
<link href="https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700;800;900&family=Playfair+Display:wght@700&display=swap" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0;}
body{font-family:'Nunito',sans-serif;min-height:100vh;background:#0d0d1a;color:#fff;padding:90px 16px 60px;position:relative;overflow-x:hidden;}
body::before{content:'';position:fixed;inset:0;background:radial-gradient(ellipse 80% 60% at 20% 40%,rgba(244,114,182,0.07) 0%,transparent 60%),radial-gradient(ellipse 60% 80% at 80% 20%,rgba(167,139,250,0.07) 0%,transparent 60%);pointer-events:none;animation:aurora 10s ease-in-out infinite alternate;}
@keyframes aurora{0%{transform:scale(1);}100%{transform:scale(1.06) rotate(-1deg);}}
.topnav{position:fixed;top:0;left:0;right:0;display:flex;justify-content:space-between;align-items:center;padding:14px 24px;background:rgba(13,13,26,0.85);backdrop-filter:blur(16px);border-bottom:1px solid rgba(255,255,255,0.07);z-index:100;}
.brand{font-family:'Playfair Display',serif;font-size:1.2rem;color:#fff;}
.nav-links a{color:rgba(255,255,255,0.5);text-decoration:none;font-size:0.82rem;font-weight:700;margin-left:12px;padding:6px 14px;border-radius:20px;border:1px solid rgba(255,255,255,0.1);transition:all 0.2s;}
.nav-links a:hover{color:#fff;background:rgba(255,255,255,0.08);}
.page-wrap{position:relative;z-index:1;max-width:700px;margin:0 auto;}
.page-title{font-family:'Playfair Display',serif;font-size:1.8rem;margin-bottom:4px;}
.page-sub{color:rgba(255,255,255,0.4);font-size:0.85rem;margin-bottom:24px;}
.stats-row{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-bottom:20px;}
.stat-card{background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.08);border-radius:18px;padding:16px;text-align:center;}
.stat-val{font-size:1.8rem;font-weight:900;background:linear-gradient(135deg,#f472b6,#a78bfa);-webkit-background-clip:text;-webkit-text-fill-color:transparent;}
.stat-lbl{font-size:0.72rem;color:rgba(255,255,255,0.4);margin-top:4px;font-weight:700;text-transform:uppercase;letter-spacing:0.5px;}
.log-card{background:rgba(255,255,255,0.04);backdrop-filter:blur(20px);border:1px solid rgba(255,255,255,0.09);border-radius:24px;padding:28px;margin-bottom:20px;}
.log-card h3{font-family:'Playfair Display',serif;font-size:1.2rem;margin-bottom:18px;}
.mood-grid{display:grid;grid-template-columns:repeat(5,1fr);gap:10px;margin-bottom:20px;}
.mood-btn{display:flex;flex-direction:column;align-items:center;gap:6px;padding:14px 8px;border-radius:16px;border:2px solid rgba(255,255,255,0.08);background:rgba(255,255,255,0.04);cursor:pointer;transition:all 0.25s;font-family:'Nunito',sans-serif;}
.mood-btn:hover{transform:translateY(-3px);}
.mood-btn.selected{border-width:2px;}
.mood-emoji{font-size:2rem;line-height:1;}
.mood-label{font-size:0.72rem;font-weight:800;color:rgba(255,255,255,0.6);}
.intensity-row{margin-bottom:16px;}
.intensity-label{font-size:0.82rem;font-weight:700;color:rgba(255,255,255,0.5);margin-bottom:8px;}
.intensity-track{display:flex;gap:8px;}
.int-btn{flex:1;padding:8px 4px;border-radius:10px;border:1.5px solid rgba(255,255,255,0.1);background:rgba(255,255,255,0.04);color:rgba(255,255,255,0.5);font-family:'Nunito',sans-serif;font-weight:800;font-size:0.82rem;cursor:pointer;transition:all 0.2s;text-align:center;}
.int-btn.active{background:linear-gradient(135deg,#f472b6,#a78bfa);border-color:transparent;color:#fff;}
.note-input{width:100%;padding:12px 16px;background:rgba(255,255,255,0.06);border:1.5px solid rgba(255,255,255,0.1);border-radius:14px;color:#fff;font-family:'Nunito',sans-serif;font-size:0.9rem;resize:none;outline:none;margin-bottom:14px;transition:border-color 0.3s;}
.note-input:focus{border-color:rgba(244,114,182,0.5);}
.note-input::placeholder{color:rgba(255,255,255,0.3);}
.save-btn{width:100%;padding:14px;border:none;border-radius:14px;font-family:'Nunito',sans-serif;font-weight:800;font-size:1rem;cursor:pointer;background:linear-gradient(135deg,#f472b6,#a78bfa);color:#fff;transition:transform 0.2s,box-shadow 0.2s;}
.save-btn:hover{transform:translateY(-2px);box-shadow:0 8px 24px rgba(244,114,182,0.3);}
.saved-toast{display:none;text-align:center;color:#34d399;font-weight:800;font-size:0.9rem;margin-top:10px;}
.chart-card{background:rgba(255,255,255,0.04);backdrop-filter:blur(20px);border:1px solid rgba(255,255,255,0.09);border-radius:24px;padding:24px;margin-bottom:20px;}
.chart-card h3{font-family:'Playfair Display',serif;font-size:1.1rem;margin-bottom:4px;}
.chart-sub{color:rgba(255,255,255,0.35);font-size:0.78rem;margin-bottom:18px;}
.chart-tabs{display:flex;gap:8px;margin-bottom:16px;}
.ctab{padding:6px 16px;border-radius:20px;border:1.5px solid rgba(255,255,255,0.1);background:transparent;color:rgba(255,255,255,0.4);font-family:'Nunito',sans-serif;font-weight:700;font-size:0.8rem;cursor:pointer;transition:all 0.2s;}
.ctab.active{background:rgba(244,114,182,0.15);border-color:rgba(244,114,182,0.4);color:#f472b6;}
.logs-list{display:flex;flex-direction:column;gap:10px;}
.log-entry{display:flex;align-items:center;gap:12px;padding:12px 16px;background:rgba(255,255,255,0.04);border-radius:14px;border:1px solid rgba(255,255,255,0.07);transition:transform 0.2s;}
.log-entry:hover{transform:translateX(4px);}
.log-mood-icon{font-size:1.6rem;flex-shrink:0;}
.log-info{flex:1;}
.log-mood-name{font-weight:800;font-size:0.9rem;}
.log-note{color:rgba(255,255,255,0.4);font-size:0.78rem;margin-top:2px;}
.log-date{font-size:0.72rem;color:rgba(255,255,255,0.3);text-align:right;flex-shrink:0;}
.intensity-pip{display:flex;gap:3px;margin-top:4px;}
.pip{width:8px;height:8px;border-radius:50%;}
.no-logs{text-align:center;padding:30px;color:rgba(255,255,255,0.3);font-size:0.9rem;}
.mood-insights{background:rgba(255,255,255,0.03);border-radius:14px;padding:16px;margin-top:12px;border:1px solid rgba(255,255,255,0.06);}
.insight-title{font-size:0.78rem;font-weight:800;color:rgba(255,255,255,0.4);text-transform:uppercase;letter-spacing:1px;margin-bottom:10px;}
.insight-item{display:flex;align-items:center;gap:8px;padding:6px 0;font-size:0.85rem;color:rgba(255,255,255,0.7);font-weight:600;}
</style>
</head>
<body>
<nav class="topnav"><span class="brand">MindSpace 🌿</span><div class="nav-links"><a href="/">🏠 Home</a><a href="/emotion">🔍 Emotions</a><a href="/chat">🤖 Chat</a><a href="/logout">👋 Logout</a></div></nav>
<div class="page-wrap">
    <h1 class="page-title">📅 Mood Tracker</h1>
    <p class="page-sub">Log how you feel each day and uncover emotional patterns over time</p>
    <div class="stats-row">
        <div class="stat-card"><div class="stat-val">{{ streak }}</div><div class="stat-lbl">🔥 Day Streak</div></div>
        <div class="stat-card"><div class="stat-val">{{ total_logs }}</div><div class="stat-lbl">📝 Total Logs</div></div>
        <div class="stat-card"><div class="stat-val">{{ dominant_mood_emoji }}</div><div class="stat-lbl">{{ dominant_mood_label }}</div></div>
    </div>
    <div class="log-card">
        <h3>How are you feeling right now?</h3>
        <form method="post" id="moodForm">
            <input type="hidden" name="mood" id="selectedMood" value="">
            <input type="hidden" name="intensity" id="selectedIntensity" value="3">
            <div class="mood-grid">
                {% for m, meta in mood_meta.items() %}
                <button type="button" class="mood-btn {% if saved and request.form.get('mood')==m %}selected{% endif %}"
                    onclick="selectMood('{{ m }}','{{ meta.color }}','{{ meta.bg }}','{{ meta.border }}')"
                    id="mbtn-{{ m }}"
                    style="{% if saved and request.form.get('mood')==m %}background:{{ meta.bg }};border-color:{{ meta.color }};{% endif %}">
                    <span class="mood-emoji">{{ meta.emoji }}</span>
                    <span class="mood-label">{{ m }}</span>
                </button>
                {% endfor %}
            </div>
            <div class="intensity-row">
                <div class="intensity-label">Intensity level</div>
                <div class="intensity-track">
                    <button type="button" class="int-btn" onclick="selectIntensity(1,this)">1 — Mild</button>
                    <button type="button" class="int-btn active" onclick="selectIntensity(2,this)">2</button>
                    <button type="button" class="int-btn" onclick="selectIntensity(3,this)">3 — Mid</button>
                    <button type="button" class="int-btn" onclick="selectIntensity(4,this)">4</button>
                    <button type="button" class="int-btn" onclick="selectIntensity(5,this)">5 — Strong</button>
                </div>
            </div>
            <textarea class="note-input" name="note" rows="2" placeholder="Optional: add a note about your day…">{{ request.form.get('note','') if saved else '' }}</textarea>
            <button type="submit" class="save-btn">💾 Save Today's Mood</button>
            {% if saved %}<div class="saved-toast" style="display:block;">✅ Mood logged successfully! Keep it up 🌟</div>{% endif %}
        </form>
    </div>
    <div class="chart-card">
        <h3>📊 Emotional Trends</h3>
        <p class="chart-sub">Visualise your mood patterns over time</p>
        <div class="chart-tabs">
            <button class="ctab active" onclick="showChart('weekly',this)">Weekly</button>
            <button class="ctab" onclick="showChart('monthly',this)">Monthly</button>
        </div>
        <div id="chartWeekly" style="position:relative;height:260px;">
            <canvas id="weekChart"></canvas>
        </div>
        <div id="chartMonthly" style="position:relative;height:260px;display:none;">
            <canvas id="monthChart"></canvas>
        </div>
        {% if total_logs > 0 %}
        <div class="mood-insights">
            <div class="insight-title">🔮 Your Mood Insights</div>
            {% for insight in insights %}
            <div class="insight-item">{{ insight }}</div>
            {% endfor %}
        </div>
        {% endif %}
    </div>
    <div class="chart-card">
        <h3>🗓️ Recent Entries</h3>
        <p class="chart-sub">Your last 12 mood logs</p>
        <div class="logs-list">
            {% if recent %}
                {% for row in recent %}
                {% set meta = mood_meta.get(row[0], {'emoji':'😐','color':'#94a3b8'}) %}
                <div class="log-entry">
                    <div class="log-mood-icon">{{ meta.emoji }}</div>
                    <div class="log-info">
                        <div class="log-mood-name" style="color:{{ meta.color }};">{{ row[0] }}<span style="color:rgba(255,255,255,0.3);font-size:0.75rem;font-weight:600;"> · intensity {{ row[1] }}</span></div>
                        {% if row[2] %}<div class="log-note">{{ row[2][:80] }}{% if row[2]|length > 80 %}…{% endif %}</div>{% endif %}
                        <div class="intensity-pip">{% for p in range(row[1]) %}<div class="pip" style="background:{{ meta.color }};opacity:0.8;"></div>{% endfor %}{% for p in range(5 - row[1]) %}<div class="pip" style="background:rgba(255,255,255,0.1);"></div>{% endfor %}</div>
                    </div>
                    <div class="log-date">{{ row[3] }}<br><span style="font-size:0.65rem;">{{ row[4] }}</span></div>
                </div>
                {% endfor %}
            {% else %}
                <div class="no-logs">🌱 No mood entries yet. Log your first mood above!</div>
            {% endif %}
        </div>
    </div>
</div>
<script>
const weekLabels={{ week_labels|tojson }};const weekData={{ week_data|tojson }};const monthCounts={{ month_counts|tojson }};
const MOOD_COLORS={Happy:'#34d399',Calm:'#60a5fa',Sad:'#818cf8',Angry:'#f87171',Stressed:'#fbbf24'};
const weekCtx=document.getElementById('weekChart').getContext('2d');
new Chart(weekCtx,{type:'bar',data:{labels:weekLabels,datasets:Object.entries(weekData).map(([mood,data])=>({label:mood,data:data,backgroundColor:MOOD_COLORS[mood]+'99',borderColor:MOOD_COLORS[mood],borderWidth:1,borderRadius:4}))},options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{display:true,position:'top',labels:{color:'rgba(255,255,255,0.5)',font:{family:'Nunito',size:11},boxWidth:10,padding:14}}},scales:{x:{stacked:true,grid:{color:'rgba(255,255,255,0.04)'},ticks:{color:'rgba(255,255,255,0.4)',font:{family:'Nunito',size:11}}},y:{stacked:true,grid:{color:'rgba(255,255,255,0.04)'},ticks:{color:'rgba(255,255,255,0.4)',font:{family:'Nunito',size:11},stepSize:1}}}}});
const monthCtx=document.getElementById('monthChart').getContext('2d');
const monthLabels=Object.keys(monthCounts),monthVals=Object.values(monthCounts),monthColors=monthLabels.map(m=>MOOD_COLORS[m]||'#888');
new Chart(monthCtx,{type:'doughnut',data:{labels:monthLabels,datasets:[{data:monthVals,backgroundColor:monthColors.map(c=>c+'bb'),borderColor:monthColors,borderWidth:2,hoverOffset:8}]},options:{responsive:true,maintainAspectRatio:false,cutout:'62%',plugins:{legend:{display:true,position:'right',labels:{color:'rgba(255,255,255,0.6)',font:{family:'Nunito',size:12},boxWidth:12,padding:12}}}}});
function showChart(view,btn){document.querySelectorAll('.ctab').forEach(b=>b.classList.remove('active'));btn.classList.add('active');document.getElementById('chartWeekly').style.display=view==='weekly'?'block':'none';document.getElementById('chartMonthly').style.display=view==='monthly'?'block':'none';}
function selectMood(mood,color,bg,border){document.getElementById('selectedMood').value=mood;document.querySelectorAll('.mood-btn').forEach(b=>{b.style.background='rgba(255,255,255,0.04)';b.style.borderColor='rgba(255,255,255,0.08)';b.classList.remove('selected');});const btn=document.getElementById('mbtn-'+mood);btn.style.background=bg;btn.style.borderColor=color;btn.classList.add('selected');}
function selectIntensity(val,btn){document.getElementById('selectedIntensity').value=val;document.querySelectorAll('.int-btn').forEach(b=>b.classList.remove('active'));btn.classList.add('active');}
{% if saved %}selectMood('{{ request.form.get("mood","") }}','{{ mood_meta.get(request.form.get("mood","Happy"), {"color":"#34d399"}).color }}','{{ mood_meta.get(request.form.get("mood","Happy"), {"bg":"rgba(52,211,153,0.15)"}).bg }}','{{ mood_meta.get(request.form.get("mood","Happy"), {"border":"rgba(52,211,153,0.35)"}).border }}');{% endif %}
</script>
</body></html>
""", mood_meta=MOOD_META, saved=saved, recent=recent,
     week_labels=week_labels, week_data=week_data, month_counts=month_counts,
     request=request, streak=streak,
     total_logs=len(rows),
     dominant_mood_emoji=MOOD_META.get(max(month_counts, key=month_counts.get, default="Happy"),{"emoji":"🌱"})["emoji"] if rows else "🌱",
     dominant_mood_label=("Most: " + max(month_counts, key=month_counts.get)) if rows else "No data yet",
     insights=_mood_insights(rows, month_counts, streak))

def _mood_insights(rows, month_counts, streak):
    insights = []
    if not rows:
        return ["Start logging your mood to get personalised insights!"]
    dominant = max(month_counts, key=month_counts.get)
    if dominant in ["Happy","Calm"]:
        insights.append(f"✨ You've been feeling {dominant.lower()} most often lately — great work!")
    elif dominant in ["Stressed","Angry"]:
        insights.append(f"💙 You've been feeling {dominant.lower()} frequently — consider trying a breathing exercise")
    elif dominant == "Sad":
        insights.append("🌿 You've had some sad days — reaching out to someone can help")
    if streak >= 7:
        insights.append(f"🔥 Amazing {streak}-day logging streak! Consistency builds self-awareness")
    elif streak >= 3:
        insights.append(f"⭐ {streak}-day streak — you're building a great habit!")
    total = len(rows)
    if total >= 10:
        insights.append(f"📊 {total} mood entries logged — you're gaining real emotional insight")
    return insights if insights else ["Keep logging to unlock personalised insights!"]

app.jinja_env.globals['_mood_insights'] = _mood_insights

# ─────────────────────────────────────────────
# GAMES PAGE — Chess with Computer Mode (Minimax AI)
# ─────────────────────────────────────────────

@app.route("/games")
def games():
    if "user" not in session:
        return redirect("/login")
    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>MindSpace — Mind Games</title>
<link href="https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700;800;900&family=Playfair+Display:wght@700&display=swap" rel="stylesheet">
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0;}
body{font-family:'Nunito',sans-serif;min-height:100vh;background:#0d0d1a;color:#fff;padding:90px 16px 40px;position:relative;overflow-x:hidden;}
body::before{content:'';position:fixed;inset:0;background:radial-gradient(ellipse 80% 60% at 20% 40%,rgba(100,200,255,0.1) 0%,transparent 60%),radial-gradient(ellipse 60% 80% at 80% 20%,rgba(180,120,255,0.1) 0%,transparent 60%);animation:aurora 10s ease-in-out infinite alternate;pointer-events:none;}
@keyframes aurora{0%{transform:scale(1);}100%{transform:scale(1.08) rotate(-2deg);}}
.topnav{position:fixed;top:0;left:0;right:0;display:flex;justify-content:space-between;align-items:center;padding:14px 24px;background:rgba(13,13,26,0.85);backdrop-filter:blur(16px);border-bottom:1px solid rgba(255,255,255,0.07);z-index:100;}
.brand{font-family:'Playfair Display',serif;font-size:1.2rem;color:#fff;}
.nav-links a{color:rgba(255,255,255,0.5);text-decoration:none;font-size:0.82rem;font-weight:700;margin-left:12px;padding:6px 14px;border-radius:20px;border:1px solid rgba(255,255,255,0.1);transition:all 0.2s;}
.nav-links a:hover{color:#fff;background:rgba(255,255,255,0.08);}
.page-wrap{position:relative;z-index:1;max-width:720px;margin:0 auto;}
.page-title{font-family:'Playfair Display',serif;font-size:1.8rem;margin-bottom:4px;}
.page-sub{color:rgba(255,255,255,0.4);font-size:0.85rem;margin-bottom:24px;}
.game-tabs{display:flex;gap:10px;margin-bottom:24px;background:rgba(255,255,255,0.04);padding:6px;border-radius:16px;border:1px solid rgba(255,255,255,0.08);}
.tab-btn{flex:1;padding:10px;border:none;border-radius:12px;font-family:'Nunito',sans-serif;font-weight:800;font-size:0.9rem;cursor:pointer;transition:all 0.25s;background:transparent;color:rgba(255,255,255,0.4);}
.tab-btn.active{background:linear-gradient(135deg,#5bc8f5,#a78bfa);color:#fff;box-shadow:0 4px 16px rgba(92,200,245,0.3);}
.game-panel{display:none;}.game-panel.active{display:block;}

/* SUDOKU */
.sudoku-wrap{display:flex;flex-direction:column;align-items:center;}
.sudoku-status{text-align:center;color:rgba(255,255,255,0.5);font-size:0.85rem;margin-bottom:14px;min-height:24px;}
.sudoku-outer{display:grid;grid-template-columns:repeat(3,1fr);gap:3px;background:rgba(92,200,245,0.5);border-radius:12px;padding:3px;max-width:378px;width:100%;}
.sudoku-box{display:grid;grid-template-columns:repeat(3,1fr);gap:1px;background:rgba(255,255,255,0.08);}
.sudoku-cell{background:#111827;aspect-ratio:1;display:flex;align-items:center;justify-content:center;font-size:1.05rem;font-weight:800;cursor:pointer;transition:background 0.15s;border:none;color:#fff;font-family:'Nunito',sans-serif;min-width:0;}
.sudoku-cell:hover{background:#1e293b;}
.sudoku-cell.given{color:#5bc8f5;cursor:default;}
.sudoku-cell.selected{background:#1e3a5f!important;}
.sudoku-cell.highlight{background:#1a2744;}
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

/* CHESS */
.chess-wrap{max-width:460px;margin:0 auto;}
.chess-mode-row{display:flex;gap:8px;justify-content:center;margin-bottom:12px;flex-wrap:wrap;}
.mode-btn{padding:8px 18px;border:1.5px solid rgba(255,255,255,0.12);border-radius:20px;background:transparent;color:rgba(255,255,255,0.5);font-family:'Nunito',sans-serif;font-weight:700;font-size:0.82rem;cursor:pointer;transition:all 0.2s;}
.mode-btn.active{background:linear-gradient(135deg,#5bc8f5,#a78bfa);border-color:transparent;color:#fff;}
.diff-ai-row{display:flex;gap:8px;justify-content:center;margin-bottom:12px;}
.chess-top{display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;}
.chess-player{display:flex;align-items:center;gap:8px;padding:8px 14px;background:rgba(255,255,255,0.05);border-radius:12px;border:1.5px solid rgba(255,255,255,0.08);font-weight:800;font-size:0.88rem;}
.chess-player.active-turn{border-color:rgba(92,200,245,0.5);background:rgba(92,200,245,0.08);}
.board-wrapper{position:relative;}
.rank-labels{position:absolute;left:-20px;top:0;height:100%;display:flex;flex-direction:column;justify-content:space-around;color:rgba(255,255,255,0.35);font-size:0.7rem;font-weight:700;}
.file-labels{display:flex;justify-content:space-around;padding:4px 0;color:rgba(255,255,255,0.35);font-size:0.7rem;font-weight:700;}
.chess-board{display:grid;grid-template-columns:repeat(8,1fr);border-radius:10px;overflow:hidden;border:2px solid rgba(255,255,255,0.12);}
.chess-sq{aspect-ratio:1;display:flex;align-items:center;justify-content:center;font-size:1.65rem;cursor:pointer;transition:all 0.12s;position:relative;user-select:none;}
.chess-sq.light{background:rgba(240,217,181,0.15);}
.chess-sq.dark{background:rgba(100,60,30,0.35);}
.chess-sq.selected{background:rgba(92,200,245,0.4)!important;}
.chess-sq.valid-move::after{content:'';position:absolute;width:32%;height:32%;border-radius:50%;background:rgba(92,200,245,0.55);pointer-events:none;}
.chess-sq.valid-capture{background:rgba(255,80,80,0.3)!important;}
.chess-sq.in-check{background:rgba(255,50,50,0.55)!important;}
.chess-sq.last-from{background:rgba(255,220,80,0.18)!important;}
.chess-sq.last-to{background:rgba(255,220,80,0.28)!important;}
.chess-sq.computer-thinking{animation:pulseCell 0.6s ease-in-out infinite;}
@keyframes pulseCell{0%,100%{opacity:1;}50%{opacity:0.5;}}
.chess-info-bar{display:flex;justify-content:space-between;align-items:center;padding:10px 14px;margin-top:10px;background:rgba(255,255,255,0.04);border-radius:12px;border:1px solid rgba(255,255,255,0.07);}
.chess-status{font-weight:700;font-size:0.85rem;color:rgba(255,255,255,0.6);}
.captured-row{display:flex;gap:4px;flex-wrap:wrap;min-height:24px;}
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
.thinking-indicator{text-align:center;padding:8px;color:#a78bfa;font-size:0.85rem;font-weight:700;display:none;}
.thinking-indicator.show{display:block;animation:pulse 1s ease-in-out infinite;}
@keyframes pulse{0%,100%{opacity:1;}50%{opacity:0.4;}}
</style>
</head>
<body>
<nav class="topnav"><span class="brand">MindSpace 🌿</span><div class="nav-links"><a href="/">🏠 Home</a><a href="/logout">👋 Logout</a></div></nav>
<div class="page-wrap">
    <h1 class="page-title">🎮 Mind Games</h1>
    <p class="page-sub">Sharpen your mind with these strategy games</p>
    <div class="game-tabs">
        <button class="tab-btn active" onclick="switchTab('sudoku',this)">🔢 Sudoku</button>
        <button class="tab-btn" onclick="switchTab('chess',this)">♟️ Chess</button>
    </div>

    <!-- SUDOKU -->
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

    <!-- CHESS -->
    <div class="game-panel" id="panel-chess">
        <div class="chess-wrap">
            <!-- Mode selector -->
            <div class="chess-mode-row">
                <button class="mode-btn active" id="modeHuman" onclick="setChessMode('human')">👥 Two Players</button>
                <button class="mode-btn" id="modeComp" onclick="setChessMode('computer')">🤖 vs Computer</button>
            </div>
            <!-- AI difficulty (shown in computer mode) -->
            <div class="diff-ai-row" id="aiDiffRow" style="display:none;">
                <button class="diff-btn active" id="aiEasy" onclick="setAIDiff(1,this)">🟢 Easy</button>
                <button class="diff-btn" id="aiMed" onclick="setAIDiff(2,this)">🟡 Medium</button>
                <button class="diff-btn" id="aiHard" onclick="setAIDiff(3,this)">🔴 Hard</button>
            </div>
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
            <div class="thinking-indicator" id="thinkingIndicator">🤖 Computer is thinking…</div>
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
// ═══════════════════════════════════════
// SUDOKU ENGINE
// ═══════════════════════════════════════
let sudokuPuzzle=[],sudokuSolution=[],selectedCell=-1,difficulty='easy';
let timerInterval=null,timerSeconds=0;
const PUZZLES={easy:[[5,3,0,0,7,0,0,0,0,6,0,0,1,9,5,0,0,0,0,9,8,0,0,0,0,6,0,8,0,0,0,6,0,0,0,3,4,0,0,8,0,3,0,0,1,7,0,0,0,2,0,0,0,6,0,6,0,0,0,0,2,8,0,0,0,0,4,1,9,0,0,5,0,0,0,0,8,0,0,7,9],[0,0,0,2,6,0,7,0,1,6,8,0,0,7,0,0,9,0,1,9,0,0,0,4,5,0,0,8,2,0,1,0,0,0,4,0,0,0,4,6,0,2,9,0,0,0,5,0,0,0,3,0,2,8,0,0,9,3,0,0,0,7,4,0,4,0,0,5,0,0,3,6,7,0,3,0,1,8,0,0,0]],medium:[[0,2,0,0,0,0,0,0,0,0,0,0,6,0,0,0,0,3,0,7,4,0,8,0,0,0,0,0,0,0,0,0,3,0,0,2,0,8,0,0,4,0,0,1,0,6,0,0,5,0,0,0,0,0,0,0,0,0,1,0,7,8,0,5,0,0,0,0,9,0,0,0,0,0,0,0,0,0,0,4,0],[0,0,0,0,0,0,2,0,0,0,8,0,0,3,0,0,7,0,0,0,3,6,0,0,0,8,0,0,1,0,0,0,0,0,0,0,0,0,8,5,0,0,0,0,6,0,0,0,0,0,4,0,0,0,0,2,0,0,0,3,9,0,0,0,4,0,0,8,0,0,2,0,0,0,5,0,0,0,0,0,0]],hard:[[8,0,0,0,0,0,0,0,0,0,0,3,6,0,0,0,0,0,0,7,0,0,9,0,2,0,0,0,5,0,0,0,7,0,0,0,0,0,0,0,4,5,7,0,0,0,0,0,1,0,0,0,3,0,0,0,1,0,0,0,0,6,8,0,0,8,5,0,0,0,1,0,0,9,0,0,0,0,4,0,0],[0,0,5,3,0,0,0,0,0,8,0,0,0,0,0,0,2,0,0,7,0,0,1,0,5,0,0,4,0,0,0,0,5,3,0,0,0,1,0,0,7,0,0,0,6,0,0,3,2,0,0,0,8,0,0,6,0,5,0,0,0,0,9,0,0,4,0,0,0,0,3,0,0,0,0,0,0,9,7,0,0]]};

function solveSudoku(b){const bd=[...b];function ok(b,r,c,n){for(let i=0;i<9;i++){if(b[r*9+i]===n||b[i*9+c]===n)return false;}const br=Math.floor(r/3)*3,bc=Math.floor(c/3)*3;for(let i=0;i<3;i++)for(let j=0;j<3;j++)if(b[(br+i)*9+(bc+j)]===n)return false;return true;}function solve(){const e=bd.indexOf(0);if(e===-1)return true;const r=Math.floor(e/9),c=e%9;for(let n=1;n<=9;n++){if(ok(bd,r,c,n)){bd[e]=n;if(solve())return true;bd[e]=0;}}return false;}solve();return bd;}
function setDiff(d,btn){difficulty=d;document.querySelectorAll('.diff-btn').forEach(b=>b.classList.remove('active'));btn.classList.add('active');newSudokuGame();}
let origPuzzle=[];
function updateTimer(){const m=String(Math.floor(timerSeconds/60)).padStart(2,'0'),s=String(timerSeconds%60).padStart(2,'0');document.getElementById('timerRow').textContent=`⏱ ${m}:${s}`;}
function newSudokuGame(){const pool=PUZZLES[difficulty];const base=pool[Math.floor(Math.random()*pool.length)];origPuzzle=[...base];sudokuPuzzle=[...base];sudokuSolution=solveSudoku([...base]);selectedCell=-1;clearInterval(timerInterval);timerSeconds=0;updateTimer();timerInterval=setInterval(()=>{timerSeconds++;updateTimer();},1000);renderSudoku();document.getElementById('sudokuStatus').textContent='Select a cell and type a number';document.getElementById('sudokuStatus').style.color='rgba(255,255,255,0.5)';}
function renderSudoku(){const outer=document.getElementById('sudokuOuter');outer.innerHTML='';for(let box=0;box<9;box++){const boxDiv=document.createElement('div');boxDiv.className='sudoku-box';const boxRow=Math.floor(box/3)*3,boxCol=(box%3)*3;for(let ri=0;ri<3;ri++)for(let ci=0;ci<3;ci++){const r=boxRow+ri,c=boxCol+ci,idx=r*9+c;const cell=document.createElement('button');cell.className='sudoku-cell';const isOrig=origPuzzle[idx]!==0;if(isOrig)cell.classList.add('given');if(idx===selectedCell)cell.classList.add('selected');else if(selectedCell>=0){const sr=Math.floor(selectedCell/9),sc=selectedCell%9;if(r===sr||c===sc||Math.floor(r/3)===Math.floor(sr/3)&&Math.floor(c/3)===Math.floor(sc/3))cell.classList.add('highlight');}cell.textContent=sudokuPuzzle[idx]||'';if(sudokuPuzzle[idx]!==0&&!isOrig&&sudokuPuzzle[idx]!==sudokuSolution[idx])cell.classList.add('error');cell.onclick=()=>{if(!isOrig){selectedCell=idx;renderSudoku();}};boxDiv.appendChild(cell);}outer.appendChild(boxDiv);}}
function enterNum(n){if(selectedCell===-1)return;if(origPuzzle[selectedCell]!==0)return;sudokuPuzzle[selectedCell]=n;renderSudoku();if(!sudokuPuzzle.includes(0)){const allOk=sudokuPuzzle.every((v,i)=>v===sudokuSolution[i]);if(allOk){clearInterval(timerInterval);const m=String(Math.floor(timerSeconds/60)).padStart(2,'0'),s=String(timerSeconds%60).padStart(2,'0');document.getElementById('sudokuStatus').textContent=`🎉 Solved in ${m}:${s}!`;document.getElementById('sudokuStatus').style.color='#6ee7b7';}}}
function clearCell(){if(selectedCell===-1||origPuzzle[selectedCell]!==0)return;sudokuPuzzle[selectedCell]=0;renderSudoku();}
function hintCell(){if(selectedCell===-1)return;if(origPuzzle[selectedCell]!==0)return;sudokuPuzzle[selectedCell]=sudokuSolution[selectedCell];renderSudoku();}
function checkSudoku(){let errors=0;sudokuPuzzle.forEach((v,i)=>{if(v!==0&&v!==sudokuSolution[i])errors++;});const status=document.getElementById('sudokuStatus');if(errors===0&&!sudokuPuzzle.includes(0)){clearInterval(timerInterval);status.textContent='🎉 Puzzle Complete!';status.style.color='#6ee7b7';}else if(errors>0){status.textContent=`❌ ${errors} error(s)`;status.style.color='#ff9a9a';}else{status.textContent='✅ Correct so far!';status.style.color='#6ee7b7';}}
document.addEventListener('keydown',e=>{if(document.getElementById('panel-sudoku').classList.contains('active')){const n=parseInt(e.key);if(n>=1&&n<=9)enterNum(n);else if(e.key==='Backspace'||e.key==='Delete')clearCell();}});

const np=document.getElementById('numpad');for(let n=1;n<=9;n++){const b=document.createElement('button');b.className='num-btn';b.textContent=n;b.onclick=()=>enterNum(n);np.appendChild(b);}
newSudokuGame();

// ═══════════════════════════════════════
// CHESS ENGINE — Full Minimax AI
// ═══════════════════════════════════════
const PIECES={wK:'♔',wQ:'♕',wR:'♖',wB:'♗',wN:'♘',wP:'♙',bK:'♚',bQ:'♛',bR:'♜',bB:'♝',bN:'♞',bP:'♟'};

// Piece values for evaluation
const PIECE_VALUES = {K:20000,Q:900,R:500,B:330,N:320,P:100};

// Piece-square tables for positional evaluation (from white's perspective, rank 0=black's back rank)
const PST = {
  P: [
     0,  0,  0,  0,  0,  0,  0,  0,
    50, 50, 50, 50, 50, 50, 50, 50,
    10, 10, 20, 30, 30, 20, 10, 10,
     5,  5, 10, 25, 25, 10,  5,  5,
     0,  0,  0, 20, 20,  0,  0,  0,
     5, -5,-10,  0,  0,-10, -5,  5,
     5, 10, 10,-20,-20, 10, 10,  5,
     0,  0,  0,  0,  0,  0,  0,  0
  ],
  N: [
    -50,-40,-30,-30,-30,-30,-40,-50,
    -40,-20,  0,  0,  0,  0,-20,-40,
    -30,  0, 10, 15, 15, 10,  0,-30,
    -30,  5, 15, 20, 20, 15,  5,-30,
    -30,  0, 15, 20, 20, 15,  0,-30,
    -30,  5, 10, 15, 15, 10,  5,-30,
    -40,-20,  0,  5,  5,  0,-20,-40,
    -50,-40,-30,-30,-30,-30,-40,-50
  ],
  B: [
    -20,-10,-10,-10,-10,-10,-10,-20,
    -10,  0,  0,  0,  0,  0,  0,-10,
    -10,  0,  5, 10, 10,  5,  0,-10,
    -10,  5,  5, 10, 10,  5,  5,-10,
    -10,  0, 10, 10, 10, 10,  0,-10,
    -10, 10, 10, 10, 10, 10, 10,-10,
    -10,  5,  0,  0,  0,  0,  5,-10,
    -20,-10,-10,-10,-10,-10,-10,-20
  ],
  R: [
     0,  0,  0,  0,  0,  0,  0,  0,
     5, 10, 10, 10, 10, 10, 10,  5,
    -5,  0,  0,  0,  0,  0,  0, -5,
    -5,  0,  0,  0,  0,  0,  0, -5,
    -5,  0,  0,  0,  0,  0,  0, -5,
    -5,  0,  0,  0,  0,  0,  0, -5,
    -5,  0,  0,  0,  0,  0,  0, -5,
     0,  0,  0,  5,  5,  0,  0,  0
  ],
  Q: [
    -20,-10,-10, -5, -5,-10,-10,-20,
    -10,  0,  0,  0,  0,  0,  0,-10,
    -10,  0,  5,  5,  5,  5,  0,-10,
     -5,  0,  5,  5,  5,  5,  0, -5,
      0,  0,  5,  5,  5,  5,  0, -5,
    -10,  5,  5,  5,  5,  5,  0,-10,
    -10,  0,  5,  0,  0,  0,  0,-10,
    -20,-10,-10, -5, -5,-10,-10,-20
  ],
  K: [
    -30,-40,-40,-50,-50,-40,-40,-30,
    -30,-40,-40,-50,-50,-40,-40,-30,
    -30,-40,-40,-50,-50,-40,-40,-30,
    -30,-40,-40,-50,-50,-40,-40,-30,
    -20,-30,-30,-40,-40,-30,-30,-20,
    -10,-20,-20,-20,-20,-20,-20,-10,
     20, 20,  0,  0,  0,  0, 20, 20,
     20, 30, 10,  0,  0, 10, 30, 20
  ]
};

let board=[],turn='w',selected=null,validMoves=[],gameOver=false;
let capturedWhite=[],capturedBlack=[],enPassantTarget=null;
let castlingRights={wK:true,wQ:true,bK:true,bQ:true};
let lastFrom=-1,lastTo=-1,moveList=[],pendingPromotion=null;
let chessMode='human'; // 'human' or 'computer'
let aiDepth=2;         // minimax depth (1=easy,2=medium,3=hard)
let computerThinking=false;

function sq(r,c){return r*8+c;}function rc(idx){return{r:Math.floor(idx/8),c:idx%8};}
function inBounds(r,c){return r>=0&&r<8&&c>=0&&c<8;}
function color(p){return p?p[0]:null;}function type(p){return p?p[1]:null;}

function setChessMode(mode){
    chessMode=mode;
    document.getElementById('modeHuman').classList.toggle('active',mode==='human');
    document.getElementById('modeComp').classList.toggle('active',mode==='computer');
    document.getElementById('aiDiffRow').style.display=mode==='computer'?'flex':'none';
    newChessGame();
}
function setAIDiff(d,btn){
    aiDepth=d;
    document.querySelectorAll('#aiDiffRow .diff-btn').forEach(b=>b.classList.remove('active'));
    btn.classList.add('active');
    newChessGame();
}

function initChess(){
    board=new Array(64).fill(null);
    const backRank=['R','N','B','Q','K','B','N','R'];
    for(let c=0;c<8;c++){board[sq(0,c)]='b'+backRank[c];board[sq(1,c)]='bP';board[sq(6,c)]='wP';board[sq(7,c)]='w'+backRank[c];}
    turn='w';selected=null;validMoves=[];gameOver=false;computerThinking=false;
    capturedWhite=[];capturedBlack=[];enPassantTarget=null;
    castlingRights={wK:true,wQ:true,bK:true,bQ:true};
    lastFrom=-1;lastTo=-1;moveList=[];pendingPromotion=null;
    renderChess();updateChessUI();
    document.getElementById('thinkingIndicator').classList.remove('show');
}

function findKing(col){return board.findIndex(p=>p===col+'K');}

function isAttacked(idx,byColor){
    const{r,c}=rc(idx);const pDir=byColor==='w'?1:-1;
    for(const dc of[-1,1]){const ar=r+pDir,ac=c+dc;if(inBounds(ar,ac)&&board[sq(ar,ac)]===byColor+'P')return true;}
    for(const[dr,dc]of[[-2,-1],[-2,1],[-1,-2],[-1,2],[1,-2],[1,2],[2,-1],[2,1]]){const nr=r+dr,nc=c+dc;if(inBounds(nr,nc)&&board[sq(nr,nc)]===byColor+'N')return true;}
    for(const[dr,dc]of[[-1,-1],[-1,0],[-1,1],[0,-1],[0,1],[1,-1],[1,0],[1,1]]){const nr=r+dr,nc=c+dc;if(inBounds(nr,nc)&&board[sq(nr,nc)]===byColor+'K')return true;}
    for(const[dr,dc]of[[1,0],[-1,0],[0,1],[0,-1]]){let nr=r+dr,nc=c+dc;while(inBounds(nr,nc)){const p=board[sq(nr,nc)];if(p){if(color(p)===byColor&&(type(p)==='R'||type(p)==='Q'))return true;break;}nr+=dr;nc+=dc;}}
    for(const[dr,dc]of[[1,1],[1,-1],[-1,1],[-1,-1]]){let nr=r+dr,nc=c+dc;while(inBounds(nr,nc)){const p=board[sq(nr,nc)];if(p){if(color(p)===byColor&&(type(p)==='B'||type(p)==='Q'))return true;break;}nr+=dr;nc+=dc;}}
    return false;
}
function isInCheck(col){return isAttacked(findKing(col),col==='w'?'b':'w');}

function getPseudoMoves(fromIdx,boardState,epTarget){
    const p=boardState[fromIdx];if(!p)return[];
    const col=color(p),tp=type(p);
    const{r,c}=rc(fromIdx);const opp=col==='w'?'b':'w';
    const pseudo=[];
    const addIf=(r2,c2)=>{if(inBounds(r2,c2)&&color(boardState[sq(r2,c2)])!==col)pseudo.push(sq(r2,c2));};
    const slide=(dr,dc)=>{let nr=r+dr,nc=c+dc;while(inBounds(nr,nc)){const t2=boardState[sq(nr,nc)];if(!t2)pseudo.push(sq(nr,nc));else{if(color(t2)===opp)pseudo.push(sq(nr,nc));break;}nr+=dr;nc+=dc;}};
    if(tp==='P'){const dir=col==='w'?-1:1;const startRow=col==='w'?6:1;if(inBounds(r+dir,c)&&!boardState[sq(r+dir,c)]){pseudo.push(sq(r+dir,c));if(r===startRow&&!boardState[sq(r+2*dir,c)])pseudo.push(sq(r+2*dir,c));}for(const dc of[-1,1]){const nr=r+dir,nc=c+dc;if(inBounds(nr,nc)){if(color(boardState[sq(nr,nc)])===opp)pseudo.push(sq(nr,nc));if(epTarget!==null&&sq(nr,nc)===epTarget)pseudo.push(sq(nr,nc));}}}
    else if(tp==='N'){[[-2,-1],[-2,1],[-1,-2],[-1,2],[1,-2],[1,2],[2,-1],[2,1]].forEach(([dr,dc])=>addIf(r+dr,c+dc));}
    else if(tp==='R'){slide(1,0);slide(-1,0);slide(0,1);slide(0,-1);}
    else if(tp==='B'){slide(1,1);slide(1,-1);slide(-1,1);slide(-1,-1);}
    else if(tp==='Q'){slide(1,0);slide(-1,0);slide(0,1);slide(0,-1);slide(1,1);slide(1,-1);slide(-1,1);slide(-1,-1);}
    else if(tp==='K'){[[-1,-1],[-1,0],[-1,1],[0,-1],[0,1],[1,-1],[1,0],[1,1]].forEach(([dr,dc])=>addIf(r+dr,c+dc));}
    return pseudo;
}

function getLegalMoves(fromIdx,boardState,epTarget,castR){
    boardState=boardState||board;epTarget=epTarget!==undefined?epTarget:enPassantTarget;castR=castR||castlingRights;
    const p=boardState[fromIdx];if(!p)return[];
    const col=color(p),tp=type(p);const{r,c}=rc(fromIdx);const opp=col==='w'?'b':'w';
    let pseudo=getPseudoMoves(fromIdx,boardState,epTarget);
    // Castling
    if(tp==='K'){
        const row=col==='w'?7:0;
        if(r===row&&c===4){
            const inChk=isAttackedBoard(sq(row,4),opp,boardState);
            if(!inChk){
                if(castR[col+'K']&&!boardState[sq(row,5)]&&!boardState[sq(row,6)]&&!isAttackedBoard(sq(row,5),opp,boardState)&&!isAttackedBoard(sq(row,6),opp,boardState))pseudo.push(sq(row,6));
                if(castR[col+'Q']&&!boardState[sq(row,3)]&&!boardState[sq(row,2)]&&!boardState[sq(row,1)]&&!isAttackedBoard(sq(row,3),opp,boardState)&&!isAttackedBoard(sq(row,2),opp,boardState))pseudo.push(sq(row,2));
            }
        }
    }
    return pseudo.filter(to=>{
        const testBoard=[...boardState];
        const{r:fr,c:fc}=rc(fromIdx);const{r:tr,c:tc}=rc(to);
        // En passant capture
        if(tp==='P'&&to===epTarget){testBoard[sq(fr,tc)]=null;}
        testBoard[to]=p;testBoard[fromIdx]=null;
        // Castling rook
        if(tp==='K'){const dc2=tc-fc;if(Math.abs(dc2)===2){const row2=col==='w'?7:0;if(dc2>0){testBoard[sq(row2,5)]=col+'R';testBoard[sq(row2,7)]=null;}else{testBoard[sq(row2,3)]=col+'R';testBoard[sq(row2,0)]=null;}}}
        const kIdx=testBoard.findIndex(x=>x===col+'K');
        return kIdx>=0&&!isAttackedBoard(kIdx,opp,testBoard);
    });
}

function isAttackedBoard(idx,byColor,boardState){
    const{r,c}=rc(idx);const pDir=byColor==='w'?1:-1;
    for(const dc of[-1,1]){const ar=r+pDir,ac=c+dc;if(inBounds(ar,ac)&&boardState[sq(ar,ac)]===byColor+'P')return true;}
    for(const[dr,dc]of[[-2,-1],[-2,1],[-1,-2],[-1,2],[1,-2],[1,2],[2,-1],[2,1]]){const nr=r+dr,nc=c+dc;if(inBounds(nr,nc)&&boardState[sq(nr,nc)]===byColor+'N')return true;}
    for(const[dr,dc]of[[-1,-1],[-1,0],[-1,1],[0,-1],[0,1],[1,-1],[1,0],[1,1]]){const nr=r+dr,nc=c+dc;if(inBounds(nr,nc)&&boardState[sq(nr,nc)]===byColor+'K')return true;}
    for(const[dr,dc]of[[1,0],[-1,0],[0,1],[0,-1]]){let nr=r+dr,nc=c+dc;while(inBounds(nr,nc)){const p=boardState[sq(nr,nc)];if(p){if(color(p)===byColor&&(type(p)==='R'||type(p)==='Q'))return true;break;}nr+=dr;nc+=dc;}}
    for(const[dr,dc]of[[1,1],[1,-1],[-1,1],[-1,-1]]){let nr=r+dr,nc=c+dc;while(inBounds(nr,nc)){const p=boardState[sq(nr,nc)];if(p){if(color(p)===byColor&&(type(p)==='B'||type(p)==='Q'))return true;break;}nr+=dr;nc+=dc;}}
    return false;
}

function isInCheckBoard(col,boardState){const kIdx=boardState.findIndex(p=>p===col+'K');return kIdx>=0&&isAttackedBoard(kIdx,col==='w'?'b':'w',boardState);}

// ── AI Evaluation ──────────────────────────────────────────────
function evaluateBoard(boardState){
    let score=0;
    for(let i=0;i<64;i++){
        const p=boardState[i];if(!p)continue;
        const col=color(p),tp=type(p);
        const{r,c}=rc(i);
        const baseVal=PIECE_VALUES[tp]||0;
        // PST index: white uses rank from bottom (row 7=rank1), black uses rank from top
        const pstIdx=col==='w'?i:((7-Math.floor(i/8))*8+(i%8));
        const pstVal=(PST[tp]?PST[tp][pstIdx]:0);
        const pieceScore=baseVal+pstVal;
        score+=(col==='w'?pieceScore:-pieceScore);
    }
    return score;
}

function getAllMovesForColor(col,boardState,epTarget,castR){
    const moves=[];
    for(let i=0;i<64;i++){
        if(boardState[i]&&color(boardState[i])===col){
            const lm=getLegalMoves(i,boardState,epTarget,castR);
            lm.forEach(to=>moves.push({from:i,to}));
        }
    }
    return moves;
}

function applyMoveToBoard(boardState,from,to,epTarget,castR){
    const newBoard=[...boardState];
    const p=newBoard[from];
    const col=color(p),tp=type(p);
    const{r:fr,c:fc}=rc(from);const{r:tr,c:tc}=rc(to);
    const newCastR={...castR};let newEP=null;
    // En passant
    if(tp==='P'&&to===epTarget){newBoard[sq(fr,tc)]=null;}
    newBoard[to]=p;newBoard[from]=null;
    // Promotion (auto-queen for AI)
    if(tp==='P'&&(tr===0||tr===7)){newBoard[to]=col+'Q';}
    // Castling rook
    if(tp==='K'){const dc2=tc-fc;if(Math.abs(dc2)===2){const row2=col==='w'?7:0;if(dc2>0){newBoard[sq(row2,5)]=col+'R';newBoard[sq(row2,7)]=null;}else{newBoard[sq(row2,3)]=col+'R';newBoard[sq(row2,0)]=null;}}newCastR[col+'K']=false;newCastR[col+'Q']=false;}
    if(tp==='R'){if(fc===0)newCastR[col+'Q']=false;if(fc===7)newCastR[col+'K']=false;}
    if(tp==='P'&&Math.abs(tr-fr)===2)newEP=sq((fr+tr)/2,fc);
    return{board:newBoard,ep:newEP,castR:newCastR};
}

function minimax(boardState,depth,alpha,beta,maximizing,epTarget,castR){
    const col=maximizing?'w':'b';
    const moves=getAllMovesForColor(col,boardState,epTarget,castR);
    if(moves.length===0){
        if(isInCheckBoard(col,boardState))return maximizing?-100000:100000;
        return 0;
    }
    if(depth===0)return evaluateBoard(boardState);
    if(maximizing){
        let best=-Infinity;
        for(const mv of moves){
            const{board:nb,ep:ne,castR:nc}=applyMoveToBoard(boardState,mv.from,mv.to,epTarget,castR);
            const val=minimax(nb,depth-1,alpha,beta,false,ne,nc);
            best=Math.max(best,val);alpha=Math.max(alpha,best);
            if(beta<=alpha)break;
        }
        return best;
    }else{
        let best=Infinity;
        for(const mv of moves){
            const{board:nb,ep:ne,castR:nc}=applyMoveToBoard(boardState,mv.from,mv.to,epTarget,castR);
            const val=minimax(nb,depth-1,alpha,beta,true,ne,nc);
            best=Math.min(best,val);beta=Math.min(beta,best);
            if(beta<=alpha)break;
        }
        return best;
    }
}

function getBestMove(){
    // Computer always plays black
    const moves=getAllMovesForColor('b',board,enPassantTarget,castlingRights);
    if(!moves.length)return null;
    let bestMove=null,bestVal=Infinity;
    // Shuffle for variety at same score
    moves.sort(()=>Math.random()-0.5);
    for(const mv of moves){
        const{board:nb,ep:ne,castR:nc}=applyMoveToBoard(board,mv.from,mv.to,enPassantTarget,castlingRights);
        const val=minimax(nb,aiDepth-1,-Infinity,Infinity,true,ne,nc);
        if(val<bestVal){bestVal=val;bestMove=mv;}
    }
    return bestMove;
}

function applyMove(from,to){
    const p=board[from],col=color(p),tp=type(p);
    const{r:fr,c:fc}=rc(from);const{r:tr,c:tc}=rc(to);
    const captured=board[to];
    if(tp==='P'&&to===enPassantTarget){const epIdx=sq(fr,tc);if(board[epIdx]){(col==='w'?capturedBlack:capturedWhite).push(board[epIdx]);board[epIdx]=null;}}
    else if(captured){(col==='w'?capturedBlack:capturedWhite).push(captured);}
    board[to]=p;board[from]=null;
    if(tp==='K'){const dc2=tc-fc;if(dc2===2){board[sq(tr,5)]=col+'R';board[sq(tr,7)]=null;}else if(dc2===-2){board[sq(tr,3)]=col+'R';board[sq(tr,0)]=null;}}
    if(tp==='K'){castlingRights[col+'K']=false;castlingRights[col+'Q']=false;}
    if(tp==='R'){if(fc===0)castlingRights[col+'Q']=false;if(fc===7)castlingRights[col+'K']=false;}
    enPassantTarget=null;
    if(tp==='P'&&Math.abs(tr-fr)===2)enPassantTarget=sq((fr+tr)/2,fc);
    lastFrom=from;lastTo=to;
    const notation=getNotation(p,from,to);moveList.push({col,notation});
    turn=turn==='w'?'b':'w';
    if(tp==='P'&&(tr===0||tr===7)){pendingPromotion={from,to};showPromotion(col);}
    else finishMove();
}

function finishMove(){
    renderChess();updateChessUI();updateMoveHistory();
    // Computer move trigger
    if(!gameOver&&chessMode==='computer'&&turn==='b'&&!pendingPromotion){
        triggerComputerMove();
    }
}

function triggerComputerMove(){
    if(computerThinking)return;
    computerThinking=true;
    document.getElementById('thinkingIndicator').classList.add('show');
    document.getElementById('chessStatus').textContent='🤖 Computer is thinking…';
    setTimeout(()=>{
        const mv=getBestMove();
        document.getElementById('thinkingIndicator').classList.remove('show');
        computerThinking=false;
        if(mv){applyMove(mv.from,mv.to);}
        else{gameOver=true;renderChess();updateChessUI();}
    },150);
}

function getNotation(p,from,to){
    const files='abcdefgh';const{r:fr,c:fc}=rc(from);const{r:tr,c:tc}=rc(to);const tp=type(p);
    if(tp==='K'&&Math.abs(tc-fc)===2)return tc>fc?'O-O':'O-O-O';
    return(tp!=='P'?tp:'')+files[fc]+(8-fr)+files[tc]+(8-tr);
}

function showPromotion(col){
    const modal=document.getElementById('promoModal');modal.classList.add('show');
    const choices=document.getElementById('promoChoices');choices.innerHTML='';
    ['Q','R','B','N'].forEach(t=>{
        const btn=document.createElement('button');btn.className='promo-btn';btn.textContent=PIECES[col+t];
        btn.onclick=()=>{board[pendingPromotion.to]=col+t;pendingPromotion=null;modal.classList.remove('show');finishMove();};
        choices.appendChild(btn);
    });
}

function handleChessClick(idx){
    if(gameOver||computerThinking)return;
    if(chessMode==='computer'&&turn==='b')return; // computer's turn
    if(selected!==null){
        if(validMoves.includes(idx)){applyMove(selected,idx);selected=null;validMoves=[];return;}
        selected=null;validMoves=[];
    }
    const p=board[idx];
    if(p&&color(p)===turn){selected=idx;validMoves=getLegalMoves(idx);}
    renderChess();
}

function renderChess(){
    const b=document.getElementById('chessBoard');b.innerHTML='';
    for(let r=0;r<8;r++)for(let c=0;c<8;c++){
        const idx=sq(r,c);const sqEl=document.createElement('div');
        sqEl.className='chess-sq '+((r+c)%2===0?'light':'dark');
        if(selected===idx)sqEl.classList.add('selected');
        if(validMoves.includes(idx)){if(board[idx])sqEl.classList.add('valid-capture');else sqEl.classList.add('valid-move');}
        if(idx===lastFrom)sqEl.classList.add('last-from');
        if(idx===lastTo)sqEl.classList.add('last-to');
        if(board[idx]&&type(board[idx])==='K'&&isInCheckBoard(color(board[idx]),board))sqEl.classList.add('in-check');
        if(board[idx])sqEl.textContent=PIECES[board[idx]]||board[idx];
        sqEl.onclick=()=>handleChessClick(idx);
        b.appendChild(sqEl);
    }
    document.getElementById('capturedByBlack').innerHTML=capturedBlack.map(p=>`<span style="font-size:1.1rem;opacity:0.7">${PIECES[p]||p}</span>`).join('');
    document.getElementById('capturedByWhite').innerHTML=capturedWhite.map(p=>`<span style="font-size:1.1rem;opacity:0.7">${PIECES[p]||p}</span>`).join('');
}

function getLegalMovesForColor(col,boardState,epTarget,castR){
    let all=[];
    for(let i=0;i<64;i++){if(boardState[i]&&color(boardState[i])===col)all=all.concat(getLegalMoves(i,boardState,epTarget,castR));}
    return all;
}

function updateChessUI(){
    const inCheckW=isInCheckBoard('w',board),inCheckB=isInCheckBoard('b',board);
    const legalW=getLegalMovesForColor('w',board,enPassantTarget,castlingRights).length;
    const legalB=getLegalMovesForColor('b',board,enPassantTarget,castlingRights).length;
    document.getElementById('whitePlayer').classList.toggle('active-turn',turn==='w');
    document.getElementById('blackPlayer').classList.toggle('active-turn',turn==='b');
    let status='';
    if(turn==='w'&&legalW===0){gameOver=true;status=inCheckW?'Checkmate — Black wins! 🏆':'Stalemate — Draw!';}
    else if(turn==='b'&&legalB===0){gameOver=true;status=inCheckB?'Checkmate — White wins! 🏆':'Stalemate — Draw!';}
    else if(inCheckW||inCheckB){status=(inCheckW?'White':'Black')+' is in check!';}
    else{
        if(chessMode==='computer'){status=turn==='w'?'Your turn (White)':'Computer thinking…';}
        else{status=turn==='w'?'White to move':'Black to move';}
    }
    if(!computerThinking||gameOver)document.getElementById('chessStatus').textContent=status;
}

function updateMoveHistory(){
    const wrap=document.getElementById('moveHistoryWrap');
    if(moveList.length===0){wrap.style.display='none';return;}
    wrap.style.display='block';
    const mh=document.getElementById('moveHistory');mh.innerHTML='';
    for(let i=0;i<moveList.length;i+=2){
        const n=i/2+1;const wm=moveList[i],bm=moveList[i+1];
        mh.innerHTML+=`<div class="move-entry white"><span style="color:rgba(255,255,255,0.3);font-size:0.7rem;">${n}.</span> ${wm.notation}</div><div class="move-entry">${bm?bm.notation:''}</div>`;
    }
    wrap.scrollTop=wrap.scrollHeight;
}

function newChessGame(){initChess();}

// Board labels
document.getElementById('rankLabels').innerHTML=['8','7','6','5','4','3','2','1'].map(r=>`<span>${r}</span>`).join('');
document.getElementById('chessFiles').innerHTML=['a','b','c','d','e','f','g','h'].map(f=>`<span>${f}</span>`).join('');
initChess();

function switchTab(tab,btn){
    document.querySelectorAll('.tab-btn').forEach(b=>b.classList.remove('active'));
    document.querySelectorAll('.game-panel').forEach(p=>p.classList.remove('active'));
    btn.classList.add('active');
    document.getElementById('panel-'+tab).classList.add('active');
}
</script>
</body></html>
""")

# ─────────────────────────────────────────────
# PUZZLE PAGE
# ─────────────────────────────────────────────

@app.route("/puzzle")
def puzzle():
    if "user" not in session:
        return redirect("/login")
    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>MindSpace — Brain Puzzles</title>
<link href="https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700;800;900&family=Playfair+Display:wght@700&display=swap" rel="stylesheet">
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0;}
body{font-family:'Nunito',sans-serif;min-height:100vh;background:#0d0d1a;color:#fff;padding:90px 16px 40px;position:relative;overflow-x:hidden;}
body::before{content:'';position:fixed;inset:0;background:radial-gradient(ellipse 80% 60% at 20% 40%,rgba(249,168,212,0.08) 0%,transparent 60%),radial-gradient(ellipse 60% 80% at 80% 20%,rgba(167,139,250,0.08) 0%,transparent 60%);pointer-events:none;}
.topnav{position:fixed;top:0;left:0;right:0;display:flex;justify-content:space-between;align-items:center;padding:14px 24px;background:rgba(13,13,26,0.85);backdrop-filter:blur(16px);border-bottom:1px solid rgba(255,255,255,0.07);z-index:100;}
.brand{font-family:'Playfair Display',serif;font-size:1.2rem;color:#fff;}
.nav-links a{color:rgba(255,255,255,0.5);text-decoration:none;font-size:0.82rem;font-weight:700;margin-left:12px;padding:6px 14px;border-radius:20px;border:1px solid rgba(255,255,255,0.1);transition:all 0.2s;}
.nav-links a:hover{color:#fff;background:rgba(255,255,255,0.08);}
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
.memory-info{display:flex;justify-content:space-between;align-items:center;margin-bottom:14px;flex-wrap:wrap;gap:8px;}
.memory-stat{background:rgba(255,255,255,0.05);border:1px solid rgba(255,255,255,0.08);border-radius:12px;padding:8px 16px;font-weight:800;font-size:0.88rem;}
.memory-grid{display:grid;gap:10px;margin-bottom:16px;}
.mem-card{aspect-ratio:1;background:rgba(249,168,212,0.1);border:2px solid rgba(249,168,212,0.2);border-radius:14px;display:flex;align-items:center;justify-content:center;font-size:2rem;cursor:pointer;transition:all 0.3s;user-select:none;}
.mem-card.flipped,.mem-card.matched{background:rgba(249,168,212,0.2);border-color:rgba(249,168,212,0.5);}
.mem-card.matched{background:rgba(110,231,183,0.15);border-color:rgba(110,231,183,0.4);cursor:default;}
.mem-card:not(.flipped):not(.matched) span{opacity:0;}
.mem-card:hover:not(.flipped):not(.matched){background:rgba(249,168,212,0.15);transform:scale(1.04);}
.memory-actions{display:flex;gap:10px;align-items:center;}
.word-wrap{text-align:center;}
.scrambled-word{font-size:3rem;font-weight:900;letter-spacing:8px;color:#f9a8d4;margin:24px 0;font-family:'Playfair Display',serif;}
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
</style>
</head>
<body>
<nav class="topnav"><span class="brand">MindSpace 🌿</span><div class="nav-links"><a href="/">🏠 Home</a><a href="/logout">👋 Logout</a></div></nav>
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
const WORDS=[{w:'HAPPY',h:'Feeling joyful'},{w:'CALM',h:'Peaceful state'},{w:'BREATHE',h:'Inhale and exhale'},{w:'MINDFUL',h:'Being present'},{w:'BALANCE',h:'Equilibrium'},{w:'SERENE',h:'Tranquil and calm'},{w:'FOCUS',h:'Concentrate'},{w:'ENERGY',h:'Vitality'},{w:'PEACE',h:'Inner harmony'},{w:'STRENGTH',h:'Power'},{w:'YOGA',h:'Mind-body practice'},{w:'RELAX',h:'Ease tension'},{w:'HEALTH',h:'State of well-being'},{w:'SLEEP',h:'Rest and recovery'},{w:'WATER',h:'Essential hydration'},{w:'SMILE',h:'Facial expression of happiness'},{w:'GRATITUDE',h:'Feeling thankful'},{w:'COURAGE',h:'Bravery'},{w:'WISDOM',h:'Deep understanding'},{w:'KINDNESS',h:'Being considerate'}];
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
</script>
</body></html>
""")

# ─────────────────────────────────────────────
# ACTIVITY PAGE
# ─────────────────────────────────────────────

@app.route("/activity")
def activity():
    if "user" not in session:
        return redirect("/login")
    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>MindSpace — Physical Activity</title>
<link href="https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700;800;900&family=Playfair+Display:wght@700&display=swap" rel="stylesheet">
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0;}
body{font-family:'Nunito',sans-serif;min-height:100vh;background:#0d0d1a;color:#fff;padding:90px 16px 60px;position:relative;overflow-x:hidden;}
body::before{content:'';position:fixed;inset:0;background:radial-gradient(ellipse 80% 60% at 20% 40%,rgba(52,211,153,0.07) 0%,transparent 60%),radial-gradient(ellipse 60% 80% at 80% 20%,rgba(92,200,245,0.07) 0%,transparent 60%);pointer-events:none;}
.topnav{position:fixed;top:0;left:0;right:0;display:flex;justify-content:space-between;align-items:center;padding:14px 24px;background:rgba(13,13,26,0.85);backdrop-filter:blur(16px);border-bottom:1px solid rgba(255,255,255,0.07);z-index:100;}
.brand{font-family:'Playfair Display',serif;font-size:1.2rem;color:#fff;}
.nav-links a{color:rgba(255,255,255,0.5);text-decoration:none;font-size:0.82rem;font-weight:700;margin-left:12px;padding:6px 14px;border-radius:20px;border:1px solid rgba(255,255,255,0.1);transition:all 0.2s;}
.nav-links a:hover{color:#fff;background:rgba(255,255,255,0.08);}
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
.pose-icon{font-size:2.8rem;margin-bottom:10px;line-height:1;}
.pose-name{font-weight:800;font-size:0.95rem;margin-bottom:4px;}
.pose-duration{color:rgba(255,255,255,0.4);font-size:0.75rem;margin-bottom:8px;}
.pose-benefit{display:inline-block;padding:3px 10px;border-radius:99px;font-size:0.72rem;font-weight:700;margin-top:4px;}
.tag-yoga{background:rgba(52,211,153,0.15);color:#34d399;}
.tag-stretch{background:rgba(92,200,245,0.15);color:#5bc8f5;}
.tag-strength{background:rgba(167,139,250,0.15);color:#a78bfa;}
.pose-modal{display:none;position:fixed;inset:0;background:rgba(0,0,0,0.75);z-index:500;align-items:center;justify-content:center;padding:20px;}
.pose-modal.show{display:flex;}
.pose-modal-box{background:#111827;border:1px solid rgba(255,255,255,0.1);border-radius:24px;padding:32px;max-width:520px;width:100%;max-height:90vh;overflow-y:auto;animation:slideUp 0.4s cubic-bezier(0.16,1,0.3,1);}
@keyframes slideUp{from{opacity:0;transform:translateY(30px);}to{opacity:1;transform:translateY(0);}}
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
.breathing-wrap{display:flex;flex-direction:column;align-items:center;padding:20px 0;}
.breath-circle{width:200px;height:200px;border-radius:50%;border:3px solid rgba(52,211,153,0.3);display:flex;align-items:center;justify-content:center;flex-direction:column;margin:0 auto 24px;position:relative;transition:all 1s ease;background:rgba(52,211,153,0.05);}
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
.workout-wrap{max-width:560px;margin:0 auto;}
.builder-row{display:flex;gap:10px;margin-bottom:16px;align-items:center;flex-wrap:wrap;}
.builder-label{color:rgba(255,255,255,0.5);font-size:0.82rem;font-weight:700;min-width:80px;}
.builder-select{padding:8px 14px;background:rgba(255,255,255,0.06);border:1.5px solid rgba(255,255,255,0.12);border-radius:12px;color:#fff;font-family:'Nunito',sans-serif;font-weight:700;font-size:0.88rem;outline:none;cursor:pointer;}
.workout-plan{display:flex;flex-direction:column;gap:10px;margin-bottom:16px;}
.workout-exercise{display:flex;align-items:center;gap:12px;padding:14px 16px;background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.07);border-radius:14px;}
.ex-num{width:30px;height:30px;border-radius:50%;background:linear-gradient(135deg,#34d399,#5bc8f5);display:flex;align-items:center;justify-content:center;font-weight:900;font-size:0.82rem;flex-shrink:0;}
.ex-info{flex:1;}
.ex-name{font-weight:800;font-size:0.9rem;margin-bottom:2px;}
.ex-detail{color:rgba(255,255,255,0.4);font-size:0.75rem;}
.ex-icon{font-size:1.5rem;}
</style>
</head>
<body>
<nav class="topnav"><span class="brand">MindSpace 🌿</span><div class="nav-links"><a href="/">🏠 Home</a><a href="/logout">👋 Logout</a></div></nav>
<div class="page-wrap">
    <h1 class="page-title">🧘 Physical Activity</h1>
    <p class="page-sub">Yoga poses, stretches, strength training & breathing exercises</p>
    <div class="section-tabs">
        <button class="tab-btn active" onclick="switchTab('yoga',this)">🧘 Yoga</button>
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
            <div class="breath-circle" id="breathCircle"><div class="breath-phase" id="breathPhase">Press Start</div><div class="breath-count" id="breathCountNum"></div></div>
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
        <div class="modal-icon" id="mIcon"></div>
        <div class="modal-title" id="mTitle"></div>
        <div class="modal-sub" id
