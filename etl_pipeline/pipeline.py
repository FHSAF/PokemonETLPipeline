# etl_pipeline/pipeline.py

import asyncio
import aiohttp
import logging
import sqlite3
from dataclasses import dataclass
from typing import List, Dict, Any, Optional

from config import settings

# --- Data Structure for Evolution Steps ---
@dataclass
class EvolutionStep:
    from_species: str
    to_species: str
    trigger: str
    trigger_item: Optional[str]
    min_level: Optional[int]

# --- Data Structure for Transformed Data ---
@dataclass
class TransformedPokemon:
    id: int
    name: str
    height: float
    weight: float
    base_experience: int
    sprite_url: Optional[str]
    shiny_sprite_url: Optional[str]
    types: List[str]
    abilities: List[str]
    stats: Dict[str, int]
    evolution_steps: List[EvolutionStep]
    flavor_text: Optional[str]
    is_legendary: bool
    is_mythical: bool
    color: Optional[str]

# --- The Main ETL Pipeline Class ---
class ETLPipeline:
    # This is used exclusively by the migration method to add new columns.
    TARGET_SCHEMA = {
        'id': 'INTEGER PRIMARY KEY',
        'name': 'TEXT NOT NULL UNIQUE',
        'height': 'REAL',
        'weight': 'REAL',
        'base_experience': 'INTEGER',
        'sprite_url': 'TEXT',
        'shiny_sprite_url': 'TEXT',
        'flavor_text': 'TEXT',
        'is_legendary': 'BOOLEAN',
        'is_mythical': 'BOOLEAN',
        'color': 'TEXT',
    }
    
    def __init__(self, pokemon_list: List[str], db_path: str):
        self.pokemon_to_fetch = pokemon_list
        self.db_path = db_path
        self.raw_data: List[Dict[str, Any]] = []
        self.transformed_data: List[TransformedPokemon] = []
        self.logger = logging.getLogger(__name__)
        self.conn = None

    # The migration method to handle alterations.
    def _run_migrations(self):
        """Checks the pokemon table schema and applies any missing columns."""
        self.logger.info("Running database migrations for 'pokemon' table...")
        cursor = self.conn.cursor()

        try:
            cursor.execute("PRAGMA table_info(pokemon)")
            actual_columns = {row[1] for row in cursor.fetchall()}
        except sqlite3.OperationalError:
            # The table doesn't exist yet, _create_all_tables will handle it.
            actual_columns = set()

        desired_columns = set(self.TARGET_SCHEMA.keys())
        missing_columns = desired_columns - actual_columns

        if not missing_columns:
            self.logger.info("'pokemon' table schema is up to date.")
            return

        self.logger.info(f"Schema mismatch found. Missing columns: {missing_columns}")
        for col_name in missing_columns:
            self.logger.info(f"Applying migration: Adding column '{col_name}' to 'pokemon' table...")
            col_definition = self.TARGET_SCHEMA[col_name]
            alter_sql = f"ALTER TABLE pokemon ADD COLUMN {col_name} {col_definition}"
            cursor.execute(alter_sql)
        
        self.conn.commit()
        self.logger.info("Database migrations applied successfully.")
        
    # --- 1. EXTRACT PHASE ---
    async def _fetch_url(self, session: aiohttp.ClientSession, url: str) -> Optional[Dict[str, Any]]:
        """A robust fetcher for a single URL with error handling."""
        try:
            async with session.get(url) as response:
                response.raise_for_status(); return await response.json()
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            self.logger.error(f"Network error while fetching {url}: {e}")
        except Exception as e:
            self.logger.error(f"An unexpected error occurred for {url}: {e}")
        return None

    async def _fetch_pokemon_details(self, session: aiohttp.ClientSession, name: str) -> Optional[Dict[str, Any]]:
        """Fetches and combines data from /pokemon, /pokemon-species, and the evolution chain URL."""
        self.logger.info(f"Fetching details for {name}...")
        pokemon_url = f"{settings.BASE_URL}/{name}"
        species_url = f"{settings.BASE_URL.replace('/pokemon', '/pokemon-species')}/{name}"
        pokemon_data, species_data = await asyncio.gather(self._fetch_url(session, pokemon_url), self._fetch_url(session, species_url))
        if not pokemon_data:
            self.logger.warning(f"Could not retrieve primary data for {name}. Skipping."); return None
        evolution_data = None
        if species_data and species_data.get("evolution_chain", {}).get("url"):
            evolution_data = await self._fetch_url(session, species_data["evolution_chain"]["url"])
        return {"pokemon_data": pokemon_data, "species_data": species_data, "evolution_data": evolution_data}

    async def _extract(self):
        """Orchestrates the concurrent extraction of data for all Pokémon."""
        self.logger.info(f"Starting EXTRACT phase for {len(self.pokemon_to_fetch)} Pokémon.")
        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            tasks = [self._fetch_pokemon_details(session, name) for name in self.pokemon_to_fetch]
            results = await asyncio.gather(*tasks)
        self.raw_data = [res for res in results if res is not None]
        self.logger.info(f"EXTRACT phase complete. Successfully fetched data for {len(self.raw_data)} Pokémon.")

    # --- 2. TRANSFORM PHASE ---
    def _parse_evolution_chain(self, evolution_data: Optional[Dict]) -> List[EvolutionStep]:
        """
        Recursively walks through the evolution chain JSON and flattens it into a list of steps.
        """
        if not evolution_data:
            return []

        steps = []
        chain_root = evolution_data.get("chain", {})

        def walk_chain(node: Dict):
            if not node: return
            for next_evolution in node.get("evolves_to", []):
                # Gracefully handle an empty evolution_details list
                details = next_evolution.get("evolution_details", [])
                detail_data = details[0] if details else {}

                # Safely access nested dictionaries
                trigger_obj = detail_data.get("trigger") or {}
                item_obj = detail_data.get("item") or {}
                
                step = EvolutionStep(
                    from_species=node["species"]["name"],
                    to_species=next_evolution["species"]["name"],
                    trigger=trigger_obj.get("name"),
                    trigger_item=item_obj.get("name"),
                    min_level=detail_data.get("min_level")
                )
                steps.append(step)
                
                # RECURSION: Walk down the rest of the chain
                walk_chain(next_evolution)

        walk_chain(chain_root)
        return steps

    def _transform(self):
        """Transforms the raw, nested data into clean, structured dataclass objects."""
        self.logger.info(f"Starting TRANSFORM phase for {len(self.raw_data)} Pokémon.")
        for data in self.raw_data:
            p_data, s_data, e_data = data["pokemon_data"], data["species_data"], data["evolution_data"]
            def get_flavor_text():
                if not s_data: return None
                for entry in s_data.get("flavor_text_entries", []):
                    if entry.get("language", {}).get("name") == "en": return entry["flavor_text"].replace("\n", " ").replace("\f", " ")
                return None
            self.transformed_data.append(TransformedPokemon(
                id=p_data["id"], name=p_data["name"], height=p_data["height"], weight=p_data["weight"],
                base_experience=p_data["base_experience"], sprite_url=p_data["sprites"]["front_default"],
                shiny_sprite_url=p_data["sprites"]["front_shiny"],
                types=[t["type"]["name"] for t in p_data["types"]],
                abilities=[a["ability"]["name"] for a in p_data["abilities"]],
                stats={s["stat"]["name"]: s["base_stat"] for s in p_data["stats"]},
                evolution_steps=self._parse_evolution_chain(e_data),
                flavor_text=get_flavor_text(),
                is_legendary=s_data.get("is_legendary", False) if s_data else False,
                is_mythical=s_data.get("is_mythical", False) if s_data else False,
                color=s_data.get("color", {}).get("name") if s_data else None,
            ))
        self.logger.info("TRANSFORM phase complete.")

    # --- 3. LOAD PHASE ---
    def _create_all_tables(self):
        """Creates all necessary tables for the normalized schema if they don't already exist."""
        self.logger.info("Ensuring all database tables exist...")
        cursor = self.conn.cursor()
        # The pokemon table is created with its BASE schema. _run_migrations will handle additions.
        base_pokemon_schema = ", ".join([f"{name} {definition}" for name, definition in self.TARGET_SCHEMA.items()])
        cursor.execute(f"CREATE TABLE IF NOT EXISTS pokemon ({base_pokemon_schema})")
        cursor.execute("CREATE TABLE IF NOT EXISTS stats (id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE)")
        cursor.execute("""CREATE TABLE IF NOT EXISTS pokemon_stats (pokemon_id INTEGER, stat_id INTEGER, base_value INTEGER NOT NULL, PRIMARY KEY (pokemon_id, stat_id), FOREIGN KEY (pokemon_id) REFERENCES pokemon(id), FOREIGN KEY (stat_id) REFERENCES stats(id))""")
        cursor.execute("""CREATE TABLE IF NOT EXISTS evolutions (id INTEGER PRIMARY KEY AUTOINCREMENT, from_species TEXT NOT NULL, to_species TEXT NOT NULL, trigger TEXT, trigger_item TEXT, min_level INTEGER, UNIQUE(from_species, to_species, trigger_item, min_level))""")
        cursor.execute("CREATE TABLE IF NOT EXISTS types (id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE)")
        cursor.execute("CREATE TABLE IF NOT EXISTS abilities (id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE)")
        cursor.execute("""CREATE TABLE IF NOT EXISTS pokemon_types (pokemon_id INTEGER, type_id INTEGER, PRIMARY KEY (pokemon_id, type_id), FOREIGN KEY (pokemon_id) REFERENCES pokemon(id), FOREIGN KEY (type_id) REFERENCES types(id))""")
        cursor.execute("""CREATE TABLE IF NOT EXISTS pokemon_abilities (pokemon_id INTEGER, ability_id INTEGER, PRIMARY KEY (pokemon_id, ability_id), FOREIGN KEY (pokemon_id) REFERENCES pokemon(id), FOREIGN KEY (ability_id) REFERENCES abilities(id))""")
        self.conn.commit()

    def _load(self):
        """Loads the transformed data into the normalized SQLite database."""
        self.logger.info(f"Starting LOAD phase into database: {self.db_path}")
        try:
            self.conn = sqlite3.connect(self.db_path)
            # 1. Ensure all tables are created with their base schema.
            self._create_all_tables()
            # 2. Run migrations to add any new columns to the pokemon table.
            self._run_migrations()
            
            cursor = self.conn.cursor()
            for p in self.transformed_data:
                pokemon_sql = """INSERT OR REPLACE INTO pokemon (id, name, height, weight, base_experience, sprite_url, shiny_sprite_url, flavor_text, is_legendary, is_mythical, color) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"""
                cursor.execute(pokemon_sql, (p.id, p.name, p.height, p.weight, p.base_experience, p.sprite_url, p.shiny_sprite_url, p.flavor_text, p.is_legendary, p.is_mythical, p.color))
                for stat_name, base_value in p.stats.items():
                    cursor.execute("INSERT OR IGNORE INTO stats (name) VALUES (?)", (stat_name,))
                    stat_id = cursor.execute("SELECT id FROM stats WHERE name=?", (stat_name,)).fetchone()[0]
                    cursor.execute("INSERT OR REPLACE INTO pokemon_stats (pokemon_id, stat_id, base_value) VALUES (?, ?, ?)", (p.id, stat_id, base_value))
                for step in p.evolution_steps:
                    cursor.execute("""INSERT OR IGNORE INTO evolutions (from_species, to_species, trigger, trigger_item, min_level) VALUES (?, ?, ?, ?, ?)""", (step.from_species, step.to_species, step.trigger, step.trigger_item, step.min_level))
                for type_name in p.types:
                    type_id = cursor.execute("INSERT OR IGNORE INTO types (name) VALUES (?)", (type_name,)).lastrowid or cursor.execute("SELECT id FROM types WHERE name=?", (type_name,)).fetchone()[0]
                    cursor.execute("INSERT OR IGNORE INTO pokemon_types (pokemon_id, type_id) VALUES (?, ?)", (p.id, type_id))
                for ability_name in p.abilities:
                    ability_id = cursor.execute("INSERT OR IGNORE INTO abilities (name) VALUES (?)", (ability_name,)).lastrowid or cursor.execute("SELECT id FROM abilities WHERE name=?", (ability_name,)).fetchone()[0]
                    cursor.execute("INSERT OR IGNORE INTO pokemon_abilities (pokemon_id, ability_id) VALUES (?, ?)", (p.id, ability_id))
            self.conn.commit()
            self.logger.info("LOAD phase complete. Data saved to normalized database.")
        except Exception as e:
            self.logger.error(f"An error occurred during the load phase: {e}")
            if self.conn: self.conn.rollback()
        finally:
            if self.conn: self.conn.close()

    # --- RUNNER ---
    async def run(self):
        """Executes the full ETL pipeline in order."""
        self.logger.info("Starting ETL pipeline execution...")
        self.conn = sqlite3.connect(self.db_path)
        await self._extract()
        if self.raw_data:
            self.logger.info("Database path: %s", self.db_path)
            self._transform()
            self._load()
        else:
            self.logger.warning("No data was extracted, skipping transform and load.")