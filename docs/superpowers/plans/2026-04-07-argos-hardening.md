# Argos Hardening & Multi-Canal — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Tornar o Argos production-ready: persistência de sessões via Supabase, Pix no Stripe, lookup de pagamento por número (não nome), timeout em tools, abstração multi-canal e integração Telegram para testes.

**Architecture:** Cada mensagem entra por um `Channel` (WhatsApp ou Telegram), que extrai `(numero, texto)` e passa para o grafo LangGraph. O estado do grafo é persistido no Supabase keyed por `(numero, canal)`. O webhook do Stripe busca sessões por `numero` nos metadados do checkout, eliminando ambiguidade por nome.

**Tech Stack:** Python 3.11+, FastAPI, LangGraph, LangChain Anthropic, Supabase (supabase-py), Stripe, UazAPI, Telegram Bot API (via requests diretos), pytest, unittest.mock

---

## Pré-requisitos

Antes de começar:
- Você tem o token do bot Telegram novo (revogado o antigo via `/token` no @BotFather)
- Você tem `SUPABASE_URL` e `SUPABASE_SERVICE_KEY` disponíveis
- Python 3.11+ instalado localmente (`python --version`)
- Acesso ao repositório em `/c/Users/Dell/argos/`

---

## Task 1: requirements.txt + setup de testes

**Files:**
- Create: `requirements.txt`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`

- [ ] **Step 1: Criar requirements.txt**

```
langgraph>=0.2
langchain-anthropic>=0.2
langchain-core>=0.3
fastapi>=0.115
uvicorn[standard]>=0.30
python-dotenv>=1.0
stripe>=10.0
requests>=2.32
supabase>=2.7
pytest>=8.0
pytest-mock>=3.14
```

Salve em `/c/Users/Dell/argos/requirements.txt`.

- [ ] **Step 2: Instalar dependências**

```bash
cd /c/Users/Dell/argos
pip install -r requirements.txt
```

Saída esperada: `Successfully installed supabase-2.x.x ...` (sem erros)

- [ ] **Step 3: Criar estrutura de testes**

`tests/__init__.py` — arquivo vazio.

`tests/conftest.py`:
```python
import os
import pytest

# Garante que env vars de teste não quebram imports
os.environ.setdefault("ANTHROPIC_API_KEY", "sk-ant-test")
os.environ.setdefault("UAZAPI_URL", "https://test.uazapi.com")
os.environ.setdefault("UAZAPI_TOKEN", "test-token")
os.environ.setdefault("UAZAPI_INSTANCE", "test")
os.environ.setdefault("STRIPE_SECRET_KEY", "sk_test_xxx")
os.environ.setdefault("STRIPE_WEBHOOK_SECRET", "whsec_test")
os.environ.setdefault("SUCCESS_URL", "https://test.com/obrigado")
os.environ.setdefault("CANCEL_URL", "https://test.com/")
os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("SUPABASE_SERVICE_KEY", "eyJ.test")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "123:test")
os.environ.setdefault("TELEGRAM_WEBHOOK_SECRET", "test-secret")
os.environ.setdefault("BASE_URL", "https://test.com")
```

- [ ] **Step 4: Verificar que pytest funciona**

```bash
cd /c/Users/Dell/argos
pytest tests/ -v
```

Saída esperada: `no tests ran` (sem erros de import)

- [ ] **Step 5: Commit**

```bash
git add requirements.txt tests/__init__.py tests/conftest.py
git commit -m "chore: add requirements.txt and test scaffolding"
```

---

## Task 2: config.py — validação de env vars

**Files:**
- Create: `config.py`
- Create: `tests/test_config.py`

- [ ] **Step 1: Escrever o teste (TDD — vai falhar)**

`tests/test_config.py`:
```python
import os
import pytest
from unittest.mock import patch


def test_validate_passa_quando_todas_vars_presentes():
    """Não deve levantar exceção quando todas vars obrigatórias estão setadas."""
    import config
    # conftest.py já setou todas as vars — validate() deve passar sem erro
    config.validate()  # sem exceção = sucesso


def test_validate_falha_quando_var_ausente():
    """Deve chamar SystemExit quando uma var obrigatória está ausente."""
    import config
    with patch.dict(os.environ, {"ANTHROPIC_API_KEY": ""}, clear=False):
        with pytest.raises(SystemExit):
            config.validate()


def test_validate_lista_todas_vars_ausentes(capsys):
    """A mensagem de erro deve listar todas as vars faltando."""
    import config
    with patch.dict(os.environ, {
        "ANTHROPIC_API_KEY": "",
        "STRIPE_SECRET_KEY": "",
    }, clear=False):
        with pytest.raises(SystemExit):
            config.validate()
    captured = capsys.readouterr()
    assert "ANTHROPIC_API_KEY" in captured.err
    assert "STRIPE_SECRET_KEY" in captured.err
```

- [ ] **Step 2: Rodar e confirmar que falha**

```bash
cd /c/Users/Dell/argos
pytest tests/test_config.py -v
```

Saída esperada: `ERROR` ou `ModuleNotFoundError: No module named 'config'`

- [ ] **Step 3: Implementar config.py**

`config.py`:
```python
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
            f"[ARGOS] ERRO: variáveis obrigatórias ausentes: {', '.join(missing)}",
            file=sys.stderr,
        )
        raise SystemExit(1)
