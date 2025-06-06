# Pokémon ETL Pipeline & Interactive Pokédex

This project demonstrates a complete, end-to-end data pipeline and web application. It automatically fetches data for a list of Pokémon from the public PokeAPI, transforms the complex JSON into a normalized relational structure, and loads it into a SQLite database. The processed data is then displayed in a rich, interactive web frontend built with Streamlit.

The entire application is containerized with Docker and managed by Docker Compose for easy, one-command setup and execution.

### Key Features

  * **Automated ETL Pipeline:** Asynchronous data extraction, advanced transformation, and loading into a normalized database.
  * **Interactive Web Frontend:** A user-friendly Pokédex to browse, search, and filter Pokémon.
  * **Rich Data Insights:** Visualizes Pokémon stats with radar charts and displays full evolution chains.
  * **Containerized Environment:** Uses Docker and Docker Compose for a consistent, portable, and easy-to-run setup.

### Technology Stack

  * **Backend:** Python, asyncio, aiohttp, Pandas
  * **Frontend:** Streamlit, Plotly
  * **Database:** SQLite
  * **Containerization:** Docker, Docker Compose

-----

### Database Schema Relations

The database uses a normalized, relational schema to store the Pokémon data efficiently and without redundancy. The core idea is to have a central `pokemon` table linked to several lookup and junction tables that manage many-to-many relationships.

#### Entity-Relationship Diagram (ERD)

This diagram shows how the tables are connected:

```
+-----------+      +-------------------+      +-------+
|   types   |      |   pokemon_types   |      |       |
|-----------|      |-------------------|      |       |
| id (PK)   |---<--| type_id (FK)      |      |       |
| name      |      | pokemon_id (FK)   |-->---|       |
+-----------+      +-------------------+      |       |
                                              |       |
+-----------+      +---------------------+    |       |
| abilities |      | pokemon_abilities   |    |pokemon|
|-----------|      |---------------------|    |-------|
| id (PK)   |---<--| ability_id (FK)     |    |id (PK)|
| name      |      | pokemon_id (FK)     |-->-|name   |
+-----------+      +---------------------+    |...    |
                                              |       |
+-----------+      +-------------------+      |       |
|   stats   |      |   pokemon_stats   |      |       |
|-----------|      |-------------------|      |       |
| id (PK)   |---<--| stat_id (FK)      |      |       |
| name      |      | pokemon_id (FK)   |-->---|       |
+-----------+      | base_value        |      +-------+
                   +-------------------+

+-------------------------------------------------+
|                   evolutions                    |
|-------------------------------------------------|
| id (PK)                                         |
| from_species (relates to pokemon.name)          |
| to_species (relates to pokemon.name)            |
| trigger, trigger_item, min_level                |
+-------------------------------------------------+
```

---

### Table Breakdown

* #### `pokemon`
    This is the central table containing the core information for each unique Pokémon.
    * `id (PK)`: The Pokémon's unique National Pokédex ID.
    * `name`: The name of the Pokémon.
    * Other fields include `height`, `weight`, `sprite_url`, `flavor_text`, etc.

* #### `types`, `abilities`, `stats`
    These are **lookup tables**. Their purpose is to store the unique names of each type, ability, or stat, giving each one a unique `id`. This prevents us from storing the same text (e.g., "grass", "attack") over and over.

* #### `pokemon_types`, `pokemon_abilities`, `pokemon_stats`
    These are **junction tables** (or linking tables). They resolve the many-to-many relationships.
    * A Pokémon can have multiple types, and a type can apply to many Pokémon. The `pokemon_types` table connects them using foreign keys:
        * `pokemon_id (FK)`: Connects to the `pokemon` table.
        * `type_id (FK)`: Connects to the `types` table.
    * The `pokemon_abilities` and `pokemon_stats` tables work in exactly the same way. The `pokemon_stats` table has an additional `base_value` column to store the Pokémon's score for that specific stat.

* #### `evolutions`
    This table stores the flattened evolution tree data. It represents a relationship between Pokémon species.
    * `from_species` / `to_species`: These fields store the names of the Pokémon in an evolution step (e.g., from "charmander" to "charmeleon").
    * `trigger`, `trigger_item`, `min_level`: These fields describe the condition required for the evolution to occur.

-----

### The ETL Process Explained

Our pipeline is divided into three distinct phases, each with a clear purpose.

#### 1\. Extract

  * **What We Do:** We concurrently fetch data for each Pokémon from two separate API endpoints: `/pokemon` and `/pokemon-species`. We also fetch the full data for each Pokémon's evolution chain.
  * **Why We Do It:** By combining the "battle stats" from `/pokemon` with the "encyclopedic data" (like rarity and evolution info) from `/pokemon-species`, we create a single, rich raw record for each creature, to provide a complete picture.

#### 2\. Transform

  * **What We Do:** This is the core logic phase. We take the raw, nested JSON data and convert it into clean, structured Python objects. This involves flattening data, restructuring lists of stats and types, and running a **recursive algorithm** to parse the entire evolution tree into a simple list of steps.
  * **Why We Do It:** Raw API data is not suitable for a relational database. This phase adds immense value by cleaning, structuring, and normalizing the data, making it consistent and ready for efficient loading and querying.

#### 3\. Load

  * **What We Do:** We take the transformed objects and load them into a normalized SQLite database. This involves populating multiple related tables, including `pokemon`, `types`, `abilities`, `pokemon_stats`, and `evolutions`.
  * **Why We Do It:** To persist the clean data in a robust, scalable, and queryable format. Storing the data in a normalized database is highly efficient and allows our frontend application to perform complex lookups (like finding an evolution chain) with simple SQL queries.

-----

### Running the Application with Docker Compose

**Prerequisites:** Docker and Docker Compose must be installed.

#### Step 1: Run the ETL Pipeline

This command will build the Docker image and run the pipeline to fetch the data and populate the database. Run this first.

```bash
docker compose build pipeline
docker compose run --rm pipeline
```

#### Step 2: Start the Frontend Application

Once the pipeline is complete, this command will build, and start the web server.

```bash
docker compose up frontend --build
# Or simply start
docker compose up frontend
```

#### Step 3: Access the Pokédex

Open your web browser and navigate to the following URL:

[**http://localhost:8501**](http://localhost:8501)