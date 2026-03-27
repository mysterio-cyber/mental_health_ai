from flask import Flask, request, jsonify, render_template_string
import os

app = Flask(__name__)

# HTML page
html_page = """
<!DOCTYPE html>
<html>
<head>
<title>AI Mental Health Risk Assessment</title>
<style>
body{
font-family: Arial;
background: linear-gradient(135deg,#667eea,#764ba2);
height:100vh;
display:flex;
justify-content:center;
align-items:center;
margin:0;
}
.container{
background:white;
padding:30px;
border-radius:15px;
width:400px;
text-align:center;
box-shadow:0 10px 25px rgba(0,0,0,0.2);
}
input{
width:100%;
padding:10px;
margin:10px 0;
border-radius:8px;
border:1px solid #ccc;
}
button{
width:100%;
padding:12px;
background:#667eea;
color:white;
border:none;
border-radius:10px;
font-size:16px;
cursor:pointer;
}
.result{
margin-top:20px;
font-size:20px;
font-weight:bold;
}
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
    let stress = document.getElementById("stress").value || 0;
    let sleep = document.getElementById("sleep").value || 0;
    let screen = document.getElementById("screen").value || 0;
    let exercise = document.getElementById("exercise").value || 0;
    let mood = document.getElementById("mood").value || 0;

    // Remove any non-numeric characters
    stress = parseFloat(stress.replace(/[^0-9.]/g,'')) || 0;
    sleep = parseFloat(sleep.replace(/[^0-9.]/g,'')) || 0;
    screen = parseFloat(screen.replace(/[^0-9.]/g,'')) || 0;
    exercise = parseFloat(exercise.replace(/[^0-9.]/g,'')) || 0;
    mood = parseFloat(mood.replace(/[^0-9.]/g,'')) || 0;

    let response = await fetch("/predict",{
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({stress, sleep, screen, exercise, mood})
    });

    let data = await response.json();
    document.getElementById("result").innerHTML = "Risk Level: " + data.risk;
}
</script>

</body>
</html>
"""

@app.route("/")
def home():
    return render_template_string(html_page)

@app.route("/predict", methods=["POST"])
def predict():
    data = request.get_json()
    try:
        stress = float(str(data.get("stress",0)))
        sleep = float(str(data.get("sleep",0)))
        screen = float(str(data.get("screen",0)))
        exercise = float(str(data.get("exercise",0)))
        mood = float(str(data.get("mood",0)))
    except ValueError:
        return jsonify({"risk":"Invalid input, please enter numbers only"}), 400

    score = (stress*2) + (screen*1.5) - (sleep*2) - (exercise*1.2) - (mood*2)

    if score < 10:
        risk="Low Risk 🟢"
    elif score < 25:
        risk="Moderate Risk 🟡"
    else:
        risk="High Risk 🔴"

    return jsonify({"risk":risk})

# ✅ Correct port for Render deployment
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)