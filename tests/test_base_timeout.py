import time
import pytest
from unittest.mock import MagicMock, patch


def test_execute_retorna_erro_em_timeout():
    """_execute deve retornar string de erro quando tool demora mais que TOOL_TIMEOUT."""
    import nodes.base as base

    def tool_lenta(*args, **kwargs):
        time.sleep(5)
        return "nunca chega aqui"

    mock_tool = MagicMock()
    mock_tool.invoke = tool_lenta

    with patch.dict(base._TOOL_FN, {"tool_lenta": mock_tool}):
        base.TOOL_TIMEOUT = 1
        result = base._execute("tool_lenta", {})

    assert "Timeout" in result or "timeout" in result or "não respondeu" in result


def test_execute_retorna_resultado_normal():
    """_execute deve retornar resultado da tool quando executa dentro do tempo."""
    import nodes.base as base

    mock_tool = MagicMock()
    mock_tool.invoke.return_value = {"url": "https://stripe.com/pay/xxx"}

    with patch.dict(base._TOOL_FN, {"gerar_link": mock_tool}):
        result = base._execute("gerar_link", {"nome": "João"})

    assert result == {"url": "https://stripe.com/pay/xxx"}


def test_execute_retorna_erro_em_excecao():
    """_execute deve retornar string de erro (não propagar exceção) quando tool falha."""
    import nodes.base as base

    mock_tool = MagicMock()
    mock_tool.invoke.side_effect = ConnectionError("UazAPI offline")

    with patch.dict(base._TOOL_FN, {"whatsapp_tool": mock_tool}):
        result = base._execute("whatsapp_tool", {})

    assert isinstance(result, str)
    assert "Erro" in result or "erro" in result
