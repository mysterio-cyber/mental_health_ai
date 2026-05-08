from flask import Flask, request, render_template_string, jsonify, redirect, session
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
import random
import string
import os

app = Flask(__name__)
# FIX: Use a FIXED secret key so sessions survive server restarts
# In production, set SECRET_KEY env var to a long random string
app.secret_key = os.environ.get("SECRET_KEY", "mindspace-super-secret-key-change-in-prod-2024")
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE'] = False  # Set True if HTTPS

# ---------------- DATABASE ----------------
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
    CREATE TABLE IF NOT EXISTS otp_store (
        mobile TEXT PRIMARY KEY,
        otp TEXT,
        username TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )""")
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

# -------- OPTIONAL: Twilio SMS --------
def send_otp_sms(mobile, otp):
    sid   = os.environ.get("TWILIO_SID")
    token = os.environ.get("TWILIO_TOKEN")
    from_ = os.environ.get("TWILIO_FROM")
    if sid and token and from_:
        try:
            from twilio.rest import Client
            Client(sid, token).messages.create(
                body=f"Your MindSpace OTP is: {otp}",
                from_=from_,
                to=f"+91{mobile}" if not mobile.startswith("+") else mobile
            )
            return True
        except Exception as e:
            print(f"SMS error: {e}")
    return False

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
    width: 420px;
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

.btn-secondary {
    background: rgba(255,255,255,0.08);
    border: 1px solid rgba(255,255,255,0.15);
    color: rgba(255,255,255,0.7);
    margin-top: 8px;
}

.btn-secondary:hover { background: rgba(255,255,255,0.12); color: #fff; }

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

.success-msg {
    background: rgba(0,200,100,0.15);
    border: 1px solid rgba(0,200,100,0.3);
    color: #6ee7b7;
    padding: 10px 14px;
    border-radius: 10px;
    font-size: 0.85rem;
    margin-bottom: 14px;
}

@keyframes shake {
    0%,100%{ transform:translateX(0); }
    25%{ transform:translateX(-6px); }
    75%{ transform:translateX(6px); }
}

.step-indicator {
    display: flex;
    gap: 8px;
    margin-bottom: 24px;
}

.step-dot {
    height: 4px;
    flex: 1;
    border-radius: 99px;
    background: rgba(255,255,255,0.1);
    transition: background 0.4s;
}

.step-dot.active { background: linear-gradient(90deg, #5bc8f5, #a78bfa); }
.step-dot.done { background: rgba(110,231,183,0.6); }
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

# ---------------- SIGNUP (Step 1) ----------------
@app.route("/signup", methods=["GET","POST"])
def signup():
    error = ""
    if request.method == "POST":
        u = request.form.get("username","").strip()
        m = request.form.get("mobile","").strip()

        if not u or not m:
            error = "⚠️ Please fill in all fields."
        elif not m.isdigit() or len(m) < 10:
            error = "⚠️ Enter a valid mobile number."
        else:
            conn = sqlite3.connect("app.db")
            cur = conn.cursor()
            cur.execute("SELECT id FROM users WHERE username=?", (u,))
            existing = cur.fetchone()
            conn.close()
            if existing:
                error = "⚠️ Username already exists. Try another one."
            else:
                otp = ''.join(random.choices(string.digits, k=6))
                conn = sqlite3.connect("app.db")
                cur = conn.cursor()
                cur.execute("INSERT OR REPLACE INTO otp_store (mobile, otp, username) VALUES (?,?,?)", (m, otp, u))
                conn.commit()
                conn.close()
                sms_sent = send_otp_sms(m, otp)
                # FIX: Store all pending info in session
                session['pending_mobile'] = m
                session['pending_username'] = u
                session['demo_otp'] = otp   # always store for demo display
                session['sms_sent'] = sms_sent
                session.modified = True     # FIX: Force Flask to save session
                return redirect("/verify-otp")

    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>MindSpace — Sign Up</title>
<style>{{ styles }}</style>
</head>
<body>
<div class="card">
    <h2>MindSpace 🌿</h2>
    <p class="subtitle">Create your account to begin your wellness journey ✨</p>
    <div class="step-indicator">
        <div class="step-dot active"></div>
        <div class="step-dot"></div>
        <div class="step-dot"></div>
    </div>
    <div style="color:rgba(255,255,255,0.5);font-size:0.78rem;margin-bottom:16px;font-weight:700;text-transform:uppercase;letter-spacing:1px;">Step 1 — Your Details</div>
    {% if error %}<div class="error-msg">{{ error }}</div>{% endif %}
    <form method="post" autocomplete="off">
        <div class="input-group">
            <input name="username" required placeholder="👤  Username" autofocus value="{{ req_username }}">
        </div>
        <div class="input-group">
            <input name="mobile" type="tel" required placeholder="📱  Mobile Number" value="{{ req_mobile }}">
        </div>
        <button class="btn btn-primary" type="submit">Send OTP 📲</button>
    </form>
    <div class="link-row">Already have an account? <a href="/login">Log in →</a></div>
</div>
<script>{{ particles }}</script>
</body>
</html>
""", styles=BASE_STYLES, particles=PARTICLES_JS, error=error,
     req_username=request.form.get('username',''),
     req_mobile=request.form.get('mobile',''))


# ---------------- VERIFY OTP (Step 2) ----------------
@app.route("/verify-otp", methods=["GET","POST"])
def verify_otp():
    # FIX: Guard — if session is missing, redirect to signup
    if 'pending_mobile' not in session or 'pending_username' not in session:
        return redirect("/signup")

    error = ""
    # FIX: Read demo_otp from session, not recomputed
    demo_otp = session.get('demo_otp', '')
    sms_sent = session.get('sms_sent', False)

    if request.method == "POST":
        entered = request.form.get("otp","").strip()

        if not entered or len(entered) != 6:
            error = "❌ Please enter the complete 6-digit OTP."
        else:
            # FIX: Fetch from DB AND match username to prevent session mix-up
            conn = sqlite3.connect("app.db")
            cur = conn.cursor()
            cur.execute("SELECT otp, username FROM otp_store WHERE mobile=?",
                        (session['pending_mobile'],))
            row = cur.fetchone()
            conn.close()

            if row and row[0] == entered and row[1] == session['pending_username']:
                session['otp_verified'] = True
                session.modified = True  # FIX: force session save
                # Delete OTP from DB (one-time use)
                conn = sqlite3.connect("app.db")
                cur = conn.cursor()
                cur.execute("DELETE FROM otp_store WHERE mobile=?", (session['pending_mobile'],))
                conn.commit()
                conn.close()
                return redirect("/set-password")
            else:
                error = "❌ Invalid OTP. Please try again."

    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>MindSpace — Verify OTP</title>
<style>
{{ styles }}
.otp-demo {
    background: rgba(110,231,183,0.1);
    border: 1px solid rgba(110,231,183,0.3);
    color: #6ee7b7;
    padding: 14px;
    border-radius: 10px;
    font-size: 0.85rem;
    margin-bottom: 14px;
    text-align: center;
}
.otp-demo strong { font-size: 1.8rem; letter-spacing: 8px; display: block; margin-top: 6px; color: #fff; }
.otp-inputs { display: flex; gap: 10px; justify-content: center; margin-bottom: 20px; }
.otp-inputs input {
    width: 48px !important; height: 56px;
    text-align: center; font-size: 1.4rem; font-weight: 800;
    padding: 0 !important; border-radius: 12px !important;
}
</style>
</head>
<body>
<div class="card">
    <h2>Verify OTP 📲</h2>
    <p class="subtitle">OTP sent to {{ mobile }}</p>
    <div class="step-indicator">
        <div class="step-dot done"></div>
        <div class="step-dot active"></div>
        <div class="step-dot"></div>
    </div>

    {% if not sms_sent %}
    <div class="otp-demo">
        🧪 Demo Mode — Your OTP is:
        <strong>{{ demo_otp }}</strong>
    </div>
    {% else %}
    <div class="success-msg">✅ OTP sent to your mobile number!</div>
    {% endif %}

    {% if error %}<div class="error-msg">{{ error }}</div>{% endif %}

    <form method="post" autocomplete="off" id="otpForm">
        <div class="otp-inputs">
            <input class="otp-box" maxlength="1" type="text" inputmode="numeric" autofocus>
            <input class="otp-box" maxlength="1" type="text" inputmode="numeric">
            <input class="otp-box" maxlength="1" type="text" inputmode="numeric">
            <input class="otp-box" maxlength="1" type="text" inputmode="numeric">
            <input class="otp-box" maxlength="1" type="text" inputmode="numeric">
            <input class="otp-box" maxlength="1" type="text" inputmode="numeric">
        </div>
        <input type="hidden" name="otp" id="otpHidden">
        <button class="btn btn-primary" type="submit">Verify OTP ✅</button>
        <a href="/signup" style="display:block;text-align:center;margin-top:14px;color:rgba(255,255,255,0.4);font-size:0.82rem;text-decoration:none;">← Go back</a>
    </form>
</div>
<script>
{{ particles }}
const boxes = document.querySelectorAll('.otp-box');
boxes.forEach((box, i) => {
    box.addEventListener('input', e => {
        box.value = box.value.replace(/[^0-9]/g, '');
        if (box.value && i < boxes.length - 1) boxes[i+1].focus();
        updateHidden();
    });
    box.addEventListener('keydown', e => {
        if (e.key === 'Backspace' && !box.value && i > 0) boxes[i-1].focus();
    });
    box.addEventListener('paste', e => {
        e.preventDefault();
        const text = (e.clipboardData || window.clipboardData).getData('text').replace(/[^0-9]/g,'');
        [...text.slice(0,6)].forEach((ch, idx) => { if (boxes[idx]) boxes[idx].value = ch; });
        updateHidden();
        boxes[Math.min(text.length, 5)].focus();
    });
});
function updateHidden() {
    document.getElementById('otpHidden').value = Array.from(boxes).map(b=>b.value).join('');
}
document.getElementById('otpForm').addEventListener('submit', e => { updateHidden(); });
</script>
</body>
</html>
""", styles=BASE_STYLES, particles=PARTICLES_JS,
     mobile=session.get('pending_mobile',''),
     demo_otp=demo_otp, sms_sent=sms_sent, error=error)


# ---------------- SET PASSWORD (Step 3) ----------------
@app.route("/set-password", methods=["GET","POST"])
def set_password():
    # FIX: Both session flags must exist
    if not session.get('otp_verified') or 'pending_username' not in session:
        return redirect("/signup")

    error = ""
    if request.method == "POST":
        p1 = request.form.get("password","")
        p2 = request.form.get("confirm","")
        if len(p1) < 6:
            error = "⚠️ Password must be at least 6 characters."
        elif p1 != p2:
            error = "⚠️ Passwords do not match."
        else:
            hashed = generate_password_hash(p1)
            try:
                conn = sqlite3.connect("app.db")
                cur = conn.cursor()
                # FIX: Check for collision before insert
                cur.execute("SELECT id FROM users WHERE username=?", (session['pending_username'],))
                if cur.fetchone():
                    conn.close()
                    error = "⚠️ Username already taken. Please restart signup."
                else:
                    cur.execute(
                        "INSERT INTO users (username, mobile, password) VALUES (?,?,?)",
                        (session['pending_username'], session['pending_mobile'], hashed)
                    )
                    conn.commit()
                    conn.close()
                    # FIX: Clear only signup-related session keys, not everything
                    for k in ['pending_mobile','pending_username','otp_verified','demo_otp','sms_sent']:
                        session.pop(k, None)
                    session.modified = True
                    return redirect("/login?registered=1")
            except Exception as ex:
                print(f"Signup error: {ex}")
                error = "⚠️ An error occurred. Please try again."

    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>MindSpace — Set Password</title>
<style>{{ styles }}</style>
</head>
<body>
<div class="card">
    <h2>Set Password 🔐</h2>
    <p class="subtitle">Almost there! Choose a secure password.</p>
    <div class="step-indicator">
        <div class="step-dot done"></div>
        <div class="step-dot done"></div>
        <div class="step-dot active"></div>
    </div>
    {% if error %}<div class="error-msg">{{ error }}</div>{% endif %}
    <form method="post" autocomplete="off">
        <div class="input-group">
            <input name="password" type="password" required placeholder="🔒  New Password" autofocus>
        </div>
        <div class="input-group">
            <input name="confirm" type="password" required placeholder="🔒  Confirm Password">
        </div>
        <button class="btn btn-primary" type="submit">Create Account 🚀</button>
    </form>
</div>
<script>{{ particles }}</script>
</body>
</html>
""", styles=BASE_STYLES, particles=PARTICLES_JS, error=error)


