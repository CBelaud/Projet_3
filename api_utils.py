# api_utils.py
import requests
import time
import pandas as pd
import streamlit as st
import folium
import matplotlib.pyplot as plt
from folium.plugins import MarkerCluster
from wordcloud import WordCloud
from typing import Optional, Tuple

import plotly.express as px

from config import API_KEY, FIELD_MASK, FILTERED_URL, nltk_stopwords
from models import Restaurant, LocationData
from streamlit_folium import st_folium

@st.cache_resource
def get_place_details_cached(place_id: str) -> dict:
    """Récupère les détails d'un lieu via l'API Place Details (avec mise en cache)."""
    details_url = "https://maps.googleapis.com/maps/api/place/details/json"
    params = {
        "place_id": place_id,
        "key": API_KEY,
        "language": "fr",
        "fields": "reviews,opening_hours"
    }
    try:
        response = requests.get(details_url, params=params, timeout=10)
        return response.json().get("result", {})
    except Exception:
        return {}

def find_restaurants(query: str, location: LocationData = None) -> Optional[pd.DataFrame]:
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": API_KEY,
        "X-Goog-FieldMask": FIELD_MASK
    }
    data = {"textQuery": query, "languageCode": "fr"}
    if location:
        data["locationBias"] = {
            "circle": {
                "center": {"latitude": location.latitude, "longitude": location.longitude},
                "radius": 5000.0
            }
        }
    try:
        response = requests.post(FILTERED_URL, headers=headers, json=data, timeout=10)
        response.raise_for_status()
        places = response.json().get('places', [])
        if places:
            df = pd.json_normalize(places)
            df.rename(columns={"id": "placeId"}, inplace=True)
            return df[['placeId', 'displayName.text', 'formattedAddress',
                       'location.latitude', 'location.longitude', 'rating',
                       'userRatingCount', 'primaryType']]
    except Exception as e:
        st.error(f"Erreur API: {str(e)}")
    return None

def create_restaurant(row: pd.Series) -> Optional[Restaurant]:
    try:
        details = get_place_details_cached(row['placeId'])
        reviews = details.get('reviews', [])
        return Restaurant(
            name=row['displayName.text'],
            address=row['formattedAddress'],
            rating=row.get('rating'),
            latitude=row['location.latitude'],
            longitude=row['location.longitude'],
            user_ratings_total=row.get('userRatingCount', 0),
            primary_type=row.get('primaryType'),
            place_id=row['placeId'],
            all_reviews=[review['text'] for review in reviews],
            latest_review=reviews[0]['text'] if reviews else None,
            review_rating=reviews[0]['rating'] if reviews else None,
            maps_url=f"https://www.google.com/maps/place/?q=place_id:{row['placeId']}",
            opening_hours="\n".join(details.get('opening_hours', {}).get('weekday_text', []))
        )
    except Exception as e:
        st.error(f"Erreur création restaurant: {str(e)}")
        return None

def generate_wordcloud(text: str) -> plt.Figure:
    wc = WordCloud(width=800, height=400, background_color='white',
                   stopwords=nltk_stopwords, colormap='Oranges').generate(text)
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.imshow(wc, interpolation='bilinear')
    ax.axis("off")
    return fig

def get_route(user_location: Tuple[float, float], restaurant_location: Tuple[float, float]) -> Tuple[Optional[dict], Optional[float], Optional[float]]:
    lon1, lat1 = user_location[1], user_location[0]
    lon2, lat2 = restaurant_location[1], restaurant_location[0]
    url = f"http://router.project-osrm.org/route/v1/driving/{lon1},{lat1};{lon2},{lat2}?overview=full&geometries=geojson"
    response = requests.get(url).json()
    if response.get("code") == "Ok":
        route = response["routes"][0]
        return route["geometry"], route["distance"], route["duration"]
    return None, None, None
