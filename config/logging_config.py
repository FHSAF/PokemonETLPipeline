# config/logging_config.py
import logging
import sys

def configure_logger():
    """Configures a basic logger to stream to stdout."""
    # Define the log format
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Get the root logger
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # Avoid adding handlers multiple times
    if not logger.handlers:
        # Create a handler to write log messages to the console (standard output)
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter(log_format))
        
        # Add the handler to the logger
        logger.addHandler(handler)