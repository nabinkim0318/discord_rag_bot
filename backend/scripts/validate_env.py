#!/usr/bin/env python3
"""
Environment variable validation script for Docker containers
"""

import os
import sys
from typing import List


class EnvValidator:
    """Environment variable validator"""

    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def validate_required(self, var_name: str, description: str = None) -> bool:
        """Validate that a required environment variable is set"""
        value = os.getenv(var_name)
        if not value:
            error_msg = f"Required environment variable '{var_name}' is not set"
            if description:
                error_msg += f" ({description})"
            self.errors.append(error_msg)
            return False
        return True

    def validate_optional(
        self, var_name: str, default_value: str = None, description: str = None
    ) -> str:
        """Validate optional environment variable and return value or default"""
        value = os.getenv(var_name, default_value)
        if not value and description:
            self.warnings.append(
                f"Optional environment variable '{var_name}' not set ({description})"
            )
        return value

    def validate_url(self, var_name: str, required: bool = True) -> bool:
        """Validate URL format"""
        value = os.getenv(var_name)
        if not value:
            if required:
                self.errors.append(
                    f"Required URL environment variable '{var_name}' is not set"
                )
            return False

        if not (value.startswith("http://") or value.startswith("https://")):
            self.errors.append(f"Invalid URL format for '{var_name}': {value}")
            return False

        return True

    def validate_port(self, var_name: str, required: bool = True) -> bool:
        """Validate port number"""
        value = os.getenv(var_name)
        if not value:
            if required:
                self.errors.append(
                    f"Required port environment variable '{var_name}' is not set"
                )
            return False

        try:
            port = int(value)
            if not (1 <= port <= 65535):
                self.errors.append(
                    f"Invalid port number for '{var_name}': {port} (must be 1-65535)"
                )
                return False
        except ValueError:
            self.errors.append(
                f"Invalid port format for '{var_name}': {value} (must be integer)"
            )
            return False

        return True

    def validate_boolean(self, var_name: str, default_value: bool = False) -> bool:
        """Validate boolean environment variable"""
        value = os.getenv(var_name)
        if not value:
            return default_value

        return value.lower() in ("true", "1", "yes", "on", "enabled")

    def print_results(self) -> bool:
        """Print validation results and return success status"""
        if self.warnings:
            print("⚠️  Warnings:")
            for warning in self.warnings:
                print(f"   {warning}")
            print()

        if self.errors:
            print("❌ Errors:")
            for error in self.errors:
                print(f"   {error}")
            print()
            return False

        print("✅ All environment variables validated successfully!")
        return True


def validate_backend_env() -> bool:
    """Validate backend environment variables"""
    print("🔍 Validating backend environment variables...")
    validator = EnvValidator()

    # Required variables
    validator.validate_required("OPENAI_API_KEY", "OpenAI API key for LLM access")
    validator.validate_required("WEAVIATE_URL", "Weaviate vector database URL")

    # Optional variables with defaults
    validator.validate_optional(
        "DATABASE_URL", "sqlite:///./data/app.db", "Database connection string"
    )
    validator.validate_optional("LOG_LEVEL", "INFO", "Logging level")
    validator.validate_optional("ENVIRONMENT", "development", "Application environment")

    # URL validations
    validator.validate_url("WEAVIATE_URL", required=True)
    validator.validate_url("FRONTEND_URL", required=False)

    # Port validations
    validator.validate_port("API_PORT", required=False)
    validator.validate_port("WEAVIATE_PORT", required=False)

    # Boolean validations
    debug_mode = validator.validate_boolean("DEBUG", default_value=False)
    if debug_mode:
        validator.warnings.append(
            "DEBUG mode is enabled - not recommended for production"
        )

    return validator.print_results()


def validate_bot_env() -> bool:
    """Validate Discord bot environment variables"""
    print("🤖 Validating Discord bot environment variables...")
    validator = EnvValidator()

    # Required variables
    validator.validate_required("DISCORD_TOKEN", "Discord bot token")
    validator.validate_required("DISCORD_GUILD_ID", "Discord server ID")

    # Optional variables
    validator.validate_optional("BOT_PREFIX", "!", "Command prefix")
    validator.validate_optional("BOT_ACTIVITY", "RAG Assistant", "Bot activity status")

    # URL validations
    validator.validate_url("API_URL", required=False)

    # Boolean validations
    auto_sync = validator.validate_boolean("AUTO_SYNC_COMMANDS", default_value=True)
    if not auto_sync:
        validator.warnings.append(
            "Auto-sync commands is disabled - commands may not update"
        )

    return validator.print_results()


def validate_monitoring_env() -> bool:
    """Validate monitoring environment variables"""
    print("📊 Validating monitoring environment variables...")
    validator = EnvValidator()

    # Optional monitoring variables
    validator.validate_optional("PROMETHEUS_PORT", "9090", "Prometheus server port")
    validator.validate_optional("GRAFANA_PORT", "3001", "Grafana server port")

    # Port validations
    validator.validate_port("PROMETHEUS_PORT", required=False)
    validator.validate_port("GRAFANA_PORT", required=False)

    # Boolean validations
    enable_metrics = validator.validate_boolean("ENABLE_METRICS", default_value=True)
    if not enable_metrics:
        validator.warnings.append("Metrics collection is disabled")

    return validator.print_results()


def main():
    """Main validation function"""
    print("🚀 Environment Variable Validation")
    print("=" * 50)

    # Determine which services to validate based on environment
    validate_services = []

    # Check if we're in a specific service context
    service_context = os.getenv("SERVICE_CONTEXT", "all")

    if service_context in ["all", "backend", "api"]:
        validate_services.append(validate_backend_env)

    if service_context in ["all", "bot", "discord"]:
        validate_services.append(validate_bot_env)

    if service_context in ["all", "monitoring"]:
        validate_services.append(validate_monitoring_env)

    # If no specific context, validate all
    if not validate_services:
        validate_services = [
            validate_backend_env,
            validate_bot_env,
            validate_monitoring_env,
        ]

    # Run validations
    all_passed = True
    for validation_func in validate_services:
        print()
        if not validation_func():
            all_passed = False

    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 All validations passed!")
        sys.exit(0)
    else:
        print("💥 Validation failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
