import logging
import sys

# ANSI escape codes for colors
COLORS = {
    'DEBUG': '\033[94m',    # Blue
    'INFO': '\033[92m',     # Green
    'WARNING': '\033[93m',  # Yellow
    'ERROR': '\033[91m',    # Red
    'CRITICAL': '\033[1;91m', # Bold Red
    'RESET': '\033[0m'
}

class ColorFormatter(logging.Formatter):
    def format(self, record):
        color = COLORS.get(record.levelname, COLORS['RESET'])
        reset = COLORS['RESET']
        message = super().format(record)
        return f"{color}{message}{reset}"

def get_logger(module_name: str) -> logging.Logger:
    logger = logging.getLogger(f"{module_name}")
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        formatter = ColorFormatter('[%(name)s] - %(levelname)s: %(message)s')
        
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    return logger
