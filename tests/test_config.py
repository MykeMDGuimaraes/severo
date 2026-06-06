import os
import pytest
from unittest.mock import patch


def test_validate_passa_quando_todas_vars_presentes():
    """Não deve levantar exceção quando todas vars obrigatórias estão setadas."""
    import config
    # conftest.py já setou todas as vars — validate() deve passar sem erro
    config.validate()  # sem exceção = sucesso


def test_validate_falha_quando_var_ausente():
    """Deve chamar SystemExit quando uma var obrigatória está ausente."""
    import config
    with patch.dict(os.environ, {"ANTHROPIC_API_KEY": ""}, clear=False):
        with pytest.raises(SystemExit):
            config.validate()


def test_validate_lista_todas_vars_ausentes(capsys):
    """A mensagem de erro deve listar todas as vars faltando."""
    import config
    with patch.dict(os.environ, {
        "ANTHROPIC_API_KEY": "",
        "STRIPE_SECRET_KEY": "",
    }, clear=False):
        with pytest.raises(SystemExit):
            config.validate()
    captured = capsys.readouterr()
    assert "ANTHROPIC_API_KEY" in captured.err
    assert "STRIPE_SECRET_KEY" in captured.err


def test_validate_exige_webhook_secret(monkeypatch):
    import config
    monkeypatch.delenv("WEBHOOK_SECRET", raising=False)
    with pytest.raises(SystemExit):
        config.validate()


def test_validate_exige_internal_jids(monkeypatch):
    import config
    monkeypatch.setenv("WEBHOOK_SECRET", "x")
    monkeypatch.delenv("INTERNAL_JIDS", raising=False)
    with pytest.raises(SystemExit):
        config.validate()