```

- [ ] **Step 4: Rodar testes e confirmar que passam**

```bash
pytest tests/test_config.py -v
```

Saída esperada:
```
PASSED tests/test_config.py::test_validate_passa_quando_todas_vars_presentes
PASSED tests/test_config.py::test_validate_falha_quando_var_ausente
PASSED tests/test_config.py::test_validate_lista_todas_vars_ausentes
```

- [ ] **Step 5: Commit**

```bash
git add config.py tests/test_config.py
git commit -m "feat: add startup env var validation (config.py)"
```

---

## Task 3: state.py — adicionar campo `numero`

**Files:**
- Modify: `state.py`

O campo `numero` (telefone ou chat_id) precisa viver no estado para que tools como `gerar_link_pagamento` possam incluí-lo nos metadados do Stripe sem depender de parâmetros externos.

- [ ] **Step 1: Adicionar campo ao AgentState**

Abra `state.py` e adicione `numero` após `objecao_ativa`:

```python
from typing import TypedDict, Annotated, Optional
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    messages: Annotated[list, add_messages]

    fase: str  # qualificacao_lead | aprofundamento_da_dor |
               # apresentacao_da_oferta | gerar_link_pagamento |
               # confirmacao_pagamento | instrucao_conexao |
               # conexao_estabelecida | encerrado

    nome_lead: Optional[str]
    nome_clinica: Optional[str]
    sistema_operacional: Optional[str]  # android | iphone

    pagamento_confirmado: bool
    token_gerado: Optional[str]
    conexao_estabelecida: bool
    link_pagamento: Optional[str]

    canal_origem: str  # whatsapp | telegram

    usa_whatsapp: Optional[bool]
    lead_qualificado: Optional[bool]
    objecao_ativa: Optional[str]

    numero: Optional[str]  # identificador do lead: telefone (WhatsApp) ou chat_id (Telegram)
```

- [ ] **Step 2: Verificar que o grafo ainda importa sem erro**

```bash
cd /c/Users/Dell/argos
python -c "from graph import argos; print('OK')"
```

Saída esperada: `OK` (sem erro de TypedDict)

- [ ] **Step 3: Commit**

```bash
git add state.py
git commit -m "feat: add 'numero' field to AgentState for Stripe metadata"
```

---

## Task 4: session_store.py — persistência Supabase

**Files:**
- Create: `session_store.py`
- Create: `tests/test_session_store.py`

- [ ] **Step 1: Criar tabela no Supabase**

Acesse o painel do seu projeto Supabase → SQL Editor e execute:

```sql
CREATE TABLE IF NOT EXISTS argos_sessions (
    numero      TEXT NOT NULL,
    canal       TEXT NOT NULL DEFAULT 'whatsapp',
    state       JSONB NOT NULL,
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (numero, canal)
);

CREATE INDEX IF NOT EXISTS idx_argos_sessions_updated_at
    ON argos_sessions (updated_at);
```

Confirme que a tabela aparece em Table Editor antes de continuar.

- [ ] **Step 2: Escrever os testes**

`tests/test_session_store.py`:
```python
import pytest
from unittest.mock import MagicMock, patch


@pytest.fixture
def mock_supabase(monkeypatch):
    """Substitui o cliente Supabase real por um mock."""
    mock_client = MagicMock()
    monkeypatch.setattr("session_store._client", mock_client)
    return mock_client


def _make_chain(mock_client, data=None):
    """Helper: configura a cadeia de chamadas .table().select()... .execute()"""
    chain = MagicMock()
    chain.execute.return_value = MagicMock(data=data or [])
    mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value = chain
    mock_client.table.return_value.upsert.return_value.execute.return_value = MagicMock()
    mock_client.table.return_value.delete.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock()
    mock_client.table.return_value.delete.return_value.lt.return_value.execute.return_value = MagicMock(data=[{"numero": "1"}, {"numero": "2"}])
    return chain


def test_get_retorna_none_quando_nao_existe(mock_supabase):
    _make_chain(mock_supabase, data=[])
    import session_store
    result = session_store.get("5511999", "whatsapp")
    assert result is None


def test_get_retorna_estado_quando_existe(mock_supabase):
    estado_salvo = {"fase": "qualificacao_lead", "messages": []}
    _make_chain(mock_supabase, data=[{"state": estado_salvo}])
    import session_store
    result = session_store.get("5511999", "whatsapp")
    assert result == estado_salvo


def test_set_chama_upsert(mock_supabase):
    _make_chain(mock_supabase)
    import session_store
    estado = {"fase": "qualificacao_lead", "messages": []}
    session_store.set("5511999", estado, "whatsapp")
    mock_supabase.table.assert_called_with("argos_sessions")
    mock_supabase.table.return_value.upsert.assert_called_once()


def test_delete_chama_delete(mock_supabase):
    _make_chain(mock_supabase)
    import session_store
    session_store.delete("5511999", "whatsapp")
    mock_supabase.table.assert_called_with("argos_sessions")


def test_cleanup_old_retorna_count(mock_supabase):
    _make_chain(mock_supabase)
    import session_store
    count = session_store.cleanup_old(days=30)
    assert count == 2
```

- [ ] **Step 3: Rodar e confirmar que falha**

```bash
pytest tests/test_session_store.py -v
```

Saída esperada: `ModuleNotFoundError: No module named 'session_store'`

- [ ] **Step 4: Implementar session_store.py**

`session_store.py`:
```python
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
```

- [ ] **Step 5: Rodar testes e confirmar que passam**

```bash
pytest tests/test_session_store.py -v
```

Saída esperada: 5 testes PASSED.

- [ ] **Step 6: Commit**

```bash
git add session_store.py tests/test_session_store.py
git commit -m "feat: add Supabase session persistence (session_store.py)"
```

---

## Task 5: nodes/base.py — timeout em tool calls

**Files:**
- Modify: `nodes/base.py`
- Create: `tests/test_base_timeout.py`

- [ ] **Step 1: Escrever o teste**

`tests/test_base_timeout.py`:
```python
import time
import pytest
from unittest.mock import MagicMock, patch


