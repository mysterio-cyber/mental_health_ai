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
    {"id":"stress","label":"How often do you feel stressed?"},
    {"id":"sleep","label":"How is your sleep quality?"},
    {"id":"exercise","label":"How often do you exercise?"},
    {"id":"mood","label":"How often do you feel sad?"},
    {"id":"anxiety","label":"How often do you feel anxious?"},
    {"id":"focus","label":"Do you have trouble concentrating?"},
    {"id":"social","label":"Do you avoid social interaction?"},
    {"id":"motivation","label":"How motivated are you?"},
    {"id":"energy","label":"How is your energy level?"}
]

BINAURAL = "https://youtu.be/lkkGlVWvkLk"

# ---------------- SIGNUP ----------------
@app.route("/signup", methods=["GET","POST"])
def signup():
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
            return "User exists"

    return """
    <style>
    body{background:linear-gradient(135deg,#a1c4fd,#c2e9fb);display:flex;justify-content:center;align-items:center;height:100vh;}
    .box{background:white;padding:30px;border-radius:20px;width:300px;text-align:center;}
    input,button{width:100%;padding:10px;margin:10px 0;}
    button{background:#2193b0;color:white;border:none;}
    </style>
    <div class="box">
    <h2>Signup 🌿</h2>
    <form method="post">
    <input name="username" required placeholder="Username">
    <input name="password" type="password" required placeholder="Password">
    <button>Signup</button>
    </form>
    <a href="/login">Login</a>
    </div>
    """

# ---------------- LOGIN ----------------
@app.route("/login", methods=["GET","POST"])
def login():
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
        return "Invalid login"

    return """
    <style>
    body{background:linear-gradient(135deg,#89f7fe,#66a6ff);display:flex;justify-content:center;align-items:center;height:100vh;}
    .box{background:white;padding:30px;border-radius:20px;width:300px;text-align:center;}
    input,button{width:100%;padding:10px;margin:10px 0;}
    button{background:#66a6ff;color:white;border:none;}
    </style>
    <div class="box">
    <h2>Login 🌿</h2>
    <form method="post">
    <input name="username" required>
    <input name="password" type="password" required>
    <button>Login</button>
    </form>
    <a href="/signup">Signup</a>
    </div>
    """

# ---------------- HOME ----------------
@app.route("/")
def home():
    if "user" not in session:
        return redirect("/login")

    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
body{background:#eef;font-family:sans-serif;text-align:center;padding:20px;}
.container{background:white;padding:20px;border-radius:15px;}
button{padding:10px;margin-top:10px;background:#2193b0;color:white;border:none;}
</style>
</head>
<body>

<h3>Welcome {{session['user']}}</h3>
<a href="/history">History</a> | <a href="/logout">Logout</a>

<div class="container">
<div id="q"></div>
<div id="opt"></div>
<button onclick="next()">Next</button>
<div id="res"></div>
</div>

<script>
const q={{questions|tojson}};
let i=0,ans={};

function load(){
let x=q[i];
document.getElementById("q").innerHTML="<h3>"+x.label+"</h3>";
let h="";
for(let j=1;j<=5;j++){
h+=`<input type="radio" name="a" value="${j}">${j}<br>`;
}
document.getElementById("opt").innerHTML=h;
}
load();

function next(){
let v=document.querySelector("input[name=a]:checked");
if(!v){alert("select");return;}
ans[q[i].id]=parseInt(v.value);

if(i<q.length-1){i++;load();}
else{
fetch("/assess",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(ans)})
.then(r=>r.json()).then(d=>{
document.getElementById("res").innerHTML=
`<h2 style="color:${d.color}">${d.status}</h2>
Score:${d.score}<br>${d.remedies.join("<br>")}
<br><a href="${d.link}" target="_blank">🎧 Relax</a>`;
});
}
}
</script>

</body>
</html>
""",questions=questions)

# ---------------- ASSESS ----------------
@app.route("/assess", methods=["POST"])
def assess():
    data=request.get_json()
    score=0
    positive=["sleep","exercise","motivation","energy"]

    for k,v in data.items():
        score+= (6-v if k in positive else v)

    max_score=len(data)*5

    if score<=max_score*0.25: status,color="Stable 🟢","#0a0"
    elif score<=max_score*0.5: status,color="Mild 🟡","#e6b800"
    elif score<=max_score*0.75: status,color="Moderate 🟠","#f80"
    else: status,color="High 🔴","#f00"

    conn=sqlite3.connect("app.db")
    cur=conn.cursor()
    cur.execute("INSERT INTO results (username,score,status) VALUES (?,?,?)",
                (session["user"],score,status))
    conn.commit()
    conn.close()

    remedies=["Maintain routine","Exercise","Sleep well"]

    return jsonify({"status":status,"color":color,"score":score,"remedies":remedies,"link":BINAURAL})

# ---------------- HISTORY ----------------
@app.route("/history")
def history():
    if "user" not in session:
        return redirect("/login")

    conn=sqlite3.connect("app.db")
    cur=conn.cursor()
    cur.execute("SELECT score FROM results WHERE username=?",(session["user"],))
    data=[r[0] for r in cur.fetchall()]
    conn.close()

    return f"""
    <h2>History</h2>
    <canvas id='c'></canvas>
    <script src='https://cdn.jsdelivr.net/npm/chart.js'></script>
    <script>
    new Chart(document.getElementById('c'),{{
    type:'line',
    data:{{labels:{list(range(len(data)))},datasets:[{{data:{data}}}]}}
    }});
    </script>
    <a href='/'>Back</a>
    """

# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

# ---------------- RUN ----------------
if __name__=="__main__":
    import os

port = int(os.environ.get("PORT", 5000))
app.run(host="0.0.0.0", port=port)
