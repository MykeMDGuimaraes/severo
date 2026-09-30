# Severó — FASE 0: Hardening Pré-Go-Live Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Endurecer o Severó para go-live com tráfego real de WhatsApp (UAZAPI), filtrando grupos/equipe interna, blindando o webhook, deduplicando retries, adicionando escalação humana e resposta de mídia — sem tocar no funil de 7 fases, prompts de fase ou fluxo Stripe.

**Architecture:** O ponto central é trocar o contrato de `parse_incoming` de `tuple[str,str] | None` para um `ParseResult` estruturado (user_id, text, message_id, action, reason). Isso destrava os filtros com motivo (item 1), o dedup por messageId (item 3) e a resposta de mídia (item 7). Os demais itens (path secreto, fail-closed admin, escalação, .dockerignore, env vars) são localizados. Dedup é cache em memória (single replica no Swarm).

**Tech Stack:** Python 3.12, FastAPI, LangGraph, UAZAPI (WhatsApp), pytest. Sem dependências novas (sem Redis).

**Restrições globais:**
- NÃO mudar o funil de 7 fases, os prompts de fase nem o fluxo Stripe (exceto o mínimo do item 4 para registrar a tool de escalação).
- Nenhum secret hardcoded — tudo via `os.getenv`.
- `ANTHROPIC_MODEL=claude-haiku-4-5-20251001` permanece (decisão MD: Haiku por ora).

---

## Mapa de Arquivos

| Arquivo | Itens | O que muda |
|---|---|---|
| `config.py` | 8 | `WEBHOOK_SECRET`, `INTERNAL_JIDS` obrigatórias; `ESCALATION_NUMBER` opcional |
| `channels/base.py` | 1,3,7 | Novo `ParseResult` dataclass + nova assinatura de `parse_incoming` |
| `channels/whatsapp.py` | 1,3,7 | Drop `@g.us` antes do strip, filtro `INTERNAL_JIDS`, extrai `message_id`, sinaliza mídia |
| `channels/telegram.py` | 1,3 | Conforma ao `ParseResult` |
| `main.py` | 1,2,3,6,7 | Rota com secret, dedup cache, fail-closed admin, branch de mídia, HTTP reasons |
| `tools/escalacao.py` (novo) | 4 | `escalar_para_humano(motivo, resumo_conversa)` |
| `tools/__init__.py` | 4 | Registra a nova tool em `ALL_TOOLS` |
| `nodes/base.py` | 4 | Handler da tool `escalar_para_humano` |
| `prompts/fases.py` | 4 | Menção mínima de quando escalar (afirmação positiva) |
| `.dockerignore` (novo) | 5 | `.env`, `tests/`, `.git/`, `__pycache__/`, `*.pyc`, `docs/` |
| `tests/conftest.py` | 8 | Adicionar `WEBHOOK_SECRET`, `INTERNAL_JIDS` ao env de teste |
| `tests/test_*.py` | gate | Novos testes por item |

---

## ETAPA 1 — Backup (executar na VPS antes de tudo)

Roda no SSH da VPS. Não altera código — só snapshot.

```bash
mkdir -p /root/backups
cd /etc/easypanel/projects/n8n/severo/code
tar -czf /root/backups/severo_pre_fase0_$(date +%F_%H%M).tar.gz .
cp .env /root/backups/severo.env.bak_$(date +%F_%H%M)
docker service inspect n8n_severo > /root/backups/severo_service_spec_$(date +%F_%H%M).json
ls -la /root/backups/
```

Esperado: 3 arquivos novos em `/root/backups/` (tar.gz, .env.bak, .json).

---

## Task 1: Env vars novas em config.py (Item 8)

**Files:**
- Modify: `config.py:8-19`
- Modify: `tests/conftest.py:23`
- Test: `tests/test_config.py`

- [ ] **Step 1: Escrever teste falhando**

Adicionar em `tests/test_config.py`:

```python
def test_validate_exige_webhook_secret(monkeypatch):
    import config
    monkeypatch.delenv("WEBHOOK_SECRET", raising=False)
    with pytest.raises(SystemExit):
        config.validate()


def test_validate_exige_internal_jids(monkeypatch):
    import config
    monkeypatch.setenv("WEBHOOK_SECRET", "x")
    monkeypatch.delenv("INTERNAL_JIDS", raising=False)
    with pytest.raises(SystemExit):
        config.validate()
```

- [ ] **Step 2: Rodar e verificar que falha**

Run: `cd /c/Users/Dell/argos && python -m pytest tests/test_config.py -v`
Expected: FAIL (WEBHOOK_SECRET ainda não é obrigatória).

- [ ] **Step 3: Adicionar as vars obrigatórias**

Em `config.py`, adicionar ao `REQUIRED_VARS` (após `"SUPABASE_SERVICE_KEY",`):

```python
    "WEBHOOK_SECRET",
    "INTERNAL_JIDS",
```

- [ ] **Step 4: Atualizar conftest para os testes não quebrarem**

Em `tests/conftest.py`, adicionar antes da linha em branco final (linha 23):

