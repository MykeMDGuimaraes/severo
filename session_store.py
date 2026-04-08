"""
Persistência de sessões do Argos via Supabase.
Interface pública: get / set / delete / cleanup_old
main.py usa apenas estas funções — agnóstico do backend.
"""
import os
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from supabase import create_client, Client

logger = logging.getLogger("argos")

_client: Optional[Client] = None
_TABLE = "argos_sessions"


def _get_client() -> Client:
    global _client
    if _client is None:
        url = os.getenv("SUPABASE_URL", "")
        key = os.getenv("SUPABASE_SERVICE_KEY", "")
        _client = create_client(url, key)
    return _client


def get(numero: str, canal: str = "whatsapp") -> Optional[dict]:
    """Carrega estado da sessão. Retorna None se não existir."""
    try:
        resp = (
            _get_client()
            .table(_TABLE)
            .select("state")
            .eq("numero", numero)
            .eq("canal", canal)
            .execute()
        )
        if resp.data:
            return resp.data[0]["state"]
        return None
    except Exception as e:
        logger.error("[STORE] Erro ao carregar sessão %s/%s: %s", canal, numero, e)
        return None


def set(numero: str, estado: dict, canal: str = "whatsapp") -> None:
    """Salva (cria ou atualiza) estado da sessão."""
    try:
        _get_client().table(_TABLE).upsert(
            {
                "numero": numero,
                "canal": canal,
                "state": estado,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        ).execute()
    except Exception as e:
        logger.error("[STORE] Erro ao salvar sessão %s/%s: %s", canal, numero, e)


def delete(numero: str, canal: str = "whatsapp") -> None:
    """Remove sessão (usado no endpoint DELETE /sessao/{canal}/{numero})."""
    try:
        (
            _get_client()
            .table(_TABLE)
            .delete()
            .eq("numero", numero)
            .eq("canal", canal)
            .execute()
        )
    except Exception as e:
        logger.error("[STORE] Erro ao deletar sessão %s/%s: %s", canal, numero, e)


def cleanup_old(days: int = 30) -> int:
    """
    Remove sessões sem atualização nos últimos `days` dias.
    Retorna a quantidade de sessões removidas.
    """
    try:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        resp = (
            _get_client()
            .table(_TABLE)
            .delete()
            .lt("updated_at", cutoff)
            .execute()
        )
        count = len(resp.data) if resp.data else 0
        logger.info("[STORE] cleanup_old: %d sessões removidas (cutoff=%s)", count, cutoff)
        return count
    except Exception as e:
        logger.error("[STORE] Erro no cleanup: %s", e)
        return 0
