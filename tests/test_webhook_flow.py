import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("WEBHOOK_SECRET", "s3cr3t")
    monkeypatch.setenv("INTERNAL_JIDS", "5531991258669")
    monkeypatch.setenv("ADMIN_SECRET", "")
    import importlib
    import main
    importlib.reload(main)
    return TestClient(main.app)


def _wpp(texto="oi", jid="5511888@s.whatsapp.net", msg_id="M1"):
    return {
        "event": "MESSAGES_UPSERT",
        "data": {"key": {"remoteJid": jid, "fromMe": False, "id": msg_id},
                 "message": {"conversation": texto}},
    }


def test_rota_sem_secret_da_404(client):
    r = client.post("/webhook/whatsapp", json=_wpp())
    assert r.status_code == 404


def test_rota_secret_errado_da_404(client):
    r = client.post("/webhook/whatsapp/errado", json=_wpp())
    assert r.status_code == 404


def test_grupo_e_ignorado(client):
    with patch("main.severo.invoke") as inv:
        r = client.post("/webhook/whatsapp/s3cr3t", json=_wpp(jid="12-9@g.us"))
    assert r.json()["status"] == "ignored"
    assert r.json()["reason"] == "group"
    inv.assert_not_called()


def test_interno_e_ignorado(client):
    with patch("main.severo.invoke") as inv:
        r = client.post("/webhook/whatsapp/s3cr3t",
                        json=_wpp(jid="5531991258669@s.whatsapp.net"))
    assert r.json()["status"] == "ignored"
    assert r.json()["reason"] == "internal"
    inv.assert_not_called()


def test_dedup_segunda_chamada(client):
    with patch("main.severo.invoke") as inv, \
         patch("main.store.get", return_value=None), \
         patch("main.store.set"), \
         patch("main.CANAIS") as canais:
        canal = MagicMock()
        from channels.base import ParseResult
        canal.parse_incoming.return_value = ParseResult(
            action="process", user_id="5511888", text="oi", message_id="DUP1")
        canal.send.return_value = True
        canal.name = "whatsapp"
        canais.get.return_value = canal
        inv.return_value = {"messages": [], "fase": "qualificacao_lead"}
        r1 = client.post("/webhook/whatsapp/s3cr3t", json=_wpp(msg_id="DUP1"))
        r2 = client.post("/webhook/whatsapp/s3cr3t", json=_wpp(msg_id="DUP1"))
    assert r2.json()["status"] == "duplicate"


def test_midia_responde_fixo_sem_modelo(client):
    with patch("main.severo.invoke") as inv, patch("main.CANAIS") as canais:
        canal = MagicMock()
        from channels.base import ParseResult
        canal.parse_incoming.return_value = ParseResult(
            action="media_fallback", user_id="5511888", message_id="AUD9")
        canal.name = "whatsapp"
        canais.get.return_value = canal
        r = client.post("/webhook/whatsapp/s3cr3t", json=_wpp())
    assert r.json()["status"] == "media_fallback"
    inv.assert_not_called()
    canal.send.assert_called_once()
    assert "só leio texto" in canal.send.call_args.args[1]


def test_delete_sessao_sem_admin_secret_da_404(client):
    r = client.delete("/sessao/whatsapp/5511888")
    assert r.status_code == 404
