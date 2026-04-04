from flask import Flask, request, render_template_string, jsonify, redirect, session
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "supersecretkey"

# ---------------- DATABASE ----------------
def init_db():
    conn = sqlite3.connect("app.db")
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        score INTEGER,
        status TEXT
    )
    """)

    conn.commit()
    conn.close()

init_db()

# ---------------- QUESTIONS ----------------
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

# ---------------- SHARED STYLES ----------------
BASE_STYLES = """
@import url('https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700;800;900&family=Playfair+Display:wght@700&display=swap');

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

body {
    font-family: 'Nunito', sans-serif;
    min-height: 100vh;
    background: #0d0d1a;
    display: flex;
    justify-content: center;
    align-items: center;
    overflow: hidden;
    position: relative;
}

/* Animated aurora background */
body::before {
    content: '';
    position: fixed;
    inset: 0;
    background:
        radial-gradient(ellipse 80% 60% at 20% 40%, rgba(100,200,255,0.12) 0%, transparent 60%),
        radial-gradient(ellipse 60% 80% at 80% 20%, rgba(180,120,255,0.12) 0%, transparent 60%),
        radial-gradient(ellipse 70% 50% at 50% 90%, rgba(100,255,200,0.08) 0%, transparent 60%);
    animation: aurora 10s ease-in-out infinite alternate;
    pointer-events: none;
    z-index: 0;
}

@keyframes aurora {
    0%   { transform: scale(1) rotate(0deg); opacity: 0.8; }
    50%  { transform: scale(1.1) rotate(2deg); opacity: 1; }
    100% { transform: scale(1) rotate(-2deg); opacity: 0.8; }
}

/* Floating particles */
.particle {
    position: fixed;
    border-radius: 50%;
    pointer-events: none;
    animation: float linear infinite;
    z-index: 0;
}
@keyframes float {
    0%   { transform: translateY(110vh) scale(0); opacity: 0; }
    10%  { opacity: 0.5; }
    90%  { opacity: 0.3; }
    100% { transform: translateY(-10vh) scale(1.2); opacity: 0; }
}

.card {
    position: relative;
    z-index: 1;
    background: rgba(255,255,255,0.04);
    backdrop-filter: blur(24px);
    -webkit-backdrop-filter: blur(24px);
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 28px;
    padding: 40px 36px;
    width: 380px;
    box-shadow: 0 20px 60px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.1);
    animation: slideUp 0.7s cubic-bezier(0.16,1,0.3,1) both;
}

@keyframes slideUp {
    from { opacity: 0; transform: translateY(40px) scale(0.96); }
    to   { opacity: 1; transform: translateY(0) scale(1); }
}

h2 {
    font-family: 'Playfair Display', serif;
    font-size: 2rem;
    color: #fff;
    margin-bottom: 8px;
    letter-spacing: -0.5px;
}

.subtitle {
    color: rgba(255,255,255,0.45);
    font-size: 0.85rem;
    margin-bottom: 28px;
}

.input-group {
    position: relative;
    margin-bottom: 16px;
}

.input-group input {
    width: 100%;
    padding: 14px 18px;
    background: rgba(255,255,255,0.07);
    border: 1px solid rgba(255,255,255,0.12);
    border-radius: 14px;
    color: #fff;
    font-size: 0.95rem;
    font-family: 'Nunito', sans-serif;
    transition: border-color 0.3s, background 0.3s, box-shadow 0.3s;
    outline: none;
}

.input-group input::placeholder { color: rgba(255,255,255,0.3); }

.input-group input:focus {
    border-color: rgba(120,200,255,0.6);
    background: rgba(255,255,255,0.1);
    box-shadow: 0 0 0 4px rgba(120,200,255,0.1);
}

.btn {
    width: 100%;
    padding: 14px;
    border: none;
    border-radius: 14px;
    font-size: 1rem;
    font-weight: 800;
    font-family: 'Nunito', sans-serif;
    cursor: pointer;
    position: relative;
    overflow: hidden;
    transition: transform 0.2s, box-shadow 0.2s;
    margin-top: 6px;
}

.btn::after {
    content: '';
    position: absolute;
    inset: 0;
    background: rgba(255,255,255,0.15);
    opacity: 0;
    transition: opacity 0.2s;
}

.btn:hover { transform: translateY(-2px); box-shadow: 0 8px 24px rgba(0,0,0,0.3); }
.btn:hover::after { opacity: 1; }
.btn:active { transform: translateY(0); }

