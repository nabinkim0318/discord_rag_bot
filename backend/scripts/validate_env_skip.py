#!/usr/bin/env python3
"""
Environment variable validation script that skips validation during build
"""

import os
import sys


def main():
    """Skip validation during build time"""
    # Check if we're in build context (no environment variables set)
    if not os.getenv("OPENAI_API_KEY") and not os.getenv("WEAVIATE_URL"):
        print("⚠️  Skipping environment validation during build time")
        print("✅ Environment variables will be validated at runtime")
        sys.exit(0)

    # If environment variables are set, run normal validation
    from validate_env import main as validate_main

    validate_main()


if __name__ == "__main__":
    main()