# ---------------- LOGIN ----------------
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
            cur = conn.cursor()
            # FIX: Select both password AND username to confirm row exists
            cur.execute("SELECT id, password FROM users WHERE username=?", (u,))
            user = cur.fetchone()
            conn.close()

            if user and check_password_hash(user[1], p):
                session.clear()
                session["user"] = u
                session.modified = True  # FIX: force session persistence
                return redirect("/")
            else:
                error = "❌ Invalid username or password."

    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>MindSpace — Login</title>
<style>{{ styles }}</style>
</head>
<body>
<div class="card">
    <h2>Welcome back 🌙</h2>
    <p class="subtitle">Your safe space is waiting for you 💙</p>
    {% if success %}<div class="success-msg">{{ success }}</div>{% endif %}
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
""", styles=BASE_STYLES, particles=PARTICLES_JS, error=error, success=success)


# ---------------- HOME (Solar System) ----------------
@app.route("/")
def home():
    if "user" not in session:
        return redirect("/login")

    conn = sqlite3.connect("app.db")
    cur = conn.cursor()
    cur.execute("SELECT score, status FROM results WHERE username=? ORDER BY id DESC LIMIT 1", (session["user"],))
    last = cur.fetchone()
    conn.close()
    last_score = last[0] if last else None
    last_status = last[1] if last else None

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

:root {
    --bg: #0d0d1a;
    --card-bg: rgba(255,255,255,0.04);
    --card-border: rgba(255,255,255,0.09);
    --text: #fff;
    --text-muted: rgba(255,255,255,0.5);
    --topnav-bg: rgba(13,13,26,0.85);
}

body.light-mode {
    --bg: #f0f4ff;
    --card-bg: rgba(255,255,255,0.85);
    --card-border: rgba(100,150,255,0.2);
    --text: #1a1a2e;
    --text-muted: rgba(30,30,60,0.5);
    --topnav-bg: rgba(240,244,255,0.92);
}

body {
    font-family: 'Nunito', sans-serif;
    min-height: 100vh;
    background: var(--bg);
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 90px 16px 40px;
    position: relative;
    overflow-x: hidden;
    transition: background 0.4s;
}

/* ===== SOLAR SYSTEM CANVAS ===== */
#solar-canvas {
    position: fixed;
    top: 0; left: 0;
    width: 100%; height: 100%;
    z-index: 0;
    pointer-events: none;
    opacity: 0.6;
}
body.light-mode #solar-canvas { opacity: 0.2; }

body::before {
    content: '';
    position: fixed;
    inset: 0;
    background:
        radial-gradient(ellipse 80% 60% at 20% 40%, rgba(100,200,255,0.07) 0%, transparent 60%),
        radial-gradient(ellipse 60% 80% at 80% 20%, rgba(180,120,255,0.07) 0%, transparent 60%);
    animation: aurora 10s ease-in-out infinite alternate;
    pointer-events: none;
    z-index: 1;
}
@keyframes aurora { 0% { transform: scale(1); } 100% { transform: scale(1.08) rotate(-2deg); } }

/* TOP NAV */
.topnav {
    position: fixed;
    top: 0; left: 0; right: 0;
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 12px 24px;
    background: var(--topnav-bg);
    backdrop-filter: blur(16px);
    border-bottom: 1px solid rgba(255,255,255,0.07);
    z-index: 100;
}

.brand { font-family: 'Playfair Display', serif; font-size: 1.2rem; color: var(--text); }

.nav-right { display: flex; align-items: center; gap: 12px; position: relative; }

.profile-btn {
    width: 38px; height: 38px; border-radius: 50%;
    background: linear-gradient(135deg, #5bc8f5, #a78bfa);
    border: 2px solid rgba(255,255,255,0.2);
    cursor: pointer;
    display: flex; align-items: center; justify-content: center;
    font-size: 1rem; font-weight: 800; color: #fff;
    transition: transform 0.2s, box-shadow 0.2s;
    user-select: none;
}
.profile-btn:hover { transform: scale(1.08); box-shadow: 0 4px 16px rgba(92,200,245,0.4); }

.profile-dropdown {
    display: none;
    position: absolute;
    top: calc(100% + 10px); right: 0;
    background: rgba(20,20,40,0.97);
    backdrop-filter: blur(20px);
    border: 1px solid rgba(255,255,255,0.12);
    border-radius: 18px;
    padding: 16px;
    min-width: 240px;
    box-shadow: 0 16px 48px rgba(0,0,0,0.5);
    animation: dropDown 0.25s cubic-bezier(0.16,1,0.3,1) both;
    z-index: 200;
}
body.light-mode .profile-dropdown { background: rgba(255,255,255,0.98); border-color: rgba(100,150,255,0.2); }
.profile-dropdown.open { display: block; }

@keyframes dropDown {
    from { opacity:0; transform:translateY(-10px) scale(0.96); }
    to   { opacity:1; transform:translateY(0) scale(1); }
}

.profile-header {
    display: flex; align-items: center; gap: 12px;
    padding-bottom: 14px;
    border-bottom: 1px solid rgba(255,255,255,0.08);
    margin-bottom: 12px;
}
body.light-mode .profile-header { border-color: rgba(0,0,0,0.08); }

.profile-avatar-lg {
    width: 46px; height: 46px; border-radius: 50%;
    background: linear-gradient(135deg, #5bc8f5, #a78bfa);
    display: flex; align-items: center; justify-content: center;
    font-size: 1.3rem; font-weight: 900; color: #fff; flex-shrink: 0;
}

.profile-info-name { font-weight: 800; color: var(--text); font-size: 0.95rem; }
.profile-info-sub { color: var(--text-muted); font-size: 0.75rem; }

.dropdown-item {
    display: flex; align-items: center; gap: 10px;
    padding: 10px 12px; border-radius: 10px;
    color: var(--text-muted); text-decoration: none;
    font-size: 0.88rem; font-weight: 700; cursor: pointer;
    transition: all 0.2s; border: none; background: none;
    width: 100%; text-align: left; font-family: 'Nunito', sans-serif;
}
.dropdown-item:hover { background: rgba(255,255,255,0.06); color: var(--text); }
body.light-mode .dropdown-item:hover { background: rgba(0,0,0,0.05); }
.dropdown-item.danger { color: rgba(255,120,120,0.8); }
.dropdown-item.danger:hover { background: rgba(255,80,80,0.1); color: #ff6b6b; }

.dropdown-divider { height: 1px; background: rgba(255,255,255,0.07); margin: 8px 0; }
body.light-mode .dropdown-divider { background: rgba(0,0,0,0.08); }

.theme-toggle-row {
    display: flex; align-items: center; justify-content: space-between;
    padding: 8px 12px; border-radius: 10px;
}
.theme-label { display: flex; align-items: center; gap: 8px; color: var(--text-muted); font-size: 0.88rem; font-weight: 700; }

.toggle-switch { position: relative; width: 44px; height: 26px; cursor: pointer; }
.toggle-switch input { display: none; }
.toggle-track { width: 44px; height: 26px; border-radius: 13px; background: rgba(255,255,255,0.15); transition: background 0.3s; position: relative; }
body.light-mode .toggle-track { background: rgba(0,0,0,0.12); }
.toggle-switch input:checked + .toggle-track { background: linear-gradient(135deg, #5bc8f5, #a78bfa); }
.toggle-thumb { position: absolute; top: 3px; left: 3px; width: 20px; height: 20px; border-radius: 50%; background: #fff; box-shadow: 0 2px 6px rgba(0,0,0,0.3); transition: transform 0.3s cubic-bezier(0.34,1.56,0.64,1); }
.toggle-switch input:checked + .toggle-track .toggle-thumb { transform: translateX(18px); }

/* CONTENT */
.page-content {
    position: relative;
    z-index: 2;
    width: 100%;
    max-width: 560px;
}

.greeting {
    font-family: 'Playfair Display', serif;
    font-size: 1.8rem;
    color: var(--text);
    margin-bottom: 4px;
    animation: slideUp 0.6s cubic-bezier(0.16,1,0.3,1) both;
}
.greeting-sub {
    color: var(--text-muted);
    font-size: 0.88rem;
    margin-bottom: 28px;
    animation: slideUp 0.6s 0.1s cubic-bezier(0.16,1,0.3,1) both;
}
@keyframes slideUp { from { opacity:0; transform:translateY(20px); } to { opacity:1; transform:translateY(0); } }

.feature-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 14px;
    margin-bottom: 14px;
    animation: slideUp 0.6s 0.15s cubic-bezier(0.16,1,0.3,1) both;
}

.feature-card {
    background: var(--card-bg);
    backdrop-filter: blur(20px);
    border: 1px solid var(--card-border);
    border-radius: 20px;
    padding: 22px 18px;
    text-decoration: none;
    display: flex; flex-direction: column; gap: 10px;
    cursor: pointer;
    transition: transform 0.25s, box-shadow 0.25s, border-color 0.25s;
    position: relative; overflow: hidden;
}
.feature-card::before {
    content: ''; position: absolute; inset: 0;
    opacity: 0; transition: opacity 0.3s; border-radius: 20px;
}
.feature-card:hover { transform: translateY(-4px); box-shadow: 0 12px 36px rgba(0,0,0,0.3); }
.feature-card:hover::before { opacity: 1; }
.feature-card.test::before   { background: radial-gradient(ellipse at top left, rgba(91,200,245,0.12), transparent 70%); }
.feature-card.score::before  { background: radial-gradient(ellipse at top left, rgba(167,139,250,0.12), transparent 70%); }
.feature-card.therapy::before{ background: radial-gradient(ellipse at top left, rgba(110,231,183,0.12), transparent 70%); }
.feature-card.games::before  { background: radial-gradient(ellipse at top left, rgba(253,230,138,0.12), transparent 70%); }

.card-icon  { font-size: 2rem; line-height: 1; }
.card-title { font-size: 0.95rem; font-weight: 800; color: var(--text); line-height: 1.3; }
.card-desc  { font-size: 0.75rem; color: var(--text-muted); line-height: 1.4; }

.score-badge {
    display: inline-flex; align-items: center; gap: 6px;
    padding: 4px 12px; border-radius: 99px;
    font-size: 0.78rem; font-weight: 800; margin-top: 6px;
}
.card-arrow { position: absolute; top: 16px; right: 16px; color: var(--text-muted); font-size: 0.9rem; opacity: 0.5; }
</style>
</head>
<body>

<!-- SOLAR SYSTEM CANVAS -->
<canvas id="solar-canvas"></canvas>

<!-- TOP NAV -->
<nav class="topnav">
    <span class="brand">MindSpace 🌿</span>
    <div class="nav-right">
        <div class="profile-btn" id="profileBtn" onclick="toggleDropdown()">
            {{ session['user'][0].upper() }}
        </div>
        <div class="profile-dropdown" id="profileDropdown">
            <div class="profile-header">
                <div class="profile-avatar-lg">{{ session['user'][0].upper() }}</div>
                <div>
                    <div class="profile-info-name">{{ session['user'] }}</div>
                    <div class="profile-info-sub">Wellness member</div>
                </div>
            </div>
            <div class="theme-toggle-row">
                <span class="theme-label">🌙 Dark Mode</span>
                <label class="toggle-switch">
                    <input type="checkbox" id="themeToggle" onchange="toggleTheme(this)">
                    <div class="toggle-track"><div class="toggle-thumb"></div></div>
                </label>
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

<!-- CONTENT -->
<div class="page-content">
    <h1 class="greeting">Hello, {{ session['user'] }} 👋</h1>
    <p class="greeting-sub">How are you feeling today? Let's check in.</p>

    <div class="feature-grid">
        <a href="/test" class="feature-card test">
            <span class="card-arrow">↗</span>
            <div class="card-icon">🧠</div>
            <div>
                <div class="card-title">Take Test</div>
                <div class="card-desc">Mental wellness check-in</div>
            </div>
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
            <div>
                <div class="card-title">Sound Therapy</div>
                <div class="card-desc">Binaural beats for calm</div>
            </div>
        </a>
        <a href="/games" class="feature-card games">
            <span class="card-arrow">↗</span>
            <div class="card-icon">🎮</div>
            <div>
                <div class="card-title">Mind Games</div>
                <div class="card-desc">Sudoku & Chess</div>
            </div>
        </a>
    </div>
</div>

<script>
// ===== SOLAR SYSTEM ANIMATION =====
(function() {
    const canvas = document.getElementById('solar-canvas');
    const ctx = canvas.getContext('2d');
    let W, H, cx, cy, scale;

    function resize() {
        W = canvas.width  = window.innerWidth;
        H = canvas.height = window.innerHeight;
        cx = W / 2; cy = H / 2;
        scale = Math.min(W, H) / 900;
    }
    resize();
    window.addEventListener('resize', resize);

    const SUN_R = 28;
    const planets = [
        { name:'Mercury', r:5,  orbitR:80,  speed:4.1,   color:'#b5b5b5', glow:'rgba(181,181,181,0.4)', angle:0,    moons:[] },
        { name:'Venus',   r:9,  orbitR:130, speed:1.6,   color:'#e8cda0', glow:'rgba(232,205,160,0.4)', angle:1.2,  moons:[] },
        { name:'Earth',   r:10, orbitR:185, speed:1.0,   color:'#4f9fff', glow:'rgba(79,159,255,0.45)', angle:2.5,
          moons:[{ r:3, orbitR:20, speed:13, color:'#ccc', angle:0 }] },
        { name:'Mars',    r:7,  orbitR:245, speed:0.53,  color:'#c1440e', glow:'rgba(193,68,14,0.4)',   angle:0.8,
          moons:[{ r:2, orbitR:15, speed:22, color:'#aaa', angle:1 }] },
        { name:'Jupiter', r:22, orbitR:330, speed:0.084, color:'#c88b3a', glow:'rgba(200,139,58,0.35)', angle:3.5,
          bands: true,
          moons:[
            { r:3, orbitR:32, speed:8.9,  color:'#f0c040', angle:0 },
            { r:2, orbitR:42, speed:4.5,  color:'#c0b0a0', angle:2 },
          ]
        },
        { name:'Saturn',  r:18, orbitR:420, speed:0.034, color:'#e4d191', glow:'rgba(228,209,145,0.35)', angle:1.0,
          rings: true, moons:[{ r:3, orbitR:36, speed:5.3, color:'#e0d8c0', angle:1.5 }]
        },
        { name:'Uranus',  r:13, orbitR:500, speed:0.012, color:'#7de8e8', glow:'rgba(125,232,232,0.35)', angle:4.2, moons:[] },
        { name:'Neptune', r:12, orbitR:570, speed:0.006, color:'#4b70dd', glow:'rgba(75,112,221,0.35)',  angle:5.1, moons:[] },
    ];

    const stars = Array.from({length:200}, () => ({
        x: Math.random(), y: Math.random(),
        r: Math.random() * 1.5 + 0.2,
        opacity: Math.random() * 0.7 + 0.2,
        twinkle: Math.random() * Math.PI * 2,
        twinkleSpeed: Math.random() * 0.02 + 0.005
    }));

    const asteroids = Array.from({length:70}, () => ({
        angle: Math.random() * Math.PI * 2,
        orbitR: 278 + (Math.random() - 0.5) * 26,
        speed: 0.18 + Math.random() * 0.12,
        r: Math.random() * 1.5 + 0.3,
        opacity: Math.random() * 0.5 + 0.2
    }));

    let t = 0;

    function drawSun() {
        [80,55,35].forEach((gr) => {
            const grad = ctx.createRadialGradient(cx, cy, 0, cx, cy, gr * scale);
            grad.addColorStop(0, 'rgba(255,200,80,0.06)');
            grad.addColorStop(1, 'rgba(255,200,80,0)');
            ctx.fillStyle = grad;
            ctx.beginPath(); ctx.arc(cx, cy, gr * scale, 0, Math.PI*2); ctx.fill();
        });
        ctx.save(); ctx.translate(cx, cy); ctx.rotate(t * 0.001);
        for (let i = 0; i < 8; i++) {
            ctx.save(); ctx.rotate((i / 8) * Math.PI * 2);
            const fGrad = ctx.createLinearGradient(0, 0, 0, -SUN_R * scale * 2.2);
            fGrad.addColorStop(0, 'rgba(255,220,80,0.18)'); fGrad.addColorStop(1, 'rgba(255,140,0,0)');
            ctx.fillStyle = fGrad;
            ctx.beginPath(); ctx.moveTo(-3*scale, 0); ctx.quadraticCurveTo(0, -SUN_R*scale*1.5, 3*scale, 0); ctx.fill();
            ctx.restore();
        }
        ctx.restore();
        const sunGrad = ctx.createRadialGradient(cx-SUN_R*scale*0.3, cy-SUN_R*scale*0.3, 0, cx, cy, SUN_R*scale);
        sunGrad.addColorStop(0, '#fff7a0'); sunGrad.addColorStop(0.3, '#ffe066');
        sunGrad.addColorStop(0.7, '#ff9900'); sunGrad.addColorStop(1, '#ff6600');
        ctx.fillStyle = sunGrad;
        ctx.beginPath(); ctx.arc(cx, cy, SUN_R*scale, 0, Math.PI*2); ctx.fill();
    }

    function lighten(hex, amt) {
        const n = parseInt(hex.replace('#',''), 16);
        return `rgb(${Math.min(255,(n>>16)+amt)},${Math.min(255,((n>>8)&0xff)+amt)},${Math.min(255,(n&0xff)+amt)})`;
    }
    function darken(hex, amt) {
        const n = parseInt(hex.replace('#',''), 16);
        return `rgb(${Math.max(0,(n>>16)-amt)},${Math.max(0,((n>>8)&0xff)-amt)},${Math.max(0,(n&0xff)-amt)})`;
    }

    function drawPlanet(p) {
        const angle = p.angle + t * p.speed * 0.0008;
        const px = cx + Math.cos(angle) * p.orbitR * scale;
        const py = cy + Math.sin(angle) * p.orbitR * scale;
        const pr = p.r * scale;

        if (p.glow) {
            const gGrad = ctx.createRadialGradient(px, py, 0, px, py, pr*3);
            gGrad.addColorStop(0, p.glow); gGrad.addColorStop(1, 'rgba(0,0,0,0)');
            ctx.fillStyle = gGrad; ctx.beginPath(); ctx.arc(px, py, pr*3, 0, Math.PI*2); ctx.fill();
        }

        if (p.rings) {
            ctx.save(); ctx.translate(px, py); ctx.scale(1, 0.3);
            const rg = ctx.createRadialGradient(0, 0, pr*1.3, 0, 0, pr*2.6);
            rg.addColorStop(0, 'rgba(228,209,145,0.55)'); rg.addColorStop(0.5, 'rgba(200,180,120,0.35)'); rg.addColorStop(1, 'rgba(180,160,100,0)');
            ctx.fillStyle = rg; ctx.beginPath(); ctx.arc(0, 0, pr*2.6, 0, Math.PI*2); ctx.fill(); ctx.restore();
        }

        const pGrad = ctx.createRadialGradient(px-pr*0.3, py-pr*0.3, 0, px, py, pr);
        if (p.name === 'Jupiter') {
            pGrad.addColorStop(0, '#e8b870'); pGrad.addColorStop(0.5, '#c88b3a'); pGrad.addColorStop(1, '#8a5a20');
        } else if (p.name === 'Earth') {
            pGrad.addColorStop(0, '#7dc8ff'); pGrad.addColorStop(0.4, '#4f9fff'); pGrad.addColorStop(0.8, '#2a5fc0'); pGrad.addColorStop(1, '#1a3a80');
        } else {
            pGrad.addColorStop(0, lighten(p.color, 50)); pGrad.addColorStop(0.6, p.color); pGrad.addColorStop(1, darken(p.color, 50));
        }
        ctx.fillStyle = pGrad; ctx.beginPath(); ctx.arc(px, py, pr, 0, Math.PI*2); ctx.fill();

        if (p.name === 'Jupiter') {
            ctx.save(); ctx.beginPath(); ctx.arc(px, py, pr, 0, Math.PI*2); ctx.clip();
            ['rgba(160,90,30,0.3)','rgba(220,170,90,0.2)','rgba(140,80,20,0.25)'].forEach((bc, i) => {
                ctx.fillStyle = bc; ctx.fillRect(px-pr, py-pr+(pr*2/4)*(i+1)-2, pr*2, 4+i*2);
            }); ctx.restore();
        }

        if (p.moons) {
            p.moons.forEach(m => {
                const ma = m.angle + t * m.speed * 0.0008;
                const mx2 = px + Math.cos(ma) * m.orbitR * scale;
                const my2 = py + Math.sin(ma) * m.orbitR * scale;
                ctx.fillStyle = m.color; ctx.beginPath(); ctx.arc(mx2, my2, m.r*scale, 0, Math.PI*2); ctx.fill();
            });
        }
    }

    function animate() {
        ctx.clearRect(0, 0, W, H);
        ctx.fillStyle = '#0a0a18'; ctx.fillRect(0, 0, W, H);

        stars.forEach(s => {
            s.twinkle += s.twinkleSpeed;
            ctx.fillStyle = `rgba(255,255,255,${s.opacity*(0.7+0.3*Math.sin(s.twinkle))})`;
            ctx.beginPath(); ctx.arc(s.x*W, s.y*H, s.r, 0, Math.PI*2); ctx.fill();
        });

        // Orbit rings
        ctx.strokeStyle = 'rgba(255,255,255,0.06)'; ctx.lineWidth = 1;
        planets.forEach(p => { ctx.beginPath(); ctx.arc(cx, cy, p.orbitR*scale, 0, Math.PI*2); ctx.stroke(); });

        // Asteroid belt
        asteroids.forEach(a => {
            a.angle += a.speed * 0.0004;
            ctx.fillStyle = `rgba(180,160,140,${a.opacity})`;
            ctx.beginPath(); ctx.arc(cx+Math.cos(a.angle)*a.orbitR*scale, cy+Math.sin(a.angle)*a.orbitR*scale, a.r*scale, 0, Math.PI*2); ctx.fill();
        });

        drawSun();
        planets.forEach(p => drawPlanet(p));
        t++;
        requestAnimationFrame(animate);
    }
    animate();
})();

// ===== DROPDOWN & THEME =====
function toggleDropdown() {
    document.getElementById('profileDropdown').classList.toggle('open');
}
document.addEventListener('click', e => {
    if (!document.getElementById('profileBtn').contains(e.target) &&
        !document.getElementById('profileDropdown').contains(e.target)) {
        document.getElementById('profileDropdown').classList.remove('open');
    }
});

// FIX: Theme logic — dark mode = toggle checked
const savedTheme = localStorage.getItem('mindspace-theme');
const isDark = savedTheme !== 'light';
document.getElementById('themeToggle').checked = isDark;
if (!isDark) document.body.classList.add('light-mode');

function toggleTheme(cb) {
    document.body.classList.toggle('light-mode', !cb.checked);
    localStorage.setItem('mindspace-theme', cb.checked ? 'dark' : 'light');
}
</script>
</body>
</html>
""", session=session, binaural=BINAURAL, last_score=last_score, last_status=last_status)


