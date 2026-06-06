"""
Canal Telegram via Bot API.
Usado para testes internos do funil — canal de produção é WhatsApp.
"""
import logging
import os

import requests

from .base import Channel, ParseResult

logger = logging.getLogger("severo")


class TelegramChannel(Channel):
    name = "telegram"

    def __init__(self) -> None:
        self._token = os.getenv("TELEGRAM_BOT_TOKEN", "")

    def _api(self, method: str) -> str:
        return f"https://api.telegram.org/bot{self._token}/{method}"

    def parse_incoming(self, body: dict) -> ParseResult:
        if "edited_message" in body:
            return ParseResult(action="ignore", reason="edited")

        message = body.get("message", {})
        if not message:
            return ParseResult(action="ignore", reason="no_message")

        chat_id = str(message.get("chat", {}).get("id", ""))
        if not chat_id:
            return ParseResult(action="ignore", reason="no_chat")

        message_id = str(message.get("message_id", ""))
        texto = message.get("text", "").strip()
        if not texto:
            return ParseResult(action="ignore", reason="no_text", message_id=message_id)

        return ParseResult(
            action="process", user_id=chat_id, text=texto, message_id=message_id
        )

    def send(self, chat_id: str, texto: str) -> bool:
        try:
            resp = requests.post(
                self._api("sendMessage"),
                json={"chat_id": chat_id, "text": texto},
                timeout=10,
            )
            return resp.status_code == 200
        except Exception as e:
            logger.error("[TELEGRAM] Erro ao enviar para %s: %s", chat_id, e)
            return False

    def setup_webhook(self, webhook_url: str, secret_token: str) -> bool:
        """
        Registra o webhook no Telegram. Chamado uma vez no startup.
        Telegram exige HTTPS na URL do webhook.
        """
        try:
            resp = requests.post(
                self._api("setWebhook"),
                json={"url": webhook_url, "secret_token": secret_token},
                timeout=10,
            )
            ok = resp.status_code == 200
            if not ok:
                logger.error("[TELEGRAM] Falha ao registrar webhook: %s", resp.text)
            return ok
        except Exception as e:
            logger.error("[TELEGRAM] Erro ao registrar webhook: %s", e)
            return False
