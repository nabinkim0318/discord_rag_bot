"""Tests that Weaviate client construction follows application settings."""

from unittest.mock import MagicMock, patch

from app.core.weaviate_client import (
    create_configured_weaviate_client,
    get_weaviate_client,
)


def test_create_configured_client_uses_settings_url_and_api_key():
    mock_weaviate = MagicMock()
    mock_weaviate.AuthApiKey.return_value = "auth-secret"
    mock_weaviate.Client.return_value = object()

    with (
        patch("app.core.weaviate_client.weaviate", mock_weaviate),
        patch("app.core.weaviate_client.settings") as mock_settings,
    ):
        mock_settings.WEAVIATE_URL = "http://configured-weaviate:8080"
        mock_settings.WEAVIATE_API_KEY = "configured-dev-key"
        create_configured_weaviate_client()

    mock_weaviate.AuthApiKey.assert_called_once_with(api_key="configured-dev-key")
    mock_weaviate.Client.assert_called_once_with(
        url="http://configured-weaviate:8080",
        auth_client_secret="auth-secret",
    )
    assert mock_weaviate.Client.call_args.kwargs["url"] != "http://weaviate:8080" or (
        mock_settings.WEAVIATE_URL == "http://weaviate:8080"
    )


def test_create_configured_client_omits_auth_when_api_key_absent():
    mock_weaviate = MagicMock()
    mock_weaviate.Client.return_value = object()

    with (
        patch("app.core.weaviate_client.weaviate", mock_weaviate),
        patch("app.core.weaviate_client.settings") as mock_settings,
    ):
        mock_settings.WEAVIATE_URL = "http://configured-weaviate:8080"
        mock_settings.WEAVIATE_API_KEY = None
        create_configured_weaviate_client()

    mock_weaviate.AuthApiKey.assert_not_called()
    mock_weaviate.Client.assert_called_once_with(
        url="http://configured-weaviate:8080",
        auth_client_secret=None,
    )


def test_get_weaviate_client_uses_configured_settings_not_hardcoded_host():
    mock_client = MagicMock()
    mock_client.is_ready.return_value = True

    with (
        patch(
            "app.core.weaviate_client.create_configured_weaviate_client",
            return_value=mock_client,
        ) as mock_create,
        patch("app.core.weaviate_client.settings") as mock_settings,
    ):
        mock_settings.WEAVIATE_CLASS_NAME = "KBChunk"
        mock_settings.WEAVIATE_URL = "http://configured-weaviate:8080"
        client = get_weaviate_client()

    mock_create.assert_called_once()
    assert client.client is mock_client
    assert client.health_check() is True
