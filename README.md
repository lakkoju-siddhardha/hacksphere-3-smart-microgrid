# GridSense AI — Smart Energy Microgrid

An intelligent energy demand forecasting and microgrid management application developed for HackSphere 3.0.

## Problem Statement

Forecast hourly electricity demand for the next 24 hours and use predicted demand to determine whether the system should operate in Main Grid Mode or Renewable Storage Mode.

## Planned Features

* Electricity demand forecasting using Zoho Catalyst QuickML.
* Weather telemetry ingestion and validation.
* 24-hour demand forecast visualisation.
* Automated grid transition decisions.
* Critical overload alerts.
* Interactive energy management dashboard.

## Technology Stack

* Python
* Pandas and NumPy
* Scikit-learn for local model experimentation
* Zoho Catalyst QuickML
* React and Vite
* Recharts
* Git and GitHub

## Transition Controller Rules

* Predicted demand greater than 160 kW: Renewable Storage Mode.
* Time between 18:00 and 22:00 inclusive: Renewable Storage Mode.
* Otherwise: Main Grid Mode.
* Predicted demand greater than or equal to 200 kW: Critical Overload Alert.

## Project Status

* [x] Python environment configured.
* [x] Initial dataset analysis completed.
* [x] GitHub repository created.
* [ ] Regression model comparison.
* [ ] QuickML model training and publication.
* [ ] Prediction API integration.
* [ ] Dashboard development.
* [ ] Zoho Catalyst deployment.

## Security

Credentials and API keys must be stored in environment variables and must never be committed to the repository.
