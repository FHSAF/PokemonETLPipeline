# main.py

import asyncio
import logging

from config.logging_config import configure_logger
from config import settings
from etl_pipeline.pipeline import ETLPipeline

configure_logger()

async def main():
    """Initializes and runs the ETL pipeline."""
    logger = logging.getLogger(__name__)
    logger.info("--- Pokémon ETL Pipeline Initialized ---")
    
    pipeline = ETLPipeline(
        pokemon_list=settings.POKEMON_TO_FETCH,
        db_path=settings.DATABASE_PATH
    )
    await pipeline.run()
    
    logger.info("--- Pipeline Execution Finished ---")

if __name__ == "__main__":
    # To run this script, execute from the project's root directory:
    # python -m etl_pipeline.main
    asyncio.run(main())