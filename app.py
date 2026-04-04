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
<title>Sign Up</title>
</head>
<body>
<h2>Signup</h2>
<form method="post">
<input name="username" required placeholder="Username"><br>
<input name="password" type="password" required placeholder="Password"><br>
<button type="submit">Signup</button>
</form>
{{error}}
</body>
</html>
""", error=error)

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
        error = "Invalid login"

    return render_template_string("""
<!DOCTYPE html>
<html>
<body>
<h2>Login</h2>
<form method="post">
<input name="username">
<input name="password" type="password">
<button>Login</button>
</form>
{{error}}
</body>
</html>
""", error=error)

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
<title>MindSpace</title>

<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js"></script>

</head>
<body>

<h2>MindSpace Check</h2>

<div id="question"></div>
<div id="options"></div>

<button onclick="next()">Next</button>

<div id="result" style="display:none;">
    <h3 id="status"></h3>
    <p id="score"></p>

    <canvas id="radarChart"></canvas>

    <button onclick="downloadPDF()">Download PDF</button>
</div>

<script>

const q = {{ questions|tojson }};
let i=0, ans={};

function load(){
    document.getElementById("question").innerText=q[i].label;

    let html="";
    for(let j=1;j<=5;j++){
        html+=`<input type="radio" name="a" value="${j}">${j}<br>`;
    }
    document.getElementById("options").innerHTML=html;
}
load();

function next(){
    let v=document.querySelector("input[name=a]:checked");
    if(!v) return alert("Select");

    ans[q[i].id]=parseInt(v.value);

    if(i<q.length-1){
        i++; load();
    }else{
        fetch("/assess",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(ans)})
        .then(r=>r.json())
        .then(d=>{
            document.getElementById("result").style.display="block";

            document.getElementById("status").innerText=d.status;
            document.getElementById("score").innerText=d.score;

            const ctx=document.getElementById('radarChart').getContext('2d');

            new Chart(ctx,{
                type:'radar',
                data:{
                    labels:Object.keys(ans),
                    datasets:[{data:Object.values(ans)}]
                }
            });
        });
    }
}

async function downloadPDF(){
    const { jsPDF } = window.jspdf;

    const element=document.getElementById("result");

    const canvas=await html2canvas(element,{scale:2});
    const img=canvas.toDataURL("image/png");

    const pdf=new jsPDF();
    pdf.addImage(img,"PNG",10,10,180,0);

    pdf.save("report.pdf");
}

</script>

</body>
</html>
""", questions=questions)

# ---------------- ASSESS ----------------
@app.route("/assess", methods=["POST"])
def assess():
    data = request.get_json()
    score = sum(data.values())

    status = "Good" if score<20 else "Bad"

    conn = sqlite3.connect("app.db")
    cur = conn.cursor()
    cur.execute("INSERT INTO results (username,score,status) VALUES (?,?,?)",
                (session["user"], score, status))
    conn.commit()
    conn.close()

    return jsonify({"status":status,"score":score})

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(debug=True)
