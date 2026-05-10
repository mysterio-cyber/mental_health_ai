from flask import Flask, request, render_template_string, jsonify, redirect, session
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
import os, json, datetime, random, urllib.request, urllib.error

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "mindspace-super-secret-key-change-in-prod-2024")
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE'] = False

# ── Anthropic API key (set via environment variable) ──────────────────────────
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
    has_api = bool(ANTHROPIC_API_KEY)

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
            <div><div class="card-title">AI Therapist{% if has_api %}<span class="api-badge">AI</span>{% endif %}</div><div class="card-desc">{% if has_api %}Powered by Claude AI{% else %}Calm AI companion{% endif %}</div></div>
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
# FEATURE 1 — EMOTION DETECTOR (Enhanced NLP)
# ─────────────────────────────────────────────

EMOTION_LEXICON = {
    "stress": [
        "stressed","overwhelmed","pressure","tense","burden","worried","nervous",
        "frantic","restless","on edge","wound up","tight","cant cope","too much",
        "exhausted","burned out","overloaded","swamped","deadline","workload"
    ],
    "anxiety": [
        "anxious","anxiety","panic","fear","phobia","dread","terror","frightened",
        "scared","paranoid","trembling","shaking","heart racing","cant breathe",
        "insomnia","worry","uneasy","apprehensive","racing thoughts","what if"
    ],
    "sadness": [
        "sad","unhappy","depressed","lonely","hopeless","miserable","grief","sorrow",
        "cry","crying","tears","heartbroken","devastated","empty","numb","down",
        "blue","gloomy","despairing","lost","worthless","meaningless","pointless"
    ],
    "anger": [
        "angry","furious","rage","hate","irritated","frustrated","annoyed","mad",
        "livid","resentful","bitter","hostile","outraged","offended","disgusted",
        "fed up","sick of","cant stand","unfair","betrayed","cheated"
    ],
    "happiness": [
        "happy","joyful","excited","great","wonderful","fantastic","amazing","love",
        "grateful","blessed","cheerful","content","peaceful","calm","relaxed",
        "proud","confident","hopeful","thrilled","elated","good","awesome","perfect"
    ]
}

# Negation words that flip sentiment
NEGATIONS = ["not","no","never","don't","doesn't","didn't","isn't","wasn't","aren't","weren't","hardly","barely"]

