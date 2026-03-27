import pandas as pd
from sklearn.ensemble import RandomForestClassifier
import joblib

data = pd.DataFrame({
    "stress":[8,2,6,9,3,7,4,5],
    "sleep":[4,8,5,3,7,4,6,5],
    "screen":[10,3,7,12,4,8,5,6],
    "exercise":[10,40,20,5,30,15,25,20],
    "mood":[3,8,5,2,7,4,6,5],
    "risk":[2,0,1,2,0,1,0,1]
})

X = data.drop("risk", axis=1)
y = data["risk"]

model = RandomForestClassifier()
model.fit(X, y)

joblib.dump(model, "model.pkl")

print("Model trained!")