def test_execute_retorna_erro_em_timeout():
    """_execute deve retornar string de erro quando tool demora mais que TOOL_TIMEOUT."""
    import nodes.base as base

    def tool_lenta(*args, **kwargs):
        time.sleep(5)
        return "nunca chega aqui"

    mock_tool = MagicMock()
    mock_tool.invoke = tool_lenta

    with patch.dict(base._TOOL_FN, {"tool_lenta": mock_tool}):
        with patch.dict("os.environ", {"TOOL_TIMEOUT_SECONDS": "1"}):
            # Recarregar a constante
            base.TOOL_TIMEOUT = 1
            result = base._execute("tool_lenta", {})

    assert "Timeout" in result or "timeout" in result or "não respondeu" in result


def test_execute_retorna_resultado_normal():
    """_execute deve retornar resultado da tool quando executa dentro do tempo."""
    import nodes.base as base

    mock_tool = MagicMock()
    mock_tool.invoke.return_value = {"url": "https://stripe.com/pay/xxx"}

    with patch.dict(base._TOOL_FN, {"gerar_link": mock_tool}):
        result = base._execute("gerar_link", {"nome": "João"})

    assert result == {"url": "https://stripe.com/pay/xxx"}


def test_execute_retorna_erro_em_excecao():
    """_execute deve retornar string de erro (não propagar exceção) quando tool falha."""
    import nodes.base as base

    mock_tool = MagicMock()
    mock_tool.invoke.side_effect = ConnectionError("UazAPI offline")

    with patch.dict(base._TOOL_FN, {"whatsapp_tool": mock_tool}):
        result = base._execute("whatsapp_tool", {})

    assert isinstance(result, str)
    assert "Erro" in result or "erro" in result
```

- [ ] **Step 2: Rodar e confirmar que falha**

```bash
pytest tests/test_base_timeout.py -v
```

Saída esperada: FAILED (AttributeError ou timeout não implementado)

- [ ] **Step 3: Modificar nodes/base.py — adicionar imports e TOOL_TIMEOUT**

Substitua o bloco de imports e constantes no topo de `nodes/base.py`:

```python
import os
import logging
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import SystemMessage, ToolMessage, AIMessage
from prompts.fases import get_prompt_fase
from tools import ALL_TOOLS

logger = logging.getLogger("argos")

MODEL_ID = os.getenv("ANTHROPIC_MODEL", "claude-opus-4-5")
MAX_TOOL_ITERATIONS = 5
TOOL_TIMEOUT = int(os.getenv("TOOL_TIMEOUT_SECONDS", "15"))

_model = ChatAnthropic(model=MODEL_ID, temperature=0.3)
_model_with_tools = _model.bind_tools(ALL_TOOLS)

_TOOL_FN = {t.name: t for t in ALL_TOOLS}
```

- [ ] **Step 4: Substituir a função `_execute` em nodes/base.py**

Substitua a função `_execute` existente (linhas 33-37):

```python
def _execute(tool_name: str, args: dict):
    """
    Executa uma tool com timeout.
    Retorna o resultado ou uma string de erro — nunca propaga exceção.
    Isso garante que o modelo receba um ToolMessage válido mesmo em falhas.
    """
    fn = _TOOL_FN.get(tool_name)
    if fn is None:
        return f"Tool '{tool_name}' não encontrada."
    try:
        with ThreadPoolExecutor(max_workers=1) as ex:
            future = ex.submit(fn.invoke, args)
            return future.result(timeout=TOOL_TIMEOUT)
    except FuturesTimeout:
        logger.error("[ARGOS] Timeout na tool '%s' após %ds", tool_name, TOOL_TIMEOUT)
        return f"Erro: tool '{tool_name}' não respondeu em {TOOL_TIMEOUT}s. Tente novamente."
    except Exception as e:
        logger.error("[ARGOS] Erro na tool '%s': %s", tool_name, e)
        return f"Erro ao executar '{tool_name}': {str(e)}"
```

- [ ] **Step 5: Rodar testes e confirmar que passam**

```bash
pytest tests/test_base_timeout.py -v
```

Saída esperada: 3 testes PASSED (o teste de timeout pode levar ~1s).

- [ ] **Step 6: Commit**

```bash
git add nodes/base.py tests/test_base_timeout.py
git commit -m "feat: add timeout and error handling to tool execution in base.py"
```

---

## Task 6: tools/pagamento.py — Pix + metadata com numero/canal

**Files:**
- Modify: `tools/pagamento.py`
- Modify: `nodes/base.py` (injeção de numero/canal ao chamar gerar_link_pagamento)
- Create: `tests/test_pagamento.py`

- [ ] **Step 1: Escrever os testes**

`tests/test_pagamento.py`:
```python
import pytest
from unittest.mock import patch, MagicMock


def test_gerar_link_inclui_pix_nos_metodos():
    """O checkout Stripe deve incluir 'pix' como método de pagamento."""
    with patch("tools.pagamento.stripe") as mock_stripe:
        mock_session = MagicMock()
        mock_session.url = "https://checkout.stripe.com/pay/cs_test_xxx"
        mock_stripe.checkout.Session.create.return_value = mock_session

        from tools.pagamento import gerar_link_pagamento
        result = gerar_link_pagamento.invoke({
            "nome_lead": "João",
            "nome_clinica": "Clínica Saúde",
            "numero": "5511999999999",
            "canal": "whatsapp",
        })

    call_kwargs = mock_stripe.checkout.Session.create.call_args[1]
    assert "pix" in call_kwargs["payment_method_types"]
    assert "card" in call_kwargs["payment_method_types"]


