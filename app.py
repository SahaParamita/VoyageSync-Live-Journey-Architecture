import streamlit as st
import requests
import math
from datetime import datetime

# ================= CONFIG =================
SERP_API_KEY = "834d8e3e5ae23da65700a04625a65620af878f867b4038d10e8ab1c0ed55a8d3"  
SERP_API_URL = "https://serpapi.com/search"
OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
IPINFO_URL = "https://ipinfo.io"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"


# --- Live location function  ---



def geocode(query):
    """Robust manual geocoder using OpenStreetMap Nominatim."""
    try:
        params = {"format": "json", "q": query, "limit": 1}
        r = requests.get(
            NOMINATIM_URL,
            params=params,
            headers={"User-Agent": "TravelPlanner/1.0"},  # required by Nominatim
            timeout=15
        )
        arr = r.json()
        if arr:
            return {
                "lat": float(arr[0]["lat"]),
                "lon": float(arr[0]["lon"]),
                "display_name": arr[0].get("display_name", query)
            }
    except:
        pass
    return None
#_________________________________________________________________________________________________________
def get_live_location():
    try:
        r = requests.get(IPINFO_URL, timeout=10)
        data = r.json()
        city = data.get("city", "")
        region = data.get("region", "")
        country = data.get("country", "")
        loc = data.get("loc", "")
        lat, lon = loc.split(",") if loc else ("", "")
        return {
            "city": city,
            "region": region,
            "country": country,
            "lat": float(lat) if lat else None,
            "lon": float(lon) if lon else None,
        }
    except:
        return None

# --- Distance function for filtering ---
#______________________________________________________________________________________________________________
def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * \
        math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    return R * (2 * math.atan2(math.sqrt(a), math.sqrt(1-a)))

# --- Generic SerpAPI fetch with radius filtering ---
def fetch_serpapi_results(lat, lon, query, radius_km=10):
    try:
        params = {
            "engine": "google_maps",
            "type": "search",
            "q": query,
            "ll": f"@{lat},{lon},14z",
            "google_domain": "google.co.in",
            "hl": "en",
            "gl": "in",
            "api_key": SERP_API_KEY
        }
        r = requests.get(SERP_API_URL, params=params, timeout=20)
        data = r.json()

        results = []
        for res in data.get("local_results", []):
            r_lat = res.get("gps_coordinates", {}).get("latitude")
            r_lon = res.get("gps_coordinates", {}).get("longitude")
            if not r_lat or not r_lon:
                continue
            if haversine(lat, lon, r_lat, r_lon) <= radius_km:
                results.append({
                    "name": res.get("title", "Unnamed"),
                    "address": res.get("address"),
                    "rating": res.get("rating"),
                    "reviews": res.get("reviews"),
                    "lat": r_lat,
                    "lon": r_lon,
                    "type": res.get("type")
                })
        return results
    except Exception as e:
        st.error(f"SerpAPI error: {e}")
        return []

# --- Specialized wrappers ---
def get_pois(lat, lon, radius_km):
    return fetch_serpapi_results(lat, lon, "tourist attractions", radius_km)

def get_hotels(lat, lon, radius_km):
    return fetch_serpapi_results(lat, lon, "hotels", radius_km)

# --- Weather ---
def get_weather(lat, lon):
    try:
        params = {
            "latitude": lat,
            "longitude": lon,
            "current_weather": True
        }
        r = requests.get(OPEN_METEO_URL, params=params, timeout=20)
        return r.json().get("current_weather", {})
    except:
        return {}

# ================= UI =================
st.set_page_config(page_title="VoyageSync - Live Journey Architect", layout="wide")
st.title("VoyageSync - Live Journey Architect")

# Sidebar controls
st.sidebar.header("Trip Settings")
days = st.sidebar.number_input("Days", 1, 14, 3)
people = st.sidebar.number_input("People", 1, 20, 2)
budget = st.sidebar.number_input("Total Budget (₹)", 1000, 100000, 20000, step=500)
poi_radius_meters = st.sidebar.slider("Top spot radius (meters)", 500, 10000, 3000)
spots_per_day = st.sidebar.slider("Spots per Day", 1, 6, 3)

# --- Location mode ---
st.subheader("Location Mode")
loc_mode = st.radio("Choose Location Source", ["Live (Auto-detect)", "Manual"])

if loc_mode == "Live (Auto-detect)":
    live_loc = get_live_location()
    if live_loc and live_loc["lat"] and live_loc["lon"]:
        lat, lon = live_loc["lat"], live_loc["lon"]
        st.success(f"📍 {live_loc['city']} {live_loc['region']} {live_loc['country']} ({lat}, {lon})")
    else:
        st.error("Could not detect live location.")
        st.stop()
else:
    manual_loc = st.text_input("Enter location (city, state, country)", placeholder="e.g., Agartala, Tripura, India")
    if manual_loc:
        g = geocode(manual_loc)
        if g:
            lat, lon = g["lat"], g["lon"]
            st.success(f"📍 {g['display_name']} ({lat}, {lon})")
            # continue to weather/POIs/hotels exactly like live mode
        else:
            st.error("Could not geocode that place. Try a broader or corrected name.")
            st.stop()
    else:
        st.info("Type a location like: Agartala, Tripura, India")
        st.stop()


# --- Show Weather ---
weather = get_weather(lat, lon)
st.subheader("Current Weather")
if weather:
    st.metric("Temperature (°C)", weather.get("temperature"))
    st.metric("Wind (km/h)", weather.get("windspeed"))
else:
    st.warning("No weather data available.")



# --- Nearby Attractions ---
st.subheader("Nearby Attractions")
pois = get_pois(lat, lon, poi_radius_meters / 1000)
if pois:
    for i, p in enumerate(pois, 1):
        st.write(f"{i}. *{p['name']}* — ⭐ {p['rating']} ({p['reviews']} reviews) — {p['address']}")
else:
    st.warning("No attractions found within your radius.")

# --- Nearby Hotels ---
st.subheader("Nearby Accommodations")
hotels = get_hotels(lat, lon, poi_radius_meters / 1000)
if hotels:
    for i, h in enumerate(hotels, 1):
        st.write(f"{i}. *{h['name']}* — ⭐ {h['rating']} ({h['reviews']} reviews) — {h['address']}")
else:
    st.warning("No accommodations found within your radius.")

# --- Budget Snapshot ---
st.subheader("Budget Snapshot (Very Rough)")
rooms_needed = math.ceil(people / 2)
remaining = budget - (rooms_needed * 3000)
st.metric("Estimated Trip Cost (₹)", budget)
st.metric("Rooms Needed", rooms_needed)
st.metric("Remaining (₹)", remaining)

# --- Generate Itinerary ---
st.subheader("Build Itinerary")
if st.button("Generate Plan"):
    if not pois:
        st.warning("Not enough POIs to make a plan. Try increasing radius.")
    else:
        day_plan = {}
        idx = 0
        for day in range(1, days + 1):
            day_plan[day] = pois[idx: idx + spots_per_day]
            idx += spots_per_day
        for day, spots in day_plan.items():
            st.write(f"### Day {day}")
            for spot in spots:
                st.write(f"- {spot['name']} — {spot['address']}")
