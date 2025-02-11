# config.py
import streamlit as st
import nltk
from nltk.corpus import stopwords
import plotly.express as px

# --- Configuration Streamlit ---
st.set_page_config(
    page_title="🍽️ Restaurant Explorer",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Couleurs et paramètres par défaut ---
COLOR_SCHEME = px.colors.sequential.Oranges
DEFAULT_LOCATION = (48.8566, 2.3522)  # Coordonnées de Paris

# --- Clé API et configuration Google Places ---
try:
    with open('api_searchtext.txt') as f:
        API_KEY = f.read().strip()
except FileNotFoundError:
    API_KEY = st.secrets.get("GOOGLE_API_KEY", "")

FILTERED_URL = "https://places.googleapis.com/v1/places:searchText"
FIELD_MASK = (
    "places.id,places.displayName,places.formattedAddress,"
    "places.location,places.rating,places.userRatingCount,places.primaryType"
)

# --- Téléchargement des stopwords ---
nltk.download('stopwords')
nltk_stopwords = set(stopwords.words('french'))
