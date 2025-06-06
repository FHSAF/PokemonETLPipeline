# app.py

import streamlit as st
import pandas as pd
import sqlite3
from pathlib import Path
import plotly.graph_objects as go
from typing import Tuple
from config import settings

# --- Page Configuration ---
# Sets the title, icon, and layout for the browser tab.
st.set_page_config(
    page_title="Pokémon Pokédex",
    page_icon="pokeball.png",
    layout="wide",
)

# --- Database Connection & Data Loading ---
DB_PATH = Path(settings.DATABASE_PATH)

# --- UI Styling ---
# A dictionary to map Pokémon types to specific colors for visual flair.
TYPE_COLORS = {
    "normal": "#A8A77A", "fire": "#EE8130", "water": "#6390F0", "electric": "#F7D02C",
    "grass": "#7AC74C", "ice": "#96D9D6", "fighting": "#C22E28", "poison": "#A33EA1",
    "ground": "#E2BF65", "flying": "#A98FF3", "psychic": "#F95587", "bug": "#A6B91A",
    "rock": "#B6A136", "ghost": "#735797", "dragon": "#6F35FC", "dark": "#705746",
    "steel": "#B7B7CE", "fairy": "#D685AD"
}

# Custom CSS is injected to style the Pokémon sprites and type badges.
st.markdown("""
<style>
    /* Style for the pokemon image to be round */
    .st-emotion-cache-1v0mbdj > img {
        border-radius: 50%;
        border: 2px solid #555;
    }
    /* Style for the colored type badges */
    .type-badge {
        display: inline-block;
        padding: .25em .6em;
        font-size: .75em;
        font-weight: 700;
        line-height: 1;
        text-align: center;
        white-space: nowrap;
        vertical-align: baseline;
        border-radius: .375rem;
        color: white;
        margin-right: .5em;
    }
</style>
""", unsafe_allow_html=True)


# --- Data Loading Function ---
@st.cache_data(ttl=3600)  # Cache data for 1 hour to improve performance
def load_data() -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Loads all necessary data from the normalized SQLite database.
    It returns two separate DataFrames: one for pokemon details and one for evolutions.
    """
    if not DB_PATH.exists():
        return pd.DataFrame(), pd.DataFrame()

    with sqlite3.connect(DB_PATH) as con:
        # Query for main pokemon data, joining with types
        pokemon_query = """
        SELECT 
            p.*, 
            GROUP_CONCAT(t.name) as types
        FROM pokemon p
        LEFT JOIN pokemon_types pt ON p.id = pt.pokemon_id
        LEFT JOIN types t ON pt.type_id = t.id
        GROUP BY p.id
        """
        pokemon_df = pd.read_sql_query(pokemon_query, con)
        pokemon_df['types'] = pokemon_df['types'].apply(lambda x: x.split(',') if x else [])

        # Query for normalized stats data
        stats_query = """
        SELECT 
            ps.pokemon_id,
            s.name as stat_name,
            ps.base_value
        FROM pokemon_stats ps
        JOIN stats s ON ps.stat_id = s.id
        """
        stats_df = pd.read_sql_query(stats_query, con)

        # Pivot the stats data to turn rows into columns for easy access
        if not stats_df.empty:
            stats_pivot_df = stats_df.pivot(index='pokemon_id', columns='stat_name', values='base_value').reset_index()
            # Merge the pivoted stats back into the main pokemon dataframe
            pokemon_df = pd.merge(pokemon_df, stats_pivot_df, left_on='id', right_on='pokemon_id', how='left')

        # Query for the complete evolution data
        evolutions_df = pd.read_sql_query("SELECT * FROM evolutions", con)

    return pokemon_df, evolutions_df


# --- Helper Functions for Insights ---
def create_radar_chart(pokemon: pd.Series):
    """Creates a Plotly radar chart for a single Pokémon's stats."""
    stats_cols = ['hp', 'attack', 'defense', 'special-attack', 'special-defense', 'speed']
    stats_labels = [s.replace('-', ' ').title() for s in stats_cols]
    stats_values = [pokemon.get(s, 0) for s in stats_cols]

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=stats_values,
        theta=stats_labels,
        fill='toself',
        name=pokemon['name'].title()
    ))
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 255])),
        showlegend=False, height=300, margin=dict(l=40, r=40, t=40, b=40)
    )
    return fig

