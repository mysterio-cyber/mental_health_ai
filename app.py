from flask import Flask, request, jsonify, render_template_string
import os

app = Flask(__name__)

html_page = """
<!DOCTYPE html>
<html>
<head>
<title>Mental Health Assessment</title>
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
    width:600px;
    text-align:left;
    box-shadow:0 10px 25px rgba(0,0,0,0.2);
}
label{
    font-weight:bold;
}
input, select{
    width:100%;
    padding:10px;
    margin:8px 0 16px 0;
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
    text-align:center;
}
</style>
</head>
<body>
<div class="container">
<h2>🧠 Mental Health Questionnaire</h2>
<form id="questionnaire">
{% for q in questions %}
<label>{{ q.label }}</label>
<select id="{{ q.id }}">
    {% for i, option in enumerate(q.options) %}
    <option value="{{ i }}">{{ option }}</option>
    {% endfor %}
</select>
{% endfor %}
<button type="button" onclick="submitForm()">Submit</button>
</form>
<div class="result" id="result"></div>
</div>

<script>
async function submitForm(){
    let answers = {};
    {% for q in questions %}
    answers["{{ q.id }}"] = parseInt(document.getElementById("{{ q.id }}").value) || 0;
    {% endfor %}
    let response = await fetch("/assess", {
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body: JSON.stringify(answers)
    });
    let data = await response.json();
    document.getElementById("result").innerHTML = "Mental Health Status: " + data.status;
}
</script>
</body>
</html>
"""

# Define questions
questions = [
    {"id":"stress","label":"1. How often do you feel stressed?","options":["Never","Sometimes","Often","Always"]},
    {"id":"sleep","label":"2. How many hours do you sleep per night?","options":["<4","4-5","6-7","8+"]},
    {"id":"exercise","label":"3. How many minutes of exercise do you get per week?","options":["0","1-59","60-149","150+"]},
    {"id":"mood","label":"4. How often do you feel sad or down?","options":["Never","Sometimes","Often","Always"]},
    {"id":"anxiety","label":"5. How often do you feel anxious or nervous?","options":["Never","Sometimes","Often","Always"]},
    {"id":"focus","label":"6. How often do you have trouble concentrating?","options":["Never","Sometimes","Often","Always"]},
    {"id":"irritability","label":"7. How often do you feel irritable?","options":["Never","Sometimes","Often","Always"]},
    {"id":"social","label":"8. How often do you avoid social interactions?","options":["Never","Sometimes","Often","Always"]},
    {"id":"motivation","label":"9. How motivated are you to do daily tasks?","options":["Very Low","Low","Moderate","High"]},
    {"id":"appetite","label":"10. How is your appetite?","options":["Very Poor","Poor","Normal","Good"]},
    {"id":"energy","label":"11. How is your energy level?","options":["Very Low","Low","Moderate","High"]},
    {"id":"sleep_quality","label":"12. How would you rate your sleep quality?","options":["Very Poor","Poor","Good","Very Good"]}
]

@app.route("/")
def home():
    return render_template_string(html_page, questions=questions)

@app.route("/assess", methods=["POST"])
def assess():
    data = request.get_json()
    score = 0

    # Map answers to numeric score
    for key, value in data.items():
        try:
            value = int(value)
        except:
            value = 0

        # Invert score for positive questions
        if key in ["sleep","exercise","motivation","appetite","energy","sleep_quality"]:
            score += 3 - value  # Higher value = better, reduce risk
        else:
            score += value      # Higher value = worse

    # Calculate risk
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
    port = int(os.environ.get("PORT",5000))
    app.run(host="0.0.0.0", port=port, debug=True)
