import logging
import sys

# Configure logging
logger = logging.getLogger('tetrix')
logger.setLevel(logging.DEBUG)

# Create console handler
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)

# Create formatter
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)

# Add handler to logger
logger.addHandler(handler) 