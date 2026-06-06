import pytest
from unittest.mock import patch, MagicMock


# ── WhatsApp ──────────────────────────────────────────────────────────────

def _wpp_body(texto="Olá", from_me=False, jid="5511999@s.whatsapp.net", msg_id="MSG1", message=None):
    if message is None:
        message = {"conversation": texto}
    return {
        "event": "MESSAGES_UPSERT",
        "data": {
            "key": {"remoteJid": jid, "fromMe": from_me, "id": msg_id},
            "message": message,
        },
    }


def test_whatsapp_parse_process_normal():
    from channels.whatsapp import WhatsAppChannel
    canal = WhatsAppChannel()
    r = canal.parse_incoming(_wpp_body("Quero saber mais", msg_id="X1"))
    assert r.action == "process"
    assert r.user_id == "5511999"
    assert r.text == "Quero saber mais"
    assert r.message_id == "X1"


def test_whatsapp_parse_dropa_grupo_antes_do_strip():
    from channels.whatsapp import WhatsAppChannel
    canal = WhatsAppChannel()
    r = canal.parse_incoming(_wpp_body(jid="123456789-987@g.us"))
    assert r.action == "ignore"
    assert r.reason == "group"


def test_whatsapp_parse_dropa_numero_interno(monkeypatch):
    monkeypatch.setenv("INTERNAL_JIDS", "5531991258669,5511933006574")
    from channels.whatsapp import WhatsAppChannel
    canal = WhatsAppChannel()
    r = canal.parse_incoming(_wpp_body(jid="5531991258669@s.whatsapp.net"))
    assert r.action == "ignore"
    assert r.reason == "internal"


def test_whatsapp_parse_dropa_from_me():
    from channels.whatsapp import WhatsAppChannel
    canal = WhatsAppChannel()
    r = canal.parse_incoming(_wpp_body(from_me=True))
    assert r.action == "ignore"
    assert r.reason == "fromMe"


def test_whatsapp_parse_evento_desconhecido():
    from channels.whatsapp import WhatsAppChannel
    canal = WhatsAppChannel()
    r = canal.parse_incoming({"event": "CONNECTION_UPDATE", "data": {}})
    assert r.action == "ignore"
    assert r.reason == "unknown_event"


def test_whatsapp_parse_audio_sem_texto_vira_media_fallback():
    from channels.whatsapp import WhatsAppChannel
    canal = WhatsAppChannel()
    body = _wpp_body(message={"audioMessage": {"seconds": 5}}, msg_id="AUD1")
    r = canal.parse_incoming(body)
    assert r.action == "media_fallback"
    assert r.user_id == "5511999"
    assert r.message_id == "AUD1"


def test_whatsapp_parse_imagem_com_caption_processa():
    from channels.whatsapp import WhatsAppChannel
    canal = WhatsAppChannel()
    body = _wpp_body(message={"imageMessage": {"caption": "olha isso"}}, msg_id="IMG1")
    r = canal.parse_incoming(body)
    assert r.action == "process"
    assert r.text == "olha isso"


def test_whatsapp_send_retorna_true_em_sucesso():
    from channels.whatsapp import WhatsAppChannel
    canal = WhatsAppChannel()
    with patch("channels.whatsapp.requests.post") as mock_post:
        mock_post.return_value = MagicMock(status_code=200)
        result = canal.send("5511999", "Olá lead!")
    assert result is True


def test_whatsapp_send_retorna_false_em_erro():
    from channels.whatsapp import WhatsAppChannel
    canal = WhatsAppChannel()
    with patch("channels.whatsapp.requests.post") as mock_post:
        mock_post.side_effect = ConnectionError("timeout")
        result = canal.send("5511999", "Olá")
    assert result is False


# ── Telegram ──────────────────────────────────────────────────────────────

def _tg_body(texto="Olá", chat_id=123456789):
    return {
        "message": {
            "chat": {"id": chat_id},
            "text": texto,
        }
    }


def test_telegram_parse_retorna_chat_id_e_texto():
    from channels.telegram import TelegramChannel
    canal = TelegramChannel()
    result = canal.parse_incoming(_tg_body("Quero saber mais", chat_id=987654))
    assert result == ("987654", "Quero saber mais")


def test_telegram_parse_ignora_edited_message():
    from channels.telegram import TelegramChannel
    canal = TelegramChannel()
    body = {"edited_message": {"chat": {"id": 123}, "text": "editado"}}
    result = canal.parse_incoming(body)
    assert result is None


def test_telegram_parse_ignora_sem_texto():
    from channels.telegram import TelegramChannel
    canal = TelegramChannel()
    body = {"message": {"chat": {"id": 123}}}
    result = canal.parse_incoming(body)
    assert result is None


def test_telegram_send_retorna_true_em_sucesso():
    from channels.telegram import TelegramChannel
    canal = TelegramChannel()
    with patch("channels.telegram.requests.post") as mock_post:
        mock_post.return_value = MagicMock(status_code=200)
        result = canal.send("123456", "Olá lead!")
    assert result is True


def test_telegram_send_retorna_false_em_erro():
    from channels.telegram import TelegramChannel
    canal = TelegramChannel()
    with patch("channels.telegram.requests.post") as mock_post:
        mock_post.side_effect = ConnectionError("offline")
        result = canal.send("123456", "Olá")
    assert result is False