def test_gerar_link_inclui_numero_nos_metadados():
    """Os metadados do checkout devem incluir numero e canal para lookup no webhook."""
    with patch("tools.pagamento.stripe") as mock_stripe:
        mock_session = MagicMock()
        mock_session.url = "https://checkout.stripe.com/pay/cs_test_xxx"
        mock_stripe.checkout.Session.create.return_value = mock_session

        from tools.pagamento import gerar_link_pagamento
        gerar_link_pagamento.invoke({
            "nome_lead": "Maria",
            "nome_clinica": "Clínica Bem Estar",
            "numero": "5521888888888",
            "canal": "telegram",
        })

    call_kwargs = mock_stripe.checkout.Session.create.call_args[1]
    assert call_kwargs["metadata"]["numero"] == "5521888888888"
    assert call_kwargs["metadata"]["canal"] == "telegram"
    assert call_kwargs["metadata"]["nome_lead"] == "Maria"


def test_gerar_link_retorna_url():
    """Deve retornar dict com chave 'url' apontando para o link de pagamento."""
    with patch("tools.pagamento.stripe") as mock_stripe:
        mock_session = MagicMock()
        mock_session.url = "https://checkout.stripe.com/pay/cs_test_abc"
        mock_stripe.checkout.Session.create.return_value = mock_session

        from tools.pagamento import gerar_link_pagamento
        result = gerar_link_pagamento.invoke({
            "nome_lead": "Ana",
            "nome_clinica": "Clínica Ana",
            "numero": "5511777777777",
            "canal": "whatsapp",
        })

    assert result["url"] == "https://checkout.stripe.com/pay/cs_test_abc"
```

- [ ] **Step 2: Rodar e confirmar que falham**

```bash
pytest tests/test_pagamento.py -v
```

Saída esperada: FAILED (pix não presente, numero não nos metadados)

- [ ] **Step 3: Reescrever tools/pagamento.py**

```python
"""
Integração com Stripe para geração de links de pagamento.
"""
import os
import stripe
from langchain_core.tools import tool

stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")

SUCCESS_URL      = os.getenv("SUCCESS_URL", "")
CANCEL_URL       = os.getenv("CANCEL_URL", "")
PRECO_CENTAVOS   = int(os.getenv("PRECO_CENTAVOS", "4990"))


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
```

- [ ] **Step 4: Injetar numero/canal em nodes/base.py ao chamar gerar_link_pagamento**

No método `node` dentro de `create_agent_node` em `nodes/base.py`, localize o bloco `elif name == "gerar_link_pagamento":` e substitua por:

```python
elif name == "gerar_link_pagamento":
    has_action_tools = True
    # Injeta numero e canal do estado para que o Stripe inclua nos metadados
    enriched_args = {
        **args,
        "numero": state.get("numero", ""),
        "canal": state.get("canal_origem", "whatsapp"),
    }
    result = _execute(name, enriched_args)
    if isinstance(result, dict):
        updates["link_pagamento"] = result.get("url", "")
    tool_messages.append(ToolMessage(
        content=str(result),
        tool_call_id=tid,
    ))
    logger.info("[ARGOS] gerar_link_pagamento → %s", updates.get("link_pagamento"))
```

- [ ] **Step 5: Rodar todos os testes**

```bash
pytest tests/ -v
```

Saída esperada: todos os testes anteriores continuam passando + 3 novos PASSED.

- [ ] **Step 6: Commit**

```bash
git add tools/pagamento.py nodes/base.py tests/test_pagamento.py
git commit -m "feat: add Pix support and numero/canal metadata to Stripe checkout"
```

---

## Task 7: webhook_stripe.py — lookup por numero/canal

**Files:**
- Modify: `webhook_stripe.py`
- Create: `tests/test_webhook_stripe.py`

- [ ] **Step 1: Escrever os testes**

`tests/test_webhook_stripe.py`:
```python
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
import hmac, hashlib, time


def _make_stripe_event(numero="5511999", canal="whatsapp", nome_lead="João"):
    return {
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "metadata": {
                    "numero": numero,
                    "canal": canal,
                    "nome_lead": nome_lead,
                    "nome_clinica": "Clínica Teste",
                }
            }
        }
    }


def test_webhook_atualiza_sessao_por_numero(monkeypatch):
    """Deve usar numero+canal dos metadados para encontrar e atualizar a sessão."""
    estado_mock = {
        "fase": "gerar_link_pagamento",
        "pagamento_confirmado": False,
        "messages": [],
        "nome_lead": "João",
        "nome_clinica": "Clínica Teste",
        "numero": "5511999",
        "canal_origem": "whatsapp",
        "sistema_operacional": None,
        "token_gerado": None,
        "conexao_estabelecida": False,
        "link_pagamento": None,
        "usa_whatsapp": None,
        "lead_qualificado": None,
        "objecao_ativa": None,
    }

    store_get = MagicMock(return_value=estado_mock)
    store_set = MagicMock()

    monkeypatch.setattr("webhook_stripe.store.get", store_get)
    monkeypatch.setattr("webhook_stripe.store.set", store_set)

    import stripe
    with patch("webhook_stripe.stripe.Webhook.construct_event") as mock_construct:
        mock_construct.return_value = _make_stripe_event()
        from webhook_stripe import processar_pagamento_confirmado
        processar_pagamento_confirmado("5511999", "whatsapp")

    store_set.assert_called_once()
    args = store_set.call_args
    assert args[0][0] == "5511999"   # numero
    assert args[0][2] == "whatsapp"  # canal
    assert args[0][1]["pagamento_confirmado"] is True
    assert args[0][1]["fase"] == "confirmacao_pagamento"


def test_webhook_nao_atualiza_quando_sessao_nao_existe(monkeypatch):
    """Não deve falhar quando numero não existe em sessoes."""
    monkeypatch.setattr("webhook_stripe.store.get", MagicMock(return_value=None))
    store_set = MagicMock()
    monkeypatch.setattr("webhook_stripe.store.set", store_set)

    from webhook_stripe import processar_pagamento_confirmado
    processar_pagamento_confirmado("9999999", "whatsapp")

    store_set.assert_not_called()