def detect_emotion_from_text(text: str) -> dict:
    text_lower = text.lower()
    words = text_lower.split()
    scores = {e: 0 for e in EMOTION_LEXICON}

    # Check for negation context (simple window-based)
    negated_positions = set()
    for idx, w in enumerate(words):
        if any(neg in w for neg in NEGATIONS):
            for offset in range(1, 4):
                negated_positions.add(idx + offset)

    # Score with negation awareness
    for emotion, keywords in EMOTION_LEXICON.items():
        for kw in keywords:
            kw_words = kw.split()
            phrase = " ".join(kw_words)
            if phrase in text_lower:
                # Check if any word of phrase is in negated position
                for idx, word in enumerate(words):
                    if word == kw_words[0]:
                        if idx in negated_positions:
                            # Negated negative emotion → slight happiness boost
                            if emotion in ["sadness","anger","stress","anxiety"]:
                                scores["happiness"] += 0.5
                        else:
                            scores[emotion] += 1
                        break

    # Intensity modifiers
    intensifiers = ["very","extremely","really","so","incredibly","absolutely","deeply","utterly"]
    for idx, w in enumerate(words):
        if w in intensifiers and idx + 1 < len(words):
            next_word = words[idx + 1]
            for emotion, keywords in EMOTION_LEXICON.items():
                if next_word in keywords:
                    scores[emotion] += 0.5  # Boost

    total = sum(scores.values())
    if total == 0:
        dominant = "neutral"
        confidence = 0
        percentages = {e: 0 for e in scores}
    else:
        dominant = max(scores, key=scores.get)
        if scores[dominant] == 0:
            dominant = "neutral"
            confidence = 0
            percentages = {e: 0 for e in scores}
        else:
            confidence = round(min(scores[dominant] / total * 100, 95))
            percentages = {e: round(scores[e] / total * 100) for e in scores}

    TIPS = {
        "stress": [
            "Try the 4-7-8 breathing exercise (inhale 4s, hold 7s, exhale 8s)",
            "Take a 10-minute walk outside to clear your head",
            "Break your tasks into smaller, manageable steps"
        ],
        "anxiety": [
            "Practice box breathing: inhale 4s, hold 4s, exhale 4s, hold 4s",
            "Ground yourself: name 5 things you can see right now",
            "Talk to someone you trust — sharing helps reduce anxiety"
        ],
        "sadness": [
            "Reach out to a friend or loved one today",
            "Do one small kind thing for yourself — music, tea, a short walk",
            "Consider speaking to a counsellor if it persists"
        ],
        "anger": [
            "Count slowly to 10 before responding",
            "Go for a brisk walk to physically release tension",
            "Write down your feelings — you don't have to send it"
        ],
        "happiness": [
            "Savour this moment — write down what made you happy",
            "Share your joy with someone close to you",
            "Use this positive energy for something creative"
        ],
        "neutral": [
            "How are you really feeling underneath?",
            "Try a short 5-minute mindfulness meditation",
            "Log your mood daily to spot patterns over time"
        ]
    }
    EMOJI  = {"stress":"😓","anxiety":"😰","sadness":"😢","anger":"😠","happiness":"😊","neutral":"😐"}
    COLOR  = {"stress":"#f59e0b","anxiety":"#a78bfa","sadness":"#60a5fa","anger":"#f87171","happiness":"#34d399","neutral":"#94a3b8"}
    return {
        "dominant": dominant,
        "emoji": EMOJI.get(dominant,"😐"),
        "color": COLOR.get(dominant,"#94a3b8"),
        "confidence": confidence,
        "scores": percentages,
        "tips": TIPS.get(dominant, TIPS["neutral"])
    }

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
.snapshot-bar{display:flex;gap:8px;justify-content:center;margin-top:12px;}
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
            <textarea id="textInput" placeholder="Type how you're feeling right now… e.g. 'I feel so overwhelmed and anxious about everything lately, I can't seem to relax or focus on anything.'"></textarea>
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
                <div class="snapshot-bar">
                    <button class="cam-btn" id="camStartBtn" onclick="startCam()">📷 Start Camera</button>
                    <button class="cam-btn stop" id="camStopBtn" onclick="stopCam()" style="display:none;">⏹ Stop</button>
                    <button class="cam-btn" id="snapBtn" onclick="snapAndAnalyse()" style="display:none;">🔍 Analyse Face</button>
                </div>
                <canvas id="snapCanvas" style="display:none;"></canvas>
                <p class="face-note">Your camera feed never leaves your device. The system captures a frame and analyses brightness/contrast patterns as proxy cues. For true facial emotion detection, integrate a face-api.js model.</p>
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
    // Sentiment polarity bar
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
    if(!SR){alert('Your browser does not support voice recognition. Try Chrome or Edge.');return;}
    if(recognition){recognition.stop();return;}
    recognition=new SR();recognition.continuous=true;recognition.interimResults=true;recognition.lang='en-US';
    document.getElementById('voiceBtn').classList.add('recording');
    document.getElementById('voiceStatus').textContent='🔴 Listening… speak freely';
    document.getElementById('voiceTranscript').style.display='block';
    recognition.onresult=e=>{let interim='',final='';for(let i=e.resultIndex;i<e.results.length;i++){if(e.results[i].isFinal)final+=e.results[i][0].transcript;else interim+=e.results[i][0].transcript;}voiceText+=final;document.getElementById('voiceTranscript').textContent=voiceText+interim;};
    recognition.onend=()=>{recognition=null;document.getElementById('voiceBtn').classList.remove('recording');document.getElementById('voiceStatus').textContent='✅ Done — review your words below';if(voiceText.trim())document.getElementById('voiceAnalyseBtn').style.display='block';};
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
    catch(e){alert('Camera access denied or unavailable.');}
}
function stopCam(){if(camStream)camStream.getTracks().forEach(t=>t.stop());document.getElementById('camVideo').style.display='none';document.getElementById('camPlaceholder').style.display='flex';document.getElementById('camStartBtn').style.display='inline-block';document.getElementById('camStopBtn').style.display='none';document.getElementById('snapBtn').style.display='none';}
async function snapAndAnalyse(){
    const video=document.getElementById('camVideo');const canvas=document.getElementById('snapCanvas');canvas.width=video.videoWidth||320;canvas.height=video.videoHeight||240;
    const ctx=canvas.getContext('2d');ctx.drawImage(video,0,0);
    // Analyse pixel brightness as proxy for expression (bright=happy, low contrast=neutral/sad)
    const imageData=ctx.getImageData(0,0,canvas.width,canvas.height);const data=imageData.data;
    let brightness=0,contrast=0;const pixels=data.length/4;
    for(let i=0;i<data.length;i+=4)brightness+=(data[i]+data[i+1]+data[i+2])/3;
    brightness/=pixels;
    // High brightness with warm tones → might indicate smiling (well-lit)
    const faceTexts=['I am smiling and feeling good','I look neutral today','I seem tired and stressed','I look calm and relaxed','I appear a bit tense'];
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
# FEATURE 2 — AI CHATBOT THERAPIST (Claude-powered with fallback)
# ─────────────────────────────────────────────

# Rule-based fallback responses
THERAPIST_RESPONSES = {
    "greet": [
        "Hello 💙 I'm so glad you reached out. How are you feeling today?",
        "Hi there 🌿 This is a safe, judgement-free space. What's on your mind?",
        "Welcome 🌙 I'm here to listen. How has your day been?"
    ],
    "stress": [
        "I can hear that you're feeling stressed. That's completely valid. 💛 Let's try something together — take a slow deep breath in for 4 counts, hold for 4, exhale for 4. How does that feel?",
        "Stress can feel so heavy. 😔 One thing that often helps is breaking tasks into tiny, manageable pieces. What's the one thing stressing you most right now?",
        "You're carrying a lot. Remember — it's okay to not have everything figured out. 🌿 What's one small thing you could let go of today?"
    ],
    "anxiety": [
        "Anxiety can feel overwhelming, but you're not alone. 💙 Try grounding yourself: name 5 things you can see right now.",
        "When anxiety peaks, our mind races ahead. 🌬️ Let's come back to the present — take three slow breaths with me. Inhale… exhale… You're safe.",
        "Anxiety is your mind trying to protect you — even if it's misfiring. 💛 What specific worry is on your mind?"
    ],
    "sadness": [
        "I'm sorry you're feeling this way. 💙 Sadness is a natural part of being human. Would you like to talk about what's making you feel down?",
        "It's okay to feel sad. 🌧️ Sometimes we need to sit with our feelings before we can move through them.",
        "Your feelings are valid. 💛 Sometimes doing one small kind thing for yourself — a warm drink, a short walk, a favourite song — can gently lift the weight."
    ],
    "anger": [
        "Anger is a signal that something important to you has been threatened. 🔥 It's okay to feel it. What happened?",
        "When we're angry, our body is in fight mode. 💨 Try this: take 10 slow breaths, or write out everything you want to say.",
        "Anger is valid. 💙 Once you've had a moment to cool down, it can help to ask: what do I actually need right now?"
    ],
    "happiness": [
        "That's wonderful! 😊✨ Savour this feeling — what made today good?",
        "I love hearing that! 🌟 Positive moments are worth celebrating. What brought you joy today?",
        "Amazing! 🎉 Gratitude helps us feel more of this — what are three things you're grateful for right now?"
    ],
    "sleep": [
        "Poor sleep can affect everything else. 😴 A few tips: keep a consistent bedtime, avoid screens 30 mins before bed, and try the 4-7-8 breathing technique.",
        "Sleep struggles are so common. 🌙 Have you tried a bedtime routine? Even 20 mins of winding down can help.",
    ],
    "help": [
        "You've taken a brave first step by asking for help. 💙 I can chat with you, share coping strategies, or just listen. What would help most right now?",
        "Asking for help is a sign of strength, not weakness. 🌿 I'm here. What's going on?",
    ],
    "crisis": [
        "I hear you, and what you're feeling matters deeply. 💙 Please reach out to a crisis helpline — in India: iCall: 9152987821 | Vandrevala Foundation: 1860-2662-345 (24/7). You deserve real human support.",
    ],
    "default": [
        "I hear you. 💙 Would you like to tell me more about how you're feeling?",
        "Thank you for sharing that with me. 🌿 How long have you been feeling this way?",
        "That sounds really tough. 💛 What kind of support would feel most helpful right now?",
        "I'm here with you. 🌙 Sometimes just saying things out loud helps. Keep going.",
        "I appreciate you opening up. 💙 Remember: you are not your feelings. They visit, but they also pass."
    ]
}

def rule_based_reply(user_msg: str) -> str:
    msg = user_msg.lower()
    crisis_words = ["suicide","kill myself","end my life","self harm","hurt myself","want to die","can't go on","no reason to live"]
    if any(w in msg for w in crisis_words):
        return random.choice(THERAPIST_RESPONSES["crisis"])
    if any(w in msg for w in ["hello","hi ","hey ","good morning","good evening","howdy","sup "]):
        return random.choice(THERAPIST_RESPONSES["greet"])
    if any(w in msg for w in ["help","support","dont know","don't know","lost","confused","what do i do"]):
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

def claude_chat_reply(messages_history: list, user_msg: str) -> str:
    """Call Claude API for intelligent therapy responses."""
    if not ANTHROPIC_API_KEY:
        return rule_based_reply(user_msg)

    system_prompt = """You are Sage, a compassionate AI mental wellness companion built into MindSpace — a wellness app. Your role is to:
- Listen with empathy and without judgment
- Provide evidence-based coping strategies (CBT, mindfulness, breathing exercises)
- Give emotional support for stress, anxiety, sadness, anger, and loneliness
- Gently encourage users to seek professional help when needed
- Keep responses warm, concise (2–4 sentences), and conversational — use emojis sparingly but naturally
- NEVER diagnose, prescribe, or replace professional therapy
- If someone expresses suicidal ideation, immediately provide Indian crisis helplines: iCall 9152987821, Vandrevala Foundation 1860-2662-345
- Always respond in first person as Sage

Important: Keep responses short and supportive, not lecture-like."""

    api_messages = []
    # Include last 6 messages for context
    for m in messages_history[-6:]:
        api_messages.append({"role": m["role"], "content": m["content"]})
    api_messages.append({"role": "user", "content": user_msg})

    payload = json.dumps({
        "model": "claude-haiku-4-5-20251001",
        "max_tokens": 300,
        "system": system_prompt,
        "messages": api_messages
    }).encode("utf-8")

    try:
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
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            return result["content"][0]["text"]
    except Exception:
        return rule_based_reply(user_msg)

@app.route("/chat")
def chat_page():
    if "user" not in session:
        return redirect("/login")
    has_api = bool(ANTHROPIC_API_KEY)
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
</style>
</head>
<body>
<nav class="topnav"><span class="brand">MindSpace 🌿</span><div class="nav-links"><a href="/">🏠 Home</a><a href="/emotion">🔍 Emotions</a><a href="/logout">👋 Logout</a></div></nav>
<div class="chat-header">
    <div class="bot-avatar">🤖</div>
    <div>
        <div class="bot-name">Sage — Your AI Companion{% if has_api %}<span class="ai-badge">✦ Claude AI</span>{% endif %}</div>
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
<div class="input-row">
    <input class="chat-input" id="chatInput" placeholder="Share what's on your mind…" onkeydown="if(event.key==='Enter')sendMsg()">
    <button class="send-btn" onclick="sendMsg()">➤</button>
</div>
<script>
const messagesEl=document.getElementById('messages');
let chatHistory=[];
function nowTime(){const d=new Date();return d.getHours().toString().padStart(2,'0')+':'+d.getMinutes().toString().padStart(2,'0');}
function addMsg(text,role){
    const div=document.createElement('div');div.className='msg '+role;
    div.innerHTML=`<div class="bubble">${text}</div><div class="msg-time">${nowTime()}</div>`;
    messagesEl.appendChild(div);messagesEl.scrollTop=messagesEl.scrollHeight;
    chatHistory.push({role:role==='bot'?'assistant':'user',content:text});
}
function showTyping(){const div=document.createElement('div');div.className='msg bot';div.id='typing';div.innerHTML=`<div class="typing-bubble"><div class="typing-dot"></div><div class="typing-dot"></div><div class="typing-dot"></div></div>`;messagesEl.appendChild(div);messagesEl.scrollTop=messagesEl.scrollHeight;}
function removeTyping(){const t=document.getElementById('typing');if(t)t.remove();}
async function sendMsg(){
    const input=document.getElementById('chatInput');const text=input.value.trim();if(!text)return;
    input.value='';document.getElementById('quickReplies').style.display='none';
    addMsg(text,'user');showTyping();
    const res=await fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:text,history:chatHistory.slice(-10)})});
    const d=await res.json();removeTyping();addMsg(d.reply,'bot');
}
function quickSend(text){document.getElementById('chatInput').value=text;sendMsg();}
setTimeout(()=>{addMsg('Hello {{ session["user"] }} 💙 I\'m Sage, your calm AI companion. This is a safe, judgement-free space. How are you feeling today?','bot');},400);
</script>
</body></html>
""", has_api=has_api)

@app.route("/api/chat", methods=["POST"])
def api_chat():
    if "user" not in session:
        return jsonify({"error": "Not logged in"}), 401
    data = request.get_json()
    msg = data.get("message","")
    history = data.get("history", [])
    reply = claude_chat_reply(history, msg)
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
            cur.execute("INSERT INTO mood_logs (username,mood,note,intensity) VALUES (?,?,?,?)",
                        (session["user"], mood, note, intensity))
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
    # Mood streak calculation
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
.saved-toast{display:none;text-align:center;color:#34d399;font-weight:800;font-size:0.9rem;margin-top:10px;animation:fadeIn 0.4s ease;}
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
@keyframes fadeIn{from{opacity:0;}to{opacity:1;}}
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

    <!-- STATS -->
    <div class="stats-row">
        <div class="stat-card"><div class="stat-val">{{ streak }}</div><div class="stat-lbl">🔥 Day Streak</div></div>
        <div class="stat-card"><div class="stat-val">{{ total_logs }}</div><div class="stat-lbl">📝 Total Logs</div></div>
        <div class="stat-card"><div class="stat-val">{{ dominant_mood_emoji }}</div><div class="stat-lbl">{{ dominant_mood_label }}</div></div>
    </div>

    <!-- LOG FORM -->
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
            <textarea class="note-input" name="note" rows="2" placeholder="Optional: add a note about your day… (e.g. 'Had a stressful meeting but felt better after a walk')">{{ request.form.get('note','') if saved else '' }}</textarea>
            <button type="submit" class="save-btn">💾 Save Today's Mood</button>
            {% if saved %}<div class="saved-toast" style="display:block;">✅ Mood logged successfully! Keep it up 🌟</div>{% endif %}
        </form>
    </div>

    <!-- CHARTS -->
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

    <!-- RECENT LOGS -->
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
                        <div class="log-mood-name" style="color:{{ meta.color }};">{{ row[0] }}
                            <span style="color:rgba(255,255,255,0.3);font-size:0.75rem;font-weight:600;"> · intensity {{ row[1] }}</span>
                        </div>
                        {% if row[2] %}<div class="log-note">{{ row[2][:80] }}{% if row[2]|length > 80 %}…{% endif %}</div>{% endif %}
                        <div class="intensity-pip">
                            {% for p in range(row[1]) %}<div class="pip" style="background:{{ meta.color }};opacity:0.8;"></div>{% endfor %}
                            {% for p in range(5 - row[1]) %}<div class="pip" style="background:rgba(255,255,255,0.1);"></div>{% endfor %}
                        </div>
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
const weekLabels  = {{ week_labels | tojson }};
const weekData    = {{ week_data | tojson }};
const monthCounts = {{ month_counts | tojson }};
const MOOD_COLORS = {Happy:'#34d399',Calm:'#60a5fa',Sad:'#818cf8',Angry:'#f87171',Stressed:'#fbbf24'};

const weekCtx = document.getElementById('weekChart').getContext('2d');
new Chart(weekCtx, {
    type:'bar',
    data:{labels:weekLabels,datasets:Object.entries(weekData).map(([mood,data])=>({label:mood,data:data,backgroundColor:MOOD_COLORS[mood]+'99',borderColor:MOOD_COLORS[mood],borderWidth:1,borderRadius:4}))},
    options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{display:true,position:'top',labels:{color:'rgba(255,255,255,0.5)',font:{family:'Nunito',size:11},boxWidth:10,padding:14}}},scales:{x:{stacked:true,grid:{color:'rgba(255,255,255,0.04)'},ticks:{color:'rgba(255,255,255,0.4)',font:{family:'Nunito',size:11}}},y:{stacked:true,grid:{color:'rgba(255,255,255,0.04)'},ticks:{color:'rgba(255,255,255,0.4)',font:{family:'Nunito',size:11},stepSize:1}}}}
});

const monthCtx = document.getElementById('monthChart').getContext('2d');
const monthLabels=Object.keys(monthCounts),monthVals=Object.values(monthCounts),monthColors=monthLabels.map(m=>MOOD_COLORS[m]||'#888');
new Chart(monthCtx,{type:'doughnut',data:{labels:monthLabels,datasets:[{data:monthVals,backgroundColor:monthColors.map(c=>c+'bb'),borderColor:monthColors,borderWidth:2,hoverOffset:8}]},options:{responsive:true,maintainAspectRatio:false,cutout:'62%',plugins:{legend:{display:true,position:'right',labels:{color:'rgba(255,255,255,0.6)',font:{family:'Nunito',size:12},boxWidth:12,padding:12}},tooltip:{callbacks:{label:ctx=>' '+ctx.label+': '+ctx.parsed+' entries'}}}}});

function showChart(view,btn){document.querySelectorAll('.ctab').forEach(b=>b.classList.remove('active'));btn.classList.add('active');document.getElementById('chartWeekly').style.display=view==='weekly'?'block':'none';document.getElementById('chartMonthly').style.display=view==='monthly'?'block':'none';}

function selectMood(mood,color,bg,border){
    document.getElementById('selectedMood').value=mood;
    document.querySelectorAll('.mood-btn').forEach(b=>{b.style.background='rgba(255,255,255,0.04)';b.style.borderColor='rgba(255,255,255,0.08)';b.classList.remove('selected');});
    const btn=document.getElementById('mbtn-'+mood);btn.style.background=bg;btn.style.borderColor=color;btn.classList.add('selected');
}
function selectIntensity(val,btn){document.getElementById('selectedIntensity').value=val;document.querySelectorAll('.int-btn').forEach(b=>b.classList.remove('active'));btn.classList.add('active');}

{% if saved %}
selectMood('{{ request.form.get("mood","") }}','{{ mood_meta.get(request.form.get("mood","Happy"), {"color":"#34d399"}).color }}','{{ mood_meta.get(request.form.get("mood","Happy"), {"bg":"rgba(52,211,153,0.15)"}).bg }}','{{ mood_meta.get(request.form.get("mood","Happy"), {"border":"rgba(52,211,153,0.35)"}).border }}');
{% endif %}
</script>
</body></html>
""", mood_meta=MOOD_META, saved=saved, recent=recent,
     week_labels=week_labels, week_data=week_data, month_counts=month_counts,
     request=request, streak=streak,
     total_logs=len(rows),
     dominant_mood_emoji=max(month_counts, key=month_counts.get, default="—") and MOOD_META.get(max(month_counts, key=month_counts.get, default="Happy"),{"emoji":"—"})["emoji"] if rows else "🌱",
     dominant_mood_label=("Most: " + max(month_counts, key=month_counts.get)) if rows else "No data yet",
     insights=_mood_insights(rows, month_counts, streak))

def _mood_insights(rows, month_counts, streak):
    insights = []
    if not rows:
        return ["Start logging your mood to get personalised insights!"]
    dominant = max(month_counts, key=month_counts.get)
    if dominant in ["Happy","Calm"]:
        insights.append(f"✨ You've been feeling {dominant.lower()} most often lately — great work!")
    elif dominant in ["Stressed","Anxious","Angry"]:
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

