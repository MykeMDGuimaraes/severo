import os
import stripe
from langchain_core.tools import tool

stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")

SUCCESS_URL = os.getenv("SUCCESS_URL", "https://seudominio.com.br/obrigado")
CANCEL_URL = os.getenv("CANCEL_URL", "https://seudominio.com.br/")
PRECO_CENTAVOS = int(os.getenv("PRECO_CENTAVOS", "4990"))  # R$49,90


@tool
def gerar_link_pagamento(nome_lead: str, nome_clinica: str) -> dict:
    """
    Gera um link de pagamento Stripe para o Choque de Gestão.
    Aceita Pix e cartão. Retorna a URL de checkout para enviar ao lead.
    """
    stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")

    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[{
            "price_data": {
                "currency": "brl",
                "product_data": {
                    "name": "Choque de Gestão — Dia Solutions",
                    "description": f"Diagnóstico de atendimento WhatsApp — {nome_clinica}",
                },
                "unit_amount": PRECO_CENTAVOS,
            },
            "quantity": 1,
        }],
        mode="payment",
        success_url=SUCCESS_URL,
        cancel_url=CANCEL_URL,
        metadata={
            "nome_lead": nome_lead,
            "nome_clinica": nome_clinica,
            "produto": "choque_de_gestao",
        },
    )
    return {
        "url": session.url,
        "session_id": session.id,
        "valor": f"R${PRECO_CENTAVOS / 100:.2f}",
    }