```

- [ ] **Step 2: Rodar e confirmar que falham**

```bash
pytest tests/test_webhook_stripe.py -v
```

Saída esperada: FAILED / ImportError (função `processar_pagamento_confirmado` não existe ainda)

- [ ] **Step 3: Reescrever webhook_stripe.py**

```python
"""
Webhook Stripe — recebe confirmação de pagamento e avança sessão do lead.
"""
import logging
import os

import stripe
from fastapi import APIRouter, Request, HTTPException

import session_store as store

logger = logging.getLogger("argos")
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
```

- [ ] **Step 4: Rodar testes**

```bash
pytest tests/test_webhook_stripe.py tests/test_session_store.py -v
```

Saída esperada: todos PASSED.

- [ ] **Step 5: Commit**

```bash
git add webhook_stripe.py tests/test_webhook_stripe.py
git commit -m "feat: fix Stripe webhook to lookup sessions by numero/canal (not name)"
```

---

## Task 8: channels/ — abstração multi-canal + WhatsApp

**Files:**
- Create: `channels/__init__.py`
- Create: `channels/base.py`
- Create: `channels/whatsapp.py`
- Create: `tests/test_channels.py`

- [ ] **Step 1: Escrever testes do canal WhatsApp**

`tests/test_channels.py`:
```python
import pytest
from unittest.mock import patch, MagicMock


# ── WhatsApp ──────────────────────────────────────────────────────────────

def _wpp_body(texto="Olá", from_me=False, jid="5511999@s.whatsapp.net"):
    return {
        "event": "MESSAGES_UPSERT",
        "data": {
            "key": {"remoteJid": jid, "fromMe": from_me},
            "message": {"conversation": texto},
        },
    }


def test_whatsapp_parse_retorna_numero_e_texto():
    from channels.whatsapp import WhatsAppChannel
    canal = WhatsAppChannel()
    result = canal.parse_incoming(_wpp_body("Quero saber mais"))
    assert result == ("5511999", "Quero saber mais")


def test_whatsapp_parse_ignora_from_me():
    from channels.whatsapp import WhatsAppChannel
    canal = WhatsAppChannel()
    result = canal.parse_incoming(_wpp_body(from_me=True))
    assert result is None


def test_whatsapp_parse_ignora_evento_desconhecido():
    from channels.whatsapp import WhatsAppChannel
    canal = WhatsAppChannel()
    body = {"event": "CONNECTION_UPDATE", "data": {}}
    result = canal.parse_incoming(body)
    assert result is None


def test_whatsapp_parse_ignora_mensagem_sem_texto():
    from channels.whatsapp import WhatsAppChannel
    canal = WhatsAppChannel()
    body = {
        "event": "MESSAGES_UPSERT",
        "data": {
            "key": {"remoteJid": "5511999@s.whatsapp.net", "fromMe": False},
            "message": {},
        },
    }
    result = canal.parse_incoming(body)
    assert result is None


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


# ── Telegram ──────────────────────────────────────────────────────────────

def _tg_body(texto="Olá", chat_id=123456789):
    return {
        "message": {
            "chat": {"id": chat_id},
            "text": texto,
        }
    }


def test_telegram_parse_retorna_chat_id_e_texto():
    from channels.telegram import TelegramChannel
    canal = TelegramChannel()
    result = canal.parse_incoming(_tg_body("Quero saber mais", chat_id=987654))
    assert result == ("987654", "Quero saber mais")


def test_telegram_parse_ignora_edited_message():
    from channels.telegram import TelegramChannel
    canal = TelegramChannel()
    body = {"edited_message": {"chat": {"id": 123}, "text": "editado"}}
    result = canal.parse_incoming(body)
    assert result is None


def test_telegram_parse_ignora_sem_texto():
    from channels.telegram import TelegramChannel
    canal = TelegramChannel()
    body = {"message": {"chat": {"id": 123}}}
    result = canal.parse_incoming(body)
    assert result is None


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

- [ ] **Step 2: Rodar e confirmar que falham**

```bash
pytest tests/test_channels.py -v
```

Saída esperada: `ModuleNotFoundError: No module named 'channels'`

- [ ] **Step 3: Criar channels/__init__.py**

```python
from .whatsapp import WhatsAppChannel
from .telegram import TelegramChannel

__all__ = ["WhatsAppChannel", "TelegramChannel"]
```

- [ ] **Step 4: Criar channels/base.py**

```python
"""
Interface base para canais de mensagem do Argos.
Cada canal implementa parse_incoming (entrada) e send (saída).
"""
from abc import ABC, abstractmethod


class Channel(ABC):
    name: str  # identificador do canal: "whatsapp" | "telegram"

    @abstractmethod
    def parse_incoming(self, body: dict) -> tuple[str, str] | None:
        """
        Extrai (identificador_usuario, texto) do payload do webhook.
        Retorna None se a mensagem deve ser ignorada
        (fromMe, evento desconhecido, sem texto, etc.).
        """

    @abstractmethod
    def send(self, user_id: str, texto: str) -> bool:
        """
        Envia mensagem ao usuário.
        Retorna True em sucesso, False em falha — nunca propaga exceção.
        """
```

- [ ] **Step 5: Criar channels/whatsapp.py**