```python
    monkeypatch.setenv("WEBHOOK_SECRET", "test-webhook-secret")
    monkeypatch.setenv("INTERNAL_JIDS", "5531991258669,5511999999999")
```

- [ ] **Step 5: Rodar testes**

Run: `cd /c/Users/Dell/argos && python -m pytest tests/test_config.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add config.py tests/conftest.py tests/test_config.py
git commit -m "feat(config): exigir WEBHOOK_SECRET e INTERNAL_JIDS no startup (item 8)"
```

---

## Task 2: ParseResult dataclass + nova interface Channel (fundação itens 1,3,7)

**Files:**
- Modify: `channels/base.py`

- [ ] **Step 1: Escrever teste falhando**

Criar `tests/test_parse_result.py`:

```python
def test_parse_result_defaults():
    from channels.base import ParseResult
    r = ParseResult(action="process", user_id="5511999", text="oi", message_id="ABC")
    assert r.action == "process"
    assert r.user_id == "5511999"
    assert r.text == "oi"
    assert r.message_id == "ABC"
    assert r.reason == ""


def test_parse_result_ignore():
    from channels.base import ParseResult
    r = ParseResult(action="ignore", reason="group")
    assert r.action == "ignore"
    assert r.reason == "group"
    assert r.user_id == ""
```

- [ ] **Step 2: Rodar e verificar que falha**

Run: `cd /c/Users/Dell/argos && python -m pytest tests/test_parse_result.py -v`
Expected: FAIL com ImportError (ParseResult não existe).

- [ ] **Step 3: Implementar ParseResult e atualizar a ABC**

Reescrever `channels/base.py`:

```python
"""
Interface base para canais de mensagem do Severo.
Cada canal implementa parse_incoming (entrada) e send (saída).
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class ParseResult:
    """
    Resultado da análise de um webhook.

    action:
      - "process"        → processar normalmente (user_id, text, message_id)
      - "ignore"         → descartar; `reason` diz o motivo (group|internal|fromMe|no_text|unknown_event)
      - "media_fallback" → mídia sem texto; responder mensagem fixa (sem modelo)
    """
    action: str = "process"
    user_id: str = ""
    text: str = ""
    message_id: str = ""
    reason: str = ""


class Channel(ABC):
    name: str  # identificador do canal: "whatsapp" | "telegram"

    @abstractmethod
    def parse_incoming(self, body: dict) -> ParseResult:
        """
        Analisa o payload do webhook e retorna um ParseResult.
        Nunca retorna None — sempre um ParseResult com action apropriada.
        """

    @abstractmethod
    def send(self, user_id: str, texto: str) -> bool:
        """
        Envia mensagem ao usuário.
        Retorna True em sucesso, False em falha — nunca propaga exceção.
        """
```

- [ ] **Step 4: Rodar testes**

Run: `cd /c/Users/Dell/argos && python -m pytest tests/test_parse_result.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add channels/base.py tests/test_parse_result.py
git commit -m "feat(channels): ParseResult dataclass + nova interface parse_incoming (fundação itens 1,3,7)"
```

---

## Task 3: WhatsApp parse — filtros, message_id e mídia (Itens 1, 7 + parte do 3)

**Files:**
- Modify: `channels/whatsapp.py`
- Modify: `tests/test_channels.py`

- [ ] **Step 1: Escrever testes falhando**

Substituir em `tests/test_channels.py` o helper `_wpp_body` e os testes de WhatsApp por:

