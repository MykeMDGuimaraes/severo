import os
import requests
from langchain_core.tools import tool


def _headers() -> dict:
    return {
        "token": os.getenv("UAZAPI_TOKEN", ""),
        "Content-Type": "application/json",
    }


def _url(path: str) -> str:
    base = os.getenv("UAZAPI_URL", "").rstrip("/")
    return f"{base}{path}"


@tool
def criar_instancia_whatsapp(nome_clinica: str) -> dict:
    """
    Cria uma nova instância na UazAPI para a clínica do lead e solicita
    um pair code (código de 8 dígitos) para ser digitado no WhatsApp Business.
    Retorna o token/código a ser enviado ao lead.
    """
    instance_name = nome_clinica.lower().replace(" ", "_").replace("-", "_")

    # 1. Verificar se instância já existe e deletar para recriar limpa
    try:
        requests.delete(_url(f"/instance/delete/{instance_name}"), headers=_headers(), timeout=10)
    except Exception:
        pass

    # 2. Criar a instância
    payload_create = {
        "instanceName": instance_name,
        "token": instance_name,
        "number": "",
        "webhook": os.getenv("UAZAPI_WEBHOOK_URL", ""),
        "webhookByEvents": True,
        "events": ["MESSAGES_UPSERT", "CONNECTION_UPDATE"],
    }
    resp_create = requests.post(
        _url("/instance/create"),
        json=payload_create,
        headers=_headers(),
        timeout=15,
    )
    data_create = resp_create.json()

    # 3. Solicitar pair code
    resp_pair = requests.post(
        _url(f"/instance/pairCode/{instance_name}"),
        json={"phoneNumber": ""},
        headers=_headers(),
        timeout=15,
    )
    data_pair = resp_pair.json()
    pair_code = data_pair.get("pairCode") or data_pair.get("code", "ERRO_AO_GERAR")

    return {
        "token": pair_code,
        "instance_name": instance_name,
        "status": data_create.get("status", "created"),
    }


@tool
def verificar_conexao_whatsapp(instance_name: str) -> dict:
    """
    Verifica se o WhatsApp Business da clínica está conectado com sucesso.
    Estado 'open' significa conectado. Use após o lead digitar o token.
    """
    resp = requests.get(
        _url(f"/instance/connectionState/{instance_name}"),
        headers=_headers(),
        timeout=10,
    )
    data = resp.json()
    estado = data.get("instance", {}).get("state", "close")

    return {
        "conectado": estado == "open",
        "estado": estado,
        "instance_name": instance_name,
    }


def enviar_mensagem(numero: str, texto: str) -> bool:
    """Envia mensagem de texto via UazAPI pela instância principal do Argos."""
    instance = os.getenv("UAZAPI_INSTANCE", "argos")
    payload = {
        "number": numero,
        "text": texto,
        "delay": 1200,
        "linkPreview": False,
    }
    try:
        resp = requests.post(
            _url(f"/message/sendText/{instance}"),
            json=payload,
            headers=_headers(),
            timeout=15,
        )
        return resp.status_code == 200
    except Exception as e:
        print(f"[ARGOS] Erro ao enviar mensagem para {numero}: {e}")
        return False


def deletar_instancia(instance_name: str) -> bool:
    """Remove instância de clínica após entrega do relatório."""
    try:
        resp = requests.delete(
            _url(f"/instance/delete/{instance_name}"),
            headers=_headers(),
            timeout=10,
        )
        return resp.status_code == 200
    except Exception:
        return False