```python
"""
Canal WhatsApp via UazAPI.
Encapsula parsing de webhooks e envio de mensagens.
"""
import logging
import os

import requests

from .base import Channel

logger = logging.getLogger("argos")


def _headers() -> dict:
    return {"apikey": os.getenv("UAZAPI_TOKEN", "")}


def _url(path: str) -> str:
    base = os.getenv("UAZAPI_URL", "").rstrip("/")
    return f"{base}{path}"


class WhatsAppChannel(Channel):
    name = "whatsapp"

    def parse_incoming(self, body: dict) -> tuple[str, str] | None:
        evento = body.get("event", "")
        if evento not in ("MESSAGES_UPSERT", "messages.upsert"):
            return None

        data = body.get("data", {})
        key = data.get("key", {})

        # Ignorar mensagens enviadas pelo próprio Argos
        if key.get("fromMe", False):
            return None

        jid: str = key.get("remoteJid", "")
        numero = jid.replace("@s.whatsapp.net", "").replace("@g.us", "")
        if not numero:
            return None

        texto = self._extrair_texto(data.get("message", {}))
        if not texto:
            return None

        return numero, texto

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

    def send(self, numero: str, texto: str) -> bool:
        instance = os.getenv("UAZAPI_INSTANCE", "argos")
        try:
            resp = requests.post(
                _url(f"/message/sendText/{instance}"),
                headers=_headers(),
                json={"number": numero, "text": texto, "delay": 1200},
                timeout=10,
            )
            return resp.status_code == 200
        except Exception as e:
            logger.error("[WHATSAPP] Erro ao enviar para %s: %s", numero[:6], e)
            return False
```

- [ ] **Step 6: Criar channels/telegram.py**

```python
"""
Canal Telegram via Bot API.
Usado para testes internos do funil — canal de produção é WhatsApp.
"""
import logging
import os

import requests

from .base import Channel

logger = logging.getLogger("argos")


class TelegramChannel(Channel):
    name = "telegram"

    def __init__(self) -> None:
        self._token = os.getenv("TELEGRAM_BOT_TOKEN", "")

    def _api(self, method: str) -> str:
        return f"https://api.telegram.org/bot{self._token}/{method}"

    def parse_incoming(self, body: dict) -> tuple[str, str] | None:
        # Ignorar mensagens editadas para evitar reprocessamento
        if "edited_message" in body:
            return None

        message = body.get("message", {})
        if not message:
            return None

        chat_id = str(message.get("chat", {}).get("id", ""))
        if not chat_id:
            return None

        texto = message.get("text", "").strip()
        if not texto:
            return None

        return chat_id, texto

    def send(self, chat_id: str, texto: str) -> bool:
        try:
            resp = requests.post(
                self._api("sendMessage"),
                json={"chat_id": chat_id, "text": texto},
                timeout=10,
            )
            return resp.status_code == 200
        except Exception as e:
            logger.error("[TELEGRAM] Erro ao enviar para %s: %s", chat_id, e)
            return False

    def setup_webhook(self, webhook_url: str, secret_token: str) -> bool:
        """
        Registra o webhook no Telegram. Chamado uma vez no startup.
        Telegram exige HTTPS na URL do webhook.
        """
        try:
            resp = requests.post(
                self._api("setWebhook"),
                json={"url": webhook_url, "secret_token": secret_token},
                timeout=10,
            )
            ok = resp.status_code == 200
            if not ok:
                logger.error("[TELEGRAM] Falha ao registrar webhook: %s", resp.text)
            return ok
        except Exception as e:
            logger.error("[TELEGRAM] Erro ao registrar webhook: %s", e)
            return False
```

- [ ] **Step 7: Rodar todos os testes de canais**

```bash
pytest tests/test_channels.py -v
```

Saída esperada: 11 testes PASSED.

- [ ] **Step 8: Rodar suite completa**

```bash
pytest tests/ -v
```

Saída esperada: todos PASSED (sem regressão).

- [ ] **Step 9: Commit**

```bash
git add channels/ tests/test_channels.py
git commit -m "feat: add multi-channel abstraction with WhatsApp and Telegram channels"
```

---

## Task 9: main.py — refatoração completa

**Files:**
- Modify: `main.py`

Esta task integra tudo que foi construído: config, session_store, channels.
A lógica de negócio não muda — só a infraestrutura de entrada/saída.

- [ ] **Step 1: Reescrever main.py**

Substitua o conteúdo completo de `main.py`:

