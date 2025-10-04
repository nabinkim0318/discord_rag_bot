#!/usr/bin/env python3
"""
Environment variables validation script
Checks if all required environment variables are set
"""

import os
import sys
from pathlib import Path
from typing import List, Tuple

from rag_agent.core.logging import logger

# Required environment variables
REQUIRED_VARS = {
    "DISCORD_BOT_TOKEN": "Discord bot token for authentication",
    "OPENAI_API_KEY": "OpenAI API key for LLM and embeddings",
    "DATABASE_URL": "Database connection URL",
    "SECRET_KEY": "Secret key for JWT token signing",
}

# Optional but recommended environment variables
RECOMMENDED_VARS = {
    "WEAVIATE_URL": "Weaviate vector database URL",
    "WEAVIATE_API_KEY": "Weaviate API key (if authentication enabled)",
    "LLM_MODEL": "LLM model name (default: gpt-4o-mini)",
    "PROMPT_TOKEN_BUDGET": "Token budget for prompts (default: 6000)",
    "GENERATION_MAX_TOKENS": "Maximum tokens for generation (default: 512)",
}

# Service-specific variables
SERVICE_VARS = {
    "discord": ["DISCORD_BOT_TOKEN", "DISCORD_GUILD_ID"],
    "backend": ["DATABASE_URL", "SECRET_KEY", "OPENAI_API_KEY"],
    "weaviate": ["WEAVIATE_URL"],
    "monitoring": ["METRICS_ENABLED"],
}


def check_env_file():
    """Check if .env file exists and is readable"""
    env_path = Path(".env")
    if not env_path.exists():
        ("❌ .env file not found")
        logger.warning("   Please copy env.template to .env and configure it")
        return False

    if not env_path.is_file():
        logger.warning("❌ .env is not a file")
        return False

    logger.info("✅ .env file found")
    return True


def check_required_vars() -> Tuple[bool, List[str]]:
    """Check if all required environment variables are set"""
    missing = []

    for var, description in REQUIRED_VARS.items():
        value = os.getenv(var)
        if not value or value.strip() == "":
            missing.append(f"{var}: {description}")
        elif "your-" in value.lower() or "change-this" in value.lower():
            missing.append(
                f"{var}: {description} (still has default/placeholder value)"
            )

    if missing:
        logger.warning("❌ Missing or invalid required environment variables:")
        for var in missing:
            logger.warning(f"   - {var}")
        return False, missing
    else:
        logger.info("✅ All required environment variables are set")
        return True, []


def check_recommended_vars() -> List[str]:
    """Check recommended environment variables"""
    missing = []

    for var, description in RECOMMENDED_VARS.items():
        value = os.getenv(var)
        if not value or value.strip() == "":
            missing.append(f"{var}: {description}")

    if missing:
        logger.warning("⚠️  Recommended environment variables not set:")
        for var in missing:
            logger.warning(f"   - {var}")
    else:
        logger.info("✅ All recommended environment variables are set")

    return missing


def check_service_vars(service: str) -> bool:
    """Check environment variables for a specific service"""
    if service not in SERVICE_VARS:
        logger.warning(f"❌ Unknown service: {service}")
        return False

    missing = []
    for var in SERVICE_VARS[service]:
        value = os.getenv(var)
        if not value or value.strip() == "":
            missing.append(var)

    if missing:
        logger.warning(
            f"❌ Missing variables for {service} service: {', '.join(missing)}"
        )
        return False
    else:
        logger.info(f"✅ All variables for {service} service are set")
        return True


def validate_values():
    """Validate environment variable values"""
    issues = []

    # Check SECRET_KEY strength
    secret_key = os.getenv("SECRET_KEY", "")
    if len(secret_key) < 32:
        issues.append("SECRET_KEY should be at least 32 characters long")

    if "your-secret-key" in secret_key.lower():
        issues.append("SECRET_KEY should be changed from default value")

    # Check DATABASE_URL format
    db_url = os.getenv("DATABASE_URL", "")
    if db_url and not (
        db_url.startswith("sqlite://") or db_url.startswith("postgresql://")
    ):
        issues.append("DATABASE_URL should start with 'sqlite://' or 'postgresql://'")

    # Check numeric values
    try:
        int(os.getenv("PROMPT_TOKEN_BUDGET", "6000"))
        int(os.getenv("GENERATION_MAX_TOKENS", "512"))
    except ValueError:
        issues.append("PROMPT_TOKEN_BUDGET and GENERATION_MAX_TOKENS should be numeric")

    if issues:
        logger.warning("⚠️  Environment variable validation issues:")
        for issue in issues:
            logger.warning(f"   - {issue}")
        return False
    else:
        logger.info("✅ Environment variable values are valid")
        return True


def main():
    """Main validation function"""
    logger.info("🔍 Checking environment variables...")
    logger.info()

    # Check .env file
    if not check_env_file():
        sys.exit(1)

    logger.info()

    # Check required variables
    required_ok, missing_required = check_required_vars()
    if not required_ok:
        logger.info()
        logger.warning("❌ Please set the missing required environment variables")
        sys.exit(1)

    logger.info()

    # Check recommended variables
    missing_recommended = check_recommended_vars()

    logger.info()

    # Validate values
    if not validate_values():
        logger.info()
        logger.warning("⚠️  Please fix the validation issues")
        sys.exit(1)

    logger.info()

    # Service-specific checks
    services = ["discord", "backend", "weaviate"]
    all_services_ok = True

    for service in services:
        if not check_service_vars(service):
            all_services_ok = False

    logger.info()

    if missing_recommended:
        logger.warning(
            "⚠️  Some recommended variables are missing, but the system should work"
        )
        logger.warning("   Consider setting them for optimal configuration")

    if all_services_ok:
        logger.info("🎉 All environment variables are properly configured!")
        sys.exit(0)
    else:
        logger.warning("❌ Some service configurations are incomplete")
        sys.exit(1)


if __name__ == "__main__":
    main()
