from flask import Flask, request, render_template_string, jsonify
import os

app = Flask(__name__)

BINAURAL_BEAT_LINK = "https://youtu.be/lkkGlVWvkLk?si=bl55Oy6iUc2wnoEK"

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

html_page = """
<!DOCTYPE html>
<html>
<head>
<title>🧘 AI Mental Health Assessment</title>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<link href="https://fonts.googleapis.com/css2?family=Roboto:wght@400;500;700&display=swap" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
body {margin:0; font-family:'Roboto',sans-serif; background:linear-gradient(135deg,#a1c4fd,#c2e9fb); display:flex; justify-content:center; align-items:center; min-height:100vh;}
.container {background:white; padding:25px; border-radius:25px; width:90%; max-width:700px; box-shadow:0 15px 35px rgba(0,0,0,0.15); max-height:90vh; overflow-y:auto;}
h2 {text-align:center; color:#333; margin-bottom:15px;}
.card {background:#f9f9f9; padding:20px; margin-bottom:15px; border-radius:15px; box-shadow:0 5px 15px rgba(0,0,0,0.05); opacity:0; transform:translateY(20px); transition:all 0.5s ease;}
.card.show {opacity:1; transform:translateY(0);}
label {display:block; margin:10px 0; color:#555; cursor:pointer;}
label input {margin-right:10px;}
button {width:100%; padding:16px; background:linear-gradient(to right,#2193b0,#6dd5ed); color:white; border:none; border-radius:12px; font-size:16px; cursor:pointer; transition:0.3s; margin-top:10px;}
button:hover {opacity:0.9;}
#progressBarContainer {background:#eee; border-radius:12px; overflow:hidden; margin-bottom:15px;}
#progressBar {height:12px; width:0%; background:linear-gradient(to right,#2193b0,#6dd5ed); transition:width 0.5s;}
.dynamicTip {margin-top:10px; font-size:0.95em; color:#006400; opacity:0; transition:opacity 0.5s;}
.dynamicTip.show {opacity:1;}
.result {margin-top:20px; font-size:18px; font-weight:bold; text-align:center; opacity:0; transition:opacity 0.5s;}
.result.show {opacity:1;}
.remedies {margin-top:15px; padding:15px; background:#eef; border-radius:12px; color:#222; font-size:0.95em; opacity:0; transition:opacity 0.5s;}
.remedies.show {opacity:1;}
#youtubeIcon {text-align:center; margin-top:20px;}
#youtubeIcon a {text-decoration:none; font-size:20px; color:#c4302b;}
.chart-container {margin-top:25px; opacity:0; transition:opacity 0.8s;}
.chart-container.show {opacity:1;}
@media(max-width:480px){.container{padding:15px;} h2{font-size:1.3em;} button{font-size:15px;} label{font-size:0.9em;}}
</style>
</head>
<body>
<div class="container">
<h2>🧘 AI Mental Health Assessment</h2>
<div id="progressBarContainer"><div id="progressBar"></div></div>
<div id="questionContainer"></div>
<div class="dynamicTip" id="dynamicTip"></div>
<button id="nextBtn">Next</button>

<div class="result" id="result"></div>
<div class="remedies" id="remedies"></div>

<div class="chart-container">
<canvas id="dashboardChart"></canvas>
</div>

<div id="youtubeIcon">
    <a href="{{ binaural_beat }}" target="_blank">🎵 Listen to Binaural Beat</a>
</div>

<script>
const questions = {{ questions|tojson }};
let currentIndex=0;
let answers={};
const container = document.getElementById('questionContainer');
const nextBtn = document.getElementById('nextBtn');
const progressBar = document.getElementById('progressBar');
const dynamicTip = document.getElementById('dynamicTip');

function showQuestion(index){
    container.innerHTML='';
    dynamicTip.classList.remove('show');
    const q = questions[index];
    const card = document.createElement('div');
    card.className='card';
    const qTitle = document.createElement('p');
    qTitle.innerHTML=`<strong>${index+1}. ${q.label}</strong>`;
    card.appendChild(qTitle);
    q.options.forEach((opt,i)=>{
        const label = document.createElement('label');
        label.innerHTML=`<input type="radio" name="${q.id}" value="${i}"> ${opt}`;
        card.appendChild(label);
    });
    container.appendChild(card);
    setTimeout(()=>{card.classList.add('show');},50);
    nextBtn.innerText = (index===questions.length-1)? "Submit":"Next";
    progressBar.style.width = `${(index/questions.length)*100}%`;
}

function getTip(questionId, value){
    const tips = {
        "stress":["You're calm!","Take short breaks.","Consider relaxation techniques.","High stress detected."],
        "sleep":["Excellent!","Maintain routine.","Sleep quality could improve.","Sleep improvement needed."],
        "exercise":["Great!","Keep regular activity.","Increase exercise.","Low activity alert."],
        "mood":["Feeling good!","Some low moods normal.","Talk to someone if needed.","Persistent sadness alert."],
        "anxiety":["No anxiety detected.","Mild anxious feelings.","Try calming exercises.","High anxiety alert."],
        "focus":["Excellent focus.","Occasional distractions ok.","Consider focus techniques.","Frequent concentration issues."],
        "irritability":["Calm and patient.","Slight irritability normal.","Try relaxation.","High irritability alert."],
        "social":["Socially active.","Occasionally avoid social events.","Consider socializing more.","Avoiding interactions frequently."],
        "motivation":["Highly motivated!","Moderate motivation ok.","Low motivation detected.","Very low motivation alert."],
        "appetite":["Good appetite.","Normal variations.","Poor appetite detected.","Very low appetite alert."],
        "energy":["High energy!","Moderate energy.","Low energy detected.","Very low energy alert."],
        "sleep_duration":["Optimal sleep.","Slightly less sleep.","Low sleep hours.","Very low sleep hours alert."]
    };
    return tips[questionId][value] || "";
}

showQuestion(currentIndex);

nextBtn.addEventListener('click', ()=>{
    const selected = document.querySelector(`input[name="${questions[currentIndex].id}"]:checked`);
    if(selected){ answers[questions[currentIndex].id]=parseInt(selected.value); }
    else { answers[questions[currentIndex].id]=0; }
    
    dynamicTip.innerHTML = getTip(questions[currentIndex].id, answers[questions[currentIndex].id]);
    dynamicTip.classList.add('show');

    if(currentIndex<questions.length-1){
        currentIndex++;
        setTimeout(()=>showQuestion(currentIndex),300);
    } else {
        fetch('/assess',{
            method:'POST',
            headers:{'Content-Type':'application/json'},
            body:JSON.stringify(answers)
        })
        .then(res=>res.json())
        .then(data=>{
            container.style.display='none';
            nextBtn.style.display='none';
            dynamicTip.style.display='none';
            progressBar.style.width='100%';

            const resultEl = document.getElementById('result');
            resultEl.innerHTML=`<span style="color:${data.color}">Mental Health Status: ${data.status}</span>`;
            resultEl.classList.add('show');

            const remediesEl = document.getElementById('remedies');
            remediesEl.innerHTML="<strong>Personalized AI Recommendations:</strong><br>"+data.remedies.join("<br>");
            remediesEl.classList.add('show');

            const chartContainer = document.querySelector('.chart-container');
            chartContainer.classList.add('show');
            const ctx = document.getElementById('dashboardChart').getContext('2d');
            new Chart(ctx,{
                type:'radar',
                data:{
                    labels:['Stress','Sleep','Exercise','Mood','Anxiety','Focus','Irritability','Social','Motivation','Appetite','Energy','Sleep Duration'],
                    datasets:[{
                        label:'Your Assessment',
                        data:Object.values(answers).map(v=>v*25),
                        backgroundColor:'rgba(33,147,176,0.3)',
                        borderColor:'#2193b0',
                        pointBackgroundColor:'#2193b0',
                        pointBorderColor:'#fff',
                        pointHoverBackgroundColor:'#fff',
                        pointHoverBorderColor:'#2193b0'
                    }]
                },
                options:{
                    scales:{r:{beginAtZero:true,max:100,ticks:{stepSize:20}}},
                    plugins:{legend:{display:false}}
                }
            });
        })
        .catch(err=>{console.error(err); document.getElementById('result').innerHTML="Error occurred. Please try again.";});
    }
});
</script>
</div>
</body>
</html>
"""

