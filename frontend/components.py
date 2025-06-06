# frontend/components.py
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from frontend.styling import TYPE_COLORS

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
                st.markdown("❔", help=f"{name.title()} not in the database.")
                st.caption(f"{name.title()}\n(Not Fetched)")

    # Find the root of the evolution chain for the current Pokémon
    current_pokemon_name = pokemon['name']
    while True:
        prev_evo = evolutions_df[evolutions_df['to_species'] == current_pokemon_name]
        if prev_evo.empty: break
        current_pokemon_name = prev_evo['from_species'].iloc[0]

    # Check if the root pokemon is part of any evolution
    root_evo_check = evolutions_df[evolutions_df['from_species'] == current_pokemon_name]
    if root_evo_check.empty:
        st.info(f"{pokemon['name'].title()} does not evolve.")
        return

    # Dynamically determine number of columns needed by walking the chain first
    chain_links = [current_pokemon_name]
    temp_name = current_pokemon_name
    while True:
        next_evo = evolutions_df[evolutions_df['from_species'] == temp_name]
        if next_evo.empty: break
        temp_name = next_evo['to_species'].iloc[0]
        chain_links.append(temp_name)

    col_count = len(chain_links) * 2 -1 if len(chain_links) > 1 else 1
    evo_cols = st.columns(col_count)
    col_idx = 0

    # Draw the first Pokémon
    draw_pokemon_in_chain(current_pokemon_name, evo_cols[col_idx])
    col_idx += 1
    
    # Walk the chain forward and draw the rest
    while True:
        next_evolutions = evolutions_df[evolutions_df['from_species'] == current_pokemon_name]
        if next_evolutions.empty: break
        
        # For UI simplicity, assume non-branching evolution
        next_evo_step = next_evolutions.iloc[0] 
        
        if col_idx < col_count:
            with evo_cols[col_idx]:
                st.markdown("<p style='text-align: center; font-size: 24px; margin-top: 25px;'>➡️</p>", unsafe_allow_html=True)
                trigger = next_evo_step
                trigger_text = trigger['trigger'].replace('-', ' ').title()
                if trigger['min_level']: trigger_text += f" (Lvl {trigger['min_level']})"
                if trigger['trigger_item']: trigger_text += f" (Use {trigger['trigger_item'].replace('-', ' ').title()})"
                st.caption(trigger_text)
            col_idx += 1

        if col_idx < col_count:
            current_pokemon_name = next_evo_step['to_species']
            draw_pokemon_in_chain(current_pokemon_name, evo_cols[col_idx])
            col_idx += 1
        else:
            break