```python
def _wpp_body(texto="Olá", from_me=False, jid="5511999@s.whatsapp.net", msg_id="MSG1", message=None):
    if message is None:
        message = {"conversation": texto}
    return {
        "event": "MESSAGES_UPSERT",
        "data": {
            "key": {"remoteJid": jid, "fromMe": from_me, "id": msg_id},
            "message": message,
        },
    }


def test_whatsapp_parse_process_normal():
    from channels.whatsapp import WhatsAppChannel
    canal = WhatsAppChannel()
    r = canal.parse_incoming(_wpp_body("Quero saber mais", msg_id="X1"))
    assert r.action == "process"
    assert r.user_id == "5511999"
    assert r.text == "Quero saber mais"
    assert r.message_id == "X1"


def test_whatsapp_parse_dropa_grupo_antes_do_strip():
    from channels.whatsapp import WhatsAppChannel
    canal = WhatsAppChannel()
    r = canal.parse_incoming(_wpp_body(jid="123456789-987@g.us"))
    assert r.action == "ignore"
    assert r.reason == "group"


def test_whatsapp_parse_dropa_numero_interno(monkeypatch):
    monkeypatch.setenv("INTERNAL_JIDS", "5531991258669,5511933006574")
    from channels.whatsapp import WhatsAppChannel
    canal = WhatsAppChannel()
    r = canal.parse_incoming(_wpp_body(jid="5531991258669@s.whatsapp.net"))
    assert r.action == "ignore"
    assert r.reason == "internal"


def test_whatsapp_parse_dropa_from_me():
    from channels.whatsapp import WhatsAppChannel
    canal = WhatsAppChannel()
    r = canal.parse_incoming(_wpp_body(from_me=True))
    assert r.action == "ignore"
    assert r.reason == "fromMe"


def test_whatsapp_parse_evento_desconhecido():
    from channels.whatsapp import WhatsAppChannel
    canal = WhatsAppChannel()
    r = canal.parse_incoming({"event": "CONNECTION_UPDATE", "data": {}})
    assert r.action == "ignore"
    assert r.reason == "unknown_event"


def test_whatsapp_parse_audio_sem_texto_vira_media_fallback():
    from channels.whatsapp import WhatsAppChannel
    canal = WhatsAppChannel()
    body = _wpp_body(message={"audioMessage": {"seconds": 5}}, msg_id="AUD1")
    r = canal.parse_incoming(body)
    assert r.action == "media_fallback"
    assert r.user_id == "5511999"
    assert r.message_id == "AUD1"


def test_whatsapp_parse_imagem_com_caption_processa():
    from channels.whatsapp import WhatsAppChannel
    canal = WhatsAppChannel()
    body = _wpp_body(message={"imageMessage": {"caption": "olha isso"}}, msg_id="IMG1")
    r = canal.parse_incoming(body)
    assert r.action == "process"
    assert r.text == "olha isso"


def test_whatsapp_send_retorna_true_em_sucesso():
    from channels.whatsapp import WhatsAppChannel
    canal = WhatsAppChannel()
    with patch("channels.whatsapp.requests.post") as mock_post:
        mock_post.return_value = MagicMock(status_code=200)
        result = canal.send("5511999", "Olá lead!")
    assert result is True


def test_whatsapp_send_retorna_false_em_erro():
    from channels.whatsapp import WhatsAppChannel
    canal = WhatsAppChannel()
    with patch("channels.whatsapp.requests.post") as mock_post:
        mock_post.side_effect = ConnectionError("timeout")
        result = canal.send("5511999", "Olá")
    assert result is False
```

- [ ] **Step 2: Rodar e verificar que falha**

Run: `cd /c/Users/Dell/argos && python -m pytest tests/test_channels.py -v`
Expected: FAIL (parse ainda retorna tuple/None).

- [ ] **Step 3: Reescrever WhatsAppChannel.parse_incoming**

Substituir a classe `WhatsAppChannel` em `channels/whatsapp.py` (mantendo `_headers`, `_url` e `send`):

```python
class WhatsAppChannel(Channel):
    name = "whatsapp"

    def parse_incoming(self, body: dict) -> ParseResult:
        evento = body.get("event", "")
        if evento not in ("MESSAGES_UPSERT", "messages.upsert"):
            return ParseResult(action="ignore", reason="unknown_event")

        data = body.get("data", {})
        key = data.get("key", {})
        message_id = key.get("id", "")

        if key.get("fromMe", False):
            return ParseResult(action="ignore", reason="fromMe", message_id=message_id)

        jid: str = key.get("remoteJid", "")

        # Drop de grupo ANTES de qualquer strip — senão @g.us viraria "número"
        if jid.endswith("@g.us"):
            return ParseResult(action="ignore", reason="group", message_id=message_id)

        numero = jid.replace("@s.whatsapp.net", "")
        if not numero:
            return ParseResult(action="ignore", reason="no_sender", message_id=message_id)

        # Filtro de números internos (equipe) — CSV em INTERNAL_JIDS
        internos = {
            n.strip() for n in os.getenv("INTERNAL_JIDS", "").split(",") if n.strip()
        }
        if numero in internos:
            return ParseResult(action="ignore", reason="internal", message_id=message_id)

        texto = self._extrair_texto(data.get("message", {}))
        if not texto:
            # Há mídia mas sem texto → fallback fixo (item 7), ainda passa pelo dedup
            return ParseResult(
                action="media_fallback", user_id=numero, message_id=message_id
            )

        return ParseResult(
            action="process", user_id=numero, text=texto, message_id=message_id
        )

    def _extrair_texto(self, msg_data: dict) -> str:
        return (
            msg_data.get("conversation")
            or msg_data.get("extendedTextMessage", {}).get("text")
            or msg_data.get("imageMessage", {}).get("caption")
            or msg_data.get("videoMessage", {}).get("caption")
            or msg_data.get("buttonsResponseMessage", {}).get("selectedDisplayText")
            or msg_data.get("listResponseMessage", {}).get("title")
            or ""
        ).strip()
```

E adicionar o import no topo de `channels/whatsapp.py` (após `from .base import Channel`):

```python
from .base import Channel, ParseResult
```

(substitui a linha `from .base import Channel`)

- [ ] **Step 4: Rodar testes**

Run: `cd /c/Users/Dell/argos && python -m pytest tests/test_channels.py -v`
Expected: PASS (testes de WhatsApp).

- [ ] **Step 5: Commit**

```bash
git add channels/whatsapp.py tests/test_channels.py
git commit -m "feat(whatsapp): filtro grupo/interno, message_id e media_fallback no parse (itens 1,7)"
```

---

## Task 4: Telegram parse conforma ao ParseResult (Item 1/3)

**Files:**
- Modify: `channels/telegram.py`
- Modify: `tests/test_channels.py`

