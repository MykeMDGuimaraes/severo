"""
Severo — Entrypoint FastAPI
Recebe webhooks de qualquer canal registrado e processa com o grafo LangGraph.
"""
import logging
import os
import time
from collections import defaultdict
from contextlib import asynccontextmanager

from dotenv import load_dotenv

load_dotenv()

# Validação de env vars — falha ruidosamente se config incompleta
import config
config.validate()

from fastapi import FastAPI, Request, HTTPException
from langchain_core.messages import HumanMessage, AIMessage

from graph import severo
from state import AgentState
import session_store as store
from dedup import DedupCache
from channels import WhatsAppChannel, TelegramChannel
from webhook_stripe import router as stripe_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger("severo")

# ── Rate limiting ──────────────────────────────────────────────────────────
_call_timestamps: dict[str, list[float]] = defaultdict(list)
_MAX_POR_MINUTO = int(os.getenv("MAX_CALLS_POR_MINUTO", "5"))
_MAX_POR_HORA   = int(os.getenv("MAX_CALLS_POR_HORA", "20"))
_MAX_MSG_LEN    = int(os.getenv("MAX_MSG_LEN", "4000"))


def _permitir_chamada(chave: str) -> bool:
    agora = time.monotonic()
    _call_timestamps[chave] = [t for t in _call_timestamps[chave] if agora - t < 3600]
    por_minuto = sum(1 for t in _call_timestamps[chave] if agora - t < 60)
    por_hora   = len(_call_timestamps[chave])
    if por_minuto >= _MAX_POR_MINUTO or por_hora >= _MAX_POR_HORA:
        return False
    _call_timestamps[chave].append(agora)
    return True


def _nova_sessao(canal: str = "whatsapp", numero: str = "") -> AgentState:
    return AgentState(
        messages=[],
        fase="qualificacao_lead",
        nome_lead=None,
        nome_clinica=None,
        sistema_operacional=None,
        pagamento_confirmado=False,
        token_gerado=None,
        conexao_estabelecida=False,
        link_pagamento=None,
        canal_origem=canal,
        usa_whatsapp=None,
        lead_qualificado=None,
        objecao_ativa=None,
        numero=numero,
    )


# ── Canais registrados ─────────────────────────────────────────────────────
CANAIS = {
    "whatsapp": WhatsAppChannel(),
    "telegram": TelegramChannel(),
}

_dedup = DedupCache(ttl_seconds=600)
_WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "")
_MEDIA_FALLBACK_MSG = "Recebi! Por aqui ainda só leio texto 🙂 Pode me escrever?"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Registrar webhook do Telegram no startup
    tg_token  = os.getenv("TELEGRAM_BOT_TOKEN", "")
    tg_secret = os.getenv("TELEGRAM_WEBHOOK_SECRET", "")
    base_url  = os.getenv("BASE_URL", "")

    if tg_token and base_url:
        canal_tg = CANAIS["telegram"]
        wh_url = f"{base_url.rstrip('/')}/webhook/telegram/{os.getenv('WEBHOOK_SECRET','')}"
        ok = canal_tg.setup_webhook(wh_url, tg_secret)
        logger.info("🤖 Telegram webhook registrado: %s → %s", wh_url, "OK" if ok else "ERRO")
    else:
        logger.warning("⚠️  Telegram não configurado (TELEGRAM_BOT_TOKEN ou BASE_URL ausente)")

    # Limpeza de sessões antigas
    deleted = store.cleanup_old(days=30)
    logger.info("🧹 Cleanup: %d sessões antigas removidas", deleted)

    logger.info("🟢 Severo iniciado — canais: %s", list(CANAIS.keys()))
    yield
    logger.info("🔴 Severo encerrado.")


app = FastAPI(title="Severo — Dia Solutions", lifespan=lifespan)
app.include_router(stripe_router)


def _enviar_respostas(canal, numero: str, estado_antes: dict, estado_depois: dict):
    """Extrai mensagens novas do estado e envia via canal."""
    qtd_antes = len(estado_antes["messages"])
    novas = estado_depois["messages"][qtd_antes:]

    for msg in novas:
        if isinstance(msg, AIMessage) and msg.content:
            texto = msg.content if isinstance(msg.content, str) else ""
            if not texto:
                for bloco in msg.content:
                    if isinstance(bloco, dict) and bloco.get("type") == "text":
                        texto = bloco.get("text", "")
                        break
            if texto:
                ok = canal.send(numero, texto)
                logger.info(
                    "[SEVERO→%s/%s] fase=%s msg=%s… ok=%s",
                    canal.name, numero[:6],
                    estado_depois.get("fase", "?"),
                    texto[:50], ok,
                )