def display_evolution_chain(pokemon: pd.Series, all_pokemon_df: pd.DataFrame, evolutions_df: pd.DataFrame):
    """
    Finds and displays the full evolution chain for a given Pokémon.
    """
    st.subheader("Evolution Chain")

    def draw_pokemon_in_chain(name, col):
        # Filter the dataframe to find the pokemon
        poke_df_filtered = all_pokemon_df[all_pokemon_df['name'] == name]

        # --- Check if the pokemon was found ---
        if not poke_df_filtered.empty:
            poke_info = poke_df_filtered.iloc[0]
            with col:
                st.image(poke_info['sprite_url'], width=80)
                st.caption(poke_info['name'].title())
        else:
            # If not found, display a placeholder instead of crashing
            with col:
                # Just show text
                st.markdown("❔", help=f"{name.title()} not in the database.")
                st.caption(f"{name.title()}\n(Not Fetched)")
    
    current_pokemon_name = pokemon['name']
    while True:
        prev_evo = evolutions_df[evolutions_df['to_species'] == current_pokemon_name]
        if prev_evo.empty: break
        current_pokemon_name = prev_evo['from_species'].iloc[0]
    
    root_evo_check = evolutions_df[evolutions_df['from_species'] == current_pokemon_name]
    if root_evo_check.empty:
        st.info(f"{pokemon['name'].title()} does not evolve.")
        return

    # Dynamically determine number of columns needed
    chain_links = [current_pokemon_name]
    temp_name = current_pokemon_name
    while True:
        next_evo = evolutions_df[evolutions_df['from_species'] == temp_name]
        if next_evo.empty: break
        temp_name = next_evo['to_species'].iloc[0]
        chain_links.append(temp_name)

    col_count = len(chain_links) * 2 -1
    evo_cols = st.columns(col_count)
    col_idx = 0

    # Draw the first Pokémon
    draw_pokemon_in_chain(current_pokemon_name, evo_cols[col_idx])
    col_idx += 1
    
    # Walk the chain forward and draw the rest
    while True:
        next_evolutions = evolutions_df[evolutions_df['from_species'] == current_pokemon_name]
        if next_evolutions.empty: break
        
        next_evo_step = next_evolutions.iloc[0] # Assuming non-branching for simplicity
        
        with evo_cols[col_idx]:
            st.markdown("<p style='text-align: center; font-size: 24px; margin-top: 25px;'>➡️</p>", unsafe_allow_html=True)
            trigger = next_evo_step
            trigger_text = trigger['trigger'].replace('-', ' ').title()
            if trigger['min_level']: trigger_text += f" (Lvl {trigger['min_level']})"
            if trigger['trigger_item']: trigger_text += f" (Use {trigger['trigger_item'].replace('-', ' ').title()})"
            st.caption(trigger_text)
        col_idx += 1

        current_pokemon_name = next_evo_step['to_species']
        draw_pokemon_in_chain(current_pokemon_name, evo_cols[col_idx])
        col_idx += 1


# --- Main Application ---
st.title("Streamlit Pokédex")
st.markdown("Browse, search, and filter Pokémon from the database built with a Python ETL pipeline.")

# Load all data at the beginning
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
    if search_query:
        filtered_df = filtered_df[filtered_df['name'].str.contains(search_query, case=False)]
    if selected_types:
        filtered_df = filtered_df[filtered_df['types'].apply(lambda x: all(t in x for t in selected_types))]
    if min_stat_value > 0:
        # Ensure the stat column exists before filtering
        if stat_to_filter in filtered_df.columns:
            filtered_df = filtered_df[filtered_df[stat_to_filter] >= min_stat_value]
        
    st.subheader(f"Showing {len(filtered_df)} of {len(pokemon_df)} Pokémon")
    st.divider()

    # --- Display Grid ---
    cols = st.columns(4)
    for index, pokemon in filtered_df.iterrows():
        with cols[index % 4]:
            with st.container(border=True, height=280):
                st.subheader(f"{pokemon['name'].title()} #{pokemon['id']}")
                st.image(pokemon['sprite_url'], width=120)
                
                types_html = "".join([f'<span class="type-badge" style="background-color:{TYPE_COLORS.get(t, "#777")}">{t.title()}</span>' for t in pokemon['types']])
                st.markdown(types_html, unsafe_allow_html=True)
            
            # Expander for detailed insights
            with st.expander("View Insights"):
                st.plotly_chart(create_radar_chart(pokemon), use_container_width=True)
                display_evolution_chain(pokemon, pokemon_df, evolutions_df)