- [ ] **Step 1: Escrever testes falhando**

Substituir os testes de Telegram em `tests/test_channels.py`:

```python
def _tg_body(texto="Olá", chat_id=123456789, msg_id=42):
    return {
        "message": {
            "message_id": msg_id,
            "chat": {"id": chat_id},
            "text": texto,
        }
    }


def test_telegram_parse_process():
    from channels.telegram import TelegramChannel
    canal = TelegramChannel()
    r = canal.parse_incoming(_tg_body("Quero saber mais", chat_id=987654, msg_id=7))
    assert r.action == "process"
    assert r.user_id == "987654"
    assert r.text == "Quero saber mais"
    assert r.message_id == "7"


def test_telegram_parse_ignora_edited():
    from channels.telegram import TelegramChannel
    canal = TelegramChannel()
    r = canal.parse_incoming({"edited_message": {"chat": {"id": 1}, "text": "x"}})
    assert r.action == "ignore"
    assert r.reason == "edited"


def test_telegram_parse_ignora_sem_texto():
    from channels.telegram import TelegramChannel
    canal = TelegramChannel()
    r = canal.parse_incoming({"message": {"message_id": 9, "chat": {"id": 1}}})
    assert r.action == "ignore"
    assert r.reason == "no_text"


def test_telegram_send_retorna_true_em_sucesso():
    from channels.telegram import TelegramChannel
    canal = TelegramChannel()
    with patch("channels.telegram.requests.post") as mock_post:
        mock_post.return_value = MagicMock(status_code=200)
        result = canal.send("123456", "Olá lead!")
    assert result is True


def test_telegram_send_retorna_false_em_erro():
    from channels.telegram import TelegramChannel
    canal = TelegramChannel()
    with patch("channels.telegram.requests.post") as mock_post:
        mock_post.side_effect = ConnectionError("offline")
        result = canal.send("123456", "Olá")
    assert result is False
```

- [ ] **Step 2: Rodar e verificar que falha**

Run: `cd /c/Users/Dell/argos && python -m pytest tests/test_channels.py -k telegram -v`
Expected: FAIL.

- [ ] **Step 3: Atualizar TelegramChannel.parse_incoming**

Em `channels/telegram.py`, trocar o import e o método `parse_incoming`:

Import (substitui `from .base import Channel`):
```python
from .base import Channel, ParseResult
```

Método:
```python
    def parse_incoming(self, body: dict) -> ParseResult:
        if "edited_message" in body:
            return ParseResult(action="ignore", reason="edited")

        message = body.get("message", {})
        if not message:
            return ParseResult(action="ignore", reason="no_message")

        chat_id = str(message.get("chat", {}).get("id", ""))
        if not chat_id:
            return ParseResult(action="ignore", reason="no_chat")

        message_id = str(message.get("message_id", ""))
        texto = message.get("text", "").strip()
        if not texto:
            return ParseResult(action="ignore", reason="no_text", message_id=message_id)

        return ParseResult(
            action="process", user_id=chat_id, text=texto, message_id=message_id
        )
```

- [ ] **Step 4: Rodar testes**

Run: `cd /c/Users/Dell/argos && python -m pytest tests/test_channels.py -v`
Expected: PASS (todos os testes de canal).

- [ ] **Step 5: Commit**

```bash
git add channels/telegram.py tests/test_channels.py
git commit -m "feat(telegram): conformar parse_incoming ao ParseResult (item 1)"
```

---

## Task 5: Dedup cache em memória (Item 3)

**Files:**
- Create: `dedup.py`
- Test: `tests/test_dedup.py`

- [ ] **Step 1: Escrever testes falhando**

Criar `tests/test_dedup.py`:

```python
def test_dedup_primeira_vez_nao_e_duplicado():
    from dedup import DedupCache
    cache = DedupCache(ttl_seconds=600)
    assert cache.is_duplicate("MSG1", now=1000.0) is False


def test_dedup_segunda_vez_e_duplicado():
    from dedup import DedupCache
    cache = DedupCache(ttl_seconds=600)
    cache.is_duplicate("MSG1", now=1000.0)
    assert cache.is_duplicate("MSG1", now=1001.0) is True


def test_dedup_expira_apos_ttl():
    from dedup import DedupCache
    cache = DedupCache(ttl_seconds=600)
    cache.is_duplicate("MSG1", now=1000.0)
    # Após TTL, o mesmo id volta a ser tratado como novo
    assert cache.is_duplicate("MSG1", now=1700.0) is False


def test_dedup_id_vazio_nunca_e_duplicado():
    from dedup import DedupCache
    cache = DedupCache(ttl_seconds=600)
    assert cache.is_duplicate("", now=1000.0) is False
    assert cache.is_duplicate("", now=1001.0) is False


def test_dedup_limpeza_lazy_remove_expirados():
    from dedup import DedupCache
    cache = DedupCache(ttl_seconds=600)
    cache.is_duplicate("A", now=1000.0)
    cache.is_duplicate("B", now=1001.0)
    # nova chamada bem depois dispara limpeza dos antigos
    cache.is_duplicate("C", now=2000.0)
    assert len(cache._seen) == 1  # só "C" sobrou
```

