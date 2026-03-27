from flask import Flask, request, jsonify, render_template_string
import joblib
import sqlite3
import re

app = Flask(__name__)

# Load trained AI model
model = joblib.load("model.pkl")

# HTML frontend
html_page = """
<!DOCTYPE html>
<html>
<head>
<title>AI Mental Health Risk Assessment</title>
<style>
body{
    font-family: Arial, sans-serif;
    background: linear-gradient(135deg,#667eea,#764ba2);
    display:flex; justify-content:center; align-items:center;
    height:100vh; margin:0;
}
.container{
    background:white;
    padding:30px;
    border-radius:15px;
    width:400px;
    text-align:center;
    box-shadow:0 10px 25px rgba(0,0,0,0.2);
}
input{width:100%; padding:10px; margin:10px 0; border-radius:8px; border:1px solid #ccc;}
button{width:100%; padding:12px; background:#667eea; color:white; border:none; border-radius:10px; font-size:16px; cursor:pointer;}
.result{margin-top:20px; font-size:20px; font-weight:bold;}
</style>
</head>
<body>
<div class="container">
<h2>🧠 AI Mental Health Risk Assessment</h2>
<input type="text" id="stress" placeholder="Stress Level (1-10)">
<input type="text" id="sleep" placeholder="Sleep Hours">
<input type="text" id="screen" placeholder="Screen Time (hours)">
<input type="text" id="exercise" placeholder="Exercise (minutes)">
<input type="text" id="mood" placeholder="Mood Rating (1-10)">
<button onclick="analyze()">Analyze Mental Health</button>
<div class="result" id="result"></div>
</div>
<script>
async function analyze(){
    let stress = document.getElementById("stress").value;
    let sleep = document.getElementById("sleep").value;
    let screen = document.getElementById("screen").value;
    let exercise = document.getElementById("exercise").value;
    let mood = document.getElementById("mood").value;

    let response = await fetch("/predict",{
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({stress,sleep,screen,exercise,mood})
    });

    let data = await response.json();
    document.getElementById("result").innerHTML = "Risk Level: " + data.risk;
}
</script>
</body>
</html>
"""

# Helper function to extract numbers
def clean_number(value):
    if not value:
        return 0
    numbers = re.findall(r"\d+\.?\d*", str(value))
    return float(numbers[0]) if numbers else 0

# Save input + prediction to SQLite
def save_to_db(data, prediction):
    conn = sqlite3.connect("data.db")
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS records
                 (stress, sleep, screen, exercise, mood, risk)""")
    c.execute("INSERT INTO records VALUES (?,?,?,?,?,?)", (*data, prediction))
    conn.commit()
    conn.close()

@app.route("/")
def home():
    return render_template_string(html_page)

@app.route("/predict", methods=["POST"])
def predict():
    data = request.get_json()
    values = [
        clean_number(data.get("stress",0)),
        clean_number(data.get("sleep",0)),
        clean_number(data.get("screen",0)),
        clean_number(data.get("exercise",0)),
        clean_number(data.get("mood",0))
    ]

    pred = model.predict([values])[0]
    risk_map = {0:"Low Risk 🟢",1:"Moderate Risk 🟡",2:"High Risk 🔴"}

    save_to_db(values, pred)
    return jsonify({"risk": risk_map[pred]})

import os

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # Use Render's port or default 5000
    app.run(host="0.0.0.0", port=port, debug=True)