import os
import pytest


@pytest.fixture(autouse=True)
def test_env(monkeypatch):
    """
    Define variáveis de ambiente para todos os testes.
    monkeypatch garante limpeza automática após cada teste.
    """
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    monkeypatch.setenv("UAZAPI_URL", "https://test.uazapi.com")
    monkeypatch.setenv("UAZAPI_TOKEN", "test-token")
    monkeypatch.setenv("UAZAPI_INSTANCE", "test")
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_xxx")
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_test")
    monkeypatch.setenv("SUCCESS_URL", "https://test.com/obrigado")
    monkeypatch.setenv("CANCEL_URL", "https://test.com/")
    monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "eyJ.test")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:test")
    monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", "test-secret")
    monkeypatch.setenv("BASE_URL", "https://test.com")
    monkeypatch.setenv("WEBHOOK_SECRET", "test-webhook-secret")
    monkeypatch.setenv("INTERNAL_JIDS", "5531991258669,5511999999999")
