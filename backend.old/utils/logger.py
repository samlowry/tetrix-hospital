import logging
from logging.handlers import RotatingFileHandler

def setup_logging():
    log_formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] - %(message)s'
    )
    
    # File handler with rotation
    file_handler = RotatingFileHandler(
        'tetrix.log',
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    file_handler.setFormatter(log_formatter)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_formatter)
    
    # Setup logger
    logger = logging.getLogger('tetrix')
    logger.setLevel(logging.INFO)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger 