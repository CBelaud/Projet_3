# ui.py
import streamlit as st
import folium
from folium.plugins import MarkerCluster
from streamlit_folium import st_folium
from api_utils import get_route, generate_wordcloud
from config import DEFAULT_LOCATION, COLOR_SCHEME
from models import Restaurant

class RestaurantUI:
    def __init__(self):
        pass

    def show_map(self, restaurants: list, user_location: tuple):
        m = folium.Map(location=user_location, zoom_start=14)
        if user_location:
            folium.Marker(
                user_location,
                tooltip="Votre position",
                icon=folium.Icon(color="red", icon="user")
            ).add_to(m)
        cluster = MarkerCluster().add_to(m)
        for r in restaurants:
            folium.Marker(
                [r.latitude, r.longitude],
                popup=f"<b>{r.name}</b><br>Note: {r.rating}/5",
                icon=folium.Icon(color="green", icon="utensils")
            ).add_to(cluster)
        st_folium(m, width=700)

    def show_route(self, user_location: tuple, restaurant: Restaurant):
        geometry, distance, duration = get_route(user_location, (restaurant.latitude, restaurant.longitude))
        if geometry:
            m_route = folium.Map(
                location=[(user_location[0] + restaurant.latitude) / 2, (user_location[1] + restaurant.longitude) / 2],
                zoom_start=13
            )
            folium.Marker(user_location, popup="Vous", icon=folium.Icon(color="blue")).add_to(m_route)
            folium.Marker(
                [restaurant.latitude, restaurant.longitude],
                popup=restaurant.name,
                icon=folium.Icon(color="red")
            ).add_to(m_route)
            folium.GeoJson(geometry, style_function=lambda x: {'color': 'green'}).add_to(m_route)
            st_folium(m_route, width=700)
            if distance and duration:
                st.write(f"**Distance:** {distance/1000:.2f} km | **Durée:** {duration/60:.1f} min")
        else:
            st.info("Aucun itinéraire trouvé.")
