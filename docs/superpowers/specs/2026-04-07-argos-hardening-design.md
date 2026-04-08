# Argos — Hardening & Multi-Canal: Design Spec
**Data:** 2026-04-07
**Status:** Aprovado
**Abordagem escolhida:** C — Faseada por camada

---

## Contexto

Argos é um agente conversacional PLG para WhatsApp que guia clínicas por um funil de 7 fases até a compra do produto "Choque de Gestão" (R$49,90) via Stripe. Stack: Python + LangGraph + Claude Opus + FastAPI + UazAPI.

O sistema está em produção na VPS mas sem clientes reais ainda — janela ideal para fixes estruturais.

**Problema raiz que motivou este spec:** um loop no grafo (nodes encadeando automaticamente via `add_conditional_edges`) causou 7 chamadas Opus por webhook → $36 de custo em uma única sessão. O loop de grafo foi corrigido previamente. Este spec endereça os problemas de estabilidade, receita e expansão de canal que restaram.

---

## Fase 1 — Estabilidade e Proteção de Receita

### 1.1 Persistência de Sessões via Supabase

**Problema:** sessões vivem em `dict` na RAM — qualquer restart do servidor apaga todos os leads em andamento.

**Solução:** novo arquivo `session_store.py` que encapsula acesso ao Supabase. `main.py` interage apenas com a interface pública do store — ignorante de qual backend está por baixo.

**Tabela Supabase:**
```sql
CREATE TABLE argos_sessions (
    numero      TEXT NOT NULL,
    canal       TEXT NOT NULL DEFAULT 'whatsapp',
    state       JSONB NOT NULL,
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (numero, canal)
);

CREATE INDEX idx_argos_sessions_updated_at ON argos_sessions (updated_at);
```

**Interface pública do `session_store.py`:**
```python
def get(numero: str, canal: str = "whatsapp") -> AgentState | None
def set(numero: str, estado: AgentState, canal: str = "whatsapp") -> None
def delete(numero: str, canal: str = "whatsapp") -> None
def cleanup_old(days: int = 30) -> int  # retorna qtd deletada
```

**Fluxo no webhook:**
```
receber mensagem
  → store.get(numero, canal)  # carrega do Supabase
  → invocar grafo
  → store.set(numero, novo_estado, canal)  # salva no Supabase
  → enviar resposta
```

**Variáveis de ambiente necessárias:**
```
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_SERVICE_KEY=eyJ...
```

**Dependências:** `supabase-py` (já pode estar na stack; se não, adicionar).

---

### 1.2 Stripe por `session_id` (não por nome do lead)

**Problema:** `webhook_stripe.py` busca sessão por `nome_lead` — dois leads com o mesmo nome no funil causam atribuição errada de pagamento.

**Fix em `tools/pagamento.py`:** a tool `gerar_link_pagamento` recebe `numero` (via estado) e o inclui nos metadados do checkout:
```python
metadata={"numero": numero, "canal": canal, "nome_lead": nome_lead}
```

**Fix em `webhook_stripe.py`:** lookup passa a ser:
```python
numero = meta.get("numero")
canal  = meta.get("canal", "whatsapp")
estado = store.get(numero, canal)
```

Lookup O(1), sem ambiguidade, sem race condition.

**Consequência:** a tool precisa receber `numero` e `canal` do estado. `base.py` passa esses campos ao invocar `gerar_link_pagamento`.

---

### 1.3 Pix via Stripe

**Problema:** prompts prometem "Pix, cartão de crédito ou débito" mas código só aceita cartão.

**Fix em `tools/pagamento.py`:**
```python
payment_method_types=["card", "pix"],
```

Stripe suporta Pix nativamente no Brasil. Nenhuma outra mudança necessária.

---

### 1.4 Timeout em Tool Calls

**Problema:** `fn.invoke(args)` em `nodes/base.py` não tem timeout — se UazAPI ou Stripe travar, o nó trava indefinidamente.

