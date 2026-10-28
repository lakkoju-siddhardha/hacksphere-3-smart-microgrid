
import requests
import pandas as pd


# Initial forecast location: SRM University-AP campus, Neerukonda.
# These are approximate campus coordinates.
LATITUDE = 16.4631
LONGITUDE = 80.5067

TIMEZONE = "Asia/Kolkata"

WEATHER_API_URL = "https://api.open-meteo.com/v1/forecast"


def get_hourly_weather(hours=24):
    """
    Fetch hourly weather forecasts and return the next requested
    number of hourly records in the format expected by QuickML.

    Returns columns:
        timestamp
        ambient_temp_c
        humidity_pct
        solar_irradiance_wm2
    """

    if not 1 <= hours <= 48:
        raise ValueError("hours must be between 1 and 48.")

    params = {
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "hourly": (
            "temperature_2m,"
            "relative_humidity_2m,"
            "shortwave_radiation"
        ),
        "timezone": TIMEZONE,
        "forecast_days": 2,
    }

    try:
        response = requests.get(
            WEATHER_API_URL,
            params=params,
            timeout=20,
        )
        response.raise_for_status()
        data = response.json()

    except requests.RequestException as exc:
        raise RuntimeError(
            "Could not retrieve hourly weather data. "
            "Check your internet connection and try again."
        ) from exc

    hourly = data.get("hourly")

    if not hourly:
        raise RuntimeError(
            "The weather API did not return hourly forecast data."
        )

    required_fields = [
        "time",
        "temperature_2m",
        "relative_humidity_2m",
        "shortwave_radiation",
    ]

    missing_fields = [
        field for field in required_fields
        if field not in hourly
    ]

    if missing_fields:
        raise RuntimeError(
            "Weather API response is missing: "
            + ", ".join(missing_fields)
        )

    weather = pd.DataFrame({
        "timestamp": pd.to_datetime(hourly["time"]),
        "ambient_temp_c": hourly["temperature_2m"],
        "humidity_pct": hourly["relative_humidity_2m"],
        "solar_irradiance_wm2": hourly["shortwave_radiation"],
    })

    # Interpret API timestamps in the requested local timezone.
    weather["timestamp"] = weather["timestamp"].dt.tz_localize(
        TIMEZONE
    )

    # Start at the next full hour in India.
    start_time = (
        pd.Timestamp.now(tz=TIMEZONE).floor("h")
        + pd.Timedelta(hours=1)
    )

    end_time = start_time + pd.Timedelta(hours=hours)

    weather = weather[
        (weather["timestamp"] >= start_time)
        & (weather["timestamp"] < end_time)
    ].copy()

    if len(weather) != hours:
        raise RuntimeError(
            f"Expected {hours} hourly weather records, "
            f"but received {len(weather)}. "
            "The API may not have returned the complete forecast window."
        )

    if weather[
        [
            "ambient_temp_c",
            "humidity_pct",
            "solar_irradiance_wm2",
        ]
    ].isna().any().any():
        raise RuntimeError(
            "The weather forecast contains missing values."
        )

    # Keep timestamps in the format expected by predict.py.
    weather["timestamp"] = weather["timestamp"].dt.strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    return weather.reset_index(drop=True)


if __name__ == "__main__":
    print("Fetching hourly weather forecast...")

    forecast = get_hourly_weather(hours=24)

    print("\nWeather forecast retrieved successfully!")
    print(f"Records received: {len(forecast)}")

    print("\nFirst 5 hourly records:")
    print(forecast.head().to_string(index=False))

    print("\nVariation across the forecast:")
    print(
        forecast[
            [
                "ambient_temp_c",
                "humidity_pct",
                "solar_irradiance_wm2",
            ]
        ].agg(["min", "max"]).to_string()
    )
