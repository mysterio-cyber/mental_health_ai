from flask import Flask, request, render_template_string, jsonify
import os

app = Flask(__name__)

# HTML template with calming colors and card-style sliders
html_page = """
<!DOCTYPE html>
<html>
<head>
<title>🧘‍♀️ Peaceful Mental Health Assessment</title>
<style>
body {
    font-family: 'Arial', sans-serif;
    background: linear-gradient(135deg, #a1c4fd, #c2e9fb);
    display: flex;
    justify-content: center;
    align-items: center;
    min-height: 100vh;
    margin: 0;
}

.container {
    background: white;
    padding: 40px;
    border-radius: 25px;
    width: 650px;
    box-shadow: 0 15px 35px rgba(0,0,0,0.15);
    overflow-y: auto;
    max-height: 90vh;
}

h2 {
    text-align: center;
    color: #333;
    margin-bottom: 25px;
}

.card {
    background: #f9f9f9;
    padding: 20px;
    margin-bottom: 15px;
    border-radius: 15px;
    transition: 0.3s;
    box-shadow: 0 5px 15px rgba(0,0,0,0.05);
}

.card:hover {
    transform: translateY(-3px);
    box-shadow: 0 10px 25px rgba(0,0,0,0.1);
}

label {
    display: block;
    font-weight: bold;
    margin-bottom: 8px;
    color: #555;
}

input[type=range] {
    width: 100%;
    margin-bottom: 5px;
    accent-color: #6dd5ed;
}

button {
    width: 100%;
    padding: 15px;
    background: linear-gradient(to right, #2193b0, #6dd5ed);
    color: white;
    border: none;
    border-radius: 12px;
    font-size: 16px;
    cursor: pointer;
    transition: 0.3s;
}

button:hover {
    opacity: 0.9;
}

.result {
    margin-top: 25px;
    font-size: 22px;
    font-weight: bold;
    text-align: center;
    color: #333;
}

/* Progress bar */
.progress-container {
    width: 100%;
    background: #eee;
    border-radius: 10px;
    margin-bottom: 20px;
}

.progress-bar {
    height: 10px;
    background: linear-gradient(to right, #2193b0, #6dd5ed);
    width: 0%;
    border-radius: 10px;
    transition: width 0.3s ease;
}
</style>
</head>
<body>

<div class="container">
<h2>🧘‍♂️ Peaceful Mental Health Assessment</h2>

<div class="progress-container">
    <div class="progress-bar" id="progress-bar"></div>
</div>

<form id="questionnaire">
    {% for q in questions %}
    <div class="card question">
        <label for="{{ q.id }}">{{ loop.index }}. {{ q.label }}</label>
        <input type="range" id="{{ q.id }}" min="0" max="3" value="0" step="1" oninput="updateProgress()">
        <div style="display:flex; justify-content: space-between; font-size:12px;">
            {% for option in q.options %}
            <span>{{ option }}</span>
            {% endfor %}
        </div>
    </div>
    {% endfor %}
    <button type="button" onclick="submitForm()">Submit</button>
</form>

<div class="result" id="result"></div>
</div>

<script>
function updateProgress() {
    let total = {{ questions|length }};
    let answered = 0;
    {% for q in questions %}
    if(document.getElementById("{{ q.id }}").value != "0") answered++;
    {% endfor %}
    let percent = (answered / total) * 100;
    document.getElementById("progress-bar").style.width = percent + "%";
}

function submitForm() {
    let answers = {};
    {% for q in questions %}
    answers["{{ q.id }}"] = parseInt(document.getElementById("{{ q.id }}").value) || 0;
    {% endfor %}

    fetch("/assess", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(answers)
    })
    .then(res => res.json())
    .then(data => {
        document.getElementById("result").innerHTML = "Mental Health Status: " + data.status;
    })
    .catch(err => console.error(err));
}
</script>

</body>
</html>
"""

# Questions
questions = [
    {"id":"stress","label":"How often do you feel stressed?","options":["Never","Sometimes","Often","Always"]},
    {"id":"sleep","label":"How is your sleep quality?","options":["Very Good","Good","Poor","Very Poor"]},
    {"id":"exercise","label":"How much do you exercise per week?","options":[">150 min","60-150 min","1-59 min","0 min"]},
    {"id":"mood","label":"How often do you feel sad or down?","options":["Never","Sometimes","Often","Always"]},
    {"id":"anxiety","label":"How often do you feel anxious or nervous?","options":["Never","Sometimes","Often","Always"]},
    {"id":"focus","label":"How often do you have trouble concentrating?","options":["Never","Sometimes","Often","Always"]},
    {"id":"irritability","label":"How often do you feel irritable?","options":["Never","Sometimes","Often","Always"]},
    {"id":"social","label":"How often do you avoid social interactions?","options":["Never","Sometimes","Often","Always"]},
    {"id":"motivation","label":"How motivated are you to do daily tasks?","options":["High","Moderate","Low","Very Low"]},
    {"id":"appetite","label":"How is your appetite?","options":["Good","Normal","Poor","Very Poor"]},
    {"id":"energy","label":"How is your energy level?","options":["High","Moderate","Low","Very Low"]},
    {"id":"sleep_duration","label":"How many hours do you sleep on average?","options":["8+","6-7","4-5","<4"]}
]

@app.route("/")
def home():
    return render_template_string(html_page, questions=questions)

@app.route("/assess", methods=["POST"])
def assess():
    data = request.get_json()
    score = 0

    for key, value in data.items():
        try:
            value = int(value)
        except:
            value = 0

        if key in ["sleep","exercise","motivation","appetite","energy","sleep_duration"]:
            score += 3 - value
        else:
            score += value

    if score <= 10:
        status = "Stable 🟢"
    elif score <= 20:
        status = "Mild Risk 🟡"
    elif score <= 30:
        status = "Moderate Risk 🟠"
    else:
        status = "High Risk 🔴"

    return jsonify({"status": status})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
