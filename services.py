# services.py
import time
import streamlit as st
import folium
from streamlit_folium import st_folium
from streamlit_js_eval import get_geolocation
from models import LocationData, Restaurant
from api_utils import find_restaurants, create_restaurant

class LocationService:
    def __init__(self):
        if "location" not in st.session_state:
            st.session_state.location = None
        if "location_history" not in st.session_state:
            st.session_state.location_history = []

    def get_user_location(self, max_age: int = 60) -> LocationData:
        current_time = time.time()
        if st.session_state.location and (current_time - st.session_state.location.timestamp) < max_age:
            return st.session_state.location

        with st.spinner("📍 Détection de votre position..."):
            geo_data = get_geolocation()
        if geo_data and 'coords' in geo_data:
            coords = geo_data['coords']
            try:
                location = LocationData(
                    latitude=coords['latitude'],
                    longitude=coords['longitude'],
                    accuracy=coords.get('accuracy'),
                    timestamp=current_time
                )
                st.session_state.location = location
                st.session_state.location_history.append(location)
                return location
            except Exception:
                pass
        return None

    def display_location_info(self):
        if st.session_state.location:
            loc = st.session_state.location
            st.success("✅ Position détectée!")
            cols = st.columns(2)
            cols[0].write(f"**Latitude:** {loc.latitude:.6f}°")
            cols[0].write(f"**Longitude:** {loc.longitude:.6f}°")
            cols[1].write(f"**Précision:** ±{loc.accuracy:.0f}m" if loc.accuracy else "")
            cols[1].write(f"**Dernière mise à jour:** {time.strftime('%H:%M:%S', time.localtime(loc.timestamp))}")

class RestaurantService:
    def __init__(self):
        pass

    def get_restaurants(self, query: str, location: LocationData = None) -> list:
        df = find_restaurants(query, location)
        restaurants = []
        if df is not None and not df.empty:
            for _, row in df.iterrows():
                r = create_restaurant(row)
                if r is not None:
                    restaurants.append(r)
        return restaurants