```python
"""
Argos — Entrypoint FastAPI
Recebe webhooks de qualquer canal registrado e processa com o grafo LangGraph.
"""
import logging
import os
import time
from collections import defaultdict
from contextlib import asynccontextmanager

from dotenv import load_dotenv

load_dotenv()

# Validação de env vars — falha ruidosamente se config incompleta
import config
config.validate()

from fastapi import FastAPI, Request, HTTPException
from langchain_core.messages import HumanMessage, AIMessage

from graph import argos
from state import AgentState
import session_store as store
from channels import WhatsAppChannel, TelegramChannel
from webhook_stripe import router as stripe_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger("argos")

# ── Rate limiting ──────────────────────────────────────────────────────────
_call_timestamps: dict[str, list[float]] = defaultdict(list)
_MAX_POR_MINUTO = int(os.getenv("MAX_CALLS_POR_MINUTO", "5"))
_MAX_POR_HORA   = int(os.getenv("MAX_CALLS_POR_HORA", "20"))
_MAX_MSG_LEN    = int(os.getenv("MAX_MSG_LEN", "4000"))


def _permitir_chamada(chave: str) -> bool:
    agora = time.monotonic()
    _call_timestamps[chave] = [t for t in _call_timestamps[chave] if agora - t < 3600]
    por_minuto = sum(1 for t in _call_timestamps[chave] if agora - t < 60)
    por_hora   = len(_call_timestamps[chave])
    if por_minuto >= _MAX_POR_MINUTO or por_hora >= _MAX_POR_HORA:
        return False
    _call_timestamps[chave].append(agora)
    return True


def _nova_sessao(canal: str = "whatsapp", numero: str = "") -> AgentState:
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
        canal_origem=canal,
        usa_whatsapp=None,
        lead_qualificado=None,
        objecao_ativa=None,
        numero=numero,
    )


# ── Canais registrados ─────────────────────────────────────────────────────
CANAIS = {
    "whatsapp": WhatsAppChannel(),
    "telegram": TelegramChannel(),
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Registrar webhook do Telegram no startup
    tg_token  = os.getenv("TELEGRAM_BOT_TOKEN", "")
    tg_secret = os.getenv("TELEGRAM_WEBHOOK_SECRET", "")
    base_url  = os.getenv("BASE_URL", "")

    if tg_token and base_url:
        canal_tg = CANAIS["telegram"]
        wh_url = f"{base_url.rstrip('/')}/webhook/telegram"
        ok = canal_tg.setup_webhook(wh_url, tg_secret)
        logger.info("🤖 Telegram webhook registrado: %s → %s", wh_url, "OK" if ok else "ERRO")
    else:
        logger.warning("⚠️  Telegram não configurado (TELEGRAM_BOT_TOKEN ou BASE_URL ausente)")

    # Limpeza de sessões antigas
    deleted = store.cleanup_old(days=30)
    logger.info("🧹 Cleanup: %d sessões antigas removidas", deleted)

    logger.info("🟢 Argos iniciado — canais: %s", list(CANAIS.keys()))
    yield
    logger.info("🔴 Argos encerrado.")


app = FastAPI(title="Argos — Dia Solutions", lifespan=lifespan)
app.include_router(stripe_router)


def _enviar_respostas(canal, numero: str, estado_antes: dict, estado_depois: dict):
    """Extrai mensagens novas do estado e envia via canal."""
    qtd_antes = len(estado_antes["messages"])
    novas = estado_depois["messages"][qtd_antes:]

    for msg in novas:
        if isinstance(msg, AIMessage) and msg.content:
            texto = msg.content if isinstance(msg.content, str) else ""
            if not texto:
                for bloco in msg.content:
                    if isinstance(bloco, dict) and bloco.get("type") == "text":
                        texto = bloco.get("text", "")
                        break
            if texto:
                ok = canal.send(numero, texto)
                logger.info(
                    "[ARGOS→%s/%s] fase=%s msg=%s… ok=%s",
                    canal.name, numero[:6],
                    estado_depois.get("fase", "?"),
                    texto[:50], ok,
                )


@app.post("/webhook/{canal_nome}")
async def receber_mensagem(canal_nome: str, request: Request):
    """
    Webhook unificado — recebe eventos de qualquer canal registrado.
    Rota: POST /webhook/whatsapp ou POST /webhook/telegram
    (Nota: /webhook/stripe é tratado separadamente pelo stripe_router)
    """
    canal = CANAIS.get(canal_nome)
    if not canal:
        return {"status": "canal_desconhecido", "canal": canal_nome}

    # Validação de autenticidade para Telegram
    if canal_nome == "telegram":
        secret_recebido = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
        secret_esperado = os.getenv("TELEGRAM_WEBHOOK_SECRET", "")
        if secret_esperado and secret_recebido != secret_esperado:
            raise HTTPException(status_code=403, detail="Token inválido")

    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="JSON inválido")

    resultado = canal.parse_incoming(body)
    if not resultado:
        return {"status": "ignored"}

    numero, texto = resultado

    # Truncar mensagens muito longas antes de chamar o modelo
    if len(texto) > _MAX_MSG_LEN:
        logger.warning("[%s/%s] Mensagem truncada: %d chars", canal_nome, numero[:6], len(texto))
        texto = texto[:_MAX_MSG_LEN]

    # Rate limiting por canal+numero
    chave = f"{canal_nome}:{numero}"
    if not _permitir_chamada(chave):
        logger.warning("[RATE LIMIT] %s bloqueado", chave)
        return {"status": "rate_limited"}

    logger.info("[%s/%s→ARGOS] %s", canal_nome, numero[:6], texto[:80])

    # Carregar ou criar sessão
    estado = store.get(numero, canal_nome)
    if estado is None:
        estado = _nova_sessao(canal_nome, numero)
        logger.info("[ARGOS] Nova sessão: %s/%s", canal_nome, numero[:6])
    else:
        # Garantir que numero está sempre atualizado no estado
        estado["numero"] = numero

    estado_antes = {**estado, "messages": list(estado["messages"])}
    estado["messages"] = list(estado["messages"]) + [HumanMessage(content=texto)]

    # Invocar grafo
    try:
        novo_estado = argos.invoke(estado)
    except Exception as e:
        logger.exception("[ARGOS] Erro no grafo para %s/%s", canal_nome, numero)
        canal.send(numero, "Tive um problema técnico aqui. Pode repetir sua mensagem? 🙏")
        return {"status": "error", "detail": str(e)}

    # Persistir estado atualizado
    store.set(numero, novo_estado, canal_nome)

    # Enviar respostas ao lead
    _enviar_respostas(canal, numero, estado_antes, novo_estado)

    logger.info("[ARGOS] %s/%s → fase=%s", canal_nome, numero[:6], novo_estado.get("fase"))
    return {"status": "ok", "fase": novo_estado.get("fase")}


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "canais": list(CANAIS.keys()),
    }


@app.delete("/sessao/{canal}/{numero}")
async def resetar_sessao(canal: str, numero: str):
    """Reseta sessão de um lead. Útil para testes."""
    store.delete(numero, canal)
    return {"status": "resetado", "canal": canal, "numero": numero}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        reload=os.getenv("ENV", "production") == "development",
    )
```

- [ ] **Step 2: Verificar que o servidor importa sem erro**

```bash
cd /c/Users/Dell/argos
python -c "import main; print('OK')"
```

Saída esperada: `OK` (sem traceback)

- [ ] **Step 3: Rodar suite completa de testes**

```bash
pytest tests/ -v
```