- [ ] **Step 2: Rodar e verificar que falha**

Run: `cd /c/Users/Dell/argos && python -m pytest tests/test_dedup.py -v`
Expected: FAIL (módulo dedup não existe).

- [ ] **Step 3: Implementar DedupCache**

Criar `dedup.py`:

```python
"""
Dedup de mensagens por messageId — cache em memória, TTL curto.
Single replica no Swarm: memória basta. Múltiplas réplicas exigiriam
dedup compartilhado (Supabase) — ver README.
"""
import time as _time


class DedupCache:
    def __init__(self, ttl_seconds: int = 600) -> None:
        self.ttl = ttl_seconds
        self._seen: dict[str, float] = {}

    def is_duplicate(self, message_id: str, now: float | None = None) -> bool:
        """
        True se message_id já foi visto dentro do TTL.
        IDs vazios nunca são considerados duplicados (sem id confiável → processa).
        Faz limpeza lazy dos expirados a cada chamada.
        """
        if not message_id:
            return False
        agora = now if now is not None else _time.monotonic()

        # Limpeza lazy
        expirados = [k for k, ts in self._seen.items() if agora - ts >= self.ttl]
        for k in expirados:
            del self._seen[k]

        if message_id in self._seen:
            return True

        self._seen[message_id] = agora
        return False
```

- [ ] **Step 4: Rodar testes**

Run: `cd /c/Users/Dell/argos && python -m pytest tests/test_dedup.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add dedup.py tests/test_dedup.py
git commit -m "feat(dedup): cache em memória por messageId com TTL (item 3)"
```

---

## Task 6: Tool escalar_para_humano (Item 4)

**Files:**
- Create: `tools/escalacao.py`
- Modify: `tools/__init__.py`
- Test: `tests/test_escalacao.py`

- [ ] **Step 1: Escrever testes falhando**

Criar `tests/test_escalacao.py`:

```python
from unittest.mock import patch, MagicMock


def test_escalar_envia_para_numero_de_escalacao(monkeypatch):
    monkeypatch.setenv("ESCALATION_NUMBER", "5531999000111")
    monkeypatch.setenv("UAZAPI_URL", "https://test.uazapi.com")
    monkeypatch.setenv("UAZAPI_TOKEN", "tok")
    monkeypatch.setenv("UAZAPI_INSTANCE", "severo")
    from tools.escalacao import escalar_para_humano
    with patch("tools.escalacao.requests.post") as mock_post:
        mock_post.return_value = MagicMock(status_code=200)
        out = escalar_para_humano.invoke({
            "motivo": "lead pediu humano",
            "resumo_conversa": "Maycon / MD Clinic quer falar com atendente",
        })
    # Enviou para o número de escalação
    enviado = mock_post.call_args.kwargs["json"]
    assert enviado["number"] == "5531999000111"
    assert "lead pediu humano" in enviado["text"]
    assert "MD Clinic" in enviado["text"]
    assert isinstance(out, str)


def test_escalar_usa_default_quando_env_ausente(monkeypatch):
    monkeypatch.delenv("ESCALATION_NUMBER", raising=False)
    monkeypatch.setenv("UAZAPI_URL", "https://test.uazapi.com")
    monkeypatch.setenv("UAZAPI_TOKEN", "tok")
    monkeypatch.setenv("UAZAPI_INSTANCE", "severo")
    from tools.escalacao import escalar_para_humano
    with patch("tools.escalacao.requests.post") as mock_post:
        mock_post.return_value = MagicMock(status_code=200)
        escalar_para_humano.invoke({"motivo": "reclamação", "resumo_conversa": "x"})
    assert mock_post.call_args.kwargs["json"]["number"] == "5531991258669"
```

- [ ] **Step 2: Rodar e verificar que falha**

Run: `cd /c/Users/Dell/argos && python -m pytest tests/test_escalacao.py -v`
Expected: FAIL (módulo não existe).

- [ ] **Step 3: Implementar a tool**

Criar `tools/escalacao.py`:

```python
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
        # Nunca propaga — o modelo recebe a confirmação mesmo se o envio falhar
        pass
    return (
        "Escalação registrada. Avise o lead, de forma acolhedora, que uma "
        "pessoa do time vai assumir a conversa em breve."
    )
```

- [ ] **Step 4: Registrar em ALL_TOOLS**

Em `tools/__init__.py`, substituir o conteúdo por:

```python
from .router import avancar_fase, contornar_objecoes, registrar_lead
from .whatsapp import criar_instancia_whatsapp, verificar_conexao_whatsapp
from .pagamento import gerar_link_pagamento
from .escalacao import escalar_para_humano

ALL_TOOLS = [
    avancar_fase,
    contornar_objecoes,
    registrar_lead,
    gerar_link_pagamento,
    criar_instancia_whatsapp,
    verificar_conexao_whatsapp,
    escalar_para_humano,
]
```

- [ ] **Step 5: Rodar testes**