# Expose _mood_insights to Jinja (used above inline)
app.jinja_env.globals['_mood_insights'] = _mood_insights

# ─────────────────────────────────────────────
# GAMES PAGE
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
.chess-wrap{max-width:440px;margin:0 auto;}
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
.move-entry span.move-num{color:rgba(255,255,255,0.3);font-size:0.7rem;}
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
            <div class="captured-row" id="capturedByBlack" style="margin-bottom:6px;justify-content:flex-start;"></div>
            <div class="board-wrapper">
                <div class="rank-labels" id="rankLabels"></div>
                <div class="chess-board" id="chessBoard"></div>
            </div>
            <div class="file-labels" id="chessFiles"></div>
            <div class="captured-row" id="capturedByWhite" style="margin-top:6px;justify-content:flex-start;"></div>
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
let sudokuPuzzle=[],sudokuSolution=[],selectedCell=-1,difficulty='easy';
let timerInterval=null,timerSeconds=0,hintsUsed=0;
const PUZZLES={easy:[[5,3,0,0,7,0,0,0,0,6,0,0,1,9,5,0,0,0,0,9,8,0,0,0,0,6,0,8,0,0,0,6,0,0,0,3,4,0,0,8,0,3,0,0,1,7,0,0,0,2,0,0,0,6,0,6,0,0,0,0,2,8,0,0,0,0,4,1,9,0,0,5,0,0,0,0,8,0,0,7,9],[0,0,0,2,6,0,7,0,1,6,8,0,0,7,0,0,9,0,1,9,0,0,0,4,5,0,0,8,2,0,1,0,0,0,4,0,0,0,4,6,0,2,9,0,0,0,5,0,0,0,3,0,2,8,0,0,9,3,0,0,0,7,4,0,4,0,0,5,0,0,3,6,7,0,3,0,1,8,0,0,0]],medium:[[0,2,0,0,0,0,0,0,0,0,0,0,6,0,0,0,0,3,0,7,4,0,8,0,0,0,0,0,0,0,0,0,3,0,0,2,0,8,0,0,4,0,0,1,0,6,0,0,5,0,0,0,0,0,0,0,0,0,1,0,7,8,0,5,0,0,0,0,9,0,0,0,0,0,0,0,0,0,0,4,0],[0,0,0,0,0,0,2,0,0,0,8,0,0,3,0,0,7,0,0,0,3,6,0,0,0,8,0,0,1,0,0,0,0,0,0,0,0,0,8,5,0,0,0,0,6,0,0,0,0,0,4,0,0,0,0,2,0,0,0,3,9,0,0,0,4,0,0,8,0,0,2,0,0,0,5,0,0,0,0,0,0]],hard:[[8,0,0,0,0,0,0,0,0,0,0,3,6,0,0,0,0,0,0,7,0,0,9,0,2,0,0,0,5,0,0,0,7,0,0,0,0,0,0,0,4,5,7,0,0,0,0,0,1,0,0,0,3,0,0,0,1,0,0,0,0,6,8,0,0,8,5,0,0,0,1,0,0,9,0,0,0,0,4,0,0],[0,0,5,3,0,0,0,0,0,8,0,0,0,0,0,0,2,0,0,7,0,0,1,0,5,0,0,4,0,0,0,0,5,3,0,0,0,1,0,0,7,0,0,0,6,0,0,3,2,0,0,0,8,0,0,6,0,5,0,0,0,0,9,0,0,4,0,0,0,0,3,0,0,0,0,0,0,9,7,0,0]]};
function solveSudoku(b){const bd=[...b];function ok(b,r,c,n){for(let i=0;i<9;i++){if(b[r*9+i]===n||b[i*9+c]===n)return false;}const br=Math.floor(r/3)*3,bc=Math.floor(c/3)*3;for(let i=0;i<3;i++)for(let j=0;j<3;j++)if(b[(br+i)*9+(bc+j)]===n)return false;return true;}function solve(){const e=bd.indexOf(0);if(e===-1)return true;const r=Math.floor(e/9),c=e%9;for(let n=1;n<=9;n++){if(ok(bd,r,c,n)){bd[e]=n;if(solve())return true;bd[e]=0;}}return false;}solve();return bd;}
function setDiff(d,btn){difficulty=d;document.querySelectorAll('.diff-btn').forEach(b=>b.classList.remove('active'));btn.classList.add('active');newSudokuGame();}
let origPuzzle=[];
function updateTimer(){const m=String(Math.floor(timerSeconds/60)).padStart(2,'0'),s=String(timerSeconds%60).padStart(2,'0');document.getElementById('timerRow').textContent=`⏱ ${m}:${s}`;}
function newSudokuGame(){const pool=PUZZLES[difficulty];const base=pool[Math.floor(Math.random()*pool.length)];origPuzzle=[...base];sudokuPuzzle=[...base];sudokuSolution=solveSudoku([...base]);selectedCell=-1;hintsUsed=0;clearInterval(timerInterval);timerSeconds=0;updateTimer();timerInterval=setInterval(()=>{timerSeconds++;updateTimer();},1000);renderSudoku();document.getElementById('sudokuStatus').textContent='Select a cell and type a number';document.getElementById('sudokuStatus').style.color='rgba(255,255,255,0.5)';}
function renderSudoku(){const outer=document.getElementById('sudokuOuter');outer.innerHTML='';for(let box=0;box<9;box++){const boxDiv=document.createElement('div');boxDiv.className='sudoku-box';const boxRow=Math.floor(box/3)*3,boxCol=(box%3)*3;for(let ri=0;ri<3;ri++)for(let ci=0;ci<3;ci++){const r=boxRow+ri,c=boxCol+ci,idx=r*9+c;const cell=document.createElement('button');cell.className='sudoku-cell';const isOrig=origPuzzle[idx]!==0;if(isOrig)cell.classList.add('given');if(idx===selectedCell)cell.classList.add('selected');else if(selectedCell>=0){const sr=Math.floor(selectedCell/9),sc=selectedCell%9;if(r===sr||c===sc||Math.floor(r/3)===Math.floor(sr/3)&&Math.floor(c/3)===Math.floor(sc/3))cell.classList.add('highlight');}cell.textContent=sudokuPuzzle[idx]||'';if(sudokuPuzzle[idx]!==0&&!isOrig&&sudokuPuzzle[idx]!==sudokuSolution[idx])cell.classList.add('error');cell.onclick=()=>{if(!isOrig){selectedCell=idx;renderSudoku();}};boxDiv.appendChild(cell);}outer.appendChild(boxDiv);}const np=document.getElementById('numpad');np.innerHTML='';for(let n=1;n<=9;n++){const b=document.createElement('button');b.className='num-btn';b.textContent=n;b.onclick=()=>enterNum(n);np.appendChild(b);}}
function enterNum(n){if(selectedCell===-1)return;if(origPuzzle[selectedCell]!==0)return;sudokuPuzzle[selectedCell]=n;renderSudoku();if(!sudokuPuzzle.includes(0)){const allOk=sudokuPuzzle.every((v,i)=>v===sudokuSolution[i]);if(allOk){clearInterval(timerInterval);const m=String(Math.floor(timerSeconds/60)).padStart(2,'0'),s=String(timerSeconds%60).padStart(2,'0');document.getElementById('sudokuStatus').textContent=`🎉 Solved in ${m}:${s}!`;document.getElementById('sudokuStatus').style.color='#6ee7b7';}}}
function clearCell(){if(selectedCell===-1||origPuzzle[selectedCell]!==0)return;sudokuPuzzle[selectedCell]=0;renderSudoku();}
function hintCell(){if(selectedCell===-1)return;if(origPuzzle[selectedCell]!==0)return;sudokuPuzzle[selectedCell]=sudokuSolution[selectedCell];hintsUsed++;renderSudoku();}
function checkSudoku(){let errors=0;sudokuPuzzle.forEach((v,i)=>{if(v!==0&&v!==sudokuSolution[i])errors++;});const status=document.getElementById('sudokuStatus');if(errors===0&&!sudokuPuzzle.includes(0)){clearInterval(timerInterval);status.textContent='🎉 Puzzle Complete!';status.style.color='#6ee7b7';}else if(errors>0){status.textContent=`❌ ${errors} error(s)`;status.style.color='#ff9a9a';}else{status.textContent='✅ Correct so far!';status.style.color='#6ee7b7';}}
document.addEventListener('keydown',e=>{if(document.getElementById('panel-sudoku').classList.contains('active')){const n=parseInt(e.key);if(n>=1&&n<=9)enterNum(n);else if(e.key==='Backspace'||e.key==='Delete')clearCell();}});
newSudokuGame();
const PIECES={wK:'♔',wQ:'♕',wR:'♖',wB:'♗',wN:'♘',wP:'♙',bK:'♚',bQ:'♛',bR:'♜',bB:'♝',bN:'♞',bP:'♟'};
let board=[],turn='w',selected=null,validMoves=[],gameOver=false;
let capturedWhite=[],capturedBlack=[],enPassantTarget=null,castlingRights={wK:true,wQ:true,bK:true,bQ:true};
let lastFrom=-1,lastTo=-1,moveList=[],pendingPromotion=null;
function sq(r,c){return r*8+c;}function rc(idx){return{r:Math.floor(idx/8),c:idx%8};}function inBounds(r,c){return r>=0&&r<8&&c>=0&&c<8;}function color(p){return p?p[0]:null;}function type(p){return p?p[1]:null;}
function initChess(){board=new Array(64).fill(null);const backRank=['R','N','B','Q','K','B','N','R'];for(let c=0;c<8;c++){board[sq(0,c)]='b'+backRank[c];board[sq(1,c)]='bP';board[sq(6,c)]='wP';board[sq(7,c)]='w'+backRank[c];}turn='w';selected=null;validMoves=[];gameOver=false;capturedWhite=[];capturedBlack=[];enPassantTarget=null;castlingRights={wK:true,wQ:true,bK:true,bQ:true};lastFrom=-1;lastTo=-1;moveList=[];pendingPromotion=null;renderChess();updateChessUI();}
function findKing(col){return board.findIndex(p=>p===col+'K');}
function isAttacked(idx,byColor){const{r,c}=rc(idx);const pDir=byColor==='w'?1:-1;for(const dc of[-1,1]){const ar=r+pDir,ac=c+dc;if(inBounds(ar,ac)&&board[sq(ar,ac)]===byColor+'P')return true;}for(const[dr,dc]of[[-2,-1],[-2,1],[-1,-2],[-1,2],[1,-2],[1,2],[2,-1],[2,1]]){const nr=r+dr,nc=c+dc;if(inBounds(nr,nc)&&board[sq(nr,nc)]===byColor+'N')return true;}for(const[dr,dc]of[[-1,-1],[-1,0],[-1,1],[0,-1],[0,1],[1,-1],[1,0],[1,1]]){const nr=r+dr,nc=c+dc;if(inBounds(nr,nc)&&board[sq(nr,nc)]===byColor+'K')return true;}for(const[dr,dc]of[[1,0],[-1,0],[0,1],[0,-1]]){let nr=r+dr,nc=c+dc;while(inBounds(nr,nc)){const p=board[sq(nr,nc)];if(p){if(color(p)===byColor&&(type(p)==='R'||type(p)==='Q'))return true;break;}nr+=dr;nc+=dc;}}for(const[dr,dc]of[[1,1],[1,-1],[-1,1],[-1,-1]]){let nr=r+dr,nc=c+dc;while(inBounds(nr,nc)){const p=board[sq(nr,nc)];if(p){if(color(p)===byColor&&(type(p)==='B'||type(p)==='Q'))return true;break;}nr+=dr;nc+=dc;}}return false;}
function isInCheck(col){return isAttacked(findKing(col),col==='w'?'b':'w');}
function getLegalMoves(fromIdx){const p=board[fromIdx];if(!p)return[];const col=color(p),tp=type(p);const{r,c}=rc(fromIdx);const opp=col==='w'?'b':'w';const pseudo=[];const addIf=(r2,c2)=>{if(inBounds(r2,c2)&&color(board[sq(r2,c2)])!==col)pseudo.push(sq(r2,c2));};const slide=(dr,dc)=>{let nr=r+dr,nc=c+dc;while(inBounds(nr,nc)){const t2=board[sq(nr,nc)];if(!t2)pseudo.push(sq(nr,nc));else{if(color(t2)===opp)pseudo.push(sq(nr,nc));break;}nr+=dr;nc+=dc;}};
if(tp==='P'){const dir=col==='w'?-1:1;const startRow=col==='w'?6:1;if(inBounds(r+dir,c)&&!board[sq(r+dir,c)]){pseudo.push(sq(r+dir,c));if(r===startRow&&!board[sq(r+2*dir,c)])pseudo.push(sq(r+2*dir,c));}for(const dc of[-1,1]){const nr=r+dir,nc=c+dc;if(inBounds(nr,nc)){if(color(board[sq(nr,nc)])===opp)pseudo.push(sq(nr,nc));if(sq(nr,nc)===enPassantTarget)pseudo.push(sq(nr,nc));}}}
else if(tp==='N'){[[-2,-1],[-2,1],[-1,-2],[-1,2],[1,-2],[1,2],[2,-1],[2,1]].forEach(([dr,dc])=>addIf(r+dr,c+dc));}
else if(tp==='R'){slide(1,0);slide(-1,0);slide(0,1);slide(0,-1);}
else if(tp==='B'){slide(1,1);slide(1,-1);slide(-1,1);slide(-1,-1);}
else if(tp==='Q'){slide(1,0);slide(-1,0);slide(0,1);slide(0,-1);slide(1,1);slide(1,-1);slide(-1,1);slide(-1,-1);}
else if(tp==='K'){[[-1,-1],[-1,0],[-1,1],[0,-1],[0,1],[1,-1],[1,0],[1,1]].forEach(([dr,dc])=>addIf(r+dr,c+dc));const row=col==='w'?7:0;if(r===row&&c===4&&!isInCheck(col)){if(castlingRights[col+'K']&&!board[sq(row,5)]&&!board[sq(row,6)]&&!isAttacked(sq(row,5),opp)&&!isAttacked(sq(row,6),opp))pseudo.push(sq(row,6));if(castlingRights[col+'Q']&&!board[sq(row,3)]&&!board[sq(row,2)]&&!board[sq(row,1)]&&!isAttacked(sq(row,3),opp)&&!isAttacked(sq(row,2),opp))pseudo.push(sq(row,2));}}
return pseudo.filter(to=>{const savedBoard=[...board],savedEP=enPassantTarget;const{r:fr,c:fc}=rc(fromIdx);const{r:tr,c:tc}=rc(to);if(tp==='P'&&to===enPassantTarget){board[sq(fr,tc)]=null;}board[to]=p;board[fromIdx]=null;if(tp==='K'){const dc2=tc-fc;if(Math.abs(dc2)===2){const row2=col==='w'?7:0;if(dc2>0){board[sq(row2,5)]=col+'R';board[sq(row2,7)]=null;}else{board[sq(row2,3)]=col+'R';board[sq(row2,0)]=null;}}}const ok=!isInCheck(col);board=[...savedBoard];enPassantTarget=savedEP;return ok;});}
function applyMove(from,to){const p=board[from],col=color(p),tp2=type(p);const{r:tr,c:tc}=rc(to);const{r:fr,c:fc}=rc(from);const captured=board[to];if(tp2==='P'&&to===enPassantTarget){const epIdx=sq(fr,tc);if(board[epIdx]){(col==='w'?capturedBlack:capturedWhite).push(board[epIdx]);board[epIdx]=null;}}else if(captured){(col==='w'?capturedBlack:capturedWhite).push(captured);}board[to]=p;board[from]=null;if(tp2==='K'){const dc2=tc-fc;if(dc2===2){board[sq(tr,5)]=col+'R';board[sq(tr,7)]=null;}else if(dc2===-2){board[sq(tr,3)]=col+'R';board[sq(tr,0)]=null;}}if(tp2==='K'){castlingRights[col+'K']=false;castlingRights[col+'Q']=false;}if(tp2==='R'){if(fc===0)castlingRights[col+'Q']=false;if(fc===7)castlingRights[col+'K']=false;}enPassantTarget=null;if(tp2==='P'&&Math.abs(tr-fr)===2)enPassantTarget=sq((fr+tr)/2,fc);lastFrom=from;lastTo=to;const notation=getNotation(p,from,to);moveList.push({col,notation});turn=turn==='w'?'b':'w';if(tp2==='P'&&(tr===0||tr===7)){pendingPromotion={from,to};showPromotion(col);}else finishMove();}
function getNotation(p,from,to){const files='abcdefgh';const{r:fr,c:fc}=rc(from);const{r:tr,c:tc}=rc(to);const tp2=type(p);if(tp2==='K'&&Math.abs(tc-fc)===2)return tc>fc?'O-O':'O-O-O';return(tp2!=='P'?tp2:'')+files[fc]+(8-fr)+files[tc]+(8-tr);}
function showPromotion(col){const modal=document.getElementById('promoModal');modal.classList.add('show');const choices=document.getElementById('promoChoices');choices.innerHTML='';['Q','R','B','N'].forEach(t=>{const btn=document.createElement('button');btn.className='promo-btn';btn.textContent=PIECES[col+t];btn.onclick=()=>{board[pendingPromotion.to]=col+t;pendingPromotion=null;modal.classList.remove('show');finishMove();};choices.appendChild(btn);});}
function finishMove(){renderChess();updateChessUI();updateMoveHistory();}
function handleChessClick(idx){if(gameOver)return;if(selected!==null){if(validMoves.includes(idx)){applyMove(selected,idx);selected=null;validMoves=[];return;}selected=null;validMoves=[];}const p=board[idx];if(p&&color(p)===turn){selected=idx;validMoves=getLegalMoves(idx);}renderChess();}
function renderChess(){const b=document.getElementById('chessBoard');b.innerHTML='';for(let r=0;r<8;r++)for(let c=0;c<8;c++){const idx=sq(r,c);const sqEl=document.createElement('div');sqEl.className='chess-sq '+((r+c)%2===0?'light':'dark');if(selected===idx)sqEl.classList.add('selected');if(validMoves.includes(idx)){if(board[idx])sqEl.classList.add('valid-capture');else sqEl.classList.add('valid-move');}if(idx===lastFrom)sqEl.classList.add('last-from');if(idx===lastTo)sqEl.classList.add('last-to');if(board[idx]&&type(board[idx])==='K'&&isInCheck(color(board[idx])))sqEl.classList.add('in-check');if(board[idx])sqEl.textContent=PIECES[board[idx]]||board[idx];sqEl.onclick=()=>handleChessClick(idx);b.appendChild(sqEl);}document.getElementById('capturedByBlack').innerHTML=capturedBlack.map(p=>`<span style="font-size:1.1rem;opacity:0.7">${PIECES[p]||p}</span>`).join('');document.getElementById('capturedByWhite').innerHTML=capturedWhite.map(p=>`<span style="font-size:1.1rem;opacity:0.7">${PIECES[p]||p}</span>`).join('');}
function getLegalMovesForColor(col){let all=[];for(let i=0;i<64;i++){if(board[i]&&color(board[i])===col)all=all.concat(getLegalMoves(i));}return all;}
function updateChessUI(){const inCheckW=isInCheck('w'),inCheckB=isInCheck('b');const legalW=getLegalMovesForColor('w').length,legalB=getLegalMovesForColor('b').length;document.getElementById('whitePlayer').classList.toggle('active-turn',turn==='w');document.getElementById('blackPlayer').classList.toggle('active-turn',turn==='b');let status='';if(turn==='w'&&legalW===0){gameOver=true;status=inCheckW?'Checkmate — Black wins! 🏆':'Stalemate — Draw!';}else if(turn==='b'&&legalB===0){gameOver=true;status=inCheckB?'Checkmate — White wins! 🏆':'Stalemate — Draw!';}else if(inCheckW||inCheckB){status=(inCheckW?'White':'Black')+' is in check!';}else{status=turn==='w'?'White to move':'Black to move';}document.getElementById('chessStatus').textContent=status;}
function updateMoveHistory(){const wrap=document.getElementById('moveHistoryWrap');if(moveList.length===0){wrap.style.display='none';return;}wrap.style.display='block';const mh=document.getElementById('moveHistory');mh.innerHTML='';for(let i=0;i<moveList.length;i+=2){const n=i/2+1;const wm=moveList[i],bm=moveList[i+1];mh.innerHTML+=`<div class="move-entry white"><span class="move-num">${n}.</span> ${wm.notation}</div><div class="move-entry">${bm?bm.notation:''}</div>`;}wrap.scrollTop=wrap.scrollHeight;}
function newChessGame(){initChess();}
document.getElementById('rankLabels').innerHTML=['8','7','6','5','4','3','2','1'].map(r=>`<span>${r}</span>`).join('');
document.getElementById('chessFiles').innerHTML=['a','b','c','d','e','f','g','h'].map(f=>`<span>${f}</span>`).join('');
initChess();
function switchTab(tab,btn){document.querySelectorAll('.tab-btn').forEach(b=>b.classList.remove('active'));document.querySelectorAll('.game-panel').forEach(p=>p.classList.remove('active'));btn.classList.add('active');document.getElementById('panel-'+tab).classList.add('active');}
</script>
</body></html>
""")

# ─────────────────────────────────────────────
# PUZZLE PAGE (kept intact)
# ─────────────────────────────────────────────

app.route("/puzzle")
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
/* MEMORY */
.memory-info{display:flex;justify-content:space-between;align-items:center;margin-bottom:14px;}
.memory-stat{background:rgba(255,255,255,0.05);border:1px solid rgba(255,255,255,0.08);border-radius:12px;padding:8px 16px;font-weight:800;font-size:0.88rem;}
.memory-grid{display:grid;gap:10px;margin-bottom:16px;}
.mem-card{aspect-ratio:1;background:rgba(249,168,212,0.1);border:2px solid rgba(249,168,212,0.2);border-radius:14px;display:flex;align-items:center;justify-content:center;font-size:2rem;cursor:pointer;transition:all 0.3s;transform:rotateY(0deg);user-select:none;}
.mem-card.flipped,.mem-card.matched{background:rgba(249,168,212,0.2);border-color:rgba(249,168,212,0.5);box-shadow:0 0 16px rgba(249,168,212,0.3);}
.mem-card.matched{background:rgba(110,231,183,0.15);border-color:rgba(110,231,183,0.4);cursor:default;}
.mem-card:not(.flipped):not(.matched) span{opacity:0;}
.mem-card:hover:not(.flipped):not(.matched){background:rgba(249,168,212,0.15);transform:scale(1.04);}
.memory-actions{display:flex;gap:10px;align-items:center;}

/* WORD SCRAMBLE */
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

/* 2048 */
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

    <!-- MEMORY MATCH -->
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
        <div class="memory-actions">
            <button class="game-btn primary" onclick="newMemGame()">🔄 New Game</button>
        </div>
    </div>

    <!-- WORD SCRAMBLE -->
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

    <!-- 2048 -->
    <div class="game-panel" id="panel-g2048">
        <div class="g2048-wrap">
            <div class="g2048-info">
                <div class="g2048-score"><div class="label">Score</div><div class="val" id="s2048">0</div></div>
                <div class="g2048-score"><div class="label">Best</div><div class="val" id="b2048">0</div></div>
            </div>
            <div class="g2048-board" id="board2048"></div>
            <div class="g2048-actions">
                <button class="game-btn primary" onclick="new2048()">🔄 New Game</button>
            </div>
            <div class="g2048-instructions">Use arrow keys or swipe to merge tiles. Reach 2048!</div>
        </div>
    </div>
</div>

<script>
function switchTab(tab,btn){document.querySelectorAll('.tab-btn').forEach(b=>b.classList.remove('active'));document.querySelectorAll('.game-panel').forEach(p=>p.classList.remove('active'));btn.classList.add('active');document.getElementById('panel-'+tab).classList.add('active');}

// ===== MEMORY MATCH =====
const EMOJIS=['🌸','🌊','🌙','⭐','🦋','🌈','🔮','🌺','🎯','🦄','🍀','🎸'];
let memCards=[],memFlipped=[],memMatched=0,memMoveCount=0,memTimer2=0,memInterval=null,memGridSize=4,memLock=false;
function setMemDiff(cols,btn){memGridSize=cols;newMemGame();}
function shuffle(a){for(let i=a.length-1;i>0;i--){const j=Math.floor(Math.random()*(i+1));[a[i],a[j]]=[a[j],a[i]];}return a;}
function newMemGame(){const pairs=memGridSize===6?12:8;const chosen=EMOJIS.slice(0,pairs);memCards=shuffle([...chosen,...chosen]);memFlipped=[];memMatched=0;memMoveCount=0;memLock=false;clearInterval(memInterval);memTimer2=0;document.getElementById('memMoves').textContent='Moves: 0';document.getElementById('memPairs').textContent=`Pairs: 0/${pairs}`;document.getElementById('memTimer').textContent='⏱ 0s';memInterval=setInterval(()=>{memTimer2++;document.getElementById('memTimer').textContent=`⏱ ${memTimer2}s`;},1000);renderMem();}
function renderMem(){const grid=document.getElementById('memGrid');const cols=memGridSize;grid.style.gridTemplateColumns=`repeat(${cols},1fr)`;grid.innerHTML='';memCards.forEach((e,i)=>{const card=document.createElement('div');card.className='mem-card';if(memFlipped.includes(i)||memCards[i]==='matched')card.classList.add('flipped');if(memCards[i]==='matched')card.classList.add('matched');card.innerHTML=`<span>${e}</span>`;card.onclick=()=>flipCard(i);grid.appendChild(card);});}
function flipCard(i){if(memLock||memFlipped.includes(i)||memCards[i]==='matched')return;memFlipped.push(i);renderMem();if(memFlipped.length===2){memMoveCount++;document.getElementById('memMoves').textContent=`Moves: ${memMoveCount}`;const[a,b]=memFlipped;if(memCards[a]===memCards[b]){memCards[a]=memCards[b]='matched';memMatched++;const pairs=memCards.filter(c=>c==='matched').length/2;document.getElementById('memPairs').textContent=`Pairs: ${pairs}/${memCards.filter(c=>c!=='matched').length/2+pairs}`;memFlipped=[];renderMem();if(pairs===memCards.length/2){clearInterval(memInterval);setTimeout(()=>alert(`🎉 You won in ${memMoveCount} moves and ${memTimer2}s!`),300);}}else{memLock=true;setTimeout(()=>{memFlipped=[];memLock=false;renderMem();},900);}}}
newMemGame();

// ===== WORD SCRAMBLE =====
const WORDS=[{w:'HAPPY',h:'Feeling joyful'},{w:'CALM',h:'Peaceful state'},{w:'BREATHE',h:'Inhale and exhale'},{w:'MINDFUL',h:'Being present'},{w:'BALANCE',h:'Equilibrium'},{w:'SERENE',h:'Tranquil and calm'},{w:'FOCUS',h:'Concentrate'},{w:'ENERGY',h:'Vitality'},{w:'PEACE',h:'Inner harmony'},{w:'STRENGTH',h:'Physical or mental power'},{w:'YOGA',h:'Mind-body practice'},{w:'RELAX',h:'Ease tension'},{w:'HEALTH',h:'State of well-being'},{w:'SLEEP',h:'Rest and recovery'},{w:'WATER',h:'Essential hydration'},{w:'SMILE',h:'Facial expression of happiness'},{w:'GRATITUDE',h:'Feeling thankful'},{w:'COURAGE',h:'Bravery'},{w:'WISDOM',h:'Deep understanding'},{w:'KINDNESS',h:'Being considerate'}];
let wScore=0,wStreak=0,wIdx=0,wWordTimer=null,wTimeLeft=30,wCurrentWord='',wHintUsed=false,shuffledWords=[];
function scramble(w){const a=w.split('');for(let i=a.length-1;i>0;i--){const j=Math.floor(Math.random()*(i+1));[a[i],a[j]]=[a[j],a[i]];}return a.join('')===w&&w.length>1?scramble(w):a.join('');}
function startWordGame(){shuffledWords=[...WORDS].sort(()=>Math.random()-0.5);wIdx=0;wScore=0;wStreak=0;document.getElementById('wordScore').textContent='0';document.getElementById('wordStreak').textContent='0';loadWord();}
function loadWord(){if(wIdx>=shuffledWords.length){wIdx=0;shuffledWords.sort(()=>Math.random()-0.5);}wCurrentWord=shuffledWords[wIdx].w;wHintUsed=false;document.getElementById('scrambledWord').textContent=scramble(wCurrentWord);document.getElementById('wordHint').textContent=`Hint: ${shuffledWords[wIdx].h} (${wCurrentWord.length} letters)`;document.getElementById('wordInput').value='';document.getElementById('wordResult').textContent='';document.getElementById('wordInput').focus();clearInterval(wWordTimer);wTimeLeft=30;document.getElementById('wordTimer').textContent=`⏱ ${wTimeLeft}`;document.getElementById('wordTimer').style.color='#a78bfa';wWordTimer=setInterval(()=>{wTimeLeft--;document.getElementById('wordTimer').textContent=`⏱ ${wTimeLeft}`;if(wTimeLeft<=10)document.getElementById('wordTimer').style.color='#ff9a9a';if(wTimeLeft<=0){clearInterval(wWordTimer);document.getElementById('wordResult').textContent=`⏰ Time's up! It was "${wCurrentWord}"`;document.getElementById('wordResult').style.color='#ff9a9a';wStreak=0;document.getElementById('wordStreak').textContent='0';setTimeout(()=>{wIdx++;loadWord();},1800);}},1000);}
function checkWord(){const guess=document.getElementById('wordInput').value.trim().toUpperCase();if(!guess)return;if(guess===wCurrentWord){clearInterval(wWordTimer);const bonus=wHintUsed?5:10;const timeBonus=Math.floor(wTimeLeft/3);wScore+=bonus+timeBonus;wStreak++;document.getElementById('wordScore').textContent=wScore;document.getElementById('wordStreak').textContent=wStreak;document.getElementById('wordResult').textContent=`✅ Correct! +${bonus+timeBonus} pts`;document.getElementById('wordResult').style.color='#6ee7b7';setTimeout(()=>{wIdx++;loadWord();},1200);}else{document.getElementById('wordResult').textContent='❌ Try again!';document.getElementById('wordResult').style.color='#ff9a9a';document.getElementById('wordInput').value='';wStreak=0;document.getElementById('wordStreak').textContent='0';}}
function skipWord(){clearInterval(wWordTimer);document.getElementById('wordResult').textContent=`⏭ Skipped — it was "${wCurrentWord}"`;document.getElementById('wordResult').style.color='#fde68a';wStreak=0;document.getElementById('wordStreak').textContent='0';setTimeout(()=>{wIdx++;loadWord();},1200);}
function showHint(){if(!wHintUsed){wHintUsed=true;const half=wCurrentWord.slice(0,Math.ceil(wCurrentWord.length/2));document.getElementById('wordResult').textContent=`💡 Starts with: ${half}...`;document.getElementById('wordResult').style.color='#fde68a';}}
startWordGame();

// ===== 2048 =====
let g2048=[], g2048Score=0, g2048Best=0;
const COLORS={'2':'#776e65','4':'#776e65','8':'#f59563','16':'#f59563','32':'#f67c5f','64':'#f65e3b','128':'#edcf72','256':'#edcc61','512':'#edc850','1024':'#edc53f','2048':'#edc22e'};
const BGCOLOR={'2':'#eee4da','4':'#ede0c8','8':'#f2b179','16':'#f59563','32':'#f67c5f','64':'#f65e3b','128':'#edcf72','256':'#edcc61','512':'#edc850','1024':'#edc53f','2048':'#edc22e'};
function new2048(){g2048=Array(16).fill(0);g2048Score=0;addTile2048();addTile2048();render2048();}
function addTile2048(){const empty=g2048.map((v,i)=>v===0?i:-1).filter(i=>i>=0);if(!empty.length)return;const idx=empty[Math.floor(Math.random()*empty.length)];g2048[idx]=Math.random()<0.9?2:4;}
function render2048(){const b=document.getElementById('board2048');b.innerHTML='';g2048.forEach(v=>{const cell=document.createElement('div');cell.className='g2048-cell';const bg=v?BGCOLOR[v]||'#3d3a6e':'rgba(255,255,255,0.05)';const col=v>4?'#f9f6f2':'#776e65';cell.style.cssText=`background:${bg};color:${col};font-size:${v>=1000?'0.85rem':v>=100?'1rem':'1.2rem'}`;cell.textContent=v||'';b.appendChild(cell);});document.getElementById('s2048').textContent=g2048Score;document.getElementById('b2048').textContent=g2048Best=Math.max(g2048Best,g2048Score);}
function slide2048(row){const r=row.filter(v=>v!==0);for(let i=0;i<r.length-1;i++){if(r[i]===r[i+1]){r[i]*=2;g2048Score+=r[i];r[i+1]=0;}}const out=r.filter(v=>v!==0);while(out.length<4)out.push(0);return out;}
function move2048(dir){const prev=[...g2048];if(dir==='left'){for(let r=0;r<4;r++){const row=g2048.slice(r*4,r*4+4);const s=slide2048(row);for(let c=0;c<4;c++)g2048[r*4+c]=s[c];}}
else if(dir==='right'){for(let r=0;r<4;r++){const row=g2048.slice(r*4,r*4+4).reverse();const s=slide2048(row).reverse();for(let c=0;c<4;c++)g2048[r*4+c]=s[c];}}
else if(dir==='up'){for(let c=0;c<4;c++){const col=[g2048[c],g2048[4+c],g2048[8+c],g2048[12+c]];const s=slide2048(col);for(let r=0;r<4;r++)g2048[r*4+c]=s[r];}}
else if(dir==='down'){for(let c=0;c<4;c++){const col=[g2048[12+c],g2048[8+c],g2048[4+c],g2048[c]];const s=slide2048(col).reverse();for(let r=0;r<4;r++)g2048[r*4+c]=s[r];}}
if(prev.some((v,i)=>v!==g2048[i])){addTile2048();render2048();}
if(g2048.includes(2048)){setTimeout(()=>alert('🎉 You reached 2048! Amazing!'),100);}}
document.addEventListener('keydown',e=>{if(!document.getElementById('panel-g2048').classList.contains('active'))return;const map={ArrowLeft:'left',ArrowRight:'right',ArrowUp:'up',ArrowDown:'down'};if(map[e.key]){e.preventDefault();move2048(map[e.key]);}});
// Touch swipe for 2048
let tx=0,ty=0;
document.getElementById('board2048').addEventListener('touchstart',e=>{tx=e.touches[0].clientX;ty=e.touches[0].clientY;},{passive:true});
document.getElementById('board2048').addEventListener('touchend',e=>{const dx=e.changedTouches[0].clientX-tx,dy=e.changedTouches[0].clientY-ty;if(Math.abs(dx)>Math.abs(dy)){move2048(dx>0?'right':'left');}else{move2048(dy>0?'down':'up');}},{passive:true});
new2048();
</script>
</body></html>
""")
# ─────────────────────────────────────────────
# ACTIVITY PAGE (kept intact)
# ─────────────────────────────────────────────