Saída esperada: todos PASSED.

- [ ] **Step 4: Commit**

```bash
git add main.py
git commit -m "refactor: rewrite main.py with channel abstraction, Supabase sessions and config validation"
```

---

## Task 10: .env.example + variáveis finais

**Files:**
- Modify: `.env.example`

- [ ] **Step 1: Atualizar .env.example**

Substitua o conteúdo completo de `.env.example`:

```bash
# ── Claude / Anthropic ─────────────────────────────────────────────────────
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-opus-4-5

# ── UazAPI (WhatsApp) ──────────────────────────────────────────────────────
UAZAPI_URL=https://seu-servidor.uazapi.com
UAZAPI_TOKEN=seu-token-aqui
UAZAPI_INSTANCE=argos
UAZAPI_WEBHOOK_URL=https://sua-url-publica.com/webhook/whatsapp

# ── Stripe ─────────────────────────────────────────────────────────────────
STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
PRECO_CENTAVOS=4990             # R$49,90
SUCCESS_URL=https://seudominio.com.br/obrigado
CANCEL_URL=https://seudominio.com.br/

# ── Supabase ───────────────────────────────────────────────────────────────
SUPABASE_URL=https://xxxxxxxxxxxx.supabase.co
SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# ── Telegram ───────────────────────────────────────────────────────────────
# Token gerado via @BotFather — NUNCA compartilhe em chats ou commits
TELEGRAM_BOT_TOKEN=1234567890:AAxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
# UUID aleatório: python3 -c "import uuid; print(uuid.uuid4())"
TELEGRAM_WEBHOOK_SECRET=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
# URL pública HTTPS da VPS (usada para registrar webhook no Telegram)
BASE_URL=https://sua-url-publica.com

# ── Servidor ───────────────────────────────────────────────────────────────
PORT=8000
ENV=production                  # production | development (ativa reload)

# ── Limites e proteções ────────────────────────────────────────────────────
MAX_CALLS_POR_MINUTO=5          # máximo de invocações por número por minuto
MAX_CALLS_POR_HORA=20           # máximo por número por hora
TOOL_TIMEOUT_SECONDS=15         # timeout para chamadas a UazAPI/Stripe (segundos)
MAX_MSG_LEN=4000                # truncar mensagens maiores que N caracteres
```

- [ ] **Step 2: Commit**

```bash
git add .env.example
git commit -m "chore: update .env.example with all new required variables"
```

---

## Task 11: VPS — deploy e registro do webhook Telegram

Esta task é executada **na VPS**, não localmente.

- [ ] **Step 1: Gerar novo token do Telegram**

No Telegram, abra @BotFather e envie:
```
/token
```
Selecione `severo_diabot`. Copie o novo token. O token antigo está invalidado.

- [ ] **Step 2: Gerar TELEGRAM_WEBHOOK_SECRET**

Na VPS:
```bash
python3 -c "import uuid; print(uuid.uuid4())"
```

Copie o UUID gerado.

- [ ] **Step 3: Atualizar .env na VPS**

```bash
cd /opt/argos
nano .env
```

Adicione/atualize:
```
SUPABASE_URL=https://seuprojetoreal.supabase.co
SUPABASE_SERVICE_KEY=eyJ...chave-real...
TELEGRAM_BOT_TOKEN=<novo-token-do-botfather>
TELEGRAM_WEBHOOK_SECRET=<uuid-gerado-acima>
BASE_URL=https://sua-url-real.com
TOOL_TIMEOUT_SECONDS=15
MAX_MSG_LEN=4000
```

- [ ] **Step 4: Puxar código atualizado**

```bash
cd /opt/argos
git pull origin main
pip install -r requirements.txt
```

Saída esperada: `Successfully installed supabase-2.x.x` entre outros.

- [ ] **Step 5: Criar tabela no Supabase** (se ainda não fez)

Execute o SQL da Task 4 Step 1 no painel do Supabase.

- [ ] **Step 6: Reiniciar o serviço**

```bash
systemctl restart argos
systemctl status argos
```

Saída esperada nas primeiras linhas de log:
```
🤖 Telegram webhook registrado: https://sua-url.com/webhook/telegram → OK
🧹 Cleanup: 0 sessões antigas removidas
🟢 Argos iniciado — canais: ['whatsapp', 'telegram']
```

- [ ] **Step 7: Testar canal Telegram**

Abra o Telegram e acesse `t.me/severo_diabot`. Envie `Olá`.

Observe nos logs da VPS:
```bash
journalctl -u argos -f
```

Saída esperada:
```
[telegram/123456→ARGOS] Olá
[ARGOS→telegram/123456] fase=qualificacao_lead msg=Olá! Sou o Argos… ok=True
```

- [ ] **Step 8: Testar health endpoint**

```bash
curl https://sua-url.com/health
```

Saída esperada:
```json
{"status": "ok", "canais": ["whatsapp", "telegram"]}
```

- [ ] **Step 9: Testar reset de sessão Telegram**

```bash
curl -X DELETE https://sua-url.com/sessao/telegram/<seu-chat-id>
```

Saída esperada: `{"status": "resetado", "canal": "telegram", "numero": "<id>"}`

Envie outra mensagem no bot — deve começar o funil do zero.

---

## Checklist de Regressão Final

Antes de considerar o deploy completo:

- [ ] WhatsApp ainda recebe mensagens normalmente (testar com número real)
- [ ] `fromMe` ainda é ignorado no WhatsApp
- [ ] Rate limiting ainda bloqueia após 5 msgs/minuto
- [ ] Sessão persiste após `systemctl restart argos`
- [ ] Stripe webhook processa pagamento e avança fase corretamente
- [ ] `/health` retorna ambos os canais
- [ ] Logs mostram `canal/numero[:6]` em todo output (não número completo)
