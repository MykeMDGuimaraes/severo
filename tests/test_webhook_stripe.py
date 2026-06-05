import pytest
from unittest.mock import patch, MagicMock


def _make_stripe_event(numero="5511999", canal="whatsapp", nome_lead="João"):
    return {
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "metadata": {
                    "numero": numero,
                    "canal": canal,
                    "nome_lead": nome_lead,
                    "nome_clinica": "Clínica Teste",
                }
            }
        }
    }


def test_webhook_atualiza_sessao_por_numero(monkeypatch):
    """Deve usar numero+canal dos metadados para encontrar e atualizar a sessão."""
    estado_mock = {
        "fase": "gerar_link_pagamento",
        "pagamento_confirmado": False,
        "messages": [],
        "nome_lead": "João",
        "nome_clinica": "Clínica Teste",
        "numero": "5511999",
        "canal_origem": "whatsapp",
        "sistema_operacional": None,
        "token_gerado": None,
        "conexao_estabelecida": False,
        "link_pagamento": None,
        "usa_whatsapp": None,
        "lead_qualificado": None,
        "objecao_ativa": None,
    }

    store_get = MagicMock(return_value=estado_mock)
    store_set = MagicMock()

    monkeypatch.setattr("webhook_stripe.store.get", store_get)
    monkeypatch.setattr("webhook_stripe.store.set", store_set)

    from webhook_stripe import processar_pagamento_confirmado
    processar_pagamento_confirmado("5511999", "whatsapp")

    store_set.assert_called_once()
    args = store_set.call_args
    assert args[0][0] == "5511999"   # numero
    assert args[0][2] == "whatsapp"  # canal
    assert args[0][1]["pagamento_confirmado"] is True
    assert args[0][1]["fase"] == "confirmacao_pagamento"


def test_webhook_nao_atualiza_quando_sessao_nao_existe(monkeypatch):
    """Não deve falhar quando numero não existe em sessoes."""
    monkeypatch.setattr("webhook_stripe.store.get", MagicMock(return_value=None))
    store_set = MagicMock()
    monkeypatch.setattr("webhook_stripe.store.set", store_set)

    from webhook_stripe import processar_pagamento_confirmado
    processar_pagamento_confirmado("9999999", "whatsapp")

    store_set.assert_not_called()