.btn-primary {
    background: linear-gradient(135deg, #5bc8f5, #a78bfa);
    color: #fff;
}

.link-row {
    margin-top: 20px;
    text-align: center;
    color: rgba(255,255,255,0.4);
    font-size: 0.85rem;
}

.link-row a {
    color: #7ec8f7;
    text-decoration: none;
    font-weight: 700;
    transition: color 0.2s;
}

.link-row a:hover { color: #a78bfa; }

.error-msg {
    background: rgba(255,80,80,0.15);
    border: 1px solid rgba(255,80,80,0.3);
    color: #ff9a9a;
    padding: 10px 14px;
    border-radius: 10px;
    font-size: 0.85rem;
    margin-bottom: 14px;
    animation: shake 0.4s ease;
}

@keyframes shake {
    0%,100%{ transform:translateX(0); }
    25%{ transform:translateX(-6px); }
    75%{ transform:translateX(6px); }
}
"""

PARTICLES_JS = """
function makeParticles() {
    const colors = ['#7ec8f7','#a78bfa','#6ee7b7','#fde68a','#f9a8d4'];
    for (let i = 0; i < 18; i++) {
        const p = document.createElement('div');
        p.className = 'particle';
        const size = Math.random() * 6 + 2;
        p.style.cssText = `
            width:${size}px; height:${size}px;
            left:${Math.random()*100}vw;
            background:${colors[Math.floor(Math.random()*colors.length)]};
            animation-duration:${Math.random()*12+8}s;
            animation-delay:${Math.random()*-15}s;
            opacity:${Math.random()*0.5+0.2};
        `;
        document.body.appendChild(p);
    }
}
makeParticles();
"""

# ---------------- SIGNUP ----------------
@app.route("/signup", methods=["GET","POST"])
def signup():
    error = ""
    if request.method == "POST":
        u = request.form["username"]
        p = generate_password_hash(request.form["password"])
        try:
            conn = sqlite3.connect("app.db")
            cur = conn.cursor()
            cur.execute("INSERT INTO users (username,password) VALUES (?,?)",(u,p))
            conn.commit()
            conn.close()
            return redirect("/login")
        except:
            error = "⚠️ Username already exists. Try another one."

    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>MindSpace — Sign Up</title>
<style>
{{ styles }}
</style>
</head>
<body>
<div class="card">
    <h2>MindSpace 🌿</h2>
    <p class="subtitle">Create your account to begin your wellness journey ✨</p>
    {% if error %}<div class="error-msg">{{ error }}</div>{% endif %}
    <form method="post" autocomplete="off">
        <div class="input-group">
            <input name="username" required placeholder="👤  Username" autofocus>
        </div>
        <div class="input-group">
            <input name="password" type="password" required placeholder="🔒  Password">
        </div>
        <button class="btn btn-primary" type="submit">Create Account 🚀</button>
    </form>
    <div class="link-row">Already have an account? <a href="/login">Log in →</a></div>
</div>
<script>{{ particles }}</script>
</body>
</html>
""", styles=BASE_STYLES, particles=PARTICLES_JS, error=error)


# ---------------- LOGIN ----------------
@app.route("/login", methods=["GET","POST"])
def login():
    error = ""
    if request.method == "POST":
        u = request.form["username"]
        p = request.form["password"]
        conn = sqlite3.connect("app.db")
        cur = conn.cursor()
        cur.execute("SELECT password FROM users WHERE username=?",(u,))
        user = cur.fetchone()
        conn.close()
        if user and check_password_hash(user[0],p):
            session["user"]=u
            return redirect("/")
        error = "❌ Invalid username or password."

    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>MindSpace — Login</title>
<style>
{{ styles }}
</style>
</head>
<body>
<div class="card">
    <h2>Welcome back 🌙</h2>
    <p class="subtitle">Your safe space is waiting for you 💙</p>
    {% if error %}<div class="error-msg">{{ error }}</div>{% endif %}
    <form method="post" autocomplete="off">
        <div class="input-group">
            <input name="username" required placeholder="👤  Username" autofocus>
        </div>
        <div class="input-group">
            <input name="password" type="password" required placeholder="🔒  Password">
        </div>
        <button class="btn btn-primary" type="submit">Log In ✨</button>
    </form>
    <div class="link-row">New here? <a href="/signup">Create account →</a></div>
</div>
<script>{{ particles }}</script>
</body>
</html>
""", styles=BASE_STYLES, particles=PARTICLES_JS, error=error)


# ---------------- HOME ----------------
@app.route("/")
def home():
    if "user" not in session:
        return redirect("/login")

    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>MindSpace — Check-In</title>
<link href="https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700;800;900&family=Playfair+Display:wght@700&display=swap" rel="stylesheet">
<style>
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

body {
    font-family: 'Nunito', sans-serif;
    min-height: 100vh;
    background: #0d0d1a;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 24px 16px 100px;
    position: relative;
    overflow-x: hidden;
}

body::before {
    content: '';
    position: fixed;
    inset: 0;
    background:
        radial-gradient(ellipse 80% 60% at 20% 40%, rgba(100,200,255,0.1) 0%, transparent 60%),
        radial-gradient(ellipse 60% 80% at 80% 20%, rgba(180,120,255,0.1) 0%, transparent 60%),
        radial-gradient(ellipse 70% 50% at 50% 90%, rgba(100,255,200,0.07) 0%, transparent 60%);
    animation: aurora 10s ease-in-out infinite alternate;
    pointer-events: none;
}
@keyframes aurora {
    0%   { transform: scale(1) rotate(0deg); }
    100% { transform: scale(1.08) rotate(-2deg); }
}

.particle { position: fixed; border-radius: 50%; pointer-events: none; animation: float linear infinite; z-index: 0; }
@keyframes float {
    0%   { transform: translateY(110vh) scale(0); opacity: 0; }
    10%  { opacity: 0.5; }
    90%  { opacity: 0.3; }
    100% { transform: translateY(-10vh) scale(1.2); opacity: 0; }
}

/* TOP NAV */
.topnav {
    position: fixed;
    top: 0; left: 0; right: 0;
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 14px 24px;
    background: rgba(13,13,26,0.8);
    backdrop-filter: blur(16px);
    border-bottom: 1px solid rgba(255,255,255,0.07);
    z-index: 100;
}

.brand {
    font-family: 'Playfair Display', serif;
    font-size: 1.2rem;
    color: #fff;
}

.nav-links a {
    color: rgba(255,255,255,0.5);
    text-decoration: none;
    font-size: 0.82rem;
    font-weight: 700;
    margin-left: 16px;
    padding: 6px 14px;
    border-radius: 20px;
    border: 1px solid rgba(255,255,255,0.1);
    transition: all 0.2s;
}

.nav-links a:hover {
    color: #fff;
    background: rgba(255,255,255,0.08);
    border-color: rgba(255,255,255,0.2);
}

/* MAIN CARD */
.main-card {
    position: relative;
    z-index: 1;
    background: rgba(255,255,255,0.04);
    backdrop-filter: blur(24px);
    border: 1px solid rgba(255,255,255,0.09);
    border-radius: 28px;
    padding: 40px 36px;
    width: 100%;
    max-width: 520px;
    box-shadow: 0 24px 80px rgba(0,0,0,0.5), inset 0 1px 0 rgba(255,255,255,0.08);
    margin-top: 60px;
    animation: slideUp 0.7s cubic-bezier(0.16,1,0.3,1) both;
}

@keyframes slideUp {
    from { opacity:0; transform:translateY(40px) scale(0.96); }
    to   { opacity:1; transform:translateY(0) scale(1); }
}

/* PROGRESS */
.progress-wrap {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 28px;
}

.progress-bar {
    flex: 1;
    height: 6px;
    background: rgba(255,255,255,0.08);
    border-radius: 99px;
    overflow: hidden;
}

.progress-fill {
    height: 100%;
    background: linear-gradient(90deg, #5bc8f5, #a78bfa);
    border-radius: 99px;
    transition: width 0.5s cubic-bezier(0.16,1,0.3,1);
    box-shadow: 0 0 10px rgba(167,139,250,0.6);
}

.progress-label {
    color: rgba(255,255,255,0.4);
    font-size: 0.78rem;
    font-weight: 700;
    white-space: nowrap;
}

/* QUESTION */
.question-wrap {
    min-height: 56px;
    margin-bottom: 28px;
    position: relative;
    overflow: hidden;
}

.question-text {
    font-size: 1.15rem;
    font-weight: 800;
    color: #fff;
    line-height: 1.5;
    animation: fadeInQ 0.4s cubic-bezier(0.16,1,0.3,1) both;
}

@keyframes fadeInQ {
    from { opacity:0; transform:translateX(30px); }
    to   { opacity:1; transform:translateX(0); }
}

/* OPTIONS */
.options {
    display: flex;
    flex-direction: column;
    gap: 10px;
    margin-bottom: 28px;
}

.option-label {
    display: flex;
    align-items: center;
    gap: 14px;
    padding: 13px 18px;
    background: rgba(255,255,255,0.04);
    border: 1.5px solid rgba(255,255,255,0.08);
    border-radius: 14px;
    cursor: pointer;
    transition: all 0.25s;
    animation: fadeInOpt 0.4s cubic-bezier(0.16,1,0.3,1) both;
}

.option-label:nth-child(1) { animation-delay: 0.05s; }
.option-label:nth-child(2) { animation-delay: 0.10s; }
.option-label:nth-child(3) { animation-delay: 0.15s; }
.option-label:nth-child(4) { animation-delay: 0.20s; }
.option-label:nth-child(5) { animation-delay: 0.25s; }

@keyframes fadeInOpt {
    from { opacity:0; transform:translateX(-20px); }
    to   { opacity:1; transform:translateX(0); }
}

.option-label:hover {
    background: rgba(92,200,245,0.08);
    border-color: rgba(92,200,245,0.35);
    transform: translateX(4px);
}

.option-label input[type="radio"] { display: none; }

.option-label.selected {
    background: rgba(92,200,245,0.12);
    border-color: #5bc8f5;
    box-shadow: 0 0 0 3px rgba(92,200,245,0.12);
}

.option-dot {
    width: 20px; height: 20px;
    border-radius: 50%;
    border: 2px solid rgba(255,255,255,0.2);
    transition: all 0.2s;
    flex-shrink: 0;
    display: flex; align-items: center; justify-content: center;
}

.option-label.selected .option-dot {
    border-color: #5bc8f5;
    background: #5bc8f5;
    box-shadow: 0 0 8px rgba(92,200,245,0.7);
}

.option-dot::after {
    content: '';
    width: 8px; height: 8px;
    border-radius: 50%;
    background: #fff;
    opacity: 0;
    transform: scale(0);
    transition: all 0.2s;
}

.option-label.selected .option-dot::after {
    opacity: 1;
    transform: scale(1);
}

.option-text {
    color: rgba(255,255,255,0.75);
    font-size: 0.9rem;
    font-weight: 600;
}

.option-val {
    margin-left: auto;
    font-size: 1.1rem;
}

/* NEXT BTN */
.btn-next {
    width: 100%;
    padding: 15px;
    border: none;
    border-radius: 14px;
    font-size: 1rem;
    font-weight: 800;
    font-family: 'Nunito', sans-serif;
    cursor: pointer;
    background: linear-gradient(135deg, #5bc8f5, #a78bfa);
    color: #fff;
    transition: transform 0.2s, box-shadow 0.2s, opacity 0.2s;
    position: relative;
    overflow: hidden;
}

.btn-next::before {
    content: '';
    position: absolute;
    top: 0; left: -100%;
    width: 100%; height: 100%;
    background: linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent);
    transition: left 0.5s;
}

.btn-next:hover { transform: translateY(-2px); box-shadow: 0 8px 28px rgba(92,200,245,0.3); }
.btn-next:hover::before { left: 100%; }
.btn-next:active { transform: translateY(0); }
.btn-next:disabled { opacity: 0.4; cursor: not-allowed; transform: none; }

/* RESULT */
.result-wrap {
    display: none;
    animation: fadeInResult 0.6s cubic-bezier(0.16,1,0.3,1) both;
}

@keyframes fadeInResult {
    from { opacity:0; transform:scale(0.9); }
    to   { opacity:1; transform:scale(1); }
}

.result-badge {
    text-align: center;
    padding: 24px;
    border-radius: 20px;
    margin-bottom: 20px;
    border: 1.5px solid rgba(255,255,255,0.1);
}

.result-status {
    font-family: 'Playfair Display', serif;
    font-size: 2rem;
    font-weight: 700;
    margin-bottom: 6px;
}

.result-score {
    color: rgba(255,255,255,0.5);
    font-size: 0.9rem;
    margin-bottom: 16px;
}

.remedies {
    display: flex;
    flex-direction: column;
    gap: 8px;
    text-align: left;
}

.remedy-item {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 10px 14px;
    background: rgba(255,255,255,0.04);
    border-radius: 10px;
    color: rgba(255,255,255,0.8);
    font-size: 0.88rem;
    font-weight: 600;
}

.btn-retake {
    width: 100%;
    padding: 13px;
    margin-top: 16px;
    border: 1.5px solid rgba(255,255,255,0.15);
    border-radius: 14px;
    background: transparent;
    color: rgba(255,255,255,0.7);
    font-family: 'Nunito', sans-serif;
    font-weight: 700;
    cursor: pointer;
    transition: all 0.2s;
    font-size: 0.9rem;
}

.btn-retake:hover {
    background: rgba(255,255,255,0.06);
    color: #fff;
    border-color: rgba(255,255,255,0.3);
}

/* FLOATING YOUTUBE BUTTON */
.yt-float {
    position: fixed;
    bottom: 28px;
    right: 28px;
    z-index: 200;
    display: none;
}

.yt-float a {
    display: flex;
    align-items: center;
    gap: 10px;
    background: linear-gradient(135deg, #5bc8f5, #a78bfa);
    color: #fff;
    text-decoration: none;
    padding: 12px 20px 12px 14px;
    border-radius: 99px;
    font-weight: 800;
    font-size: 0.85rem;
    box-shadow: 0 8px 28px rgba(92,200,245,0.35);
    transition: transform 0.3s, box-shadow 0.3s;
    animation: pulse-glow 2.5s ease-in-out infinite;
}

.yt-float a:hover {
    transform: translateY(-3px) scale(1.04);
    box-shadow: 0 12px 36px rgba(92,200,245,0.5);
}

@keyframes pulse-glow {
    0%, 100% { box-shadow: 0 8px 28px rgba(92,200,245,0.35); }
    50% { box-shadow: 0 8px 40px rgba(167,139,250,0.55); }
}

.yt-icon {
    width: 32px; height: 32px;
    background: rgba(255,255,255,0.2);
    border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    flex-shrink: 0;
}

.yt-icon svg { width: 16px; height: 16px; fill: #fff; }

/* ALERT */
.alert-toast {
    position: fixed;
    top: 80px; right: 24px;
    background: rgba(255,100,100,0.15);
    border: 1px solid rgba(255,100,100,0.3);
    color: #ffaaaa;
    padding: 12px 18px;
    border-radius: 12px;
    font-size: 0.85rem;
    font-weight: 700;
    z-index: 300;
    display: none;
    animation: slideInToast 0.3s ease;
}

@keyframes slideInToast {
    from { opacity:0; transform:translateX(20px); }
    to   { opacity:1; transform:translateX(0); }
}
</style>
</head>
<body>

<!-- TOP NAV -->
<nav class="topnav">
    <span class="brand">MindSpace 🌿</span>
    <div class="nav-links">
        <a href="/history">📈 History</a>
        <a href="/logout">👋 Logout</a>
    </div>
</nav>

<!-- ALERT TOAST -->
<div class="alert-toast" id="toast">👆 Please select an option!</div>

<!-- MAIN CARD -->
<div class="main-card" id="mainCard">

    <!-- PROGRESS -->
    <div class="progress-wrap">
        <div class="progress-bar">
            <div class="progress-fill" id="progressFill" style="width:0%"></div>
        </div>
        <span class="progress-label" id="progressLabel">0 / 9</span>
    </div>

    <!-- QUESTION AREA -->
    <div class="question-wrap">
        <div class="question-text" id="questionText"></div>
    </div>

    <!-- OPTIONS -->
    <div class="options" id="options"></div>

    <!-- NEXT -->
    <button class="btn-next" id="nextBtn" onclick="next()">Next →</button>

    <!-- RESULT (hidden initially) -->
    <div class="result-wrap" id="resultWrap">
        <div class="result-badge" id="resultBadge">
            <div class="result-status" id="resultStatus"></div>
            <div class="result-score" id="resultScore"></div>
            <div class="remedies" id="remediesList"></div>
        </div>
        <button class="btn-retake" onclick="retake()">🔄 Take Again</button>
    </div>
</div>

<!-- FLOATING YOUTUBE BUTTON -->
<div class="yt-float" id="ytFloat">
    <a href="{{ binaural }}" target="_blank" rel="noopener">
        <div class="yt-icon">
            <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                <path d="M21.8 8s-.2-1.4-.8-2c-.8-.8-1.6-.8-2-.9C16.4 5 12 5 12 5s-4.4 0-7 .1c-.4.1-1.2.1-2 .9C2.4 6.6 2.2 8 2.2 8S2 9.6 2 11.2v1.5C2 14.3 2.2 16 2.2 16s.2 1.4.8 2c.8.8 1.8.8 2.2.9C6.6 19 12 19 12 19s4.4 0 7-.1c.4-.1 1.2-.1 2-.9.6-.6.8-2 .8-2S22 14.3 22 12.7v-1.5C22 9.6 21.8 8 21.8 8zM9.7 14.5V9l5.3 2.8-5.3 2.7z"/>
            </svg>
        </div>
        🎧 Relax Now
    </a>
</div>

<script>
const q = {{ questions|tojson }};
const labels = ['Never', 'Rarely', 'Sometimes', 'Often', 'Always'];
const emoji  = ['😌','🙂','😐','😟','😣'];
let i = 0, ans = {};

function load() {
    const pct = (i / q.length) * 100;
    document.getElementById('progressFill').style.width = pct + '%';
    document.getElementById('progressLabel').textContent = i + ' / ' + q.length;

    const qEl = document.getElementById('questionText');
    qEl.style.animation = 'none';
    qEl.offsetHeight; // reflow
    qEl.style.animation = '';
    qEl.textContent = q[i].label;

    const opt = document.getElementById('options');
    opt.innerHTML = '';
    for (let j = 1; j <= 5; j++) {
        const lbl = document.createElement('label');
        lbl.className = 'option-label';
        lbl.innerHTML = `
            <input type="radio" name="a" value="${j}">
            <div class="option-dot"></div>
            <span class="option-text">${labels[j-1]}</span>
            <span class="option-val">${emoji[j-1]}</span>
        `;
        lbl.addEventListener('click', () => {
            document.querySelectorAll('.option-label').forEach(l => l.classList.remove('selected'));
            lbl.classList.add('selected');
            lbl.querySelector('input').checked = true;
        });
        opt.appendChild(lbl);
    }
}

load();

function showToast(msg) {
    const t = document.getElementById('toast');
    t.textContent = msg;
    t.style.display = 'block';
    clearTimeout(window._toastTimer);
    window._toastTimer = setTimeout(() => { t.style.display = 'none'; }, 2200);
}

function next() {
    const v = document.querySelector('input[name=a]:checked');
    if (!v) { showToast('👆 Please select an option!'); return; }
    ans[q[i].id] = parseInt(v.value);

    if (i < q.length - 1) {
        i++;
        load();
    } else {
        document.getElementById('progressFill').style.width = '100%';
        document.getElementById('progressLabel').textContent = '9 / 9';
        document.getElementById('nextBtn').disabled = true;
        document.getElementById('nextBtn').textContent = '⏳ Analyzing...';

        fetch('/assess', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(ans)
        })
        .then(r => r.json())
        .then(d => {
            document.getElementById('questionText').style.display = 'none';
            document.getElementById('options').style.display = 'none';
            document.getElementById('nextBtn').style.display = 'none';

            const badge = document.getElementById('resultBadge');
            const colorMap = {
                '#0a0': { bg: 'rgba(0,200,100,0.08)', border: 'rgba(0,200,100,0.25)' },
                '#e6b800': { bg: 'rgba(230,184,0,0.08)', border: 'rgba(230,184,0,0.25)' },
                '#f80': { bg: 'rgba(255,128,0,0.08)', border: 'rgba(255,128,0,0.25)' },
                '#f00': { bg: 'rgba(255,60,60,0.08)', border: 'rgba(255,60,60,0.25)' }
            };
            const cm = colorMap[d.color] || { bg: 'rgba(255,255,255,0.05)', border: 'rgba(255,255,255,0.1)' };
            badge.style.background = cm.bg;
            badge.style.borderColor = cm.border;

            document.getElementById('resultStatus').style.color = d.color;
            document.getElementById('resultStatus').textContent = d.status;
            document.getElementById('resultScore').textContent = '🧮 Wellness Score: ' + d.score;

            const remedyIcons = ['🌅', '🏃', '🛌'];
            const remedyList = document.getElementById('remediesList');
            remedyList.innerHTML = '';
            d.remedies.forEach((r, idx) => {
                const item = document.createElement('div');
                item.className = 'remedy-item';
                item.textContent = (remedyIcons[idx] || '✅') + '  ' + r;
                remedyList.appendChild(item);
            });

            const wrap = document.getElementById('resultWrap');
            wrap.style.display = 'block';

            // Show floating YouTube button
            const ytBtn = document.getElementById('ytFloat');
            ytBtn.href = d.link;
            ytBtn.style.display = 'block';
        });
    }
}

function retake() {
    i = 0; ans = {};
    document.getElementById('questionText').style.display = '';
    document.getElementById('options').style.display = '';
    document.getElementById('nextBtn').style.display = '';
    document.getElementById('nextBtn').disabled = false;
    document.getElementById('nextBtn').textContent = 'Next →';
    document.getElementById('resultWrap').style.display = 'none';
    document.getElementById('ytFloat').style.display = 'none';
    load();
}

// Particles
function makeParticles() {
    const colors = ['#7ec8f7','#a78bfa','#6ee7b7','#fde68a','#f9a8d4'];
    for (let p = 0; p < 18; p++) {
        const el = document.createElement('div');
        el.className = 'particle';
        const size = Math.random() * 6 + 2;
        el.style.cssText = `width:${size}px;height:${size}px;left:${Math.random()*100}vw;background:${colors[Math.floor(Math.random()*colors.length)]};animation-duration:${Math.random()*12+8}s;animation-delay:${Math.random()*-15}s;opacity:${Math.random()*0.4+0.1}`;
        document.body.appendChild(el);
    }
}
makeParticles();
</script>
</body>
</html>
""", questions=questions, binaural=BINAURAL)


