"""Alembic-backed schema application.

Runtime schema ownership lives here: the application applies Alembic
migrations rather than calling SQLModel.metadata.create_all().
"""

from pathlib import Path

from sqlalchemy.engine import Engine

from app.core.logging import logger


def alembic_ini_path() -> Path:
    """Return the backend Alembic config path."""
    return Path(__file__).resolve().parents[2] / "alembic.ini"


def apply_schema(engine: Engine) -> None:
    """Upgrade the given engine's database to the current Alembic head."""
    from alembic import command
    from alembic.config import Config

    ini = alembic_ini_path()
    if not ini.exists():
        raise FileNotFoundError(f"Alembic config not found: {ini}")

    cfg = Config(str(ini))
    sqlalchemy_url = engine.url.render_as_string(hide_password=False)
    cfg.set_main_option("sqlalchemy.url", sqlalchemy_url)
    cfg.attributes["sqlalchemy_url"] = sqlalchemy_url
    logger.info(
        "Applying Alembic migrations to {}",
        engine.url.render_as_string(hide_password=True),
    )
    command.upgrade(cfg, "head")
