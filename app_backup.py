
import os
from datetime import datetime

import pandas as pd
from flask import Flask, jsonify, render_template, request

from predict import predict
from grid_controller import build_forecast

app = Flask(__name__)


def create_forecast(weather):
    """Generate 24 hourly demand predictions using QuickML."""

    start_time = pd.Timestamp.now().floor("h") + pd.Timedelta(hours=1)

    timestamps = pd.date_range(
        start=start_time,
        periods=24,
        freq="h",
    )

    input_df = pd.DataFrame({
        "timestamp": timestamps.strftime("%Y-%m-%d %H:%M:%S"),
        "ambient_temp_c": float(weather["ambient_temp_c"]),
        "humidity_pct": float(weather["humidity_pct"]),
        "solar_irradiance_wm2": float(weather["solar_irradiance_wm2"]),
    })

    predictions = predict(input_df)
    results = build_forecast(input_df, predictions)

    return results


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/forecast", methods=["POST"])
def forecast_api():
    try:
        weather = request.get_json(silent=True) or {}

        temperature = float(weather["ambient_temp_c"])
        humidity = float(weather["humidity_pct"])
        solar = float(weather["solar_irradiance_wm2"])

        if not -50 <= temperature <= 60:
            return jsonify({"error": "Temperature must be between -50 and 60 °C."}), 400

        if not 0 <= humidity <= 100:
            return jsonify({"error": "Humidity must be between 0 and 100%."}), 400

        if not 0 <= solar <= 1500:
            return jsonify({"error": "Solar irradiance must be between 0 and 1500 W/m²."}), 400

        results = create_forecast({
            "ambient_temp_c": temperature,
            "humidity_pct": humidity,
            "solar_irradiance_wm2": solar,
        })

        records = results.to_dict(orient="records")

        return jsonify({
            "forecast": records,
            "summary": {
                "total_hours": len(records),
                "renewable_storage_hours": int(
                    (results["grid_mode"] == "Renewable Storage Mode").sum()
                ),
                "main_grid_hours": int(
                    (results["grid_mode"] == "Main Grid Mode").sum()
                ),
                "critical_alerts": int(
                    results["critical_overload"].sum()
                ),
                "peak_demand_kw": round(
                    float(results["predicted_demand_kw"].max()), 2
                ),
            },
        })

    except (KeyError, TypeError, ValueError):
        return jsonify({
            "error": "Enter valid numeric values for all three weather fields."
        }), 400

    except Exception:
        app.logger.exception("Forecast generation failed")
        return jsonify({
            "error": "Forecast generation failed. Check the server terminal."
        }), 500


if __name__ == "__main__":
    app.run(debug=True, port=5000)
