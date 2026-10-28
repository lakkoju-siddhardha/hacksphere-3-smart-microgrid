# ⚡ GridSense AI — Smart Energy Microgrid

An intelligent energy demand forecasting and microgrid management application developed for **HackSphere 3.0**. GridSense AI combines machine-learning-based electricity demand predictions, weather data, and rule-based grid transition recommendations in an interactive dashboard.

## 🌐 Live Application

**Live Demo:** [GridSense AI — Open Dashboard](https://gridsense-ai-50047133789.development.catalystappsail.in/)

**GitHub Repository:** [GridSense AI on GitHub](https://github.com/lakkoju-siddhardha/hacksphere-3-smart-microgrid)

> **Note:** The application is deployed in the Zoho Catalyst Development environment. Forecasts are model predictions, not live electricity meter readings. Battery operation is simulated and does not control physical equipment.

## 🎯 Problem Statement

Forecast hourly electricity demand for the next 24 hours and use predicted demand to recommend whether the microgrid should operate in Main Grid Mode or Renewable Storage Mode.

The system also identifies potential critical overload conditions and presents forecast information through an interactive energy management dashboard.

## ✨ Features

* **24-Hour Demand Forecasting:** Generates hourly electricity demand predictions using a regression model deployed through Zoho Catalyst QuickML.
* **Live Weather Integration:** Retrieves weather forecasts to provide temperature and humidity inputs for demand prediction.
* **Manual Weather Scenarios:** Allows users to enter temperature, humidity, and solar irradiance values to explore different scenarios.
* **Interactive Forecast Dashboard:** Displays predicted demand, peak demand, average demand, grid operating modes, and overload alerts.
* **Automated Grid Transition Recommendations:** Applies predefined rules to recommend Main Grid Mode or Renewable Storage Mode.
* **Critical Overload Alerts:** Flags predicted demand at or above 200 kW.
* **Battery Simulation:** Demonstrates simulated battery state of charge and charging or discharging behavior.
* **Responsive Interface:** Provides navigation for demand forecasts, grid operations, alerts, and project information.

## ⚙️ Grid Transition Rules

The controller applies the following rules to each forecast hour:

| Condition                               | Recommended Action                |
| --------------------------------------- | --------------------------------- |
| Predicted demand > 160 kW               | Renewable Storage Mode            |
| Time between 18:00 and 22:00, inclusive | Renewable Storage Mode            |
| Neither condition applies               | Main Grid Mode                    |
| Predicted demand ≥ 200 kW               | Trigger a Critical Overload Alert |

The overload alert is evaluated separately from the grid-mode recommendation.

**Important:** These are demonstration rules for decision support. They do not directly switch real electrical infrastructure.

## 🧰 Technology Stack

### Backend

* Python
* Flask
* Pandas
* NumPy
* Requests
* Gunicorn

### Machine Learning and Forecasting

* Zoho Catalyst QuickML
* Regression-based demand prediction
* Scikit-learn for local model experimentation
* Open-Meteo weather forecast integration

### Frontend

* HTML
* CSS
* JavaScript
* Chart.js

### Deployment and Development

* Docker
* Zoho Catalyst AppSail
* Git
* GitHub

## 🏗️ System Architecture

1. **Weather Input:** The application receives manually entered weather assumptions or retrieves forecast weather data.
2. **Data Preparation:** Weather inputs are validated and converted into the feature format required by the prediction model.
3. **Demand Prediction:** The backend sends the prepared inputs to the Zoho Catalyst QuickML prediction endpoint.
4. **Grid Decision:** Predicted demand and the time of day are evaluated against the grid transition rules.
5. **Alert Generation:** Predicted demand at or above the configured overload threshold triggers a critical alert.
6. **Battery Simulation:** The system simulates battery state-of-charge changes for demonstration purposes.
7. **Visualization:** The dashboard presents the demand forecast, recommended operating modes, summary metrics, and alerts.

## 🚀 Running Locally

### Prerequisites

* Python 3.12 or compatible version
* Docker Desktop (optional, for containerized execution)
* Zoho Catalyst QuickML endpoint credentials

### 1. Clone the repository

```bash
git clone https://github.com/lakkoju-siddhardha/hacksphere-3-smart-microgrid.git
cd hacksphere-3-smart-microgrid
```

### 2. Create and activate a virtual environment

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```powershell
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a local `.env` file with the variable names required by your application. For example:

```env
QUICKML_ENDPOINT_URL=your_quickml_endpoint_url
QUICKML_ENDPOINT_KEY=your_quickml_endpoint_key
ZOHO_ACCESS_TOKEN=your_zoho_access_token
ZOHO_REFRESH_TOKEN=your_zoho_refresh_token
ZOHO_CATALYST_ORG=your_catalyst_org_id
CATALYST_ENVIRONMENT=Development
```

Use the exact organization-variable name expected by your current code. If your authentication helper requires additional OAuth credentials, configure those as well.

**Never commit `.env` or real credentials to GitHub.** The example values above are placeholders.

### 5. Start the application

```powershell
python -m flask --app app run --host 0.0.0.0 --port 8080
```

Open `http://127.0.0.1:8080` in your browser.

If you use Docker, configure the required environment variables securely and run the container with the port expected by your Dockerfile.

## 🔐 Security

* Store API keys and OAuth credentials in environment variables.
* Never hardcode access tokens, refresh tokens, client secrets, or API keys.
* Never commit `.env` files or private datasets.
* Configure deployment secrets through the hosting platform's environment-variable settings.
* Avoid exposing authentication details in logs or screenshots.

## 📊 Project Status

* [x] Python environment configured
* [x] Initial dataset analysis completed
* [x] GitHub repository created
* [x] Demand prediction integrated with Zoho Catalyst QuickML
* [x] Prediction API integration implemented
* [x] Manual weather scenario support
* [x] Live weather forecast integration
* [x] 24-hour demand forecast dashboard
* [x] Rule-based grid transition recommendations
* [x] Critical overload alerts
* [x] Battery simulation
* [x] Docker container built and tested locally
* [x] Zoho Catalyst AppSail deployment completed
* [x] Live application tested with weather and forecast features

## ⚠️ Limitations

* Demand values are model predictions rather than real-time electricity meter readings.
* Manual weather scenarios apply the same input values across the forecast horizon.
* Forecast accuracy depends on the training data, model quality, and input data.
* Battery state of charge and charging or discharging behavior are simulated.
* Grid transition recommendations are rule-based and do not operate physical power systems.

## 🔮 Future Improvements

* Compare multiple regression models using appropriate evaluation metrics.
* Improve forecast accuracy using richer historical and weather data.
* Add model evaluation metrics such as MAE, RMSE, and R².
* Introduce more advanced battery scheduling and renewable generation estimates.
* Add historical forecast comparisons and model monitoring.
* Explore production deployment and stronger authentication and monitoring.

## 👨‍💻 Project

**GridSense AI — Smart Energy Microgrid**

Developed for **HackSphere 3.0**.

Built to demonstrate how machine learning, weather forecasting, and rule-based decision support can contribute to smarter microgrid energy management.
