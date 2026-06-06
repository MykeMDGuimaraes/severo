from unittest.mock import patch, MagicMock


def test_escalar_envia_para_numero_de_escalacao(monkeypatch):
    monkeypatch.setenv("ESCALATION_NUMBER", "5531999000111")
    monkeypatch.setenv("UAZAPI_URL", "https://test.uazapi.com")
    monkeypatch.setenv("UAZAPI_TOKEN", "tok")
    monkeypatch.setenv("UAZAPI_INSTANCE", "severo")
    from tools.escalacao import escalar_para_humano
    with patch("tools.escalacao.requests.post") as mock_post:
        mock_post.return_value = MagicMock(status_code=200)
        out = escalar_para_humano.invoke({
            "motivo": "lead pediu humano",
            "resumo_conversa": "Maycon / MD Clinic quer falar com atendente",
        })
    enviado = mock_post.call_args.kwargs["json"]
    assert enviado["number"] == "5531999000111"
    assert "lead pediu humano" in enviado["text"]
    assert "MD Clinic" in enviado["text"]
    assert isinstance(out, str)


def test_escalar_usa_default_quando_env_ausente(monkeypatch):
    monkeypatch.delenv("ESCALATION_NUMBER", raising=False)
    monkeypatch.setenv("UAZAPI_URL", "https://test.uazapi.com")
    monkeypatch.setenv("UAZAPI_TOKEN", "tok")
    monkeypatch.setenv("UAZAPI_INSTANCE", "severo")
    from tools.escalacao import escalar_para_humano
    with patch("tools.escalacao.requests.post") as mock_post:
        mock_post.return_value = MagicMock(status_code=200)
        escalar_para_humano.invoke({"motivo": "reclamação", "resumo_conversa": "x"})
    assert mock_post.call_args.kwargs["json"]["number"] == "5531991258669"
