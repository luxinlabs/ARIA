"""Configuration settings for ARIA system."""

import os
import sys

# OpenAI API Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

if not OPENAI_API_KEY:
    print("ERROR: OPENAI_API_KEY environment variable is not set!", file=sys.stderr)
    print("Please set OPENAI_API_KEY before starting the server.", file=sys.stderr)
    # Don't exit in production, just warn - let the error surface in API calls

# Model configuration
DEFAULT_MODEL = "gpt-4o-mini"
TEMPERATURE = 0.7
MAX_TOKENS = 1000
