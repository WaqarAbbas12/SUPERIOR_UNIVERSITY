import os
import requests
from dotenv import load_dotenv
from flask import Flask, request, render_template, jsonify


load_dotenv()
api_key = os.getenv("NASA_API_KEY")

# Flask App Setup
app = Flask(__name__)

AU_TO_KM = 149597870.7


def fetch_exoplanet_data():
    url = "https://exoplanetarchive.ipac.caltech.edu/cgi-bin/nstedAPI/nph-nstedAPI"
    params = {"table": "exoplanets", "format": "json", "where": "pl_kepflag=1"}

    try:
        response = requests.get(url, params=params)
        print("API Status Code:", response.status_code)

        print("API Response Text:", response.text[:500])

        if response.status_code != 200 or not response.text.strip():
            print("API request failed or returned empty data")
            return []

        data = response.json()
        print("Sample Data:", data[:3])

        return data
    except requests.exceptions.RequestException as e:
        print("Request Error:", e)
        return [
            {"pl_name": "Kepler-22b", "pl_orbsmax": 0.85},
            {"pl_name": "Kepler-442b", "pl_orbsmax": 0.409},
        ]


def calculate_trip_cost(distance_au, fuel_price=5000, efficiency=0.8):
    if distance_au is None or distance_au == "":
        return "N/A"
    try:
        distance_km = float(distance_au) * AU_TO_KM
        return round((distance_km * fuel_price) / efficiency, 2)
    except ValueError:
        return "Invalid Data"


@app.route("/", methods=["GET", "POST"])
def home():
    planets = fetch_exoplanet_data()
    cost = None
    selected_planet = None

    if request.method == "POST":
        selected_planet = request.form.get("planet")
        efficiency = float(request.form.get("efficiency", 1))
        planet_data = next(
            (p for p in planets if p.get("pl_name") == selected_planet), None
        )
        if planet_data:
            distance = planet_data.get("pl_orbsmax", 0)
            cost = calculate_trip_cost(distance, efficiency=efficiency)

    return render_template(
        "index.html", planets=planets, cost=cost, selected_planet=selected_planet
    )


if __name__ == "__main__":
    app.run(debug=True)