@app.route("/activity")
def activity():
    if "user" not in session:
        return redirect("/login")
    return render_template_string("""
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

/* POSE CARDS */
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
pose-benefit{display:inline-block;padding:3px 10px;border-radius:99px;font-size:0.72rem;font-weight:700;margin-top:4px;}
.tag-yoga{background:rgba(52,211,153,0.15);color:#34d399;}
.tag-stretch{background:rgba(92,200,245,0.15);color:#5bc8f5;}
.tag-strength{background:rgba(167,139,250,0.15);color:#a78bfa;}
.tag-breathing{background:rgba(249,168,212,0.15);color:#f9a8d4;}

/* MODAL */
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
.timer-ring{display:inline-flex;flex-direction:column;align-items:center;gap:4px;}
.timer-count{font-size:3rem;font-weight:900;color:#34d399;line-height:1;}
.timer-label{color:rgba(255,255,255,0.4);font-size:0.78rem;}
.modal-actions{display:flex;gap:10px;justify-content:center;}
.modal-btn{padding:11px 24px;border:none;border-radius:12px;font-family:'Nunito',sans-serif;font-weight:800;font-size:0.88rem;cursor:pointer;transition:all 0.2s;}
.modal-btn.primary{background:linear-gradient(135deg,#34d399,#5bc8f5);color:#fff;}
.modal-btn.secondary{background:rgba(255,255,255,0.07);border:1.5px solid rgba(255,255,255,0.12);color:rgba(255,255,255,0.6);}
.modal-btn:hover{transform:translateY(-2px);}

/* WORKOUT BUILDER */
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
.progress-ring{width:36px;height:36px;position:relative;flex-shrink:0;}
.progress-ring svg{transform:rotate(-90deg);}
.progress-ring circle{transition:stroke-dashoffset 0.5s;}

/* BREATHING */
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
</style>
</head>
<body>
<nav class="topnav"><span class="brand">MindSpace 🌿</span><div class="nav-links"><a href="/">🏠 Home</a><a href="/logout">👋 Logout</a></div></nav>
<div class="page-wrap">
    <h1 class="page-title">🧘 Physical Activity</h1>
    <p class="page-sub">Yoga poses, stretches, strength training & breathing exercises</p>
    <div class="section-tabs">
        <button class="tab-btn active" onclick="switchTab('yoga',this)">🧘 Yoga Poses</button>
        <button class="tab-btn" onclick="switchTab('stretch',this)">🤸 Stretches</button>
        <button class="tab-btn" onclick="switchTab('strength',this)">💪 Strength</button>
        <button class="tab-btn" onclick="switchTab('breathing',this)">🌬️ Breathing</button>
        <button class="tab-btn" onclick="switchTab('workout',this)">📋 Workout Plan</button>
    </div>

    <!-- YOGA -->
    <div class="section-panel active" id="panel-yoga">
        <div class="pose-grid" id="yogaGrid"></div>
    </div>
    <!-- STRETCH -->
    <div class="section-panel" id="panel-stretch">
        <div class="pose-grid" id="stretchGrid"></div>
    </div>
    <!-- STRENGTH -->
    <div class="section-panel" id="panel-strength">
        <div class="pose-grid" id="strengthGrid"></div>
    </div>
    <!-- BREATHING -->
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
    <!-- WORKOUT PLAN -->
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
<!-- POSE DETAIL MODAL -->
<div class="pose-modal" id="poseModal">
    <div class="pose-modal-box">
        <div class="modal-icon" id="mIcon"></div>
        <div class="modal-title" id="mTitle"></div>
        <div class="modal-sub" id="mSub"></div>
        <div class="modal-steps" id="mSteps"></div>
        <div class="modal-timer">
            <div class="timer-ring">
                <div class="timer-count" id="mTimerNum">—</div>
                <div class="timer-label" id="mTimerLabel">seconds</div>
            </div>
        </div>
        <div class="modal-actions">
            <button class="modal-btn primary" id="mStartBtn" onclick="togglePoseTimer()">▶ Start Timer</button>
            <button class="modal-btn secondary" onclick="closeModal()">✕ Close</button>
        </div>
    </div>
</div>

<script>
function switchTab(tab,btn){document.querySelectorAll('.tab-btn').forEach(b=>b.classList.remove('active'));document.querySelectorAll('.section-panel').forEach(p=>p.classList.remove('active'));btn.classList.add('active');document.getElementById('panel-'+tab).classList.add('active');}

const YOGA=[
    {icon:'🧘',name:'Mountain Pose',sanskrit:'Tadasana',duration:60,benefit:'yoga',desc:'Foundation of all standing poses. Builds awareness and grounding.',steps:['Stand with feet together, weight evenly distributed','Engage thighs, lift kneecaps gently','Lengthen spine, roll shoulders back and down','Arms at sides, palms facing forward','Breathe deeply, hold steady gaze']},
    {icon:'🌲',name:'Tree Pose',sanskrit:'Vrksasana',duration:45,benefit:'yoga',desc:'Improves balance, focus, and inner calm.',steps:['Stand on one leg, find a fixed gaze point','Place foot on inner thigh or calf (not knee)','Press palms together at heart center','Breathe steadily, engage core','Hold 30–60 seconds each side']},
    {icon:'🐕',name:'Downward Dog',sanskrit:'Adho Mukha',duration:60,benefit:'yoga',desc:'Energizes the body and stretches the entire back.',steps:['Start on hands and knees','Tuck toes, lift hips up and back','Straighten arms, press palms firmly','Heels move toward floor','Head between arms, neck relaxed']},
    {icon:'🌍',name:"Child's Pose",sanskrit:'Balasana',duration:90,benefit:'yoga',desc:'Deeply restorative, calms the nervous system.',steps:["Kneel, sit back on heels",'Fold forward, forehead to mat','Arms extended forward or alongside body','Breathe into lower back','Stay 1–3 minutes for deep rest']},
    {icon:'🐍',name:'Cobra Pose',sanskrit:'Bhujangasana',duration:45,benefit:'yoga',desc:'Opens chest and strengthens the spine.',steps:['Lie face down, hands under shoulders','Elbows close to body','Press into hands, lift chest off floor','Roll shoulders back, open collar bones','Keep lower belly on mat, breathe']},
    {icon:'⚔️',name:'Warrior I',sanskrit:'Virabhadrasana I',duration:60,benefit:'yoga',desc:'Builds strength, stamina, and confidence.',steps:['Step right foot forward into lunge','Back foot at 45° angle','Front knee over ankle','Raise arms overhead, palms together','Square hips to front, hold steadily']},
    {icon:'🏹',name:'Warrior II',sanskrit:'Virabhadrasana II',duration:60,benefit:'yoga',desc:'Strengthens legs and opens hips and chest.',steps:['Wide stance, feet 4 feet apart','Front foot forward, back foot 90°','Bend front knee over ankle','Arms extended parallel to floor','Gaze over front fingers, breathe']},
    {icon:'🌙',name:'Crescent Lunge',sanskrit:'Anjaneyasana',duration:45,benefit:'yoga',desc:'Opens hip flexors, lifts energy.',steps:['Low lunge with back knee down','Lift arms overhead, lengthen spine','Sink hips forward and down','Breathe into front hip crease','Hold and switch sides']}
];
const STRETCHES=[
{icon:'🦵',name:'Hamstring Stretch',duration:45,benefit:'stretch',desc:'Releases tight hamstrings and lower back.',steps:['Sit on floor, legs extended forward','Reach hands toward feet','Keep back straight, fold from hips','Breathe and relax deeper each exhale','Hold 30–60 seconds each side']},
    {icon:'🔄',name:'Seated Spinal Twist',duration:45,benefit:'stretch',desc:'Relieves spinal tension and improves rotation.',steps:['Sit with legs extended','Bend right knee, foot outside left thigh','Left elbow on right knee','Right hand behind you for support','Twist on each exhale, hold 30s each side']},
    {icon:'🦈',name:'Hip Flexor Stretch',duration:60,benefit:'stretch',desc:'Counters prolonged sitting, opens hips.',steps:['Kneel on left knee, right foot forward','Push hips gently forward','Lift torso, tuck pelvis slightly','Arms on hips or raised overhead','Hold 45s, breathe, switch sides']},
    {icon:'🐈',name:'Cat-Cow Stretch',duration:60,benefit:'stretch',desc:'Warms the spine, relieves back tension.',steps:['On all fours, neutral spine','Inhale — drop belly, lift gaze (Cow)','Exhale — round back to ceiling (Cat)','Sync breath with movement','Repeat 8–10 slow cycles']},
    {icon:'🌿',name:'Chest Opener',duration:45,benefit:'stretch',desc:'Counteracts hunching, opens the chest.',steps:['Clasp hands behind back','Squeeze shoulder blades together','Lift chest, gaze slightly upward','Breathe into chest, feel the opening','Hold 30 seconds, relax and repeat']},
    {icon:'🦋',name:'Butterfly Stretch',duration:60,benefit:'stretch',desc:'Opens inner thighs and groin gently.',steps:['Sit, soles of feet together','Hold feet with both hands','Gently press knees toward floor','Sit tall, breathe deeply','Lean slightly forward for deeper stretch']}
];
const STRENGTH=[
    {icon:'💥',name:'Push-Ups',duration:30,benefit:'strength',desc:'Upper body strength — chest, shoulders, triceps.',steps:['Hands wider than shoulder width','Body in straight line from head to heels','Lower chest to floor, elbows at 45°','Push back to start explosively','3 sets of 10–15 reps, rest 60s between']},
    {icon:'🏋️',name:'Bodyweight Squats',duration:40,benefit:'strength',desc:'Builds legs, glutes, and core stability.',steps:['Feet shoulder-width apart, toes slightly out','Arms forward for balance','Sit back and down, knees tracking toes','Thighs parallel to floor at bottom','Drive through heels to stand — 3×15']},
    {icon:'🦅',name:'Plank Hold',duration:60,benefit:'strength',desc:'Core strength and total body stability.',steps:['Forearms on ground, elbows under shoulders','Body in straight line, hips neutral','Engage abs, glutes, and quads','Breathe steadily, do not hold breath','Hold 30–60 seconds, build over time']},
    {icon:'🐸',name:'Glute Bridges',duration:45,benefit:'strength',desc:'Activates glutes and relieves lower back.',steps:['Lie on back, knees bent, feet flat','Drive hips up toward ceiling','Squeeze glutes at top, hold 2 seconds','Lower slowly with control','3 sets of 15 reps']},
    {icon:'🦩',name:'Single-Leg Balance',duration:45,benefit:'strength',desc:'Builds ankle stability and leg strength.',steps:['Stand on one foot, slight knee bend','Raise opposite knee to hip height','Hold 30 seconds, switch legs','Add small hops for challenge','3 sets per leg']},
    {icon:'🔥',name:'Burpees',duration:30,benefit:'strength',desc:'Full body cardio and strength combined.',steps:['Stand, drop hands to floor','Jump feet back to plank','Do one push-up (optional)','Jump feet forward to hands','Jump up with arms overhead — 10 reps']}
];

function renderGrid(data,gridId,cls){const grid=document.getElementById(gridId);grid.innerHTML='';data.forEach((p,i)=>{const card=document.createElement('div');card.className=`pose-card ${cls}`;card.innerHTML=`<div class="pose-icon">${p.icon}</div><div class="pose-name">${p.name}</div>${p.sanskrit?`<div class="pose-duration">${p.sanskrit}</div>`:'<div class="pose-duration">&nbsp;</div>'}<div class="pose-duration">⏱ ${p.duration}s</div><span class="pose-benefit tag-${p.benefit}">${p.benefit.charAt(0).toUpperCase()+p.benefit.slice(1)}</span>`;card.onclick=()=>openModal(p);grid.appendChild(card);});}
renderGrid(YOGA,'yogaGrid','yoga');renderGrid(STRETCHES,'stretchGrid','stretch');renderGrid(STRENGTH,'strengthGrid','strength');

let poseTimerInterval=null,poseTimerRunning=false,poseTimerLeft=0;
function openModal(p){document.getElementById('mIcon').textContent=p.icon;document.getElementById('mTitle').textContent=p.name;document.getElementById('mSub').textContent=p.desc;document.getElementById('mSteps').innerHTML=p.steps.map((s,i)=>`<div class="modal-step"><div class="step-num">${i+1}</div><div class="step-text">${s}</div></div>`).join('');poseTimerLeft=p.duration;document.getElementById('mTimerNum').textContent=poseTimerLeft;document.getElementById('mTimerLabel').textContent='seconds';document.getElementById('mStartBtn').textContent='▶ Start Timer';poseTimerRunning=false;clearInterval(poseTimerInterval);document.getElementById('poseModal').classList.add('show');}
function closeModal(){document.getElementById('poseModal').classList.remove('show');clearInterval(poseTimerInterval);poseTimerRunning=false;}
function togglePoseTimer(){if(poseTimerRunning){clearInterval(poseTimerInterval);poseTimerRunning=false;document.getElementById('mStartBtn').textContent='▶ Resume';}else{poseTimerRunning=true;document.getElementById('mStartBtn').textContent='⏸ Pause';poseTimerInterval=setInterval(()=>{poseTimerLeft--;document.getElementById('mTimerNum').textContent=poseTimerLeft;if(poseTimerLeft<=0){clearInterval(poseTimerInterval);poseTimerRunning=false;document.getElementById('mTimerNum').textContent='✅';document.getElementById('mTimerLabel').textContent='Done!';document.getElementById('mStartBtn').textContent='✅ Complete!';}},1000);}}

// ===== BREATHING ENGINE =====
const BREATH_TYPES={
    '478':{phases:['Inhale','Hold','Exhale'],times:[4,7,8],desc:'4-7-8: Inhale 4s, Hold 7s, Exhale 8s — reduces anxiety fast'},
    'box':{phases:['Inhale','Hold','Exhale','Hold'],times:[4,4,4,4],desc:'Box Breathing: 4s each phase — used by Navy SEALs for focus'},
    'belly':{phases:['Inhale','Exhale'],times:[5,5],desc:'Belly Breathing: 5s in, 5s out — deepest relaxation response'},
    'coherent':{phases:['Inhale','Exhale'],times:[5,5],desc:'Coherent: 5-5 rhythm — balances heart rate variability'}
};
let breathType='478',breathRunning=false,breathInterval=null,breathPhaseIdx=0,breathSecLeft=0,breathCycles=0;
function setBreathType(type,btn){breathType=type;document.querySelectorAll('.breath-type-btn').forEach(b=>b.classList.remove('active'));btn.classList.add('active');document.getElementById('breathInstructions').textContent=BREATH_TYPES[type].desc;resetBreath();}
function resetBreath(){clearInterval(breathInterval);breathRunning=false;breathPhaseIdx=0;breathCycles=0;breathSecLeft=BREATH_TYPES[breathType].times[0];document.getElementById('breathPhase').textContent='Press Start';document.getElementById('breathCountNum').textContent='';document.getElementById('breathStart').textContent='▶ Start';document.getElementById('cyclesCount').textContent='Cycles completed: 0';document.getElementById('breathCircle').className='breath-circle';}
function toggleBreath(){if(breathRunning){clearInterval(breathInterval);breathRunning=false;document.getElementById('breathStart').textContent='▶ Resume';}else{breathRunning=true;document.getElementById('breathStart').textContent='⏸ Pause';runBreathStep();breathInterval=setInterval(()=>{breathSecLeft--;if(breathSecLeft<=0){breathPhaseIdx++;const phases=BREATH_TYPES[breathType].phases;if(breathPhaseIdx>=phases.length){breathPhaseIdx=0;breathCycles++;document.getElementById('cyclesCount').textContent=`Cycles completed: ${breathCycles}`;}breathSecLeft=BREATH_TYPES[breathType].times[breathPhaseIdx];runBreathStep();}else{document.getElementById('breathCountNum').textContent=breathSecLeft;}},1000);}}
function runBreathStep(){const phase=BREATH_TYPES[breathType].phases[breathPhaseIdx];document.getElementById('breathPhase').textContent=phase;document.getElementById('breathCountNum').textContent=breathSecLeft;const circle=document.getElementById('breathCircle');circle.className='breath-circle';if(phase==='Inhale')setTimeout(()=>circle.classList.add('inhale'),50);else if(phase==='Exhale')setTimeout(()=>circle.classList.add('exhale'),50);else setTimeout(()=>circle.classList.add('hold'),50);}

// ===== WORKOUT BUILDER =====
const ALL_EXERCISES={calm:[{icon:'🌍',name:"Child's Pose",detail:'60s hold'},{icon:'🐈',name:'Cat-Cow Stretch',detail:'10 cycles'},{icon:'🌬️',name:'4-7-8 Breathing',detail:'4 cycles'},{icon:'🧘',name:'Mountain Pose',detail:'60s hold'},{icon:'🔄',name:'Seated Spinal Twist',detail:'45s each side'},{icon:'🌙',name:'Legs Up Wall',detail:'3 minutes'}],
energy:[{icon:'💥',name:'Jumping Jacks',detail:'3×20 reps'},{icon:'🔥',name:'Burpees',detail:'3×10 reps'},{icon:'🏋️',name:'Bodyweight Squats',detail:'3×15 reps'},{icon:'🦅',name:'High Knees',detail:'3×30s'},{icon:'💥',name:'Push-Ups',detail:'3×12 reps'},{icon:'⚡',name:'Mountain Climbers',detail:'3×20s'}],
strength:[{icon:'💥',name:'Push-Ups',detail:'4×15 reps'},{icon:'🏋️',name:'Squats',detail:'4×20 reps'},{icon:'🦅',name:'Plank Hold',detail:'3×60s'},{icon:'🐸',name:'Glute Bridges',detail:'3×15 reps'},{icon:'🦩',name:'Lunges',detail:'3×12 each leg'},{icon:'🔥',name:'Tricep Dips',detail:'3×12 reps'}],
flex:[{icon:'🦋',name:'Butterfly Stretch',detail:'60s hold'},{icon:'🦵',name:'Hamstring Stretch',detail:'45s each side'},{icon:'🦈',name:'Hip Flexor Stretch',detail:'60s each side'},{icon:'🌿',name:'Chest Opener',detail:'45s hold'},{icon:'🐍',name:'Cobra Pose',detail:'30s hold'},{icon:'🐕',name:'Downward Dog',detail:'60s hold'}]};
function buildWorkout(){const goal=document.getElementById('wGoal').value;const dur=parseInt(document.getElementById('wDur').value);const exes=ALL_EXERCISES[goal];const count=dur===10?4:dur===20?6:8;const selected=exes.slice(0,Math.min(count,exes.length));const plan=document.getElementById('workoutPlan');plan.innerHTML='';selected.forEach((e,i)=>{plan.innerHTML+=`<div class="workout-exercise"><div class="ex-num">${i+1}</div><div class="ex-info"><div class="ex-name">${e.name}</div><div class="ex-detail">${e.detail}</div></div><div class="ex-icon">${e.icon}</div></div>`;});if(!plan.innerHTML)plan.innerHTML='<p style="color:rgba(255,255,255,0.4);text-align:center;padding:20px;">Select options above and click Generate!</p>';}
buildWorkout();
</script>
</body></html>
""")
# ─────────────────────────────────────────────
# PROFILE
# ─────────────────────────────────────────────