@app.route("/")
def home():
    return render_template_string(html_page, questions=questions, binaural_beat=BINAURAL_BEAT_LINK)

@app.route("/assess", methods=["POST"])
def assess():
    data = request.get_json()
    score = 0
    for key,value in data.items():
        try: value=int(value)
        except: value=0
        if key in ["sleep","exercise","motivation","appetite","energy","sleep_duration"]:
            score += 3-value
        else:
            score += value

    if score<=10: status,color="Stable 🟢","#008000"
    elif score<=20: status,color="Mild Risk 🟡","#FFA500"
    elif score<=30: status,color="Moderate Risk 🟠","#FF8C00"
    else: status,color="High Risk 🔴","#FF0000"

    remedies=[]
    if data.get("stress",0)>=2: remedies.append("High stress detected: Try meditation or deep breathing exercises.")
    if data.get("sleep",0)>=2 or data.get("sleep_duration",0)>=2: remedies.append("Sleep issues detected: Maintain consistent sleep schedule and avoid screens before bedtime.")
    if data.get("exercise",0)>=2: remedies.append("Increase physical activity: Aim for regular exercise weekly.")
    if data.get("mood",0)>=2 or data.get("anxiety",0)>=2: remedies.append("Mood/anxiety alert: Talk to friends, family or a mental health professional if persistent.")
    if data.get("motivation",0)>=2 or data.get("energy",0)>=2: remedies.append("Low energy/motivation: Consider light exercise, healthy diet, and small achievable goals.")
    if data.get("social",0)>=2: remedies.append("Social withdrawal detected: Try social interactions or community engagement.")
    if not remedies: remedies.append("You seem to be doing well! Keep maintaining healthy habits and mindfulness.")

    return jsonify({"status":status,"color":color,"remedies":remedies})

if __name__=="__main__":
    port=int(os.environ.get("PORT",5000))
    app.run(host="0.0.0.0",port=port,debug=True)