**Fix em `nodes/base.py`:**
```python
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout

TOOL_TIMEOUT = int(os.getenv("TOOL_TIMEOUT_SECONDS", "15"))

def _execute(tool_name: str, args: dict):
    fn = _TOOL_FN.get(tool_name)
    if fn is None:
        return f"Tool '{tool_name}' não encontrada."
    try:
        with ThreadPoolExecutor(max_workers=1) as ex:
            future = ex.submit(fn.invoke, args)
            return future.result(timeout=TOOL_TIMEOUT)
    except FuturesTimeout:
        logger.error("[ARGOS] Timeout na tool '%s' após %ds", tool_name, TOOL_TIMEOUT)
        return f"Erro: tool '{tool_name}' não respondeu em {TOOL_TIMEOUT}s."
    except Exception as e:
        logger.error("[ARGOS] Erro na tool '%s': %s", tool_name, e)
        return f"Erro ao executar '{tool_name}': {str(e)}"
```

O modelo recebe o erro como `ToolMessage` e pode responder ao lead com mensagem de retry.

**Variável de ambiente:**
```
TOOL_TIMEOUT_SECONDS=15
```

---

### 1.5 Validação de Env Vars no Startup

**Problema:** servidor sobe silenciosamente mesmo com configurações erradas ou ausentes.

**Novo arquivo `config.py`:**
```python
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

def validate():
    missing = [v for v in REQUIRED_VARS if not os.getenv(v)]
    if missing:
        print(f"[ARGOS] ERRO: variáveis obrigatórias ausentes: {', '.join(missing)}")
        raise SystemExit(1)
```

Chamado no topo de `main.py` antes de qualquer import de serviço.

---

## Fase 2 — Multi-Canal + Telegram

### 2.1 Abstração de Canal

**Problema:** lógica de parse de mensagem e envio está misturada em `main.py` e `tools/whatsapp.py`. Adicionar Telegram (ou qualquer canal futuro) exigiria duplicar código.

**Novo diretório `channels/`:**

```
channels/
├── __init__.py
├── base.py        # interface Channel
├── whatsapp.py    # implementação UazAPI
└── telegram.py    # implementação Telegram Bot API
```

**`channels/base.py`:**
```python
from abc import ABC, abstractmethod

class Channel(ABC):
    name: str  # "whatsapp" | "telegram"

    @abstractmethod
    def parse_incoming(self, body: dict) -> tuple[str, str] | None:
        """Extrai (identificador_usuario, texto) do payload do webhook.
        Retorna None se a mensagem deve ser ignorada."""

    @abstractmethod
    def send(self, numero: str, texto: str) -> bool:
        """Envia mensagem para o usuário. Retorna True se sucesso."""
```

**`channels/whatsapp.py`:** extrai o parsing que hoje está em `main.py` e o `enviar_mensagem` que está em `tools/whatsapp.py`. Sem alteração de comportamento.

**`channels/telegram.py`:** implementação nova (detalhada em 2.2).

**`main.py` refatorado:**
```python
CANAIS: dict[str, Channel] = {
    "whatsapp": WhatsAppChannel(),
    "telegram": TelegramChannel(),
}

@app.post("/webhook/{canal_nome}")
async def receber_mensagem(canal_nome: str, request: Request):
    canal = CANAIS.get(canal_nome)
    if not canal:
        return {"status": "canal_desconhecido"}
    resultado = canal.parse_incoming(await request.json())
    if not resultado:
        return {"status": "ignored"}
    numero, texto = resultado
    # ... resto do fluxo igual para qualquer canal
```

---

### 2.2 Canal Telegram

**Bot criado:** `t.me/severo_diabot`

**Autenticação do webhook:**
Telegram suporta `secret_token` no `setWebhook`. O token é verificado no header `X-Telegram-Bot-Api-Secret-Token`. Resolve o problema de autenticação que WhatsApp ainda não tem.

Setup do webhook (executado uma vez na VPS ou no startup):
```python
requests.post(
    f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/setWebhook",
    json={
        "url": f"{BASE_URL}/webhook/telegram",
        "secret_token": TELEGRAM_WEBHOOK_SECRET,
    }
)
```

**`channels/telegram.py` — parse_incoming:**
```python
def parse_incoming(self, body: dict) -> tuple[str, str] | None:
    # Valida secret token (já validado no middleware, mas dupla checagem)
    message = body.get("message") or body.get("edited_message")
    if not message:
        return None
    chat_id = str(message["chat"]["id"])
    texto = message.get("text", "").strip()
    if not texto:
        return None
    return chat_id, texto
```

**`channels/telegram.py` — send:**
```python
def send(self, chat_id: str, texto: str) -> bool:
    resp = requests.post(
        f"https://api.telegram.org/bot{self._token}/sendMessage",
        json={"chat_id": chat_id, "text": texto},
        timeout=10,
    )
    return resp.status_code == 200
```