@app.route("/profile")
def profile():
    if "user" not in session:
        return redirect("/login")
    conn = sqlite3.connect("app.db")
    cur  = conn.cursor()
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
<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>MindSpace — Profile</title>
<link href="https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700;800;900&family=Playfair+Display:wght@700&display=swap" rel="stylesheet">
<style>*,*::before,*::after{box-sizing:border-box;margin:0;padding:0;}body{font-family:'Nunito',sans-serif;min-height:100vh;background:#0d0d1a;color:#fff;display:flex;flex-direction:column;align-items:center;padding:90px 16px 40px;position:relative;}body::before{content:'';position:fixed;inset:0;background:radial-gradient(ellipse 80% 60% at 20% 40%,rgba(100,200,255,0.1) 0%,transparent 60%);animation:aurora 10s ease-in-out infinite alternate;pointer-events:none;}@keyframes aurora{0%{transform:scale(1);}100%{transform:scale(1.08) rotate(-2deg);}}
.topnav{position:fixed;top:0;left:0;right:0;display:flex;justify-content:space-between;align-items:center;padding:14px 24px;background:rgba(13,13,26,0.85);backdrop-filter:blur(16px);border-bottom:1px solid rgba(255,255,255,0.07);z-index:100;}.brand{font-family:'Playfair Display',serif;font-size:1.2rem;color:#fff;}.nav-links a{color:rgba(255,255,255,0.5);text-decoration:none;font-size:0.82rem;font-weight:700;margin-left:12px;padding:6px 14px;border-radius:20px;border:1px solid rgba(255,255,255,0.1);transition:all 0.2s;}.nav-links a:hover{color:#fff;background:rgba(255,255,255,0.08);}
.profile-card{position:relative;z-index:1;background:rgba(255,255,255,0.04);backdrop-filter:blur(24px);border:1px solid rgba(255,255,255,0.09);border-radius:28px;padding:36px;width:100%;max-width:440px;}
.avatar{width:80px;height:80px;border-radius:50%;background:linear-gradient(135deg,#5bc8f5,#a78bfa);display:flex;align-items:center;justify-content:center;font-size:2.5rem;font-weight:900;color:#fff;margin:0 auto 16px;}.profile-name{font-family:'Playfair Display',serif;font-size:1.6rem;text-align:center;margin-bottom:4px;}.profile-mobile{text-align:center;color:rgba(255,255,255,0.4);font-size:0.85rem;margin-bottom:24px;}
.stats-grid{display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px;margin-bottom:24px;}.stat-box{background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.08);border-radius:16px;padding:14px;text-align:center;}.stat-val{font-size:1.4rem;font-weight:900;background:linear-gradient(135deg,#5bc8f5,#a78bfa);-webkit-background-clip:text;-webkit-text-fill-color:transparent;}.stat-label{font-size:0.7rem;color:rgba(255,255,255,0.4);margin-top:4px;}
.back-btn{display:inline-flex;align-items:center;gap:8px;padding:11px 22px;border:1.5px solid rgba(255,255,255,0.12);border-radius:99px;color:rgba(255,255,255,0.6);text-decoration:none;font-weight:700;font-size:0.85rem;transition:all 0.2s;background:rgba(255,255,255,0.04);}.back-btn:hover{color:#fff;background:rgba(255,255,255,0.08);}
</style></head><body>
<nav class="topnav"><span class="brand">MindSpace 🌿</span><div class="nav-links"><a href="/">🏠 Home</a><a href="/logout">👋 Logout</a></div></nav>
<div class="profile-card"><div class="avatar">{{ user[0][0].upper() }}</div><div class="profile-name">{{ user[0] }}</div><div class="profile-mobile">📱 {{ user[1] or 'No mobile on file' }}</div>
<div class="stats-grid">
<div class="stat-box"><div class="stat-val">{{ count }}</div><div class="stat-label">Check-ins</div></div>
<div class="stat-box"><div class="stat-val">{{ "%.0f"|format(avg) if avg else '—' }}</div><div class="stat-label">Avg Score</div></div>
<div class="stat-box"><div class="stat-val">{{ mood_count }}</div><div class="stat-label">Mood Logs</div></div>
</div>
<a class="back-btn" href="/">← Back to Home</a></div>
</body></html>
""", user=user, count=count, avg=avg, mood_count=mood_count)

# ─────────────────────────────────────────────
# SETTINGS
# ─────────────────────────────────────────────

@app.route("/settings")
def settings():
    if "user" not in session:
        return redirect("/login")
    return render_template_string("""
<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>MindSpace — Settings</title>
<link href="https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700;800;900&family=Playfair+Display:wght@700&display=swap" rel="stylesheet">
<style>*,*::before,*::after{box-sizing:border-box;margin:0;padding:0;}body{font-family:'Nunito',sans-serif;min-height:100vh;background:#0d0d1a;color:#fff;display:flex;flex-direction:column;align-items:center;padding:90px 16px 40px;position:relative;}body::before{content:'';position:fixed;inset:0;background:radial-gradient(ellipse 80% 60% at 20% 40%,rgba(100,200,255,0.1) 0%,transparent 60%);animation:aurora 10s ease-in-out infinite alternate;pointer-events:none;}@keyframes aurora{0%{transform:scale(1);}100%{transform:scale(1.08) rotate(-2deg);}}
.topnav{position:fixed;top:0;left:0;right:0;display:flex;justify-content:space-between;align-items:center;padding:14px 24px;background:rgba(13,13,26,0.85);backdrop-filter:blur(16px);border-bottom:1px solid rgba(255,255,255,0.07);z-index:100;}.brand{font-family:'Playfair Display',serif;font-size:1.2rem;color:#fff;}.nav-links a{color:rgba(255,255,255,0.5);text-decoration:none;font-size:0.82rem;font-weight:700;margin-left:12px;padding:6px 14px;border-radius:20px;border:1px solid rgba(255,255,255,0.1);transition:all 0.2s;}.nav-links a:hover{color:#fff;background:rgba(255,255,255,0.08);}
.settings-card{position:relative;z-index:1;background:rgba(255,255,255,0.04);backdrop-filter:blur(24px);border:1px solid rgba(255,255,255,0.09);border-radius:28px;padding:32px 28px;width:100%;max-width:420px;}
h2{font-family:'Playfair Display',serif;font-size:1.6rem;margin-bottom:24px;}
.setting-row{display:flex;align-items:center;justify-content:space-between;padding:14px 0;border-bottom:1px solid rgba(255,255,255,0.06);}.setting-label{font-weight:700;font-size:0.92rem;color:rgba(255,255,255,0.8);}.setting-desc{font-size:0.75rem;color:rgba(255,255,255,0.35);margin-top:2px;}
.toggle-switch{position:relative;width:44px;height:26px;cursor:pointer;}.toggle-switch input{display:none;}.toggle-track{width:44px;height:26px;border-radius:13px;background:rgba(255,255,255,0.15);transition:background 0.3s;position:relative;}.toggle-switch input:checked + .toggle-track{background:linear-gradient(135deg,#5bc8f5,#a78bfa);}.toggle-thumb{position:absolute;top:3px;left:3px;width:20px;height:20px;border-radius:50%;background:#fff;box-shadow:0 2px 6px rgba(0,0,0,0.3);transition:transform 0.3s cubic-bezier(0.34,1.56,0.64,1);}.toggle-switch input:checked + .toggle-track .toggle-thumb{transform:translateX(18px);}
.back-btn{display:inline-flex;align-items:center;gap:8px;padding:11px 22px;border:1.5px solid rgba(255,255,255,0.12);border-radius:99px;color:rgba(255,255,255,0.6);text-decoration:none;font-weight:700;font-size:0.85rem;transition:all 0.2s;background:rgba(255,255,255,0.04);margin-top:20px;}.back-btn:hover{color:#fff;background:rgba(255,255,255,0.08);}
.api-info{background:rgba(99,102,241,0.08);border:1px solid rgba(99,102,241,0.2);border-radius:12px;padding:12px 16px;margin-bottom:20px;font-size:0.82rem;color:rgba(255,255,255,0.6);line-height:1.6;}
</style></head><body>
<nav class="topnav"><span class="brand">MindSpace 🌿</span><div class="nav-links"><a href="/">🏠 Home</a><a href="/logout">👋 Logout</a></div></nav>
<div class="settings-card"><h2>⚙️ Settings</h2>
<div class="api-info">🤖 <strong>AI Therapist:</strong> Set the <code>ANTHROPIC_API_KEY</code> environment variable to enable Claude-powered intelligent responses. Without it, the app uses smart rule-based responses.</div>
<div class="setting-row"><div><div class="setting-label">🌙 Dark Mode</div><div class="setting-desc">Toggle dark / light theme</div></div><label class="toggle-switch"><input type="checkbox" id="darkToggle" onchange="toggleTheme(this)"><div class="toggle-track"><div class="toggle-thumb"></div></div></label></div>
<div class="setting-row"><div><div class="setting-label">🔔 Reminders</div><div class="setting-desc">Daily wellness check-in reminder</div></div><label class="toggle-switch"><input type="checkbox" checked><div class="toggle-track"><div class="toggle-thumb"></div></div></label></div>
<div class="setting-row"><div><div class="setting-label">🎵 Ambient Sound</div><div class="setting-desc">Auto-play sound therapy</div></div><label class="toggle-switch"><input type="checkbox"><div class="toggle-track"><div class="toggle-thumb"></div></div></label></div>
<a class="back-btn" href="/">← Back to Home</a></div>
<script>const saved=localStorage.getItem('mindspace-theme');document.getElementById('darkToggle').checked=saved!=='light';function toggleTheme(cb){localStorage.setItem('mindspace-theme',cb.checked?'dark':'light');}</script>
</body></html>
""")

# ─────────────────────────────────────────────
# HISTORY
# ─────────────────────────────────────────────

@app.route("/history")
def history():
    if "user" not in session:
        return redirect("/login")
    conn = sqlite3.connect("app.db")
    cur  = conn.cursor()
    cur.execute("SELECT score, status, created_at FROM results WHERE username=? ORDER BY id DESC LIMIT 20", (session["user"],))
    rows = cur.fetchall()
    conn.close()
    data   = [r[0] for r in reversed(rows)]
    labels = [r[2][:10] if r[2] else str(i+1) for i,r in enumerate(reversed(rows))]
    return render_template_string("""
<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>MindSpace — History</title>
<link href="https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700;800;900&family=Playfair+Display:wght@700&display=swap" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0;}
body{font-family:'Nunito',sans-serif;min-height:100vh;background:#0d0d1a;color:#fff;display:flex;flex-direction:column;align-items:center;padding:100px 16px 40px;position:relative;}
body::before{content:'';position:fixed;inset:0;background:radial-gradient(ellipse 80% 60% at 20% 40%,rgba(100,200,255,0.1) 0%,transparent 60%);animation:aurora 10s ease-in-out infinite alternate;pointer-events:none;}
@keyframes aurora{0%{transform:scale(1);}100%{transform:scale(1.08) rotate(-2deg);}}
.topnav{position:fixed;top:0;left:0;right:0;display:flex;justify-content:space-between;align-items:center;padding:14px 24px;background:rgba(13,13,26,0.85);backdrop-filter:blur(16px);border-bottom:1px solid rgba(255,255,255,0.07);z-index:100;}
.brand{font-family:'Playfair Display',serif;font-size:1.2rem;color:#fff;}
.nav-links a{color:rgba(255,255,255,0.5);text-decoration:none;font-size:0.82rem;font-weight:700;margin-left:12px;padding:6px 14px;border-radius:20px;border:1px solid rgba(255,255,255,0.1);transition:all 0.2s;}
.nav-links a:hover{color:#fff;background:rgba(255,255,255,0.08);}
.history-wrap{position:relative;z-index:1;width:100%;max-width:560px;}
.history-title{font-family:'Playfair Display',serif;font-size:1.8rem;margin-bottom:4px;}
.history-sub{color:rgba(255,255,255,0.4);font-size:0.85rem;margin-bottom:24px;}
.chart-card{background:rgba(255,255,255,0.04);backdrop-filter:blur(20px);border:1px solid rgba(255,255,255,0.09);border-radius:24px;padding:24px;margin-bottom:20px;}
.chart-card h3{font-family:'Playfair Display',serif;font-size:1.1rem;margin-bottom:16px;}
.table-wrap{background:rgba(255,255,255,0.04);backdrop-filter:blur(20px);border:1px solid rgba(255,255,255,0.09);border-radius:24px;padding:24px;margin-bottom:20px;}
.table-wrap h3{font-family:'Playfair Display',serif;font-size:1.1rem;margin-bottom:16px;}
table{width:100%;border-collapse:collapse;}
th{text-align:left;color:rgba(255,255,255,0.4);font-size:0.75rem;font-weight:800;text-transform:uppercase;letter-spacing:1px;padding:8px 12px;border-bottom:1px solid rgba(255,255,255,0.08);}
td{padding:10px 12px;font-size:0.88rem;font-weight:600;border-bottom:1px solid rgba(255,255,255,0.05);}
tr:last-child td{border-bottom:none;}
.status-pill{display:inline-block;padding:3px 10px;border-radius:99px;font-size:0.75rem;font-weight:800;}
.back-btn{display:inline-flex;align-items:center;gap:8px;padding:11px 22px;border:1.5px solid rgba(255,255,255,0.12);border-radius:99px;color:rgba(255,255,255,0.6);text-decoration:none;font-weight:700;font-size:0.85rem;transition:all 0.2s;background:rgba(255,255,255,0.04);}
.back-btn:hover{color:#fff;background:rgba(255,255,255,0.08);}
.empty-state{text-align:center;padding:40px 20px;color:rgba(255,255,255,0.3);}
</style></head><body>
<nav class="topnav"><span class="brand">MindSpace 🌿</span><div class="nav-links"><a href="/">🏠 Home</a><a href="/test">🧠 Take Test</a><a href="/logout">👋 Logout</a></div></nav>
<div class="history-wrap">
    <h1 class="history-title">📈 Your History</h1>
    <p class="history-sub">Track your mental wellness journey over time</p>
    {% if rows %}
    <div class="chart-card">
        <h3>Wellness Score Trend</h3>
        <div style="position:relative;height:220px;"><canvas id="histChart"></canvas></div>
    </div>
    <div class="table-wrap">
        <h3>Recent Check-Ins</h3>
        <table>
            <thead><tr><th>#</th><th>Date</th><th>Score</th><th>Status</th></tr></thead>
            <tbody>
            {% for i, row in enumerate(rows) %}
            <tr>
                <td style="color:rgba(255,255,255,0.3);">{{ i+1 }}</td>
                <td>{{ row[2][:10] if row[2] else '—' }}</td>
                <td style="font-weight:800;color:#5bc8f5;">{{ row[0] }}</td>
                <td>
                    {% set status = row[1] %}
                    {% if 'Stable' in status %}<span class="status-pill" style="background:rgba(0,200,100,0.15);color:#34d399;">{{ status }}</span>
                    {% elif 'Mild' in status %}<span class="status-pill" style="background:rgba(230,184,0,0.15);color:#fbbf24;">{{ status }}</span>
                    {% elif 'Moderate' in status %}<span class="status-pill" style="background:rgba(255,128,0,0.15);color:#fb923c;">{{ status }}</span>
                    {% else %}<span class="status-pill" style="background:rgba(255,60,60,0.15);color:#f87171;">{{ status }}</span>{% endif %}
                </td>
            </tr>
            {% endfor %}
            </tbody>
        </table>
    </div>
    {% else %}
    <div class="table-wrap"><div class="empty-state"><div style="font-size:3rem;margin-bottom:12px;">🌱</div><div style="font-weight:800;margin-bottom:8px;">No check-ins yet</div><div style="font-size:0.85rem;">Take your first wellness test to start tracking your journey</div><a href="/test" style="display:inline-block;margin-top:16px;padding:10px 24px;background:linear-gradient(135deg,#5bc8f5,#a78bfa);border-radius:12px;color:#fff;text-decoration:none;font-weight:800;font-size:0.9rem;">🧠 Take Test Now</a></div></div>
    {% endif %}
    <a class="back-btn" href="/">← Back to Home</a>
</div>
{% if rows %}
<script>
const labels = {{ labels | tojson }};
const data   = {{ data   | tojson }};
const ctx = document.getElementById('histChart').getContext('2d');
new Chart(ctx, {
    type: 'line',
    data: {
        labels: labels,
        datasets: [{
            label: 'Wellness Score',
            data: data,
            borderColor: '#5bc8f5',
            backgroundColor: 'rgba(91,200,245,0.08)',
            borderWidth: 2.5,
            pointBackgroundColor: '#a78bfa',
            pointBorderColor: '#fff',
            pointBorderWidth: 2,
            pointRadius: 5,
            fill: true,
            tension: 0.4
        }]
    },
    options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
            x: { grid: { color: 'rgba(255,255,255,0.04)' }, ticks: { color: 'rgba(255,255,255,0.4)', font: { family: 'Nunito', size: 10 }, maxTicksLimit: 8 } },
            y: { grid: { color: 'rgba(255,255,255,0.04)' }, ticks: { color: 'rgba(255,255,255,0.4)', font: { family: 'Nunito', size: 11 } }, min: 0 }
        }
    }
});
</script>
{% endif %}
</body></html>
""", rows=rows, data=data, labels=labels, enumerate=enumerate)

# ─────────────────────────────────────────────
# RUN
# ─────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 55)
    print("  MindSpace 🌿 — Mental Wellness App")
    print("=" * 55)
    print(f"  AI Therapist: {'✅ Claude API enabled' if ANTHROPIC_API_KEY else '⚠️  Rule-based (set ANTHROPIC_API_KEY for Claude AI)'}")
    print("  Running at: http://localhost:5000")
    print("=" * 55)
    app.run(debug=True, host="0.0.0.0", port=5000)