# ---------------- ASSESS ----------------
@app.route("/assess", methods=["POST"])
def assess():
    data = request.get_json()
    score = 0
    positive = ["sleep","exercise","motivation","energy"]

    for k, v in data.items():
        score += (6-v if k in positive else v)

    max_score = len(data) * 5

    if score <= max_score * 0.25:   status, color = "Stable 🟢", "#0a0"
    elif score <= max_score * 0.5:  status, color = "Mild 🟡", "#e6b800"
    elif score <= max_score * 0.75: status, color = "Moderate 🟠", "#f80"
    else:                           status, color = "High Risk 🔴", "#f00"

    conn = sqlite3.connect("app.db")
    cur = conn.cursor()
    cur.execute("INSERT INTO results (username,score,status) VALUES (?,?,?)",
                (session["user"], score, status))
    conn.commit()
    conn.close()

    remedies = ["Maintain a consistent daily routine", "Exercise for 30 mins daily", "Prioritize 7–8 hours of sleep"]
    return jsonify({"status": status, "color": color, "score": score, "remedies": remedies, "link": BINAURAL})


# ---------------- HISTORY ----------------
@app.route("/history")
def history():
    if "user" not in session:
        return redirect("/login")

    conn = sqlite3.connect("app.db")
    cur = conn.cursor()
    cur.execute("SELECT score, status FROM results WHERE username=? ORDER BY id DESC LIMIT 20", (session["user"],))
    rows = cur.fetchall()
    conn.close()

    data   = [r[0] for r in reversed(rows)]
    labels = list(range(1, len(data)+1))
    statuses = [r[1] for r in reversed(rows)]

    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>MindSpace — History</title>