@app.post("/webhook/{canal_nome}/{webhook_secret}")
async def receber_mensagem(canal_nome: str, webhook_secret: str, request: Request):
    """
    Webhook unificado com path secreto.
    Rotas válidas: POST /webhook/whatsapp/<WEBHOOK_SECRET> ou /webhook/telegram/<WEBHOOK_SECRET>.
    Secret inválido → 404 (não confirma a existência da rota).
    """
    if not _WEBHOOK_SECRET or webhook_secret != _WEBHOOK_SECRET:
        raise HTTPException(status_code=404, detail="Not Found")

    canal = CANAIS.get(canal_nome)
    if not canal:
        raise HTTPException(status_code=404, detail="Not Found")

    if canal_nome == "telegram":
        secret_recebido = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
        secret_esperado = os.getenv("TELEGRAM_WEBHOOK_SECRET", "")
        if secret_esperado and secret_recebido != secret_esperado:
            raise HTTPException(status_code=403, detail="Token inválido")

    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="JSON inválido")

    parsed = canal.parse_incoming(body)

    if parsed.action == "ignore":
        logger.info("[%s] drop reason=%s num=%s",
                    canal_nome, parsed.reason, parsed.user_id[:6])
        return {"status": "ignored", "reason": parsed.reason}

    if _dedup.is_duplicate(parsed.message_id):
        logger.info("[%s] duplicate msg_id=%s", canal_nome, parsed.message_id)
        return {"status": "duplicate"}

    if parsed.action == "media_fallback":
        canal.send(parsed.user_id, _MEDIA_FALLBACK_MSG)
        logger.info("[%s/%s] media_fallback respondido", canal_nome, parsed.user_id[:6])
        return {"status": "media_fallback"}

    numero = parsed.user_id
    texto = parsed.text

    if len(texto) > _MAX_MSG_LEN:
        logger.warning("[%s/%s] Mensagem truncada: %d chars", canal_nome, numero[:6], len(texto))
        texto = texto[:_MAX_MSG_LEN]

    chave = f"{canal_nome}:{numero}"
    if not _permitir_chamada(chave):
        logger.warning("[RATE LIMIT] %s bloqueado", chave)
        return {"status": "rate_limited"}

    logger.info("[%s/%s→SEVERO] %s", canal_nome, numero[:6], texto[:80])

    estado = store.get(numero, canal_nome)
    if estado is None:
        estado = _nova_sessao(canal_nome, numero)
        logger.info("[SEVERO] Nova sessão: %s/%s", canal_nome, numero[:6])
    else:
        estado["numero"] = numero

    estado_antes = {**estado, "messages": list(estado["messages"])}
    estado["messages"] = list(estado["messages"]) + [HumanMessage(content=texto)]

    try:
        novo_estado = severo.invoke(estado)
    except Exception as e:
        logger.exception("[SEVERO] Erro no grafo para %s/%s", canal_nome, numero)
        canal.send(numero, "Tive um problema técnico aqui. Pode repetir sua mensagem? 🙏")
        return {"status": "error", "detail": str(e)}

    store.set(numero, novo_estado, canal_nome)
    _enviar_respostas(canal, numero, estado_antes, novo_estado)

    logger.info("[SEVERO] %s/%s → fase=%s", canal_nome, numero[:6], novo_estado.get("fase"))
    return {"status": "ok", "fase": novo_estado.get("fase")}


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "canais": list(CANAIS.keys()),
    }


@app.delete("/sessao/{canal}/{numero}")
async def resetar_sessao(canal: str, numero: str, request: Request):
    """Reseta sessão. Fail-closed: sem ADMIN_SECRET configurado → 404."""
    admin_secret = os.getenv("ADMIN_SECRET", "")
    if not admin_secret:
        raise HTTPException(status_code=404, detail="Not Found")
    auth = request.headers.get("Authorization", "")
    if auth != f"Bearer {admin_secret}":
        raise HTTPException(status_code=401, detail="Não autorizado")
    store.delete(numero, canal)
    return {"status": "resetado", "canal": canal, "numero": numero}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        reload=os.getenv("ENV", "production") == "development",
    )
