import pytest
from unittest.mock import patch, MagicMock


# ── WhatsApp ──────────────────────────────────────────────────────────────

def _wpp_body(texto="Olá", from_me=False, jid="5511999@s.whatsapp.net"):
    return {
        "event": "MESSAGES_UPSERT",
        "data": {
            "key": {"remoteJid": jid, "fromMe": from_me},
            "message": {"conversation": texto},
        },
    }


def test_whatsapp_parse_retorna_numero_e_texto():
    from channels.whatsapp import WhatsAppChannel
    canal = WhatsAppChannel()
    result = canal.parse_incoming(_wpp_body("Quero saber mais"))
    assert result == ("5511999", "Quero saber mais")


def test_whatsapp_parse_ignora_from_me():
    from channels.whatsapp import WhatsAppChannel
    canal = WhatsAppChannel()
    result = canal.parse_incoming(_wpp_body(from_me=True))
    assert result is None


def test_whatsapp_parse_ignora_evento_desconhecido():
    from channels.whatsapp import WhatsAppChannel
    canal = WhatsAppChannel()
    body = {"event": "CONNECTION_UPDATE", "data": {}}
    result = canal.parse_incoming(body)
    assert result is None


def test_whatsapp_parse_ignora_mensagem_sem_texto():
    from channels.whatsapp import WhatsAppChannel
    canal = WhatsAppChannel()
    body = {
        "event": "MESSAGES_UPSERT",
        "data": {
            "key": {"remoteJid": "5511999@s.whatsapp.net", "fromMe": False},
            "message": {},
        },
    }
    result = canal.parse_incoming(body)
    assert result is None


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
