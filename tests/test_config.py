from app.config import settings


def test_settings_carga_desde_env():
    assert settings.secret_key
    assert settings.database_url.startswith("sqlite")
    assert settings.access_token_expire_minutes > 0
