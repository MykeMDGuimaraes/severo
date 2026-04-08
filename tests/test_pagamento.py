import pytest
from unittest.mock import patch, MagicMock


def test_gerar_link_inclui_pix_nos_metodos():
    """O checkout Stripe deve incluir 'pix' como método de pagamento."""
    with patch("tools.pagamento.stripe") as mock_stripe:
        mock_session = MagicMock()
        mock_session.url = "https://checkout.stripe.com/pay/cs_test_xxx"
        mock_stripe.checkout.Session.create.return_value = mock_session

        from tools.pagamento import gerar_link_pagamento
        result = gerar_link_pagamento.invoke({
            "nome_lead": "João",
            "nome_clinica": "Clínica Saúde",
            "numero": "5511999999999",
            "canal": "whatsapp",
        })

    call_kwargs = mock_stripe.checkout.Session.create.call_args[1]
    assert "pix" in call_kwargs["payment_method_types"]
    assert "card" in call_kwargs["payment_method_types"]


def test_gerar_link_inclui_numero_nos_metadados():
    """Os metadados do checkout devem incluir numero e canal para lookup no webhook."""
    with patch("tools.pagamento.stripe") as mock_stripe:
        mock_session = MagicMock()
        mock_session.url = "https://checkout.stripe.com/pay/cs_test_xxx"
        mock_stripe.checkout.Session.create.return_value = mock_session

        from tools.pagamento import gerar_link_pagamento
        gerar_link_pagamento.invoke({
            "nome_lead": "Maria",
            "nome_clinica": "Clínica Bem Estar",
            "numero": "5521888888888",
            "canal": "telegram",
        })

    call_kwargs = mock_stripe.checkout.Session.create.call_args[1]
    assert call_kwargs["metadata"]["numero"] == "5521888888888"
    assert call_kwargs["metadata"]["canal"] == "telegram"
    assert call_kwargs["metadata"]["nome_lead"] == "Maria"


def test_gerar_link_retorna_url():
    """Deve retornar dict com chave 'url' apontando para o link de pagamento."""
    with patch("tools.pagamento.stripe") as mock_stripe:
        mock_session = MagicMock()
        mock_session.url = "https://checkout.stripe.com/pay/cs_test_abc"
        mock_stripe.checkout.Session.create.return_value = mock_session

        from tools.pagamento import gerar_link_pagamento
        result = gerar_link_pagamento.invoke({
            "nome_lead": "Ana",
            "nome_clinica": "Clínica Ana",
            "numero": "5511777777777",
            "canal": "whatsapp",
        })

    assert result["url"] == "https://checkout.stripe.com/pay/cs_test_abc"
