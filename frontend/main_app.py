# frontend/main_app.py
import streamlit as st
from frontend.data_loader import load_data
from frontend.styling import apply_styling, TYPE_COLORS
from frontend.components import create_radar_chart, display_evolution_chain

# --- Main Application ---
st.set_page_config(page_title="Pokémon Pokédex", page_icon="pokeball.png", layout="wide")
apply_styling()

st.title("Streamlit Pokédex")
st.markdown("Browse, search, and filter Pokémon from the database built with a Python ETL pipeline.")

pokemon_df, evolutions_df = load_data()

if pokemon_df.empty:
    st.error("The Pokémon database is empty! Please run the ETL pipeline first.", icon="🚨")
    st.code("docker-compose run --rm pipeline", language="bash")
else:
    # --- Sidebar Filters ---
    st.sidebar.header("Filters")
    search_query = st.sidebar.text_input("Search by Name")

    all_types = sorted(list(set(t for types_list in pokemon_df['types'] for t in types_list)))
    selected_types = st.sidebar.multiselect("Filter by Type", options=all_types)
    
    stat_to_filter = st.sidebar.selectbox("Filter by Stat", ['hp', 'attack', 'defense', 'special-attack', 'special-defense', 'speed'])
    min_stat_value = st.sidebar.slider(f"Minimum {stat_to_filter.replace('-', ' ').title()}", min_value=0, max_value=255, value=0)

    # --- Filtering Logic ---
    filtered_df = pokemon_df.copy()
    if search_query: filtered_df = filtered_df[filtered_df['name'].str.contains(search_query, case=False)]
    if selected_types: filtered_df = filtered_df[filtered_df['types'].apply(lambda x: all(t in x for t in selected_types))]
    if min_stat_value > 0 and stat_to_filter in filtered_df.columns:
        filtered_df = filtered_df[filtered_df[stat_to_filter] >= min_stat_value]
        
    st.subheader(f"Showing {len(filtered_df)} of {len(pokemon_df)} Pokémon")
    st.divider()

    # --- Display Grid ---
    cols = st.columns(2)
    for index, pokemon in filtered_df.iterrows():
        with cols[index % 2]:
            with st.container(border=True, height=280):
                st.subheader(f"{pokemon['name'].title()} #{pokemon['id']}")
                st.image(pokemon['sprite_url'], width=120)
                
                types_html = "".join([f'<span class="type-badge" style="background-color:{TYPE_COLORS.get(t, "#777")}">{t.title()}</span>' for t in pokemon['types']])
                st.markdown(types_html, unsafe_allow_html=True)
            
            with st.expander("View Insights"):
                st.plotly_chart(create_radar_chart(pokemon), use_container_width=True)
                display_evolution_chain(pokemon, pokemon_df, evolutions_df)