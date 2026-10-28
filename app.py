from battery_simulator import simulate_battery
import pandas as pd
from flask import Flask, jsonify, render_template, request

from predict import predict
from grid_controller import build_forecast
from weather_service import get_hourly_weather

app = Flask(__name__)


def create_forecast(input_df):
    """Generate hourly demand predictions using hourly weather data."""

    predictions = predict(input_df)
    results = build_forecast(input_df, predictions)

    return results



def build_summary(results):
    """Calculate dashboard summary metrics."""

    demand = results["predicted_demand_kw"]

    summary = {
        "total_hours": len(results),
        "renewable_storage_hours": int(
            (results["grid_mode"] == "Renewable Storage Mode").sum()
        ),
        "main_grid_hours": int(
            (results["grid_mode"] == "Main Grid Mode").sum()
        ),
        "critical_alerts": int(
            results["critical_overload"].sum()
        ),
        "peak_demand_kw": round(float(demand.max()), 2),
        "average_demand_kw": round(float(demand.mean()), 2),
    }

    if not results.empty and "battery_soc_percent" in results.columns:
        summary["initial_battery_soc_percent"] = 80.0
        summary["final_battery_soc_percent"] = round(
            float(results["battery_soc_percent"].iloc[-1]), 2
        )
        summary["minimum_battery_soc_percent"] = round(
            float(results["battery_soc_percent"].min()), 2
        )

    return summary



def validate_weather(weather):
    """Validate manually supplied weather values."""

    temperature = float(weather["ambient_temp_c"])
    humidity = float(weather["humidity_pct"])
    solar = float(weather["solar_irradiance_wm2"])

    if not -50 <= temperature <= 60:
        raise ValueError("Temperature must be between -50 and 60 °C.")

    if not 0 <= humidity <= 100:
        raise ValueError("Humidity must be between 0 and 100%.")

    if not 0 <= solar <= 1500:
        raise ValueError("Solar irradiance must be between 0 and 1500 W/m².")

    return temperature, humidity, solar


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/weather", methods=["GET"])
def weather_api():
    """Return the next 24 hours of forecast weather."""

    try:
        weather_df = get_hourly_weather(hours=24)

        return jsonify({
            "source": "Open-Meteo",
            "location": {
                "latitude": 16.4631,
                "longitude": 80.5067,
                "timezone": "Asia/Kolkata",
            },
            "forecast": weather_df.to_dict(orient="records"),
        })

    except Exception:
        app.logger.exception("Weather retrieval failed")
        return jsonify({
            "error": (
                "Could not retrieve the hourly weather forecast. "
                "Check your internet connection and try again."
            )
        }), 502


@app.route("/api/forecast", methods=["POST"])
def forecast_api():
    """Generate demand predictions from live weather or manual scenarios."""

    try:
        payload = request.get_json(silent=True) or {}
        mode = payload.get("mode", "manual")

        if mode == "live":
            # Retrieve a different weather record for each forecast hour.
            input_df = get_hourly_weather(hours=24)

        elif mode == "manual":
            # Preserve compatibility with the existing frontend.
            temperature, humidity, solar = validate_weather(payload)

            start_time = (
                pd.Timestamp.now(tz="Asia/Kolkata").floor("h")
                + pd.Timedelta(hours=1)
            )

            timestamps = pd.date_range(
                start=start_time,
                periods=24,
                freq="h",
            )

            input_df = pd.DataFrame({
                "timestamp": timestamps.strftime("%Y-%m-%d %H:%M:%S"),
                "ambient_temp_c": temperature,
                "humidity_pct": humidity,
                "solar_irradiance_wm2": solar,
            })

        else:
            return jsonify({
                "error": "Mode must be either 'live' or 'manual'."
            }), 400

    
        results = create_forecast(input_df)

        

        results = simulate_battery(results)
        records = results.copy()



        # Convert timestamps to JSON-friendly strings if necessary.
        if "timestamp" in records.columns:
            records["timestamp"] = records["timestamp"].astype(str)

        # Convert missing values to JSON null rather than NaN.
        records = records.astype(object).where(pd.notna(records), None)

        return jsonify({
            "mode": mode,
            "weather_source": (
                "Open-Meteo hourly forecast" if mode == "live"
                else "Manual scenario"
            ),
            "forecast": records.to_dict(orient="records"),
            "summary": build_summary(results),
        })

    except (KeyError, TypeError, ValueError) as exc:
        return jsonify({
            "error": str(exc) or (
                "Enter valid numeric values for all three weather fields."
            )
        }), 400

    except Exception:
        app.logger.exception("Forecast generation failed")
        return jsonify({
            "error": (
                "Forecast generation failed. "
                "Check the server terminal for details."
            )
        }), 500


if __name__ == "__main__":
    app.run(debug=True, port=5000)
