"""
Webhook Stripe — recebe confirmação de pagamento e avança sessão do lead.
"""
import logging
import os

import stripe
from fastapi import APIRouter, Request, HTTPException

import session_store as store

logger = logging.getLogger("severo")
router = APIRouter()


def processar_pagamento_confirmado(numero: str, canal: str) -> None:
    """
    Atualiza a sessão do lead após pagamento confirmado.
    Busca por (numero, canal) — lookup O(1), sem ambiguidade por nome.
    """
    estado = store.get(numero, canal)
    if not estado:
        logger.warning(
            "[STRIPE] Sessão não encontrada para numero=%s canal=%s", numero, canal
        )
        return

    estado["pagamento_confirmado"] = True
    estado["fase"] = "confirmacao_pagamento"
    store.set(numero, estado, canal)
    logger.info(
        "[STRIPE] Pagamento confirmado — %s/%s avançou para confirmacao_pagamento",
        canal,
        numero,
    )


@router.post("/webhook/stripe")
async def webhook_stripe(request: Request):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")
    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET", "")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
    except stripe.errors.SignatureVerificationError:
        logger.warning("[STRIPE] Assinatura inválida no webhook")
        raise HTTPException(status_code=400, detail="Assinatura inválida")
    except Exception as e:
        logger.error("[STRIPE] Erro ao processar webhook: %s", e)
        raise HTTPException(status_code=400, detail=str(e))

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        meta = session.get("metadata", {})

        numero = meta.get("numero", "")
        canal = meta.get("canal", "whatsapp")
        nome_lead = meta.get("nome_lead", "")
        nome_clinica = meta.get("nome_clinica", "")

        logger.info(
            "[STRIPE] checkout.session.completed — lead=%s clinica=%s numero=%s canal=%s",
            nome_lead,
            nome_clinica,
            numero,
            canal,
        )

        if numero:
            processar_pagamento_confirmado(numero, canal)
        else:
            logger.warning("[STRIPE] Webhook sem numero nos metadados — pagamento não atribuído")

    return {"status": "ok"}
