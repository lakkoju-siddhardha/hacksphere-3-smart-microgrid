
import pandas as pd
import numpy as np

from pathlib import Path
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from sklearn.pipeline import make_pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import (
    RandomForestRegressor,
    ExtraTreesRegressor,
    HistGradientBoostingRegressor
)

BASE_DIR = Path(__file__).parent
DATA_PATH = BASE_DIR / "train_telemetry.csv"

# Load and sort data chronologically
df = pd.read_csv(DATA_PATH)
df["timestamp"] = pd.to_datetime(df["timestamp"], errors="raise")
df = df.sort_values("timestamp").reset_index(drop=True)

# Baseline features required by the problem statement
feature_cols = [
    "ambient_temp_c",
    "humidity_pct",
    "solar_irradiance_wm2",
]

X = df[feature_cols].copy()
y = df["target_demand_kw"].copy()

# Use the earliest 80% for training and latest 20% for validation
split = int(len(df) * 0.8)

X_train, X_val = X.iloc[:split], X.iloc[split:]
y_train, y_val = y.iloc[:split], y.iloc[split:]

models = {
    "Linear Regression": make_pipeline(
        SimpleImputer(strategy="median"),
        StandardScaler(),
        LinearRegression()
    ),

    "Random Forest": make_pipeline(
        SimpleImputer(strategy="median"),
        RandomForestRegressor(
            n_estimators=200,
            min_samples_leaf=2,
            random_state=42,
            n_jobs=-1
        )
    ),

    "Extra Trees": make_pipeline(
        SimpleImputer(strategy="median"),
        ExtraTreesRegressor(
            n_estimators=200,
            min_samples_leaf=2,
            random_state=42,
            n_jobs=-1
        )
    ),

    "HistGradientBoosting": make_pipeline(
        SimpleImputer(strategy="median"),
        HistGradientBoostingRegressor(
            max_iter=200,
            learning_rate=0.05,
            l2_regularization=1.0,
            random_state=42
        )
    ),
}

results = []

print("HACKSPHERE 3.0 - MODEL COMPARISON")
print(f"Training rows: {len(X_train)}")
print(f"Validation rows: {len(X_val)}")
print("\nTraining on earlier timestamps; validating on later timestamps.\n")

for name, model in models.items():
    model.fit(X_train, y_train)
    predictions = model.predict(X_val)

    rmse = np.sqrt(mean_squared_error(y_val, predictions))
    mae = mean_absolute_error(y_val, predictions)
    r2 = r2_score(y_val, predictions)

    results.append({
        "Model": name,
        "RMSE_kW": rmse,
        "MAE_kW": mae,
        "R2": r2
    })

results_df = pd.DataFrame(results).sort_values("RMSE_kW")

print(results_df.to_string(index=False, float_format=lambda x: f"{x:.4f}"))

print("\nExperiment complete.")
print("Lower RMSE is better. Compare these results before selecting a model.")

