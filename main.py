"""
Argos — Entrypoint FastAPI
Recebe webhooks da UazAPI e processa com o grafo LangGraph.
"""

import logging
import os
from contextlib import asynccontextmanager
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, Request, HTTPException
from langchain_core.messages import HumanMessage, AIMessage

from graph import argos
from state import AgentState
from tools.whatsapp import enviar_mensagem
from webhook_stripe import router as stripe_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger("argos")


# ── Sessões em memória (substituir por Redis em produção) ──────────────────
sessoes: dict[str, AgentState] = {}


def _nova_sessao(canal_origem: str = "instagram") -> AgentState:
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
        canal_origem=canal_origem,
        usa_whatsapp=None,
        lead_qualificado=None,
        objecao_ativa=None,
    )


def _extrair_texto(msg_data: dict) -> str:
    """Extrai texto de diferentes tipos de mensagem UazAPI."""
    return (
        msg_data.get("conversation")
        or msg_data.get("extendedTextMessage", {}).get("text")
        or msg_data.get("imageMessage", {}).get("caption")
        or msg_data.get("videoMessage", {}).get("caption")
        or msg_data.get("buttonsResponseMessage", {}).get("selectedDisplayText")
        or msg_data.get("listResponseMessage", {}).get("title")
        or ""
    ).strip()


def _enviar_respostas(numero: str, estado_antes: AgentState, estado_depois: AgentState):
    """
    Extrai as mensagens adicionadas nesta invocação e envia via WhatsApp.
    Envia apenas AIMessages com conteúdo textual — ignora ToolMessages.
    """
    qtd_antes = len(estado_antes["messages"])
    novas = estado_depois["messages"][qtd_antes:]

    for msg in novas:
        if isinstance(msg, AIMessage) and msg.content:
            # content pode ser string ou lista de blocos
            texto = msg.content if isinstance(msg.content, str) else ""
            if not texto:
                for bloco in msg.content:
                    if isinstance(bloco, dict) and bloco.get("type") == "text":
                        texto = bloco.get("text", "")
                        break
            if texto:
                sucesso = enviar_mensagem(numero, texto)
                logger.info("[ARGOS→%s] %s | ok=%s", numero, texto[:60], sucesso)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🟢 Argos iniciado — aguardando mensagens...")
    yield
    logger.info("🔴 Argos encerrado.")


app = FastAPI(title="Argos — Dia Solutions", lifespan=lifespan)
app.include_router(stripe_router)


@app.post("/webhook/whatsapp")
async def receber_mensagem(request: Request):
    """
    Webhook principal — recebe eventos da UazAPI.
    Formato esperado: MESSAGES_UPSERT com data.key.remoteJid e data.message.
    """
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="JSON inválido")

    evento = body.get("event", "")

    # Ignorar eventos que não são mensagens recebidas
    if evento not in ("MESSAGES_UPSERT", "messages.upsert"):
        return {"status": "ignored", "event": evento}

    data = body.get("data", {})
    key = data.get("key", {})

    # Ignorar mensagens enviadas pelo próprio Argos
    if key.get("fromMe", False):
        return {"status": "ignored", "reason": "fromMe"}

    jid: str = key.get("remoteJid", "")
    numero = jid.replace("@s.whatsapp.net", "").replace("@g.us", "")

    if not numero:
        return {"status": "ignored", "reason": "no_number"}

    texto = _extrair_texto(data.get("message", {}))
    if not texto:
        return {"status": "ignored", "reason": "no_text"}

    logger.info("[%s→ARGOS] %s", numero, texto[:80])

    # Recuperar ou criar sessão
    if numero not in sessoes:
        sessoes[numero] = _nova_sessao()
        logger.info("[ARGOS] Nova sessão criada para %s", numero)

    estado_antes = dict(sessoes[numero])  # snapshot para diff de mensagens
    estado_antes["messages"] = list(estado_antes["messages"])

    # Adicionar mensagem do lead
    sessoes[numero]["messages"] = list(sessoes[numero]["messages"]) + [
        HumanMessage(content=texto)
    ]

    # Invocar o grafo
    try:
        novo_estado = argos.invoke(sessoes[numero])
    except Exception as e:
        logger.exception("[ARGOS] Erro ao invocar grafo para %s", numero)
        enviar_mensagem(
            numero,
            "Tive um problema técnico aqui. Pode repetir sua mensagem? 🙏"
        )
        return {"status": "error", "detail": str(e)}

    sessoes[numero] = novo_estado

    # Enviar respostas via WhatsApp
    _enviar_respostas(numero, estado_antes, novo_estado)

    return {"status": "ok", "fase": novo_estado.get("fase")}


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "sessoes_ativas": len(sessoes),
        "fases": {n: s["fase"] for n, s in sessoes.items()},
    }


@app.delete("/sessao/{numero}")
async def resetar_sessao(numero: str):
    """Reseta a sessão de um número (útil para testes)."""
    if numero in sessoes:
        del sessoes[numero]
    return {"status": "resetado", "numero": numero}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        reload=os.getenv("ENV", "production") == "development",
    )