**Identificação de sessão no Supabase:**
- `canal = "telegram"`
- `numero = str(chat_id)` — não colide com sessões WhatsApp

**Limitações conhecidas (fase de testes):**
- Telegram não tem `fromMe` nativo — ignorar `edited_message` (messsages editadas) para evitar reprocessamento
- Fase de geração de instância WhatsApp funciona normalmente — lead recebe o par code como texto

**Variáveis de ambiente:**
```
TELEGRAM_BOT_TOKEN=<novo token após revogar o atual>
TELEGRAM_WEBHOOK_SECRET=<uuid gerado na VPS: python3 -c "import uuid; print(uuid.uuid4())">
BASE_URL=https://sua-url-publica.com  # usada no setWebhook
```

---

## Fase 3 — Operacional

### 3.1 Cleanup de Sessões Antigas

Task em background no evento `startup` do FastAPI:
```python
@asynccontextmanager
async def lifespan(app):
    deleted = store.cleanup_old(days=30)
    logger.info("[ARGOS] Cleanup: %d sessões antigas removidas", deleted)
    yield
```

`store.cleanup_old` executa:
```sql
DELETE FROM argos_sessions
WHERE updated_at < now() - INTERVAL '30 days'
RETURNING numero;
```

---

### 3.2 Structured Logging

Todo log passa a incluir contexto do lead:
```python
logger.info("[%s/%s] fase=%s msg=%s", canal, numero[:6], fase, texto[:60])
```

Formato: `canal/número_parcial` para proteger privacidade nos logs enquanto mantém rastreabilidade.

---

### 3.3 Limite de Tamanho de Mensagem

Em `main.py`, após extrair o texto e antes de invocar o grafo:
```python
MAX_MSG_LEN = int(os.getenv("MAX_MSG_LEN", "4000"))
if len(texto) > MAX_MSG_LEN:
    logger.warning("[%s/%s] Mensagem truncada: %d chars", canal, numero, len(texto))
    texto = texto[:MAX_MSG_LEN]
```

---

## Arquitetura Final de Arquivos

```
argos/
├── config.py              # [NOVO] validação de env vars
├── session_store.py       # [NOVO] persistência Supabase
├── main.py                # [REFATORADO] agnóstico de canal
├── graph.py               # sem mudança
├── state.py               # sem mudança
├── webhook_stripe.py      # [FIX] lookup por numero/canal
├── channels/              # [NOVO]
│   ├── __init__.py
│   ├── base.py
│   ├── whatsapp.py
│   └── telegram.py
├── nodes/
│   └── base.py            # [FIX] timeout em tools
├── tools/
│   └── pagamento.py       # [FIX] Pix + metadata com numero
├── prompts/               # sem mudança
└── docs/
    └── superpowers/
        └── specs/
            └── 2026-04-07-argos-hardening-design.md
```

---

## Variáveis de Ambiente — Estado Final

```bash
# Anthropic
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-opus-4-5

# UazAPI
UAZAPI_URL=https://seu-servidor.uazapi.com
UAZAPI_TOKEN=seu-token-aqui
UAZAPI_INSTANCE=argos
UAZAPI_WEBHOOK_URL=https://sua-url-publica/webhook/whatsapp

# Stripe
STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
PRECO_CENTAVOS=4990
SUCCESS_URL=https://seudominio.com.br/obrigado
CANCEL_URL=https://seudominio.com.br/

# Supabase
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_SERVICE_KEY=eyJ...

# Telegram
TELEGRAM_BOT_TOKEN=<novo token>
TELEGRAM_WEBHOOK_SECRET=<uuid>
BASE_URL=https://sua-url-publica.com

# Servidor
PORT=8000
ENV=production

# Limites e proteções
MAX_CALLS_POR_MINUTO=5
MAX_CALLS_POR_HORA=20
TOOL_TIMEOUT_SECONDS=15
MAX_MSG_LEN=4000
```

---

## Dependências a Adicionar

```
supabase          # persistência de sessões
```

---

## O Que Este Spec NÃO Cobre

- Autenticação do webhook WhatsApp via signature (UazAPI pode não suportar — verificar documentação)
- Poda de histórico de mensagens (redução de custo de tokens a longo prazo)
- A/B testing de prompts por fase
- Dashboard de funil / analytics
- Suporte a múltiplos produtos (além do Choque de Gestão)
