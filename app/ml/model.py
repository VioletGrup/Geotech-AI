import numpy as np
from sklearn.ensemble import RandomForestRegressor

# dummy data
x = np.array([
    [10, 20, 1.0],
    [15, 15, 1.2],
    [8, 18, 0.8]
])

y = np.array([1200, 1600, 900])

model = RandomForestRegressor()
model.fit(x, y)

def predict_capacity(qc, depth, diameter):
    return float(model.predict([[qc, depth, diameter]])[0])