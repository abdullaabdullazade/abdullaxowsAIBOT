"""
Logger for print
"""

import logging
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")


logger = logging.getLogger("abdullaxows")
logger.setLevel(logging.DEBUG)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)

formatter = logging.Formatter(
    "[%(asctime)s] [%(levelname)s] %(name)s: %(message)s", "%H:%M:%S"
)
console_handler.setFormatter(formatter)

if not logger.hasHandlers():
    logger.addHandler(console_handler)
