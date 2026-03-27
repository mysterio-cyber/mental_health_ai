from flask import Flask, request, render_template_string, jsonify
import os

app = Flask(__name__)

# Your YouTube binaural beat link
BINAURAL_BEAT_LINK = "https://youtu.be/lkkGlVWvkLk?si=bl55Oy6iUc2wnoEK"

html_page = """
<!DOCTYPE html>
<html>
<head>
<title>🧘‍♀️ Mental Health Assessment</title>
<style>
body {
    font-family: 'Arial', sans-serif;
    background: linear-gradient(135deg,#a1c4fd,#c2e9fb);
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
    box-shadow: 0 5px 15px rgba(0,0,0,0.05);
}
label {
    display: block;
    margin: 10px 0;
    color: #555;
}
button {
    width: 100%;
    padding: 15px;
    background: linear-gradient(to right,#2193b0,#6dd5ed);
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
    font-size: 20px;
    font-weight: bold;
    text-align: center;
    color: #333;
}
.remedies {
    margin-top: 15px;
    padding: 15px;
    background: #eef;
    border-radius: 10px;
    color: #222;
}
iframe {
    margin-top: 20px;
    width: 100%;
    height: 200px;
    border: none;
    border-radius: 15px;
}
</style>
</head>
<body>

<div class="container">
<h2>🧘 AI Based Mental Health Risk Assessment System </h2>

<form id="questionnaire">
{% for q in questions %}
<div class="card">
    <p><strong>{{ loop.index }}. {{ q.label }}</strong></p>
    {% for opt in q.options %}
    <label>
        <input type="radio" name="{{ q.id }}" value="{{ loop.index0 }}"> {{ opt }}
    </label>
    {% endfor %}
</div>
{% endfor %}
<button type="button" id="submitBtn">Submit</button>
</form>

<div class="result" id="result"></div>
<div class="remedies" id="remedies"></div>

<iframe src="{{ binaural_beat }}" allow="autoplay; encrypted-media"></iframe>

<script>
document.getElementById("submitBtn").addEventListener("click", function() {
    let answers = {};
    {% for q in questions %}
    let selected = document.querySelector('input[name="{{ q.id }}"]:checked');
    answers["{{ q.id }}"] = selected ? parseInt(selected.value) : 0;
    {% endfor %}

    fetch("/assess", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(answers)
    })
    .then(response => response.json())
    .then(data => {
        document.getElementById("result").innerHTML = "Mental Health Status: " + data.status;
        document.getElementById("remedies").innerHTML = "<strong>Remedies / Tips:</strong><br>" + data.remedies.join("<br>");
    })
    .catch(err => {
        console.error("Error:", err);
        document.getElementById("result").innerHTML = "An error occurred. Please try again.";
    });
});
</script>

</div>
</body>
</html>
"""

questions = [
    {"id":"stress","label":"How often do you feel stressed?","options":["Never","Sometimes","Often","Always"]},
    {"id":"sleep","label":"How is your sleep quality?","options":["Very Good","Good","Poor","Very Poor"]},
    {"id":"exercise","label":"How often do you exercise per week?","options":[">150 min","60-150 min","1-59 min","0 min"]},
    {"id":"mood","label":"How often do you feel sad or down?","options":["Never","Sometimes","Often","Always"]},
    {"id":"anxiety","label":"How often do you feel anxious or nervous?","options":["Never","Sometimes","Often","Always"]},
    {"id":"focus","label":"Do you have trouble concentrating?","options":["Never","Sometimes","Often","Always"]},
    {"id":"irritability","label":"Do you feel irritable frequently?","options":["Never","Sometimes","Often","Always"]},
    {"id":"social","label":"Do you avoid social interactions?","options":["Never","Sometimes","Often","Always"]},
    {"id":"motivation","label":"How motivated are you for daily tasks?","options":["High","Moderate","Low","Very Low"]},
    {"id":"appetite","label":"How is your appetite?","options":["Good","Normal","Poor","Very Poor"]},
    {"id":"energy","label":"How is your energy level?","options":["High","Moderate","Low","Very Low"]},
    {"id":"sleep_duration","label":"How many hours do you sleep on average?","options":["8+","6-7","4-5","<4"]}
]

@app.route("/")
def home():
    return render_template_string(html_page, questions=questions, binaural_beat=BINAURAL_BEAT_LINK)

@app.route("/assess", methods=["POST"])
def assess():
    data = request.get_json()
    score = 0
    for key, value in data.items():
        try:
            value = int(value)
        except:
            value = 0
        # invert score for healthy behaviors
        if key in ["sleep","exercise","motivation","appetite","energy","sleep_duration"]:
            score += 3 - value
        else:
            score += value

    # Determine risk and remedies
    if score <= 10:
        status = "Stable 🟢"
        remedies = ["Keep up the healthy routine!", "Maintain regular sleep and exercise.", "Practice mindfulness or meditation daily."]
    elif score <= 20:
        status = "Mild Risk 🟡"
        remedies = ["Reduce stress with short breaks.", "Engage in light exercise.", "Talk to friends or loved ones regularly.", "Consider journaling."]
    elif score <= 30:
        status = "Moderate Risk 🟠"
        remedies = ["Incorporate relaxation techniques like yoga.", "Maintain a consistent sleep schedule.", "Limit caffeine and screen time before bed.", "Consider speaking to a counselor."]
    else:
        status = "High Risk 🔴"
        remedies = ["Seek professional mental health support.", "Practice daily self-care routines.", "Avoid social isolation.", "Consider therapy or counseling sessions immediately."]

    return jsonify({"status": status, "remedies": remedies})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
