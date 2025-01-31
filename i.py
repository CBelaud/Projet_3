import streamlit as st
import requests
import json
import pandas as pd
import folium
from streamlit_folium import st_folium
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass
from pathlib import Path
from geopy.geocoders import Nominatim
from streamlit_js_eval import get_geolocation
from datetime import datetime

# Configurer la page pour éviter les recharges intempestives
st.set_page_config(page_title="Recherche de Lieux", layout="wide")

@dataclass
class Place:
    """Classe de données pour stocker les informations sur un lieu"""
    name: str
    address: str
    rating: float
    latitude: float
    longitude: float
    price_level: Optional[int] = None
    latest_review: Optional[str] = None
    review_rating: Optional[float] = None
    review_date: Optional[str] = None
    photo_reference: Optional[str] = None

class PlacesAPI:
    """Gestion de toutes les interactions avec l'API Google Places"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://places.googleapis.com/v1/places"
        self.headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": api_key,
            "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.location,places.rating,places.photos,places.priceLevel,places.reviews"
        }

    def get_photo_url(self, photo_reference: Optional[str]) -> str:
        """Obtenir l'URL d'une photo d'un lieu"""
        if not photo_reference:
            return "https://via.placeholder.com/400x300?text=Pas+d'image+disponible"
        
        return f"https://maps.googleapis.com/maps/api/place/photo?maxwidth=400&photo_reference={photo_reference}&key={self.api_key}"

    def search_places(self, query: str, location: Optional[Tuple[float, float, str]], max_distance: int, max_price: int, min_rating: float) -> Optional[List[Place]]:
        """Rechercher des lieux à l'aide de l'API Places"""
        url = f"{self.base_url}:searchText"
        data = {"textQuery": query, "maxResultCount": 20}
        
        if location:
            data["locationBias"] = {
                "circle": {
                    "center": {"latitude": location[0], "longitude": location[1]},
                    "radius": max_distance
                }
            }
        
        try:
            response = requests.post(url, headers=self.headers, json=data, timeout=10)
            response.raise_for_status()
            places_data = response.json().get('places', [])
            
            if not places_data:
                return None
            
            result = []
            for place in places_data:
                try:
                    photo_ref = place.get('photos', [{}])[0].get('name', '').split('/')[-1]
                    price_level = place.get('priceLevel', None)
                    reviews = place.get('reviews', [])

                    # ✅ **Ne filtre plus les avis, affiche-les simplement**
                    review_text = "Aucun avis disponible"
                    review_date = "Date inconnue"
                    review_rating = None

                    if reviews:
                        best_review = reviews[0]  # Prendre le premier avis disponible
                        review_text = best_review.get('text', "Aucun avis disponible")
                        review_rating = best_review.get('rating', None)
                        review_date = best_review.get('publishTime', "Date inconnue")

                        # 📅 **Formatage de la date en jj/mm/yyyy**
                        try:
                            review_date = datetime.fromisoformat(review_date.replace("Z", "")).strftime("%d/%m/%Y")
                        except ValueError:
                            review_date = "Date inconnue"

                    rating = float(place.get('rating', 0.0))
                    
                    if price_level is not None and price_level > max_price:
                        continue  # Filtrer par budget
                    if rating < min_rating:
                        continue  # Filtrer par note minimale
                    
                    result.append(Place(
                        name=place['displayName']['text'],
                        address=place.get('formattedAddress', 'Adresse inconnue'),
                        rating=rating,
                        latitude=place['location']['latitude'],
                        longitude=place['location']['longitude'],
                        price_level=price_level,
                        latest_review=review_text,
                        review_rating=review_rating,
                        review_date=review_date,
                        photo_reference=photo_ref
                    ))
                except (KeyError, TypeError, ValueError):
                    continue
            
            return result if result else None
        except requests.exceptions.RequestException as e:
            st.error(f"Erreur API: {str(e)}")
            return None

class PlacesApp:
    """Classe principale de l'application Streamlit"""
    
    def __init__(self):
        self.api_key = self._load_api_key()
        self.places_api = PlacesAPI(self.api_key)
        
    @staticmethod
    def _load_api_key() -> str:
        api_path = Path("api.txt")
        if not api_path.exists():
            st.error("Fichier de clé API non trouvé.")
            st.stop()
        return api_path.read_text().strip()

    def render_search_results(self, places: List[Place]):
        """Afficher les résultats de recherche dans Streamlit"""
        if not places:
            st.warning("Aucun lieu trouvé.")
            return

        # Création de la carte
        m = folium.Map(location=[places[0].latitude, places[0].longitude], zoom_start=12)

        for place in places:
            folium.Marker(
                location=[place.latitude, place.longitude],
                popup=folium.Popup(f"{place.name}\n⭐ {place.rating}", max_width=200),
                tooltip=place.name
            ).add_to(m)

            with st.container():
                col1, col2 = st.columns([3, 2])
                
                with col1:
                    st.markdown(f"### {place.name}")
                    st.write(f"📍 {place.address}")
                    st.write(f"⭐ Note : {place.rating}")
                    if place.price_level is not None:
                        st.write(f"💰 Budget : {'💵' * place.price_level}")
                    st.write(f"📝 **Dernier avis (Note: {place.review_rating} ⭐) :** {place.latest_review}")
                    st.write(f"📅 **Date de l'avis :** {place.review_date}")

                with col2:
                    photo_url = self.places_api.get_photo_url(place.photo_reference)
                    st.image(photo_url, use_container_width=True)
                    
                    google_maps_link = f"https://www.google.com/maps/search/?api=1&query={place.latitude},{place.longitude}"
                    st.markdown(f"[📍 Voir sur Google Maps]({google_maps_link})")
            st.divider()

        st_folium(m, width=700, height=500)

    def run(self):
        """Exécuter l'application Streamlit"""
        st.title("🔎 Recherche de Lieux")
        
        query = st.text_input("Que souhaitez-vous manger aujourd'hui ?")
        max_distance = st.slider("Filtrer par distance (en km)", 1, 50, 5) * 1000
        max_price = st.slider("Filtrer par budget (1=économique, 4=cher)", 1, 4, 4)
        min_rating = st.slider("Filtrer par note minimum", 1.0, 5.0, 3.0, 0.1)

        # Initialiser session_state
        if "places" not in st.session_state:
            st.session_state["places"] = None

        if st.button("Rechercher"):
            with st.spinner('Recherche en cours...'):
                st.session_state["places"] = self.places_api.search_places(query, None, max_distance, max_price, min_rating)

        # Afficher les résultats stockés en session_state
        if st.session_state["places"]:
            self.render_search_results(st.session_state["places"])
        else:
            st.warning("Effectuez une recherche pour voir les résultats.")

# Lancer l'application
if __name__ == "__main__":
    app = PlacesApp()
    app.run()
