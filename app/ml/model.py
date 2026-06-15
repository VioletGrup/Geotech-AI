from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

from config import MIN_TRAINING_ROWS, MODEL_PATH, RANDOM_STATE
from features import build_feature_record
from logger import get_logger
from retrieve import get_training_rows

logger = get_logger(__name__)

NUMERIC_FEATURES = [
    "diameter",
    "length",
    "depth",
    "qc",
    "fs",
    "slenderness",
    "qc_x_diameter",
    "length_x_diameter",
]
CATEGORICAL_FEATURES = ["pile_type", "soil_type", "site_id"]
TARGET_COLUMN = "target"

class ModelNotTrainedError(RuntimeError):
    pass

def _build_pipeline() -> Pipeline:
    numeric_transformer = Pipeline(
        steps = [("imputer", SimpleImputer(strategy="median"))]
    )
    categorical_transformer = Pipeline(
        steps = [
            ("imputer",  SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(handle_unknown="ignore"))
        ]
    )
    preprocessor = ColumnTransformer(
        transformers = [
            ("num", numeric_transformer, NUMERIC_FEATURES),
            ("cat", categorical_transformer, CATEGORICAL_FEATURES)
            
        ]
    )
    model = RandomForestRegressor(
        n_estimators=250, 
        random_state=RANDOM_STATE,
        min_samples_leaf=1, 
        n_jobs=-1,
    )
    return Pipeline(steps=[("preprocessor", preprocessor), ("model", model)])

def _rows_to_dataframe(rows: List[Dict[str, Any]]) -> pd.DataFrame:
    records: List[Dict[str, Any]] = []
    for row in rows:
        feature_row = build_feature_record(row)
        feature_row[TARGET_COLUMN] = row.get(TARGET_COLUMN)
        feature_row["pile_id"] = row.get("pile_id")
        feature_row["test_id"] = row.get("test_id")
        records.append(feature_row)
    return pd.DataFrame.from_records(records)

def train_model_from_graph() -> Dict[str, Any]:
    rows = get_training_rows()
    df = _rows_to_dataframe(rows)
    if df.empty or len(df) < MIN_TRAINING_ROWS:
        raise ValueError(
            f"Not enough historical load tests to train model. Need at least {MIN_TRAINING_ROWS}, got {len(df)}."
        )

    feature_columns = NUMERIC_FEATURES + CATEGORICAL_FEATURES
    X = df[feature_columns]
    y = df[TARGET_COLUMN]

    if len(df) >= 20:
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=RANDOM_STATE
        )
    else:
        X_train, X_test, y_train, y_test = X, X, y, y
    
    pipeline = _build_pipeline()
    pipeline.fit(X_train, y_train)
    predictions = pipeline.predict(X_test)
    metrics = {
        "training_rows": int(len(df)),
        "mae": float(mean_absolute_error(y_test, predictions)),
        "r2": float(r2_score(y_test, predictions)) if len(df) >= 20 else None,
        "trained_at": datetime.now(datetime.timezone.utc).isoformat() + "Z",
        "features": feature_columns,
    }
    bundle = {
        "pipeline": pipeline,
        "metrics": metrics,
        "feature_columns": feature_columns,
    }
    Path(MODEL_PATH).parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(bundle, MODEL_PATH)
    logger.info("Model trained and saved", extra={"metrics": metrics})
    return metrics

def load_model_bundle() -> Dict[str, Any]:
    if not Path(MODEL_PATH).exists():
        raise ModelNotTrainedError(
            f"Model not found at {MODEL_PATH}. Train model first using /predict/train."
        )
    bundle = joblib.load(MODEL_PATH)
    return bundle

def predict_capacity(payload: Dict[str, Any]) -> Dict[str, Any]:
    bundle = load_model_bundle()
    pipeline: Pipeline = bundle["pipeline"]
    metrics = bundle.get("metrics", {})
    record = build_feature_record(payload)
    X = pd.DataFrame([record])
    estimate = float(pipeline.predict(X)[0])
    return {
        "predicted_capacity": estimate,
        "model_metrics": metrics,
        "model_status": "trained"
    }