Run: `cd /c/Users/Dell/argos && python -m pytest tests/test_escalacao.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add tools/escalacao.py tools/__init__.py tests/test_escalacao.py
git commit -m "feat(tools): escalar_para_humano notifica time via UAZAPI (item 4)"
```

---

## Task 7: Handler da escalação em nodes/base.py + prompt mínimo (Item 4)

**Files:**
- Modify: `nodes/base.py:149-161`
- Modify: `prompts/fases.py`

- [ ] **Step 1: Adicionar handler da tool no loop de tool_calls**

Em `nodes/base.py`, dentro do `for tc in tool_calls:`, ANTES do bloco `else:` final (linha 157), inserir:

```python
                elif name == "escalar_para_humano":
                    has_action_tools = True
                    result = _execute(name, args)
                    tool_messages.append(ToolMessage(
                        content=str(result),
                        tool_call_id=tid,
                    ))
                    logger.info("[SEVERO] escalar_para_humano → motivo=%s", args.get("motivo"))
```

- [ ] **Step 2: Ajuste mínimo no prompt (afirmação positiva)**

Em `prompts/fases.py`, na fase `aprofundamento_da_dor`, adicionar ao final do texto retornado (antes do fechamento da string) uma instrução positiva. Localizar o `return` da fase `aprofundamento_da_dor` e acrescentar ao corpo:

```
"\n\n## QUANDO CHAMAR UMA PESSOA DO TIME\n"
"Se o lead pedir para falar com um humano, trouxer uma reclamação séria, "
"ou repetir a mesma objeção por dois turnos sem avançar, chame "
"escalar_para_humano(motivo, resumo_conversa) e avise o lead que alguém "
"do time vai assumir. Faça isso com naturalidade, mantendo o tom acolhedor."
```

(Acrescentar como concatenação de string no `return` dessa fase — não remover nada do conteúdo existente.)

- [ ] **Step 3: Verificar que o grafo ainda compila**

Run: `cd /c/Users/Dell/argos && python -c "import config; import os; os.environ.setdefault('ANTHROPIC_API_KEY','x'); os.environ.setdefault('UAZAPI_URL','x'); os.environ.setdefault('UAZAPI_TOKEN','x'); os.environ.setdefault('UAZAPI_INSTANCE','x'); os.environ.setdefault('STRIPE_SECRET_KEY','x'); os.environ.setdefault('STRIPE_WEBHOOK_SECRET','x'); os.environ.setdefault('SUCCESS_URL','x'); os.environ.setdefault('CANCEL_URL','x'); os.environ.setdefault('SUPABASE_URL','x'); os.environ.setdefault('SUPABASE_SERVICE_KEY','x'); from graph import severo; print('grafo OK')"`
Expected: `grafo OK`

- [ ] **Step 4: Commit**

```bash
git add nodes/base.py prompts/fases.py
git commit -m "feat(nodes): handler de escalar_para_humano + menção no prompt de aprofundamento (item 4)"
```

---

## Task 8: main.py — rota com secret, dedup, fail-closed, mídia (Itens 2, 3, 6, 7)

**Files:**
- Modify: `main.py`
- Test: `tests/test_webhook_flow.py`

- [ ] **Step 1: Escrever testes falhando**

Criar `tests/test_webhook_flow.py`:

```python
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("WEBHOOK_SECRET", "s3cr3t")
    monkeypatch.setenv("INTERNAL_JIDS", "5531991258669")
    monkeypatch.setenv("ADMIN_SECRET", "")  # vazio → fail-closed
    import importlib
    import main
    importlib.reload(main)
    return TestClient(main.app)


def _wpp(texto="oi", jid="5511888@s.whatsapp.net", msg_id="M1"):
    return {
        "event": "MESSAGES_UPSERT",
        "data": {"key": {"remoteJid": jid, "fromMe": False, "id": msg_id},
                 "message": {"conversation": texto}},
    }


def test_rota_sem_secret_da_404(client):
    r = client.post("/webhook/whatsapp", json=_wpp())
    assert r.status_code == 404


def test_rota_secret_errado_da_404(client):
    r = client.post("/webhook/whatsapp/errado", json=_wpp())
    assert r.status_code == 404


def test_grupo_e_ignorado(client):
    with patch("main.severo.invoke") as inv:
        r = client.post("/webhook/whatsapp/s3cr3t", json=_wpp(jid="12-9@g.us"))
    assert r.json()["status"] == "ignored"
    assert r.json()["reason"] == "group"
    inv.assert_not_called()


def test_interno_e_ignorado(client):
    with patch("main.severo.invoke") as inv:
        r = client.post("/webhook/whatsapp/s3cr3t",
                        json=_wpp(jid="5531991258669@s.whatsapp.net"))
    assert r.json()["status"] == "ignored"
    assert r.json()["reason"] == "internal"
    inv.assert_not_called()


def test_dedup_segunda_chamada(client):
    with patch("main.severo.invoke") as inv, \
         patch("main.store.get", return_value=None), \
         patch("main.store.set"), \
         patch("main.CANAIS") as canais:
        canal = MagicMock()
        from channels.base import ParseResult
        canal.parse_incoming.return_value = ParseResult(
            action="process", user_id="5511888", text="oi", message_id="DUP1")
        canal.send.return_value = True
        canal.name = "whatsapp"
        canais.get.return_value = canal
        inv.return_value = {"messages": [], "fase": "qualificacao_lead"}
        r1 = client.post("/webhook/whatsapp/s3cr3t", json=_wpp(msg_id="DUP1"))
        r2 = client.post("/webhook/whatsapp/s3cr3t", json=_wpp(msg_id="DUP1"))
    assert r2.json()["status"] == "duplicate"


def test_midia_responde_fixo_sem_modelo(client):
    with patch("main.severo.invoke") as inv, patch("main.CANAIS") as canais:
        canal = MagicMock()
        from channels.base import ParseResult
        canal.parse_incoming.return_value = ParseResult(
            action="media_fallback", user_id="5511888", message_id="AUD9")
        canal.name = "whatsapp"
        canais.get.return_value = canal
        r = client.post("/webhook/whatsapp/s3cr3t", json=_wpp())
    assert r.json()["status"] == "media_fallback"
    inv.assert_not_called()
    canal.send.assert_called_once()
    assert "só leio texto" in canal.send.call_args.args[1]


def test_delete_sessao_sem_admin_secret_da_404(client):
    r = client.delete("/sessao/whatsapp/5511888")
    assert r.status_code == 404
```