# ---------------- TEST PAGE ----------------
@app.route("/test")
def test():
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
body { font-family: 'Nunito', sans-serif; min-height: 100vh; background: #0d0d1a; display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 24px 16px 100px; position: relative; overflow-x: hidden; }
body::before { content: ''; position: fixed; inset: 0; background: radial-gradient(ellipse 80% 60% at 20% 40%, rgba(100,200,255,0.1) 0%, transparent 60%), radial-gradient(ellipse 60% 80% at 80% 20%, rgba(180,120,255,0.1) 0%, transparent 60%); animation: aurora 10s ease-in-out infinite alternate; pointer-events: none; }
@keyframes aurora { 0% { transform: scale(1); } 100% { transform: scale(1.08) rotate(-2deg); } }
.particle { position: fixed; border-radius: 50%; pointer-events: none; animation: float linear infinite; z-index: 0; }
@keyframes float { 0% { transform: translateY(110vh) scale(0); opacity: 0; } 10% { opacity: 0.5; } 90% { opacity: 0.3; } 100% { transform: translateY(-10vh) scale(1.2); opacity: 0; } }
.topnav { position: fixed; top: 0; left: 0; right: 0; display: flex; justify-content: space-between; align-items: center; padding: 14px 24px; background: rgba(13,13,26,0.8); backdrop-filter: blur(16px); border-bottom: 1px solid rgba(255,255,255,0.07); z-index: 100; }
.brand { font-family: 'Playfair Display', serif; font-size: 1.2rem; color: #fff; }
.nav-links a { color: rgba(255,255,255,0.5); text-decoration: none; font-size: 0.82rem; font-weight: 700; margin-left: 16px; padding: 6px 14px; border-radius: 20px; border: 1px solid rgba(255,255,255,0.1); transition: all 0.2s; }
.nav-links a:hover { color: #fff; background: rgba(255,255,255,0.08); }
.main-card { position: relative; z-index: 1; background: rgba(255,255,255,0.04); backdrop-filter: blur(24px); border: 1px solid rgba(255,255,255,0.09); border-radius: 28px; padding: 40px 36px; width: 100%; max-width: 520px; box-shadow: 0 24px 80px rgba(0,0,0,0.5), inset 0 1px 0 rgba(255,255,255,0.08); margin-top: 60px; animation: slideUp 0.7s cubic-bezier(0.16,1,0.3,1) both; }
@keyframes slideUp { from { opacity:0; transform:translateY(40px) scale(0.96); } to { opacity:1; transform:translateY(0) scale(1); } }
.progress-wrap { display: flex; align-items: center; gap: 12px; margin-bottom: 28px; }
.progress-bar { flex: 1; height: 6px; background: rgba(255,255,255,0.08); border-radius: 99px; overflow: hidden; }
.progress-fill { height: 100%; background: linear-gradient(90deg, #5bc8f5, #a78bfa); border-radius: 99px; transition: width 0.5s cubic-bezier(0.16,1,0.3,1); box-shadow: 0 0 10px rgba(167,139,250,0.6); }
.progress-label { color: rgba(255,255,255,0.4); font-size: 0.78rem; font-weight: 700; white-space: nowrap; }
.question-wrap { min-height: 56px; margin-bottom: 28px; }
.question-text { font-size: 1.15rem; font-weight: 800; color: #fff; line-height: 1.5; animation: fadeInQ 0.4s cubic-bezier(0.16,1,0.3,1) both; }
@keyframes fadeInQ { from { opacity:0; transform:translateX(30px); } to { opacity:1; transform:translateX(0); } }
.options { display: flex; flex-direction: column; gap: 10px; margin-bottom: 28px; }
.option-label { display: flex; align-items: center; gap: 14px; padding: 13px 18px; background: rgba(255,255,255,0.04); border: 1.5px solid rgba(255,255,255,0.08); border-radius: 14px; cursor: pointer; transition: all 0.25s; animation: fadeInOpt 0.4s cubic-bezier(0.16,1,0.3,1) both; }
.option-label:nth-child(1){animation-delay:0.05s;}.option-label:nth-child(2){animation-delay:0.10s;}.option-label:nth-child(3){animation-delay:0.15s;}.option-label:nth-child(4){animation-delay:0.20s;}.option-label:nth-child(5){animation-delay:0.25s;}
@keyframes fadeInOpt { from { opacity:0; transform:translateX(-20px); } to { opacity:1; transform:translateX(0); } }
.option-label:hover { background: rgba(92,200,245,0.08); border-color: rgba(92,200,245,0.35); transform: translateX(4px); }
.option-label input[type="radio"] { display: none; }
.option-label.selected { background: rgba(92,200,245,0.12); border-color: #5bc8f5; box-shadow: 0 0 0 3px rgba(92,200,245,0.12); }
.option-dot { width: 20px; height: 20px; border-radius: 50%; border: 2px solid rgba(255,255,255,0.2); transition: all 0.2s; flex-shrink: 0; display: flex; align-items: center; justify-content: center; }
.option-label.selected .option-dot { border-color: #5bc8f5; background: #5bc8f5; box-shadow: 0 0 8px rgba(92,200,245,0.7); }
.option-dot::after { content: ''; width: 8px; height: 8px; border-radius: 50%; background: #fff; opacity: 0; transform: scale(0); transition: all 0.2s; }
.option-label.selected .option-dot::after { opacity: 1; transform: scale(1); }
.option-text { color: rgba(255,255,255,0.75); font-size: 0.9rem; font-weight: 600; }
.option-val { margin-left: auto; font-size: 1.1rem; }
.btn-next { width: 100%; padding: 15px; border: none; border-radius: 14px; font-size: 1rem; font-weight: 800; font-family: 'Nunito', sans-serif; cursor: pointer; background: linear-gradient(135deg, #5bc8f5, #a78bfa); color: #fff; transition: transform 0.2s, box-shadow 0.2s, opacity 0.2s; }
.btn-next:hover { transform: translateY(-2px); box-shadow: 0 8px 28px rgba(92,200,245,0.3); }
.btn-next:disabled { opacity: 0.4; cursor: not-allowed; transform: none; }
.result-wrap { display: none; animation: fadeInResult 0.6s cubic-bezier(0.16,1,0.3,1) both; }
@keyframes fadeInResult { from { opacity:0; transform:scale(0.9); } to { opacity:1; transform:scale(1); } }
.result-badge { text-align: center; padding: 24px; border-radius: 20px; margin-bottom: 20px; border: 1.5px solid rgba(255,255,255,0.1); }
.result-status { font-family: 'Playfair Display', serif; font-size: 2rem; font-weight: 700; margin-bottom: 6px; }
.result-score { color: rgba(255,255,255,0.5); font-size: 0.9rem; margin-bottom: 16px; }
.remedies { display: flex; flex-direction: column; gap: 8px; text-align: left; }
.remedy-item { display: flex; align-items: center; gap: 10px; padding: 10px 14px; background: rgba(255,255,255,0.04); border-radius: 10px; color: rgba(255,255,255,0.8); font-size: 0.88rem; font-weight: 600; }
.btn-retake { width: 100%; padding: 13px; margin-top: 16px; border: 1.5px solid rgba(255,255,255,0.15); border-radius: 14px; background: transparent; color: rgba(255,255,255,0.7); font-family: 'Nunito', sans-serif; font-weight: 700; cursor: pointer; transition: all 0.2s; font-size: 0.9rem; }
.btn-retake:hover { background: rgba(255,255,255,0.06); color: #fff; }
.yt-float { position: fixed; bottom: 28px; right: 28px; z-index: 200; display: none; }
.yt-float a { display: flex; align-items: center; gap: 10px; background: linear-gradient(135deg, #5bc8f5, #a78bfa); color: #fff; text-decoration: none; padding: 12px 20px 12px 14px; border-radius: 99px; font-weight: 800; font-size: 0.85rem; box-shadow: 0 8px 28px rgba(92,200,245,0.35); transition: transform 0.3s; animation: pulse-glow 2.5s ease-in-out infinite; }
.yt-float a:hover { transform: translateY(-3px) scale(1.04); }
@keyframes pulse-glow { 0%,100% { box-shadow: 0 8px 28px rgba(92,200,245,0.35); } 50% { box-shadow: 0 8px 40px rgba(167,139,250,0.55); } }
.yt-icon { width: 32px; height: 32px; background: rgba(255,255,255,0.2); border-radius: 50%; display: flex; align-items: center; justify-content: center; }
.yt-icon svg { width: 16px; height: 16px; fill: #fff; }
.alert-toast { position: fixed; top: 80px; right: 24px; background: rgba(255,100,100,0.15); border: 1px solid rgba(255,100,100,0.3); color: #ffaaaa; padding: 12px 18px; border-radius: 12px; font-size: 0.85rem; font-weight: 700; z-index: 300; display: none; }
</style>
</head>
<body>
<nav class="topnav">
    <span class="brand">MindSpace 🌿</span>
    <div class="nav-links">
        <a href="/">🏠 Home</a>
        <a href="/history">📈 History</a>
        <a href="/logout">👋 Logout</a>
    </div>
</nav>
<div class="alert-toast" id="toast">👆 Please select an option!</div>
<div class="main-card" id="mainCard">
    <div class="progress-wrap">
        <div class="progress-bar"><div class="progress-fill" id="progressFill" style="width:0%"></div></div>
        <span class="progress-label" id="progressLabel">0 / 9</span>
    </div>
    <div class="question-wrap"><div class="question-text" id="questionText"></div></div>
    <div class="options" id="options"></div>
    <button class="btn-next" id="nextBtn" onclick="next()">Next →</button>
    <div class="result-wrap" id="resultWrap">
        <div class="result-badge" id="resultBadge">
            <div class="result-status" id="resultStatus"></div>
            <div class="result-score" id="resultScore"></div>
            <div class="remedies" id="remediesList"></div>
        </div>
        <button class="btn-retake" onclick="retake()">🔄 Take Again</button>
        <a href="/" style="display:block;text-align:center;margin-top:10px;color:rgba(255,255,255,0.4);font-size:0.85rem;text-decoration:none;font-weight:700;">← Back to Home</a>
    </div>
</div>
<div class="yt-float" id="ytFloat">
    <a href="{{ binaural }}" target="_blank" rel="noopener">
        <div class="yt-icon"><svg viewBox="0 0 24 24"><path d="M21.8 8s-.2-1.4-.8-2c-.8-.8-1.6-.8-2-.9C16.4 5 12 5 12 5s-4.4 0-7 .1c-.4.1-1.2.1-2 .9C2.4 6.6 2.2 8 2.2 8S2 9.6 2 11.2v1.5C2 14.3 2.2 16 2.2 16s.2 1.4.8 2c.8.8 1.8.8 2.2.9C6.6 19 12 19 12 19s4.4 0 7-.1c.4-.1 1.2-.1 2-.9.6-.6.8-2 .8-2S22 14.3 22 12.7v-1.5C22 9.6 21.8 8 21.8 8zM9.7 14.5V9l5.3 2.8-5.3 2.7z"/></svg></div>
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
    qEl.style.animation = 'none'; qEl.offsetHeight; qEl.style.animation = '';
    qEl.textContent = q[i].label;
    const opt = document.getElementById('options');
    opt.innerHTML = '';
    for (let j = 1; j <= 5; j++) {
        const lbl = document.createElement('label');
        lbl.className = 'option-label';
        lbl.innerHTML = `<input type="radio" name="a" value="${j}"><div class="option-dot"></div><span class="option-text">${labels[j-1]}</span><span class="option-val">${emoji[j-1]}</span>`;
        lbl.addEventListener('click', () => {
            document.querySelectorAll('.option-label').forEach(l => l.classList.remove('selected'));
            lbl.classList.add('selected');
            lbl.querySelector('input').checked = true;
        });
        opt.appendChild(lbl);
    }
}
load();
function next() {
    const v = document.querySelector('input[name=a]:checked');
    if (!v) { const t=document.getElementById('toast'); t.style.display='block'; setTimeout(()=>t.style.display='none',2200); return; }
    ans[q[i].id] = parseInt(v.value);
    if (i < q.length - 1) { i++; load(); }
    else {
        document.getElementById('progressFill').style.width = '100%';
        document.getElementById('progressLabel').textContent = '9 / 9';
        document.getElementById('nextBtn').disabled = true;
        document.getElementById('nextBtn').textContent = '⏳ Analyzing...';
        fetch('/assess', { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(ans) })
        .then(r=>r.json()).then(d=>{
            document.getElementById('questionText').style.display='none';
            document.getElementById('options').style.display='none';
            document.getElementById('nextBtn').style.display='none';
            const colorMap={'#0a0':{bg:'rgba(0,200,100,0.08)',border:'rgba(0,200,100,0.25)'},'#e6b800':{bg:'rgba(230,184,0,0.08)',border:'rgba(230,184,0,0.25)'},'#f80':{bg:'rgba(255,128,0,0.08)',border:'rgba(255,128,0,0.25)'},'#f00':{bg:'rgba(255,60,60,0.08)',border:'rgba(255,60,60,0.25)'}};
            const cm=colorMap[d.color]||{bg:'rgba(255,255,255,0.05)',border:'rgba(255,255,255,0.1)'};
            const badge=document.getElementById('resultBadge'); badge.style.background=cm.bg; badge.style.borderColor=cm.border;
            document.getElementById('resultStatus').style.color=d.color; document.getElementById('resultStatus').textContent=d.status;
            document.getElementById('resultScore').textContent='🧮 Wellness Score: '+d.score;
            const icons=['🌅','🏃','🛌']; const rl=document.getElementById('remediesList'); rl.innerHTML='';
            d.remedies.forEach((r,idx)=>{ const item=document.createElement('div'); item.className='remedy-item'; item.textContent=(icons[idx]||'✅')+'  '+r; rl.appendChild(item); });
            document.getElementById('resultWrap').style.display='block';
            document.getElementById('ytFloat').style.display='block';
        });
    }
}
function retake() {
    i=0; ans={};
    document.getElementById('questionText').style.display=''; document.getElementById('options').style.display='';
    document.getElementById('nextBtn').style.display=''; document.getElementById('nextBtn').disabled=false;
    document.getElementById('nextBtn').textContent='Next →'; document.getElementById('resultWrap').style.display='none';
    document.getElementById('ytFloat').style.display='none';
    load();
}
function makeParticles(){const colors=['#7ec8f7','#a78bfa','#6ee7b7','#fde68a','#f9a8d4'];for(let p=0;p<18;p++){const el=document.createElement('div');el.className='particle';const size=Math.random()*6+2;el.style.cssText=`width:${size}px;height:${size}px;left:${Math.random()*100}vw;background:${colors[Math.floor(Math.random()*colors.length)]};animation-duration:${Math.random()*12+8}s;animation-delay:${Math.random()*-15}s;opacity:${Math.random()*0.4+0.1}`;document.body.appendChild(el);}}
makeParticles();
</script>
</body>
</html>
""", questions=questions, binaural=BINAURAL)


# ---------------- ASSESS ----------------
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
    cur = conn.cursor()
    cur.execute("INSERT INTO results (username,score,status) VALUES (?,?,?)", (session["user"], score, status))
    conn.commit()
    conn.close()
    remedies = ["Maintain a consistent daily routine", "Exercise for 30 mins daily", "Prioritize 7–8 hours of sleep"]
    return jsonify({"status": status, "color": color, "score": score, "remedies": remedies, "link": BINAURAL})


# ---------------- GAMES ----------------
@app.route("/games")
def games():
    if "user" not in session:
        return redirect("/login")
    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>MindSpace — Mind Games</title>
<link href="https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700;800;900&family=Playfair+Display:wght@700&display=swap" rel="stylesheet">
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0;}
body{font-family:'Nunito',sans-serif;min-height:100vh;background:#0d0d1a;color:#fff;padding:90px 16px 40px;position:relative;overflow-x:hidden;}
body::before{content:'';position:fixed;inset:0;background:radial-gradient(ellipse 80% 60% at 20% 40%,rgba(100,200,255,0.1) 0%,transparent 60%),radial-gradient(ellipse 60% 80% at 80% 20%,rgba(180,120,255,0.1) 0%,transparent 60%);animation:aurora 10s ease-in-out infinite alternate;pointer-events:none;}
@keyframes aurora{0%{transform:scale(1);}100%{transform:scale(1.08) rotate(-2deg);}}
.particle{position:fixed;border-radius:50%;pointer-events:none;animation:float linear infinite;}
@keyframes float{0%{transform:translateY(110vh) scale(0);opacity:0;}10%{opacity:0.5;}90%{opacity:0.3;}100%{transform:translateY(-10vh) scale(1.2);opacity:0;}}
.topnav{position:fixed;top:0;left:0;right:0;display:flex;justify-content:space-between;align-items:center;padding:14px 24px;background:rgba(13,13,26,0.85);backdrop-filter:blur(16px);border-bottom:1px solid rgba(255,255,255,0.07);z-index:100;}
.brand{font-family:'Playfair Display',serif;font-size:1.2rem;color:#fff;}
.nav-links a{color:rgba(255,255,255,0.5);text-decoration:none;font-size:0.82rem;font-weight:700;margin-left:12px;padding:6px 14px;border-radius:20px;border:1px solid rgba(255,255,255,0.1);transition:all 0.2s;}
.nav-links a:hover{color:#fff;background:rgba(255,255,255,0.08);}
.page-wrap{position:relative;z-index:1;max-width:700px;margin:0 auto;}
.page-title{font-family:'Playfair Display',serif;font-size:1.8rem;margin-bottom:4px;animation:slideUp 0.6s cubic-bezier(0.16,1,0.3,1) both;}
.page-sub{color:rgba(255,255,255,0.4);font-size:0.85rem;margin-bottom:28px;}
@keyframes slideUp{from{opacity:0;transform:translateY(20px);}to{opacity:1;transform:translateY(0);}}
.game-tabs{display:flex;gap:10px;margin-bottom:24px;background:rgba(255,255,255,0.04);padding:6px;border-radius:16px;border:1px solid rgba(255,255,255,0.08);}
.tab-btn{flex:1;padding:10px;border:none;border-radius:12px;font-family:'Nunito',sans-serif;font-weight:800;font-size:0.9rem;cursor:pointer;transition:all 0.25s;background:transparent;color:rgba(255,255,255,0.4);}
.tab-btn.active{background:linear-gradient(135deg,#5bc8f5,#a78bfa);color:#fff;box-shadow:0 4px 16px rgba(92,200,245,0.3);}
.game-panel{display:none;}.game-panel.active{display:block;}
.sudoku-grid{display:grid;grid-template-columns:repeat(9,1fr);gap:2px;background:rgba(92,200,245,0.3);border-radius:12px;overflow:hidden;padding:2px;max-width:360px;margin:0 auto 20px;}
.sudoku-cell{background:rgba(13,13,26,0.9);aspect-ratio:1;display:flex;align-items:center;justify-content:center;font-size:1.1rem;font-weight:800;cursor:pointer;transition:background 0.2s;border:none;color:#fff;font-family:'Nunito',sans-serif;}
.sudoku-cell:hover{background:rgba(92,200,245,0.12);}
.sudoku-cell.given{color:#5bc8f5;cursor:default;}
.sudoku-cell.selected{background:rgba(92,200,245,0.2)!important;}
.sudoku-cell.error{color:#ff6b6b!important;}
.sudoku-numpad{display:flex;gap:8px;justify-content:center;flex-wrap:wrap;margin-bottom:16px;}
.num-btn{width:44px;height:44px;border:1.5px solid rgba(255,255,255,0.12);border-radius:10px;background:rgba(255,255,255,0.05);color:#fff;font-size:1.1rem;font-weight:800;cursor:pointer;font-family:'Nunito',sans-serif;transition:all 0.2s;}
.num-btn:hover{background:rgba(92,200,245,0.15);border-color:#5bc8f5;}
.game-actions{display:flex;gap:10px;justify-content:center;}
.game-btn{padding:10px 22px;border:none;border-radius:12px;font-family:'Nunito',sans-serif;font-weight:800;font-size:0.88rem;cursor:pointer;transition:all 0.2s;}
.game-btn.primary{background:linear-gradient(135deg,#5bc8f5,#a78bfa);color:#fff;}
.game-btn.secondary{background:rgba(255,255,255,0.06);border:1.5px solid rgba(255,255,255,0.12);color:rgba(255,255,255,0.7);}
.game-btn:hover{transform:translateY(-2px);}
.sudoku-status{text-align:center;color:rgba(255,255,255,0.5);font-size:0.85rem;margin-bottom:12px;}
.chess-wrap{max-width:400px;margin:0 auto;}
.chess-info{display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;padding:10px 16px;background:rgba(255,255,255,0.04);border-radius:12px;border:1px solid rgba(255,255,255,0.08);}
.chess-turn{font-weight:800;font-size:0.9rem;color:#fff;}
.chess-board{display:grid;grid-template-columns:repeat(8,1fr);border-radius:12px;overflow:hidden;border:2px solid rgba(255,255,255,0.15);}
.chess-sq{aspect-ratio:1;display:flex;align-items:center;justify-content:center;font-size:1.6rem;cursor:pointer;transition:all 0.15s;position:relative;user-select:none;}
.chess-sq.light{background:rgba(255,255,255,0.08);}
.chess-sq.dark{background:rgba(0,0,0,0.4);}
.chess-sq.selected{background:rgba(92,200,245,0.35)!important;}
.chess-sq.valid-move::after{content:'';position:absolute;width:30%;height:30%;border-radius:50%;background:rgba(92,200,245,0.5);}
.chess-sq.valid-capture{background:rgba(255,100,100,0.25)!important;}
.chess-labels{display:flex;justify-content:space-around;padding:4px 0;color:rgba(255,255,255,0.3);font-size:0.7rem;font-weight:700;}
.chess-status{text-align:center;padding:10px;margin-top:10px;background:rgba(255,255,255,0.04);border-radius:10px;font-weight:700;font-size:0.88rem;color:rgba(255,255,255,0.6);}
</style>
</head>
<body>
<nav class="topnav">
    <span class="brand">MindSpace 🌿</span>
    <div class="nav-links"><a href="/">🏠 Home</a><a href="/logout">👋 Logout</a></div>
</nav>
<div class="page-wrap">
    <h1 class="page-title">🎮 Mind Games</h1>
    <p class="page-sub">Sharpen your mind with these relaxing games</p>
    <div class="game-tabs">
        <button class="tab-btn active" onclick="switchTab('sudoku',this)">🔢 Sudoku</button>
        <button class="tab-btn" onclick="switchTab('chess',this)">♟️ Chess</button>
    </div>
    <div class="game-panel active" id="panel-sudoku">
        <div class="sudoku-status" id="sudokuStatus">Select a cell, then enter a number</div>
        <div class="sudoku-grid" id="sudokuGrid"></div>
        <div class="sudoku-numpad" id="numpad"></div>
        <div class="game-actions">
            <button class="game-btn primary" onclick="newSudokuGame()">🔄 New Game</button>
            <button class="game-btn secondary" onclick="clearCell()">⌫ Clear</button>
            <button class="game-btn secondary" onclick="checkSudoku()">✅ Check</button>
        </div>
    </div>
    <div class="game-panel" id="panel-chess">
        <div class="chess-wrap">
            <div class="chess-info">
                <span class="chess-turn" id="chessTurn">⚪ White's Turn</span>
                <button class="game-btn secondary" onclick="newChessGame()" style="padding:6px 16px;font-size:0.8rem;">🔄 Reset</button>
            </div>
            <div class="chess-labels" id="chessFiles"></div>
            <div class="chess-board" id="chessBoard"></div>
            <div class="chess-status" id="chessStatus">Click a piece to start</div>
        </div>
    </div>
</div>
<script>
function switchTab(tab, btn) {
    document.querySelectorAll('.tab-btn').forEach(b=>b.classList.remove('active'));
    document.querySelectorAll('.game-panel').forEach(p=>p.classList.remove('active'));
    btn.classList.add('active');
    document.getElementById('panel-'+tab).classList.add('active');
}
const PUZZLES = [
    [5,3,0,0,7,0,0,0,0,6,0,0,1,9,5,0,0,0,0,9,8,0,0,0,0,6,0,8,0,0,0,6,0,0,0,3,4,0,0,8,0,3,0,0,1,7,0,0,0,2,0,0,0,6,0,6,0,0,0,0,2,8,0,0,0,0,4,1,9,0,0,5,0,0,0,0,8,0,0,7,9],
    [0,0,0,2,6,0,7,0,1,6,8,0,0,7,0,0,9,0,1,9,0,0,0,4,5,0,0,8,2,0,1,0,0,0,4,0,0,0,4,6,0,2,9,0,0,0,5,0,0,0,3,0,2,8,0,0,9,3,0,0,0,7,4,0,4,0,0,5,0,0,3,6,7,0,3,0,1,8,0,0,0]
];
let sudokuPuzzle=[],sudokuSolution=[],selectedCell=-1,originalPuzzleIdx=0;
function solveSudoku(board){const b=[...board];function solve(){const empty=b.indexOf(0);if(empty===-1)return true;const row=Math.floor(empty/9),col=empty%9;for(let n=1;n<=9;n++){if(isValid(b,row,col,n)){b[empty]=n;if(solve())return true;b[empty]=0;}}return false;}function isValid(b,r,c,n){for(let i=0;i<9;i++){if(b[r*9+i]===n||b[i*9+c]===n)return false;}const br=Math.floor(r/3)*3,bc=Math.floor(c/3)*3;for(let i=0;i<3;i++)for(let j=0;j<3;j++)if(b[(br+i)*9+(bc+j)]===n)return false;return true;}solve();return b;}
function newSudokuGame(){originalPuzzleIdx=Math.floor(Math.random()*PUZZLES.length);const base=PUZZLES[originalPuzzleIdx];sudokuPuzzle=[...base];sudokuSolution=solveSudoku([...base]);selectedCell=-1;renderSudoku();document.getElementById('sudokuStatus').textContent='Select a cell, then enter a number';document.getElementById('sudokuStatus').style.color='rgba(255,255,255,0.5)';}
function checkIfOriginal(idx){return PUZZLES[originalPuzzleIdx][idx]!==0;}
function renderSudoku(){const grid=document.getElementById('sudokuGrid');grid.innerHTML='';for(let i=0;i<81;i++){const cell=document.createElement('button');cell.className='sudoku-cell';if(checkIfOriginal(i))cell.classList.add('given');if(i===selectedCell)cell.classList.add('selected');cell.textContent=sudokuPuzzle[i]||'';cell.onclick=()=>selectCell(i);grid.appendChild(cell);}const np=document.getElementById('numpad');np.innerHTML='';for(let n=1;n<=9;n++){const b=document.createElement('button');b.className='num-btn';b.textContent=n;b.onclick=()=>enterNum(n);np.appendChild(b);}}
function selectCell(idx){if(checkIfOriginal(idx))return;selectedCell=idx;renderSudoku();}
function enterNum(n){if(selectedCell===-1)return;if(checkIfOriginal(selectedCell))return;sudokuPuzzle[selectedCell]=n;renderSudoku();if(!sudokuPuzzle.includes(0))checkSudoku();}
function clearCell(){if(selectedCell===-1||checkIfOriginal(selectedCell))return;sudokuPuzzle[selectedCell]=0;renderSudoku();}
function checkSudoku(){let errors=0;const cells=document.querySelectorAll('.sudoku-cell');for(let i=0;i<81;i++){cells[i].classList.remove('error');if(sudokuPuzzle[i]!==0&&sudokuPuzzle[i]!==sudokuSolution[i]){cells[i].classList.add('error');errors++;}}const status=document.getElementById('sudokuStatus');if(errors===0&&!sudokuPuzzle.includes(0)){status.textContent='🎉 Puzzle Complete! Brilliant!';status.style.color='#6ee7b7';}else if(errors>0){status.textContent=`❌ ${errors} error(s) found`;status.style.color='#ff9a9a';}else{status.textContent='✅ Looking good so far!';status.style.color='#6ee7b7';}}
document.addEventListener('keydown',e=>{if(selectedCell===-1)return;const n=parseInt(e.key);if(n>=1&&n<=9)enterNum(n);else if(e.key==='Backspace'||e.key==='Delete')clearCell();});
newSudokuGame();
const PIECES={'wK':'♔','wQ':'♕','wR':'♖','wB':'♗','wN':'♘','wP':'♙','bK':'♚','bQ':'♛','bR':'♜','bB':'♝','bN':'♞','bP':'♟'};
let chessBoard=[],chessSelected=null,chessTurn='w',validMoves=[];
function initChess(){const back=['R','N','B','Q','K','B','N','R'];chessBoard=[];for(let r=0;r<8;r++){chessBoard.push([]);for(let c=0;c<8;c++){if(r===0)chessBoard[r][c]='b'+back[c];else if(r===1)chessBoard[r][c]='bP';else if(r===6)chessBoard[r][c]='wP';else if(r===7)chessBoard[r][c]='w'+back[c];else chessBoard[r][c]=null;}}chessTurn='w';chessSelected=null;validMoves=[];renderChess();document.getElementById('chessTurn').textContent="⚪ White's Turn";document.getElementById('chessStatus').textContent='Click a piece to start';}
function getValidMoves(r,c){const p=chessBoard[r][c];if(!p)return[];const col=p[0],type=p[1];const moves=[];const inBounds=(r,c)=>r>=0&&r<8&&c>=0&&c<8;const enemy=(r2,c2)=>chessBoard[r2][c2]&&chessBoard[r2][c2][0]!==col;const empty=(r2,c2)=>!chessBoard[r2][c2];const addIf=(r2,c2)=>{if(inBounds(r2,c2)&&(empty(r2,c2)||enemy(r2,c2)))moves.push([r2,c2]);};const slide=(dr,dc)=>{let nr=r+dr,nc=c+dc;while(inBounds(nr,nc)){if(empty(nr,nc))moves.push([nr,nc]);else{if(enemy(nr,nc))moves.push([nr,nc]);break;}nr+=dr;nc+=dc;}};if(type==='P'){const dir=col==='w'?-1:1;if(inBounds(r+dir,c)&&empty(r+dir,c))moves.push([r+dir,c]);if((col==='w'&&r===6)||(col==='b'&&r===1))if(empty(r+dir,c)&&empty(r+2*dir,c))moves.push([r+2*dir,c]);[-1,1].forEach(dc=>{if(inBounds(r+dir,c+dc)&&enemy(r+dir,c+dc))moves.push([r+dir,c+dc]);});}else if(type==='R'){slide(1,0);slide(-1,0);slide(0,1);slide(0,-1);}else if(type==='B'){slide(1,1);slide(1,-1);slide(-1,1);slide(-1,-1);}else if(type==='Q'){slide(1,0);slide(-1,0);slide(0,1);slide(0,-1);slide(1,1);slide(1,-1);slide(-1,1);slide(-1,-1);}else if(type==='N'){[[-2,-1],[-2,1],[-1,-2],[-1,2],[1,-2],[1,2],[2,-1],[2,1]].forEach(([dr,dc])=>addIf(r+dr,c+dc));}else if(type==='K'){[[-1,-1],[-1,0],[-1,1],[0,-1],[0,1],[1,-1],[1,0],[1,1]].forEach(([dr,dc])=>addIf(r+dr,c+dc));}return moves;}
function handleChessClick(r,c){const p=chessBoard[r][c];if(chessSelected){const[sr,sc]=chessSelected;const isValid=validMoves.some(([mr,mc])=>mr===r&&mc===c);if(isValid){chessBoard[r][c]=chessBoard[sr][sc];chessBoard[sr][sc]=null;if(chessBoard[r][c]==='wP'&&r===0)chessBoard[r][c]='wQ';if(chessBoard[r][c]==='bP'&&r===7)chessBoard[r][c]='bQ';chessTurn=chessTurn==='w'?'b':'w';chessSelected=null;validMoves=[];renderChess();document.getElementById('chessTurn').textContent=chessTurn==='w'?"⚪ White's Turn":"⚫ Black's Turn";document.getElementById('chessStatus').textContent=chessTurn==='w'?'White to move':'Black to move';return;}chessSelected=null;validMoves=[];}if(p&&p[0]===chessTurn){chessSelected=[r,c];validMoves=getValidMoves(r,c);}renderChess();}
function renderChess(){const board=document.getElementById('chessBoard');board.innerHTML='';for(let r=0;r<8;r++){for(let c=0;c<8;c++){const sq=document.createElement('div');sq.className='chess-sq '+((r+c)%2===0?'light':'dark');if(chessSelected&&chessSelected[0]===r&&chessSelected[1]===c)sq.classList.add('selected');const isValid=validMoves.some(([mr,mc])=>mr===r&&mc===c);if(isValid){if(chessBoard[r][c])sq.classList.add('valid-capture');else sq.classList.add('valid-move');}const p=chessBoard[r][c];if(p)sq.textContent=PIECES[p]||p;sq.onclick=()=>handleChessClick(r,c);board.appendChild(sq);}}}
function newChessGame(){initChess();}
initChess();
const files=['a','b','c','d','e','f','g','h'];
document.getElementById('chessFiles').innerHTML=files.map(f=>`<span>${f}</span>`).join('');
function makeParticles(){const colors=['#7ec8f7','#a78bfa','#6ee7b7','#fde68a'];for(let p=0;p<14;p++){const el=document.createElement('div');el.className='particle';const size=Math.random()*5+2;el.style.cssText=`width:${size}px;height:${size}px;left:${Math.random()*100}vw;background:${colors[Math.floor(Math.random()*colors.length)]};animation-duration:${Math.random()*12+8}s;animation-delay:${Math.random()*-15}s;opacity:${Math.random()*0.4+0.1}`;document.body.appendChild(el);}}
makeParticles();
</script>
</body>
</html>
""")


# ---------------- PROFILE ----------------
@app.route("/profile")
def profile():
    if "user" not in session:
        return redirect("/login")
    conn = sqlite3.connect("app.db")
    cur = conn.cursor()
    cur.execute("SELECT username, mobile FROM users WHERE username=?", (session["user"],))
    user = cur.fetchone()
    cur.execute("SELECT COUNT(*) FROM results WHERE username=?", (session["user"],))
    count = cur.fetchone()[0]
    cur.execute("SELECT AVG(score) FROM results WHERE username=?", (session["user"],))
    avg = cur.fetchone()[0]
    conn.close()
    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>MindSpace — Profile</title>
<link href="https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700;800;900&family=Playfair+Display:wght@700&display=swap" rel="stylesheet">
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0;}
body{font-family:'Nunito',sans-serif;min-height:100vh;background:#0d0d1a;color:#fff;display:flex;flex-direction:column;align-items:center;padding:90px 16px 40px;position:relative;}
body::before{content:'';position:fixed;inset:0;background:radial-gradient(ellipse 80% 60% at 20% 40%,rgba(100,200,255,0.1) 0%,transparent 60%),radial-gradient(ellipse 60% 80% at 80% 20%,rgba(180,120,255,0.1) 0%,transparent 60%);animation:aurora 10s ease-in-out infinite alternate;pointer-events:none;}
@keyframes aurora{0%{transform:scale(1);}100%{transform:scale(1.08) rotate(-2deg);}}
.topnav{position:fixed;top:0;left:0;right:0;display:flex;justify-content:space-between;align-items:center;padding:14px 24px;background:rgba(13,13,26,0.85);backdrop-filter:blur(16px);border-bottom:1px solid rgba(255,255,255,0.07);z-index:100;}
.brand{font-family:'Playfair Display',serif;font-size:1.2rem;color:#fff;}
.nav-links a{color:rgba(255,255,255,0.5);text-decoration:none;font-size:0.82rem;font-weight:700;margin-left:12px;padding:6px 14px;border-radius:20px;border:1px solid rgba(255,255,255,0.1);transition:all 0.2s;}
.nav-links a:hover{color:#fff;background:rgba(255,255,255,0.08);}
.profile-card{position:relative;z-index:1;background:rgba(255,255,255,0.04);backdrop-filter:blur(24px);border:1px solid rgba(255,255,255,0.09);border-radius:28px;padding:36px;width:100%;max-width:420px;animation:slideUp 0.7s cubic-bezier(0.16,1,0.3,1) both;}
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
</style>
</head>
<body>
<nav class="topnav">
    <span class="brand">MindSpace 🌿</span>
    <div class="nav-links"><a href="/">🏠 Home</a><a href="/logout">👋 Logout</a></div>
</nav>
<div class="profile-card">
    <div class="avatar">{{ user[0][0].upper() }}</div>
    <div class="profile-name">{{ user[0] }}</div>
    <div class="profile-mobile">📱 {{ user[1] or 'No mobile on file' }}</div>
    <div class="stats-grid">
        <div class="stat-box"><div class="stat-val">{{ count }}</div><div class="stat-label">Total Check-ins</div></div>
        <div class="stat-box"><div class="stat-val">{{ "%.0f"|format(avg) if avg else '—' }}</div><div class="stat-label">Avg. Wellness Score</div></div>
    </div>
    <a class="back-btn" href="/">← Back to Home</a>
</div>
</body>
</html>
""", user=user, count=count, avg=avg)


# ---------------- SETTINGS ----------------
@app.route("/settings")
def settings():
    if "user" not in session:
        return redirect("/login")
    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>MindSpace — Settings</title>
<link href="https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700;800;900&family=Playfair+Display:wght@700&display=swap" rel="stylesheet">
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0;}
body{font-family:'Nunito',sans-serif;min-height:100vh;background:#0d0d1a;color:#fff;display:flex;flex-direction:column;align-items:center;padding:90px 16px 40px;position:relative;}
body::before{content:'';position:fixed;inset:0;background:radial-gradient(ellipse 80% 60% at 20% 40%,rgba(100,200,255,0.1) 0%,transparent 60%);animation:aurora 10s ease-in-out infinite alternate;pointer-events:none;}
@keyframes aurora{0%{transform:scale(1);}100%{transform:scale(1.08) rotate(-2deg);}}
.topnav{position:fixed;top:0;left:0;right:0;display:flex;justify-content:space-between;align-items:center;padding:14px 24px;background:rgba(13,13,26,0.85);backdrop-filter:blur(16px);border-bottom:1px solid rgba(255,255,255,0.07);z-index:100;}
.brand{font-family:'Playfair Display',serif;font-size:1.2rem;color:#fff;}
.nav-links a{color:rgba(255,255,255,0.5);text-decoration:none;font-size:0.82rem;font-weight:700;margin-left:12px;padding:6px 14px;border-radius:20px;border:1px solid rgba(255,255,255,0.1);transition:all 0.2s;}
.nav-links a:hover{color:#fff;background:rgba(255,255,255,0.08);}
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
</style>
</head>
<body>
<nav class="topnav">
    <span class="brand">MindSpace 🌿</span>
    <div class="nav-links"><a href="/">🏠 Home</a><a href="/logout">👋 Logout</a></div>
</nav>
<div class="settings-card">
    <h2>⚙️ Settings</h2>
    <div class="setting-row">
        <div><div class="setting-label">🌙 Dark Mode</div><div class="setting-desc">Toggle dark / light theme</div></div>
        <label class="toggle-switch"><input type="checkbox" id="darkToggle" onchange="toggleTheme(this)"><div class="toggle-track"><div class="toggle-thumb"></div></div></label>
    </div>
    <div class="setting-row">
        <div><div class="setting-label">🔔 Reminders</div><div class="setting-desc">Daily wellness check-in reminder</div></div>
        <label class="toggle-switch"><input type="checkbox" checked><div class="toggle-track"><div class="toggle-thumb"></div></div></label>
    </div>
    <div class="setting-row">
        <div><div class="setting-label">🎵 Ambient Sound</div><div class="setting-desc">Auto-play sound therapy</div></div>
        <label class="toggle-switch"><input type="checkbox"><div class="toggle-track"><div class="toggle-thumb"></div></div></label>
    </div>
    <div class="setting-row">
        <div><div class="setting-label">📊 Share Progress</div><div class="setting-desc">Allow wellness data sharing</div></div>
        <label class="toggle-switch"><input type="checkbox"><div class="toggle-track"><div class="toggle-thumb"></div></div></label>
    </div>
    <a class="back-btn" href="/">← Back to Home</a>
</div>
<script>
const saved = localStorage.getItem('mindspace-theme');
document.getElementById('darkToggle').checked = saved !== 'light';
function toggleTheme(cb) { localStorage.setItem('mindspace-theme', cb.checked ? 'dark' : 'light'); }
</script>
</body>
</html>
""")


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
    data     = [r[0] for r in reversed(rows)]
    labels   = list(range(1, len(data)+1))
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
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0;}
body{font-family:'Nunito',sans-serif;min-height:100vh;background:#0d0d1a;display:flex;flex-direction:column;align-items:center;padding:100px 16px 40px;position:relative;}
body::before{content:'';position:fixed;inset:0;background:radial-gradient(ellipse 80% 60% at 20% 40%,rgba(100,200,255,0.1) 0%,transparent 60%),radial-gradient(ellipse 60% 80% at 80% 20%,rgba(180,120,255,0.1) 0%,transparent 60%);animation:aurora 10s ease-in-out infinite alternate;pointer-events:none;}
@keyframes aurora{0%{transform:scale(1);}100%{transform:scale(1.08) rotate(-2deg);}}
.topnav{position:fixed;top:0;left:0;right:0;display:flex;justify-content:space-between;align-items:center;padding:14px 24px;background:rgba(13,13,26,0.85);backdrop-filter:blur(16px);border-bottom:1px solid rgba(255,255,255,0.07);z-index:100;}
.brand{font-family:'Playfair Display',serif;font-size:1.2rem;color:#fff;}
.nav-links a{color:rgba(255,255,255,0.5);text-decoration:none;font-size:0.82rem;font-weight:700;margin-left:16px;padding:6px 14px;border-radius:20px;border:1px solid rgba(255,255,255,0.1);transition:all 0.2s;}
.nav-links a:hover{color:#fff;background:rgba(255,255,255,0.08);}
.page-title{font-family:'Playfair Display',serif;font-size:1.8rem;color:#fff;margin-bottom:6px;position:relative;z-index:1;animation:slideUp 0.6s cubic-bezier(0.16,1,0.3,1) both;}
.page-sub{color:rgba(255,255,255,0.35);font-size:0.85rem;margin-bottom:28px;position:relative;z-index:1;}
@keyframes slideUp{from{opacity:0;transform:translateY(24px);}to{opacity:1;transform:translateY(0);}}
.chart-card{position:relative;z-index:1;background:rgba(255,255,255,0.04);backdrop-filter:blur(24px);border:1px solid rgba(255,255,255,0.09);border-radius:24px;padding:28px;width:100%;max-width:640px;box-shadow:0 20px 60px rgba(0,0,0,0.4);animation:slideUp 0.7s 0.1s cubic-bezier(0.16,1,0.3,1) both;margin-bottom:20px;}
.chart-card h3{color:rgba(255,255,255,0.7);font-size:0.85rem;text-transform:uppercase;letter-spacing:1px;margin-bottom:20px;}
.no-data{text-align:center;padding:40px;color:rgba(255,255,255,0.3);font-size:1rem;}
.back-btn{position:relative;z-index:1;display:inline-flex;align-items:center;gap:8px;padding:12px 22px;border:1.5px solid rgba(255,255,255,0.12);border-radius:99px;color:rgba(255,255,255,0.6);text-decoration:none;font-weight:700;font-size:0.85rem;transition:all 0.2s;background:rgba(255,255,255,0.04);margin-top:8px;}
.back-btn:hover{color:#fff;background:rgba(255,255,255,0.08);}
</style>
</head>
<body>
<nav class="topnav">
    <span class="brand">MindSpace 🌿</span>
    <div class="nav-links"><a href="/">🏠 Home</a><a href="/logout">👋 Logout</a></div>
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
<a class="back-btn" href="/">← Back to Home</a>
{% if data %}
<script>
const ctx=document.getElementById('histChart').getContext('2d');
const gradient=ctx.createLinearGradient(0,0,0,300);
gradient.addColorStop(0,'rgba(91,200,245,0.35)');
gradient.addColorStop(1,'rgba(167,139,250,0.0)');
new Chart(ctx,{type:'line',data:{labels:{{ labels|tojson }}.map(l=>'Check-in '+l),datasets:[{label:'Wellness Score',data:{{ data|tojson }},fill:true,backgroundColor:gradient,borderColor:'#5bc8f5',borderWidth:2.5,pointBackgroundColor:'#a78bfa',pointBorderColor:'#fff',pointBorderWidth:2,pointRadius:5,pointHoverRadius:8,tension:0.4}]},options:{responsive:true,plugins:{legend:{display:false},tooltip:{backgroundColor:'rgba(13,13,26,0.9)',borderColor:'rgba(255,255,255,0.1)',borderWidth:1,titleColor:'#fff',bodyColor:'rgba(255,255,255,0.6)',padding:12}},scales:{x:{grid:{color:'rgba(255,255,255,0.05)'},ticks:{color:'rgba(255,255,255,0.4)',font:{family:'Nunito',size:11}}},y:{grid:{color:'rgba(255,255,255,0.05)'},ticks:{color:'rgba(255,255,255,0.4)',font:{family:'Nunito',size:11}}}}}});
</script>
{% endif %}
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
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)  # FIX: debug=False stops auto-reload wiping sessions
