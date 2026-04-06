"""
Webhook Stripe — confirma pagamento e avança o lead para a fase 5.
Registrar em main.py via: app.include_router(stripe_router)
"""

import logging
import os
import stripe
from fastapi import APIRouter, Request, HTTPException

logger = logging.getLogger("argos.stripe")

router = APIRouter()


@router.post("/webhook/stripe")
async def stripe_webhook(request: Request):
    """
    Recebe eventos do Stripe.
    Quando checkout.session.completed → marca pagamento confirmado
    e avança o lead para confirmacao_pagamento.
    """
    # Import aqui para evitar circular (sessoes vive em main.py)
    from main import sessoes

    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")
    secret = os.getenv("STRIPE_WEBHOOK_SECRET", "")

    try:
        event = stripe.Webhook.construct_event(payload, sig, secret)
    except stripe.errors.SignatureVerificationError:
        logger.warning("[STRIPE] Assinatura inválida — rejeitado.")
        raise HTTPException(status_code=400, detail="Assinatura Stripe inválida")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        meta = session.get("metadata", {})
        nome_lead: str = meta.get("nome_lead", "")
        nome_clinica: str = meta.get("nome_clinica", "")

        logger.info("[STRIPE] Pagamento confirmado — lead=%s clinica=%s",
                    nome_lead, nome_clinica)

        # Encontrar sessão pelo nome do lead e avançar fase
        for numero, estado in sessoes.items():
            lead_match = (
                estado.get("nome_lead", "").lower() == nome_lead.lower()
                if nome_lead else False
            )
            if lead_match or estado.get("fase") == "gerar_link_pagamento":
                estado["pagamento_confirmado"] = True
                estado["fase"] = "confirmacao_pagamento"
                if nome_lead:
                    estado["nome_lead"] = nome_lead
                if nome_clinica:
                    estado["nome_clinica"] = nome_clinica
                logger.info("[STRIPE] Sessão %s avançada para confirmacao_pagamento", numero)
                break

    return {"status": "ok"}
