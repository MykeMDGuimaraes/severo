"""
Integração com Stripe para geração de links de pagamento.
"""
import os
import stripe
from langchain_core.tools import tool

stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")

SUCCESS_URL    = os.getenv("SUCCESS_URL", "")
CANCEL_URL     = os.getenv("CANCEL_URL", "")
PRECO_CENTAVOS = int(os.getenv("PRECO_CENTAVOS", "4990"))


@tool
def gerar_link_pagamento(
    nome_lead: str,
    nome_clinica: str,
    numero: str = "",
    canal: str = "whatsapp",
) -> dict:
    """
    Gera um link de checkout Stripe para o produto Choque de Gestão.
    Aceita cartão de crédito/débito e Pix.
    Inclui numero e canal nos metadados para lookup correto no webhook do Stripe.
    Retorna {'url': str} com o link de pagamento.
    """
    stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")
    session = stripe.checkout.Session.create(
        payment_method_types=["card", "pix"],
        line_items=[
            {
                "price_data": {
                    "currency": "brl",
                    "product_data": {"name": "Choque de Gestão — Dia Solutions"},
                    "unit_amount": PRECO_CENTAVOS,
                },
                "quantity": 1,
            }
        ],
        mode="payment",
        success_url=SUCCESS_URL,
        cancel_url=CANCEL_URL,
        metadata={
            "nome_lead": nome_lead,
            "nome_clinica": nome_clinica,
            "numero": numero,
            "canal": canal,
        },
    )
    return {"url": session.url}