<link href="https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700;800;900&family=Playfair+Display:wght@700&display=swap" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
*, *::before, *::after { box-sizing:border-box; margin:0; padding:0; }

body {
    font-family: 'Nunito', sans-serif;
    min-height: 100vh;
    background: #0d0d1a;
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 100px 16px 40px;
    position: relative;
}

body::before {
    content:'';
    position:fixed; inset:0;
    background:
        radial-gradient(ellipse 80% 60% at 20% 40%, rgba(100,200,255,0.1) 0%, transparent 60%),
        radial-gradient(ellipse 60% 80% at 80% 20%, rgba(180,120,255,0.1) 0%, transparent 60%);
    animation: aurora 10s ease-in-out infinite alternate;
    pointer-events:none;
}
@keyframes aurora { 0% { transform:scale(1); } 100% { transform:scale(1.08) rotate(-2deg); } }

.particle { position:fixed; border-radius:50%; pointer-events:none; animation:float linear infinite; z-index:0; }
@keyframes float {
    0%   { transform:translateY(110vh) scale(0); opacity:0; }
    10%  { opacity:0.5; }
    90%  { opacity:0.3; }
    100% { transform:translateY(-10vh) scale(1.2); opacity:0; }
}

.topnav {
    position:fixed; top:0; left:0; right:0;
    display:flex; justify-content:space-between; align-items:center;
    padding:14px 24px;
    background:rgba(13,13,26,0.85);
    backdrop-filter:blur(16px);
    border-bottom:1px solid rgba(255,255,255,0.07);
    z-index:100;
}

