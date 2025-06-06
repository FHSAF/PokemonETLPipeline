# frontend/data_loader.py
import streamlit as st
import pandas as pd
import sqlite3
from pathlib import Path
from typing import Tuple

from config import settings

DB_PATH = Path(settings.DATABASE_PATH)

@st.cache_data(ttl=3600)
def load_data() -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Loads all necessary data from the normalized SQLite database.
    """
    if not DB_PATH.exists():
        return pd.DataFrame(), pd.DataFrame()

    with sqlite3.connect(DB_PATH) as con:
		# Query for main pokemon data, joining with types and abilities
        pokemon_query = """
        SELECT 
            p.*, 
            GROUP_CONCAT(DISTINCT t.name) as types,
            GROUP_CONCAT(DISTINCT a.name) as abilities
        FROM pokemon p
        LEFT JOIN pokemon_types pt ON p.id = pt.pokemon_id
        LEFT JOIN types t ON pt.type_id = t.id
        LEFT JOIN pokemon_abilities pa ON p.id = pa.pokemon_id
        LEFT JOIN abilities a ON pa.ability_id = a.id
        GROUP BY p.id
        """
        pokemon_df = pd.read_sql_query(pokemon_query, con)
        pokemon_df['types'] = pokemon_df['types'].apply(lambda x: x.split(',') if x else [])
        
        # Process 'abilities' column into a list
        pokemon_df['abilities'] = pokemon_df['abilities'].apply(lambda x: x.split(',') if x else [])

        stats_query = """
        SELECT ps.pokemon_id, s.name as stat_name, ps.base_value FROM pokemon_stats ps
        JOIN stats s ON ps.stat_id = s.id
        """
        stats_df = pd.read_sql_query(stats_query, con)
        if not stats_df.empty:
            stats_pivot_df = stats_df.pivot(index='pokemon_id', columns='stat_name', values='base_value').reset_index()
            pokemon_df = pd.merge(pokemon_df, stats_pivot_df, left_on='id', right_on='pokemon_id', how='left')

        evolutions_df = pd.read_sql_query("SELECT * FROM evolutions", con)
        
    return pokemon_df, evolutions_df