- [ ] **Step 2: Rodar e verificar que falha**

Run: `cd /c/Users/Dell/argos && python -m pytest tests/test_webhook_flow.py -v`
Expected: FAIL.

- [ ] **Step 3: Reescrever os endpoints em main.py**

Em `main.py`:

(a) Após `import session_store as store` adicionar:
```python
from dedup import DedupCache
```

(b) Após a definição de `CANAIS` (linha 75), adicionar:
```python
_dedup = DedupCache(ttl_seconds=600)
_WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "")
_MEDIA_FALLBACK_MSG = "Recebi! Por aqui ainda só leio texto 🙂 Pode me escrever?"
```

(c) Substituir a assinatura e o corpo do `receber_mensagem` (linha 129-202). A rota ganha `{webhook_secret}` e a lógica usa `ParseResult`:

```python
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

    # Dedup (item 3) — vale para process E media_fallback
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
```

(d) Tornar o `DELETE /sessao` fail-closed (item 6) — substituir o corpo (linha 213-222):

```python
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
```

(e) Atualizar o registro do webhook do Telegram no `lifespan` (linha 87) para incluir o secret no path:

```python
        wh_url = f"{base_url.rstrip('/')}/webhook/telegram/{os.getenv('WEBHOOK_SECRET','')}"
```

- [ ] **Step 4: Rodar testes**

Run: `cd /c/Users/Dell/argos && python -m pytest tests/test_webhook_flow.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add main.py tests/test_webhook_flow.py
git commit -m "feat(main): path secreto, dedup, fail-closed admin, media fallback (itens 2,3,6,7)"
```

---

## Task 9: .dockerignore (Item 5)

**Files:**
- Create: `.dockerignore`

- [ ] **Step 1: Criar o arquivo**

Criar `.dockerignore`:

```
.env
tests/
.git/
__pycache__/
*.pyc
docs/
.pytest_cache/
```

- [ ] **Step 2: Verificar**

Run: `cd /c/Users/Dell/argos && cat .dockerignore`
Expected: as 7 linhas acima.

- [ ] **Step 3: Commit**

```bash
git add .dockerignore
git commit -m "chore: .dockerignore exclui .env, tests, docs, caches da imagem (item 5)"
```

---

## Task 10: GATE da Etapa 2 — suíte completa

**Files:** Nenhum (verificação).

- [ ] **Step 1: Rodar suíte inteira**

Run: `cd /c/Users/Dell/argos && python -m pytest tests/ -v 2>&1 | tail -40`
Expected: TODOS passando — 27 antigos (ajustados) + novos de: filtro interno, filtro grupo, secret→404, dedup, escalação, mídia→fixa, DELETE sem ADMIN_SECRET→404.

- [ ] **Step 2: Sanity de import do app**

Run: `cd /c/Users/Dell/argos && python -c "import os; [os.environ.setdefault(k,'x') for k in ['ANTHROPIC_API_KEY','UAZAPI_URL','UAZAPI_TOKEN','UAZAPI_INSTANCE','STRIPE_SECRET_KEY','STRIPE_WEBHOOK_SECRET','SUCCESS_URL','CANCEL_URL','SUPABASE_URL','SUPABASE_SERVICE_KEY','WEBHOOK_SECRET','INTERNAL_JIDS']]; import main; print('app OK')"`
Expected: `app OK`

- [ ] **Step 3: Push**

```bash
git push origin main
```

---

## DEPLOY (ETAPAS 3-8) — executar na VPS após o GATE

> **NOTA:** As Etapas 3, 4, 6 e 7 do bloco original do ORION foram truncadas na transmissão. As Etapas abaixo refletem o que está confirmado + os ajustes do MD (Etapa 5 simplificada e Etapa 8 nova). **Confirmar o corpo completo de 3/4/6/7 antes de executar o deploy** — os passos marcados com ⚠️ são reconstrução do que faz sentido, não cópia literal do bloco.