.brand { font-family:'Playfair Display',serif; font-size:1.2rem; color:#fff; }

.nav-links a {
    color:rgba(255,255,255,0.5); text-decoration:none; font-size:0.82rem; font-weight:700;
    margin-left:16px; padding:6px 14px; border-radius:20px; border:1px solid rgba(255,255,255,0.1);
    transition:all 0.2s;
}
.nav-links a:hover { color:#fff; background:rgba(255,255,255,0.08); }

.page-title {
    font-family:'Playfair Display',serif;
    font-size:1.8rem;
    color:#fff;
    margin-bottom:6px;
    position:relative; z-index:1;
    animation: slideUp 0.6s cubic-bezier(0.16,1,0.3,1) both;
}

.page-sub { color:rgba(255,255,255,0.35); font-size:0.85rem; margin-bottom:28px; position:relative; z-index:1; }

@keyframes slideUp { from { opacity:0; transform:translateY(24px); } to { opacity:1; transform:translateY(0); } }

.chart-card {
    position:relative; z-index:1;
    background:rgba(255,255,255,0.04);
    backdrop-filter:blur(24px);
    border:1px solid rgba(255,255,255,0.09);
    border-radius:24px;
    padding:28px;
    width:100%; max-width:640px;
    box-shadow:0 20px 60px rgba(0,0,0,0.4);
    animation: slideUp 0.7s 0.1s cubic-bezier(0.16,1,0.3,1) both;
    margin-bottom:20px;
}

.chart-card h3 { color:rgba(255,255,255,0.7); font-size:0.85rem; text-transform:uppercase; letter-spacing:1px; margin-bottom:20px; }

.no-data {
    text-align:center; padding:40px;
    color:rgba(255,255,255,0.3); font-size:1rem;
}

.back-btn {
    position:relative; z-index:1;
    display:inline-flex; align-items:center; gap:8px;
    padding:12px 22px;
    border:1.5px solid rgba(255,255,255,0.12);
    border-radius:99px;
    color:rgba(255,255,255,0.6);
    text-decoration:none;
    font-weight:700; font-size:0.85rem;
    transition:all 0.2s;
    background:rgba(255,255,255,0.04);
    margin-top:8px;
}

.back-btn:hover { color:#fff; background:rgba(255,255,255,0.08); border-color:rgba(255,255,255,0.25); }
</style>
</head>
<body>

<nav class="topnav">
    <span class="brand">MindSpace 🌿</span>
    <div class="nav-links">
        <a href="/">🏠 Home</a>
        <a href="/logout">👋 Logout</a>
    </div>
</nav>

<h1 class="page-title">📈 Your Progress</h1>
<p class="page-sub">Wellness scores over your last {{ data|length }} check-ins</p>

<div class="chart-card">
    <h3>Wellness Score Trend</h3>
    {% if data %}
    <canvas id="histChart" height="200"></canvas>
    {% else %}
    <div class="no-data">🌱 No check-ins yet. Complete your first assessment!</div>
    {% endif %}
</div>

<a class="back-btn" href="/">← Back to Check-In</a>

{% if data %}
<script>
const ctx = document.getElementById('histChart').getContext('2d');
const gradient = ctx.createLinearGradient(0, 0, 0, 300);
gradient.addColorStop(0, 'rgba(91,200,245,0.35)');
gradient.addColorStop(1, 'rgba(167,139,250,0.0)');

new Chart(ctx, {
    type: 'line',
    data: {
        labels: {{ labels|tojson }}.map(l => 'Check-in ' + l),
        datasets: [{
            label: 'Wellness Score',
            data: {{ data|tojson }},
            fill: true,
            backgroundColor: gradient,
            borderColor: '#5bc8f5',
            borderWidth: 2.5,
            pointBackgroundColor: '#a78bfa',
            pointBorderColor: '#fff',
            pointBorderWidth: 2,
            pointRadius: 5,
            pointHoverRadius: 8,
            tension: 0.4
        }]
    },
    options: {
        responsive: true,
        plugins: {
            legend: { display: false },
            tooltip: {
                backgroundColor: 'rgba(13,13,26,0.9)',
                borderColor: 'rgba(255,255,255,0.1)',
                borderWidth: 1,
                titleColor: '#fff',
                bodyColor: 'rgba(255,255,255,0.6)',
                padding: 12
            }
        },
        scales: {
            x: {
                grid: { color: 'rgba(255,255,255,0.05)' },
                ticks: { color: 'rgba(255,255,255,0.4)', font: { family: 'Nunito', size: 11 } }
            },
            y: {
                grid: { color: 'rgba(255,255,255,0.05)' },
                ticks: { color: 'rgba(255,255,255,0.4)', font: { family: 'Nunito', size: 11 } }
            }
        }
    }
});
</script>
{% endif %}

<script>
function makeParticles() {
    const colors = ['#7ec8f7','#a78bfa','#6ee7b7'];
    for (let p = 0; p < 14; p++) {
        const el = document.createElement('div');
        el.className = 'particle';
        const size = Math.random() * 5 + 2;
        el.style.cssText = `width:${size}px;height:${size}px;left:${Math.random()*100}vw;background:${colors[Math.floor(Math.random()*colors.length)]};animation-duration:${Math.random()*12+8}s;animation-delay:${Math.random()*-15}s;opacity:${Math.random()*0.4+0.1}`;
        document.body.appendChild(el);
    }
}
makeParticles();
</script>
</body>
</html>
""", data=data, labels=labels, statuses=statuses)


# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


# ---------------- RUN ----------------
if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
