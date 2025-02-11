# main.py
import streamlit as st
import time
from datetime import datetime
import pandas as pd
import plotly.express as px
import folium
from folium.plugins import MarkerCluster
from streamlit_folium import st_folium

from config import DEFAULT_LOCATION, COLOR_SCHEME
from services import LocationService, RestaurantService
from ui import RestaurantUI
from api_utils import find_restaurants, create_restaurant, get_route, generate_wordcloud

def main():
    # Initialisation de l'état de session
    for key in ['restaurants', 'df', 'favorites', 'search_history', 'reviews', 'selected_route']:
        if key not in st.session_state:
            st.session_state[key] = [] if key != 'df' else pd.DataFrame()
    if "user_reviews" not in st.session_state:
        st.session_state.user_reviews = {}

    loc_service = LocationService()
    
    # Navigation principale
    tab = st.radio("Navigation", ["📍 Position", "🔍 Recherche", "👤 Profil"],
                   horizontal=True, index=1)

    if tab == "📍 Position":
        st.title("📍 Géolocalisation")
        loc = loc_service.get_user_location()
        if loc:
            loc_service.display_location_info()
        else:
            st.warning("Activer la géolocalisation dans votre navigateur")

    elif tab == "🔍 Recherche":
        st.title("🔍 Recherche de Restaurants")
        
        # Formulaire de recherche
        with st.form("search_form"):
            query = st.text_input("Rechercher des restaurants")
            if st.form_submit_button("🔍 Lancer la recherche"):
                with st.spinner("Recherche en cours..."):
                    df = find_restaurants(query, st.session_state.location)
                    if df is not None and not df.empty:
                        st.session_state.df = df
                        st.session_state.restaurants = [
                            r for r in [create_restaurant(row) for _, row in df.iterrows()] 
                            if r is not None
                        ]
                        st.session_state.search_history.append(time.time())
                        st.success(f"{len(st.session_state.restaurants)} résultats trouvés!")
                    else:
                        st.session_state.restaurants = []
                        st.warning("Aucun résultat trouvé")

        if st.session_state.restaurants:
            # Deux colonnes : liste des résultats et affichage (carte et visualisations/itinéraire)
            cols = st.columns([1, 2])
            
            with cols[0]:
                st.subheader("Liste des résultats")
                types_valides = {r.primary_type for r in st.session_state.restaurants if r.primary_type and isinstance(r.primary_type, str)}
                selected_type = st.selectbox("Filtrer par type", ["Tous"] + sorted(types_valides))
                sort_option = st.selectbox("Trier par", ["Note décroissante", "Note croissante", "Nombre d'avis"])

                filtered = [r for r in st.session_state.restaurants if selected_type == "Tous" or r.primary_type == selected_type]
                reverse = sort_option == "Note décroissante"
                if "Note" in sort_option:
                    filtered.sort(key=lambda x: x.rating or 0, reverse=reverse)
                else:
                    filtered.sort(key=lambda x: x.user_ratings_total or 0, reverse=True)

                for restaurant in filtered:
                    with st.expander(f"🏠 {restaurant.name}"):
                        st.write(f"⭐ **Note:** {restaurant.rating}/5" if restaurant.rating else "⭐ Aucune note")
                        st.write(f"📍 {restaurant.address}")
                        st.write(f"📌 Type: {restaurant.primary_type}")
                        if restaurant.latest_review:
                            st.write(f"💬 Dernier avis: _{restaurant.latest_review}_")
                        
                        col_actions = st.columns(2)
                        with col_actions[0]:
                            if st.button("🗺️ Itinéraire", key=f"route_{restaurant.place_id}"):
                                st.session_state.selected_route = restaurant
                        with col_actions[1]:
                            if st.button("❤️ Ajouter aux favoris", key=f"fav_{restaurant.place_id}"):
                                if restaurant not in st.session_state.favorites:
                                    st.session_state.favorites.append(restaurant)
                                    st.success("Ajouté aux favoris!")
                        
                        st.markdown("---")
                        # Saisie d'avis utilisateur
                        user_review = st.text_area("Votre avis", key=f"review_input_{restaurant.place_id}", height=100)
                        if st.button("Ajouter votre avis", key=f"add_review_{restaurant.place_id}"):
                            if user_review.strip():
                                if restaurant.place_id not in st.session_state.user_reviews:
                                    st.session_state.user_reviews[restaurant.place_id] = []
                                st.session_state.user_reviews[restaurant.place_id].append(user_review)
                                st.success("Votre avis a été ajouté !")
                        
                        # Affichage des avis utilisateurs
                        if restaurant.place_id in st.session_state.user_reviews and st.session_state.user_reviews[restaurant.place_id]:
                            st.markdown("**Avis des utilisateurs :**")
                            for ur in st.session_state.user_reviews[restaurant.place_id]:
                                st.write(ur)
            
            with cols[1]:
                # Carte interactive affichant la position et les résultats
                m = folium.Map(
                    location=(st.session_state.location.latitude, st.session_state.location.longitude)
                        if st.session_state.location else DEFAULT_LOCATION,
                    zoom_start=14
                )
                if st.session_state.location:
                    folium.Marker(
                        [st.session_state.location.latitude, st.session_state.location.longitude],
                        tooltip="Votre position",
                        icon=folium.Icon(color="red", icon="user")
                    ).add_to(m)
                cluster = MarkerCluster().add_to(m)
                for r in filtered:
                    folium.Marker(
                        [r.latitude, r.longitude],
                        popup=f"<b>{r.name}</b><br>Note: {r.rating}/5",
                        icon=folium.Icon(color="blue", icon="glyphicon glyphicon-cutlery")
                    ).add_to(cluster)
                st_folium(m, width=700)

                # Onglets de la colonne droite : Visualisations et Itinéraire
                tabs_right = st.tabs(["Visualisations", "Itinéraire"])
                
                with tabs_right[0]:
                    st.subheader("📈 Statistiques")
                    cols_stats = st.columns(3)
                    cols_stats[0].metric("Note moyenne", f"{st.session_state.df['rating'].mean():.1f}/5")
                    cols_stats[1].metric("Total établissements", len(st.session_state.df))
                    cols_stats[2].metric("Avis total", st.session_state.df['userRatingCount'].sum())

                    tabs_viz = st.tabs(["Distribution des notes", "Répartition par type", "Notes vs Avis", "WordCloud Avis"])
                    with tabs_viz[0]:
                        fig_hist = px.histogram(st.session_state.df, x='rating', 
                                                title='Distribution des notes',
                                                color_discrete_sequence=COLOR_SCHEME)
                        st.plotly_chart(fig_hist, use_container_width=True)
                    
                    with tabs_viz[1]:
                        if 'primaryType' in st.session_state.df.columns:
                            type_counts = st.session_state.df['primaryType'].value_counts().reset_index()
                            type_counts.columns = ['Type', 'Count']
                            fig_pie = px.pie(type_counts, values='Count', names='Type', 
                                             title="Répartition par type de restaurant",
                                             color_discrete_sequence=COLOR_SCHEME)
                            st.plotly_chart(fig_pie, use_container_width=True)
                    
                    with tabs_viz[2]:
                        fig_scatter = px.scatter(
                            st.session_state.df, x='rating', y='userRatingCount',
                            color='displayName.text', title="Relation entre note et nombre d'avis",
                            size='rating',
                            labels={'rating': "Note", 'userRatingCount': "Nombre d'avis"},
                            color_discrete_sequence=COLOR_SCHEME
                        )
                        st.plotly_chart(fig_scatter, use_container_width=True)
                    
                    with tabs_viz[3]:
                        restaurants_avec_avis = [
                            r for r in st.session_state.restaurants 
                            if (r.all_reviews and len(r.all_reviews) > 0) or 
                               (r.place_id in st.session_state.user_reviews and st.session_state.user_reviews[r.place_id])
                        ]
                        if restaurants_avec_avis:
                            restaurant_names = [r.name for r in restaurants_avec_avis]
                            selected_restaurant_name = st.selectbox(
                                "Choisissez un restaurant pour afficher le wordcloud de ses avis",
                                restaurant_names, key="wc_select"
                            )
                            selected_restaurant = next((r for r in restaurants_avec_avis if r.name == selected_restaurant_name), None)
                            if selected_restaurant:
                                all_reviews = list(selected_restaurant.all_reviews)
                                if selected_restaurant.place_id in st.session_state.user_reviews:
                                    all_reviews.extend(st.session_state.user_reviews[selected_restaurant.place_id])
                                if all_reviews:
                                    all_reviews_text = " ".join(all_reviews)
                                    st.pyplot(generate_wordcloud(all_reviews_text))
                                else:
                                    st.info("Aucun avis disponible pour ce restaurant.")
                        else:
                            st.info("Aucun avis disponible pour générer un wordcloud.")

                with tabs_right[1]:
                    st.subheader("Itinéraire détaillé")
                    if st.session_state.selected_route:
                        user_loc = (st.session_state.location.latitude, st.session_state.location.longitude)
                        resto_loc = (st.session_state.selected_route.latitude, st.session_state.selected_route.longitude)
                        geometry, distance, duration = get_route(user_loc, resto_loc)
                        if geometry:
                            m_route = folium.Map(
                                location=[(user_loc[0] + resto_loc[0]) / 2, (user_loc[1] + resto_loc[1]) / 2],
                                zoom_start=13
                            )
                            folium.Marker(user_loc, popup="Vous", icon=folium.Icon(color="blue")).add_to(m_route)
                            folium.Marker(resto_loc, popup=st.session_state.selected_route.name, icon=folium.Icon(color="red")).add_to(m_route)
                            folium.GeoJson(geometry, style_function=lambda x: {'color': 'green'}).add_to(m_route)
                            st_folium(m_route, width=700)
                            if distance and duration:
                                st.write(f"**Distance:** {distance/1000:.2f} km | **Durée:** {duration/60:.1f} min")
                        else:
                            st.info("Aucun itinéraire trouvé.")
                    else:
                        st.info("Sélectionnez un restaurant pour voir l'itinéraire détaillé.")

    elif tab == "👤 Profil":
        st.title("👤 Votre Profil")
        st.markdown("## Tableau de Bord Personnel")
        
        # Calcul des métriques
        reviews_count = len(st.session_state.reviews) if "reviews" in st.session_state else 0
        favorites_count = len(st.session_state.favorites) if "favorites" in st.session_state else 0
        rated_reviews = [rev for rev in st.session_state.reviews if rev.get("rating") is not None]
        avg_rating = sum([rev["rating"] for rev in rated_reviews]) / len(rated_reviews) if rated_reviews else 0

        # Affichage des métriques sous forme de colonnes
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Avis", reviews_count)
        col2.metric("Favoris", favorites_count)
        col3.metric("Note Moyenne", f"{avg_rating:.1f}" if rated_reviews else "N/A")
        
        st.markdown("---")
        left_col, right_col = st.columns(2)

        with left_col:
            st.subheader("Laissez Votre Avis")
            if st.session_state.restaurants:
                restaurant_names = [r.name for r in st.session_state.restaurants]
                selected_restaurant = st.selectbox("Choisissez un restaurant", options=restaurant_names)
                with st.form("profile_review_form"):
                    review_text = st.text_area("Votre avis", placeholder="Partagez votre expérience...")
                    review_rating = st.number_input("Votre note (0-5)", min_value=0.0, max_value=5.0, step=0.1, format="%.1f")
                    submitted = st.form_submit_button("Soumettre l'Avis")
                    if submitted and review_text.strip():
                        st.session_state.reviews.append({
                            "restaurant": selected_restaurant,
                            "review": review_text,
                            "rating": review_rating,
                            "date": datetime.now().strftime("%d/%m/%Y %H:%M")
                        })
                        st.success("Votre avis a été soumis avec succès !")
            else:
                st.info("Aucun restaurant disponible pour laisser un avis.")

            st.markdown("### Vos Avis Récents")
            if st.session_state.reviews:
                recent_reviews = st.session_state.reviews[-5:]
                for rev in reversed(recent_reviews):
                    st.markdown(f"**{rev['restaurant']}** – *{rev['date']}*")
                    st.info(f"> {rev['review']}")
                    if rev.get("rating") is not None:
                        st.write(f"**Note:** {rev['rating']}/5")
                    st.markdown("---")
            else:
                st.info("Vous n'avez laissé aucun avis pour le moment.")

        with right_col:
            st.subheader("Statistiques de Vos Avis")
            if st.session_state.reviews:
                df_reviews = pd.DataFrame(st.session_state.reviews)
                if not df_reviews.empty and "rating" in df_reviews.columns:
                    df_reviews["rating"] = pd.to_numeric(df_reviews["rating"], errors='coerce').fillna(0)
                
                fig_hist_reviews = px.histogram(
                    df_reviews, x="rating", nbins=10,
                    title="Distribution de Vos Notes",
                    color_discrete_sequence=COLOR_SCHEME
                )
                st.plotly_chart(fig_hist_reviews, use_container_width=True)
                
                reviews_text_user = " ".join(df_reviews["review"].astype(str).tolist())
                if reviews_text_user.strip():
                    st.markdown("### Word Cloud de Vos Avis")
                    fig_wc_user = generate_wordcloud(reviews_text_user)
                    st.pyplot(fig_wc_user)
            else:
                st.info("Vous n'avez laissé aucun avis pour le moment.")

            st.subheader("Vos Restaurants Favoris")
            if st.session_state.favorites:
                for fav in st.session_state.favorites:
                    st.markdown(f"- **{fav.name}**")
            else:
                st.info("Vous n'avez aucun favori pour le moment.")
        
        st.markdown("---")
        st.markdown(
            "<h3 style='text-align: center; color: #FF5733;'>Continuez à explorer et à partager vos expériences culinaires !</h3>",
            unsafe_allow_html=True
        )

if __name__ == "__main__":
    main()
