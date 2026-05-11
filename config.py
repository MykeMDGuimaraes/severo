"""
Validação de variáveis de ambiente obrigatórias.
Deve ser chamado no topo de main.py antes de qualquer import de serviço.
"""
import os
import sys

REQUIRED_VARS = [
    "ANTHROPIC_API_KEY",
    "UAZAPI_URL",
    "UAZAPI_TOKEN",
    "UAZAPI_INSTANCE",
    "STRIPE_SECRET_KEY",
    "STRIPE_WEBHOOK_SECRET",
    "SUCCESS_URL",
    "CANCEL_URL",
    "SUPABASE_URL",
    "SUPABASE_SERVICE_KEY",
]


def validate() -> None:
    """
    Verifica que todas as variáveis obrigatórias estão definidas e não-vazias.
    Chama SystemExit(1) se alguma estiver ausente — impede o servidor de subir
    com configuração inválida.
    """
    missing = [v for v in REQUIRED_VARS if not os.getenv(v, "").strip()]
    if missing:
        print(
            f"[SEVERO] ERRO: variáveis obrigatórias ausentes: {', '.join(missing)}",
            file=sys.stderr,
        )
        raise SystemExit(1)
