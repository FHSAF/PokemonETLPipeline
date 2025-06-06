# frontend/styling.py
import streamlit as st

TYPE_COLORS = {
    "normal": "#A8A77A", "fire": "#EE8130", "water": "#6390F0", "electric": "#F7D02C",
    "grass": "#7AC74C", "ice": "#96D9D6", "fighting": "#C22E28", "poison": "#A33EA1",
    "ground": "#E2BF65", "flying": "#A98FF3", "psychic": "#F95587", "bug": "#A6B91A",
    "rock": "#B6A136", "ghost": "#735797", "dragon": "#6F35FC", "dark": "#705746",
    "steel": "#B7B7CE", "fairy": "#D685AD"
}

CSS = """
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
"""

def apply_styling():
    st.markdown(CSS, unsafe_allow_html=True)