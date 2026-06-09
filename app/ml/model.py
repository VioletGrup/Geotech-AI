import numpy as np
from sklearn.ensemble import RandomForestRegressor

from app.ml.features import build_feature_record
from app.utils.logger import get_logger
from app.graphrag.retrieve import get_training_rows

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