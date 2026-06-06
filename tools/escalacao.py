"""
Tool de escalação para humano — notifica o time via WhatsApp (UAZAPI)
quando o lead precisa de atendimento humano.
"""
import os
import requests
from langchain_core.tools import tool

DEFAULT_ESCALATION = "5531991258669"


def _headers() -> dict:
    return {"apikey": os.getenv("UAZAPI_TOKEN", "")}


def _url(path: str) -> str:
    base = os.getenv("UAZAPI_URL", "").rstrip("/")
    return f"{base}{path}"


@tool
def escalar_para_humano(motivo: str, resumo_conversa: str) -> str:
    """
    Aciona um atendente humano do time quando o lead precisa de ajuda
    que vai além do fluxo automatizado. Use quando: o lead pede explicitamente
    para falar com uma pessoa, há uma reclamação séria, ou a mesma objeção
    persiste por 2 ou mais turnos sem progresso.

    motivo: por que está escalando (curto).
    resumo_conversa: resumo do contexto para o atendente assumir.
    """
    numero = os.getenv("ESCALATION_NUMBER", DEFAULT_ESCALATION)
    instance = os.getenv("UAZAPI_INSTANCE", "severo")
    texto = (
        "🔔 ESCALAÇÃO — Severó\n\n"
        f"Motivo: {motivo}\n\n"
        f"Resumo: {resumo_conversa}"
    )
    try:
        requests.post(
            _url(f"/message/sendText/{instance}"),
            headers=_headers(),
            json={"number": numero, "text": texto, "delay": 0},
            timeout=10,
        )
    except Exception:
        pass
    return (
        "Escalação registrada. Avise o lead, de forma acolhedora, que uma "
        "pessoa do time vai assumir a conversa em breve."
    )
