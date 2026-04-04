from flask import Flask, request, render_template_string, jsonify, redirect, session
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "secret123"

# ---------------- DATABASE ----------------
def init_db():
    conn = sqlite3.connect("users.db")
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
    {"id":"stress","label":"How often do you feel stressed?"},
    {"id":"sleep","label":"How is your sleep quality?"},
    {"id":"exercise","label":"How often do you exercise per week?"},
    {"id":"mood","label":"How often do you feel sad or down?"},
    {"id":"anxiety","label":"How often do you feel anxious?"},
    {"id":"focus","label":"Do you have trouble concentrating?"},
    {"id":"social","label":"Do you avoid social interactions?"},
    {"id":"motivation","label":"How motivated are you?"},
    {"id":"energy","label":"How is your energy level?"}
]

# ---------------- LOGIN ----------------
@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = sqlite3.connect("users.db")
        cur = conn.cursor()
        cur.execute("SELECT password FROM users WHERE username=?", (username,))
        user = cur.fetchone()
        conn.close()

        if user and check_password_hash(user[0], password):
            session["user"] = username
            return redirect("/")
        else:
            return "Invalid credentials"

    return '''
    <style>
    body{background:#667eea;display:flex;justify-content:center;align-items:center;height:100vh;font-family:sans-serif}
    .box{background:white;padding:30px;border-radius:15px;width:300px}
    input,button{width:100%;padding:10px;margin:10px 0}
    </style>
    <div class="box">
    <h2>Login</h2>
    <form method="post">
    <input name="username" placeholder="Username" required>
    <input type="password" name="password" placeholder="Password" required>
    <button>Login</button>
    </form>
    <a href="/signup">Signup</a>
    </div>
    '''

# ---------------- SIGNUP ----------------
@app.route("/signup", methods=["GET","POST"])
def signup():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        hashed = generate_password_hash(password)

        try:
            conn = sqlite3.connect("users.db")
            cur = conn.cursor()
            cur.execute("INSERT INTO users (username,password) VALUES (?,?)",(username,hashed))
            conn.commit()
            conn.close()
            return redirect("/login")
        except:
            return "User already exists"

    return '''
    <style>
    body{background:#43cea2;display:flex;justify-content:center;align-items:center;height:100vh;font-family:sans-serif}
    .box{background:white;padding:30px;border-radius:15px;width:300px}
    input,button{width:100%;padding:10px;margin:10px 0}
    </style>
    <div class="box">
    <h2>Signup</h2>
    <form method="post">
    <input name="username" placeholder="Username" required>
    <input type="password" name="password" placeholder="Password" required>
    <button>Signup</button>
    </form>
    <a href="/login">Login</a>
    </div>
    '''

# ---------------- HOME ----------------
@app.route("/")
def home():
    if "user" not in session:
        return redirect("/login")

    return render_template_string("""
    <h3>Welcome {{session['user']}}</h3>
    <a href="/logout">Logout</a> | <a href="/history">History</a>
    <hr>

    <h2>Mental Health Test</h2>
    <form id="form">
    {% for q in questions %}
        <p>{{q.label}}</p>
        {% for i in range(1,6) %}
            <input type="radio" name="{{q.id}}" value="{{i}}" required> {{i}}
        {% endfor %}
    {% endfor %}
    <br><br>
    <button type="button" onclick="submitForm()">Submit</button>
    </form>

    <div id="result"></div>

    <script>
    function submitForm(){
        let data = {};
        document.querySelectorAll("input:checked").forEach(el=>{
            data[el.name] = parseInt(el.value);
        });

        fetch('/assess',{
            method:'POST',
            headers:{'Content-Type':'application/json'},
            body:JSON.stringify(data)
        })
        .then(res=>res.json())
        .then(d=>{
            document.getElementById('result').innerHTML =
                "<h3 style='color:"+d.color+"'>"+d.status+"</h3>";
        });
    }
    </script>
    """, questions=questions)

# ---------------- ASSESS ----------------
@app.route("/assess", methods=["POST"])
def assess():
    data = request.get_json()
    score = 0

    positive = ["sleep","exercise","motivation","energy"]

    for k,v in data.items():
        if k in positive:
            score += (6 - v)
        else:
            score += v

    max_score = len(data) * 5

    if score <= max_score * 0.25:
        status, color = "Stable 🟢","#0a0"
    elif score <= max_score * 0.5:
        status, color = "Mild 🟡","#e6b800"
    elif score <= max_score * 0.75:
        status, color = "Moderate 🟠","#ff8800"
    else:
        status, color = "High 🔴","#f00"

    conn = sqlite3.connect("users.db")
    cur = conn.cursor()
    cur.execute("INSERT INTO results (username,score,status) VALUES (?,?,?)",
                (session["user"],score,status))
    conn.commit()
    conn.close()

    return jsonify({"status":status,"color":color})

# ---------------- HISTORY ----------------
@app.route("/history")
def history():
    if "user" not in session:
        return redirect("/login")

    conn = sqlite3.connect("users.db")
    cur = conn.cursor()
    cur.execute("SELECT score,status FROM results WHERE username=?",(session["user"],))
    rows = cur.fetchall()
    conn.close()

    html = "<h2>Your History</h2><a href='/'>Back</a><hr>"
    for r in rows:
        html += f"<p>Score: {r[0]} | Status: {r[1]}</p>"

    return html

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
