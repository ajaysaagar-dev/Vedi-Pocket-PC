import os

# Server configuration
HOST = os.getenv("STREAM_HOST", "0.0.0.0")
PORT = int(os.getenv("STREAM_PORT", 8080))

# Capture settings
FPS = int(os.getenv("STREAM_FPS", 30))
JPEG_QUALITY = int(os.getenv("STREAM_JPEG_QUALITY", 50))
MAX_WIDTH = int(os.getenv("STREAM_MAX_WIDTH", 640))
MAX_HEIGHT = int(os.getenv("STREAM_MAX_HEIGHT", 360))
MONITOR_INDEX = int(os.getenv("STREAM_MONITOR_INDEX", 1))

# Mouse & Control settings
MOUSE_SENSITIVITY = float(os.getenv("STREAM_MOUSE_SENSITIVITY", 1.5))
SCROLL_SENSITIVITY = float(os.getenv("STREAM_SCROLL_SENSITIVITY", 1.0))
DEBUG_MOUSE = os.getenv("STREAM_DEBUG_MOUSE", "false").lower() in ("true", "1", "yes")

# Server Metadata
SERVER_NAME = "PC Screen Stream & Remote Server"
SERVER_VERSION = "1.0.0"