### ETAPA 3 — Secret + .env em disco ⚠️ (reconstruído)

No diretório do EasyPanel, adicionar as vars novas ao `.env` em disco:

```bash
cd /etc/easypanel/projects/n8n/severo/code
# Gerar o WEBHOOK_SECRET (guardar — vai na URL do webhook UAZAPI)
WS=$(python3 -c "import uuid; print(uuid.uuid4().hex)")
echo "WEBHOOK_SECRET gerado: $WS"
cat >> .env << EOF
WEBHOOK_SECRET=$WS
INTERNAL_JIDS=5531991258669
ESCALATION_NUMBER=5531991258669
EOF
```

URL final do webhook WhatsApp (para a Etapa 5): `https://severo.mdiasolutions.tech/webhook/whatsapp/<WEBHOOK_SECRET>`

### ETAPA 4 — Rebuild com o código novo ⚠️ (reconstruído)

No EasyPanel → projeto `n8n` → serviço `severo` → **Deploy** (puxa o `main` atualizado). Aguardar convergência. Depois, reaplicar env vars no Swarm (rebuild reseta):

```bash
docker service update \
  --env-add WEBHOOK_SECRET=<WS> \
  --env-add INTERNAL_JIDS=5531991258669 \
  --env-add ESCALATION_NUMBER=5531991258669 \
  n8n_severo
```

### ETAPA 5 — UAZAPI token (ajuste MD: usar token ATUAL)

1. Setar `UAZAPI_TOKEN=<token atual da instância>` no `.env` (substituir o placeholder `sem-whatsapp-por-enquanto`):
```bash
cd /etc/easypanel/projects/n8n/severo/code
sed -i 's|^UAZAPI_TOKEN=.*|UAZAPI_TOKEN=<TOKEN_ATUAL>|' .env
docker service update --env-add UAZAPI_TOKEN=<TOKEN_ATUAL> n8n_severo
```
2. MD aponta o webhook da instância UAZAPI para a URL da Etapa 3:
   `https://severo.mdiasolutions.tech/webhook/whatsapp/<WEBHOOK_SECRET>`
3. `docker service update --force n8n_severo`

### ETAPA 6 — Verificação pós-deploy ⚠️ (reconstruído)

```bash
# Health
curl -sk https://severo.mdiasolutions.tech/health
# Rota antiga sem secret deve dar 404
curl -sk -o /dev/null -w "%{http_code}\n" -X POST https://severo.mdiasolutions.tech/webhook/whatsapp
# Logs de startup
docker service logs n8n_severo --raw --tail 20
```
Esperado: health 200; rota sem secret → 404; logs sem erro e com Telegram webhook registrado na nova URL com secret.

### ETAPA 7 — Teste de tráfego real ⚠️ (reconstruído)

- Mandar mensagem de um número externo (não-interno) → bot responde.
- Mandar mensagem de número em `INTERNAL_JIDS` → drop silencioso (log `reason=internal`, sem resposta).
- Mandar em grupo → drop (log `reason=group`).
- Mandar áudio → resposta fixa "só leio texto".
- Reenvio do mesmo messageId (retry) → `duplicate`, sem segunda resposta.

### ETAPA 8 — Rotação do Instance Token (NOVA, pós-go-live validado)

Higiene, não bloqueia go-live. Só depois de tráfego real OK:

1. Rotacionar o Instance Token no painel UAZAPI.
2. Atualizar no `.env` + Swarm:
```bash
cd /etc/easypanel/projects/n8n/severo/code
sed -i 's|^UAZAPI_TOKEN=.*|UAZAPI_TOKEN=<NOVO_TOKEN>|' .env
docker service update --env-add UAZAPI_TOKEN=<NOVO_TOKEN> --force n8n_severo
```
3. 1 teste de envio para confirmar que o envio segue funcionando.

---

## Checklist de Revisão Final

- [ ] Item 1: grupo dropado antes do strip + filtro INTERNAL_JIDS + fromMe, todos com log de motivo
- [ ] Item 2: rota `/webhook/{canal}/{secret}`, mismatch → 404; Telegram registra URL com secret
- [ ] Item 3: dedup por messageId, TTL 10min, sem dep nova
- [ ] Item 4: `escalar_para_humano` registrada, notifica ESCALATION_NUMBER, prompt menciona quando usar
- [ ] Item 5: `.dockerignore` exclui `.env`/tests/docs; runtime lê env do Swarm
- [ ] Item 6: `DELETE /sessao` fail-closed (sem ADMIN_SECRET → 404)
- [ ] Item 7: mídia sem texto → resposta fixa, passa pelo dedup, custo zero de modelo
- [ ] Item 8: `WEBHOOK_SECRET`, `INTERNAL_JIDS` obrigatórias; `ESCALATION_NUMBER` opcional; Haiku mantido
- [ ] GATE: suíte completa verde antes de qualquer deploy
- [ ] Funil de 7 fases, prompts de fase e fluxo Stripe intactos
