# Rename Argos → Severo Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Renomear o projeto de "Argos" para "Severo" em código, infra e Supabase, sem perda de sessões existentes.

**Architecture:** Substituição de referências no código (logger, table name, log prefixes, prompt, graph variable) + migração da tabela Supabase + atualização do Traefik/EasyPanel para o novo domínio `severo.mdiasolutions.tech`. O Telegram webhook se re-registra automaticamente no boot com a nova BASE_URL.

**Tech Stack:** Python 3.12, FastAPI, LangGraph, Supabase (JSONB), Traefik (EasyPanel), Docker Swarm, GitHub.

---

## Mapa de Arquivos

| Arquivo | O que muda |
|---|---|
| `session_store.py` | `_TABLE`, `getLogger` |
| `main.py` | `getLogger`, import `argos`, `argos.invoke`, FastAPI title, log prefixes |
| `nodes/base.py` | `getLogger`, log prefixes `[ARGOS]` |
| `channels/telegram.py` | `getLogger` |
| `channels/whatsapp.py` | `getLogger`, default UAZAPI_INSTANCE |
| `channels/base.py` | docstring |
| `tools/whatsapp.py` | default UAZAPI_INSTANCE, print/log prefix |
| `webhook_stripe.py` | `getLogger` |
| `config.py` | prefixo `[ARGOS]` na msg de erro |
| `graph.py` | variável `argos` → `severo` |
| `prompts/fases.py` | texto "Aqui é o Argos" → "Severo" |
| `tests/test_session_store.py` | assert `"argos_sessions"` → `"severo_sessions"` |
| VPS: Traefik `argos.yaml` | domínio + nome do arquivo |
| VPS: EasyPanel env vars | `BASE_URL` |
| Supabase | Rename tabela + migrar dados |

---

## Task 1: Renomear logger e table name nos módulos core

**Files:**
- Modify: `session_store.py`
- Modify: `webhook_stripe.py`
- Modify: `channels/telegram.py`
- Modify: `channels/whatsapp.py`
- Modify: `channels/base.py`

- [ ] **Step 1: Aplicar substituições**

```bash
cd /c/Users/Dell/argos

# session_store.py
sed -i 's/logging.getLogger("argos")/logging.getLogger("severo")/g' session_store.py
sed -i 's/_TABLE = "argos_sessions"/_TABLE = "severo_sessions"/' session_store.py
sed -i 's/Persistência de sessões do Argos/Persistência de sessões do Severo/' session_store.py

# webhook_stripe.py
sed -i 's/logging.getLogger("argos")/logging.getLogger("severo")/g' webhook_stripe.py

# channels
sed -i 's/logging.getLogger("argos")/logging.getLogger("severo")/g' channels/telegram.py
sed -i 's/logging.getLogger("argos")/logging.getLogger("severo")/g' channels/whatsapp.py
sed -i 's/do Argos\./do Severo./' channels/base.py
sed -i 's/pelo próprio Argos/pelo próprio Severo/' channels/whatsapp.py
sed -i 's/os.getenv("UAZAPI_INSTANCE", "argos")/os.getenv("UAZAPI_INSTANCE", "severo")/g' channels/whatsapp.py
```

- [ ] **Step 2: Verificar resultado**

```bash
grep -n "argos" session_store.py webhook_stripe.py channels/telegram.py channels/whatsapp.py channels/base.py
```

Esperado: **nenhuma linha** (saída vazia).

- [ ] **Step 3: Commit**

```bash
git add session_store.py webhook_stripe.py channels/telegram.py channels/whatsapp.py channels/base.py
git commit -m "refactor: renomear logger e table name argos → severo nos módulos core"
```

---

## Task 2: Renomear em nodes, tools, config e prompts

**Files:**
- Modify: `nodes/base.py`
- Modify: `tools/whatsapp.py`
- Modify: `config.py`
- Modify: `prompts/fases.py`

- [ ] **Step 1: Aplicar substituições**

```bash
cd /c/Users/Dell/argos

# nodes/base.py
sed -i 's/logging.getLogger("argos")/logging.getLogger("severo")/g' nodes/base.py
sed -i 's/\[ARGOS\]/[SEVERO]/g' nodes/base.py
sed -i 's/Factory de nós do Argos/Factory de nós do Severo/' nodes/base.py

# tools/whatsapp.py
sed -i 's/os.getenv("UAZAPI_INSTANCE", "argos")/os.getenv("UAZAPI_INSTANCE", "severo")/g' tools/whatsapp.py
sed -i 's/\[ARGOS\]/[SEVERO]/g' tools/whatsapp.py
sed -i 's/da instância principal do Argos/da instância principal do Severo/' tools/whatsapp.py

# config.py
sed -i 's/\[ARGOS\]/[SEVERO]/g' config.py

# prompts/fases.py
sed -i "s/Aqui é o Argos, da Dia Solutions/Aqui é o Severo, da Dia Solutions/" prompts/fases.py
```

- [ ] **Step 2: Verificar resultado**

```bash
grep -rn "argos\|Argos\|ARGOS" nodes/base.py tools/whatsapp.py config.py prompts/fases.py
```

Esperado: nenhuma ocorrência.

- [ ] **Step 3: Commit**

```bash
git add nodes/base.py tools/whatsapp.py config.py prompts/fases.py
git commit -m "refactor: renomear prefixos ARGOS → SEVERO em nodes, tools, config e prompts"
```

---

## Task 3: Renomear variável do grafo e FastAPI title em main.py e graph.py

**Files:**
- Modify: `graph.py`
- Modify: `main.py`

- [ ] **Step 1: graph.py — renomear variável exportada**

Abrir `graph.py` e alterar a linha final:

```python
# ANTES
argos = criar_grafo()

# DEPOIS
severo = criar_grafo()
```

```bash
sed -i 's/^argos = criar_grafo()/severo = criar_grafo()/' /c/Users/Dell/argos/graph.py
```

- [ ] **Step 2: main.py — atualizar import, invocação, logger e title**

```bash
cd /c/Users/Dell/argos

sed -i 's/from graph import argos/from graph import severo/' main.py
sed -i 's/logging.getLogger("argos")/logging.getLogger("severo")/g' main.py
sed -i 's/\[ARGOS\]/[SEVERO]/g' main.py
sed -i 's/Argos — Entrypoint FastAPI/Severo — Entrypoint FastAPI/' main.py
sed -i 's/title="Argos — Dia Solutions"/title="Severo — Dia Solutions"/' main.py
sed -i 's/🟢 Argos iniciado/🟢 Severo iniciado/' main.py
sed -i 's/🔴 Argos encerrado/🔴 Severo encerrado/' main.py
sed -i 's/novo_estado = argos\.invoke/novo_estado = severo.invoke/' main.py
```

- [ ] **Step 3: Verificar**

```bash
grep -n "argos\|Argos\|ARGOS" main.py graph.py
```

Esperado: nenhuma ocorrência.

- [ ] **Step 4: Commit**

```bash
git add graph.py main.py
git commit -m "refactor: renomear variável do grafo e referências em main.py graph.py"
```

---

## Task 4: Atualizar testes

**Files:**
- Modify: `tests/test_session_store.py`

- [ ] **Step 1: Atualizar assert da tabela**

```bash
sed -i 's/"argos_sessions"/"severo_sessions"/g' /c/Users/Dell/argos/tests/test_session_store.py
```

- [ ] **Step 2: Rodar os testes**

```bash
cd /c/Users/Dell/argos
python -m pytest tests/ -v 2>&1 | tail -30
```

Esperado: todos os testes passando (27/27 ou mais).

- [ ] **Step 3: Commit**

```bash
git add tests/test_session_store.py
git commit -m "test: atualizar assert de argos_sessions → severo_sessions"
```

---

## Task 5: Migrar tabela no Supabase

**Objetivo:** Renomear `argos_sessions` → `severo_sessions` preservando todos os dados existentes.

- [ ] **Step 1: Executar SQL de migração via MCP (Supabase project: Mike / bfqqztxjfeiljdunxmaw)**

SQL a executar:
```sql
ALTER TABLE argos_sessions RENAME TO severo_sessions;
```

- [ ] **Step 2: Verificar que a tabela existe com os dados**

```sql
SELECT COUNT(*), canal FROM severo_sessions GROUP BY canal;
```

Esperado: retorna linhas (ou 0 se não houver sessões), sem erros.

- [ ] **Step 3: Verificar que `argos_sessions` não existe mais**

```sql
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public' AND table_name = 'argos_sessions';
```

Esperado: 0 rows.

---

## Task 6: Atualizar Traefik e EasyPanel na VPS

**Objetivo:** Apontar `severo.mdiasolutions.tech` → container Docker, remover rota `argos.mdiasolutions.tech`.

- [ ] **Step 1: Criar severo.yaml no Traefik**

Rodar no terminal SSH da VPS:

```bash
python3 << 'EOF'
import json

config = {
  "http": {
    "routers": {
      "http-severo-0": {
        "service": "severo-0",
        "rule": "Host(`severo.mdiasolutions.tech`) && PathPrefix(`/`)",
        "priority": 10,
        "middlewares": ["redirect-to-https@file", "bad-gateway-error-page@file"],
        "entryPoints": ["http"]
      },
      "https-severo-0": {
        "service": "severo-0",
        "rule": "Host(`severo.mdiasolutions.tech`) && PathPrefix(`/`)",
        "priority": 10,
        "middlewares": ["bad-gateway-error-page@file"],
        "tls": {
          "certResolver": "letsencrypt",
          "domains": [{"main": "severo.mdiasolutions.tech"}]
        },
        "entryPoints": ["https"]
      }
    },
    "services": {
      "severo-0": {
        "loadBalancer": {
          "servers": [{"url": "http://n8n_oc-argos-md:8000/"}],
          "passHostHeader": True
        }
      }
    }
  }
}

with open('/etc/easypanel/traefik/config/severo.yaml', 'w') as f:
    json.dump(config, f, indent=2)

print("OK")
EOF
```

- [ ] **Step 2: Remover argos.yaml antigo**

```bash
rm /etc/easypanel/traefik/config/argos.yaml
```

- [ ] **Step 3: Aguardar Traefik recarregar e testar**

```bash
sleep 5 && curl -sk https://severo.mdiasolutions.tech/health
```

Esperado: `{"status":"ok","canais":["whatsapp","telegram"]}`

- [ ] **Step 4: Atualizar BASE_URL no container Docker**

```bash
docker service update \
  --env-add BASE_URL=https://severo.mdiasolutions.tech \
  n8n_oc-argos-md
```

- [ ] **Step 5: Verificar logs — Telegram webhook com novo domínio**

```bash
sleep 15 && docker service logs n8n_oc-argos-md --raw --tail 10
```

Esperado:
```
🤖 Telegram webhook registrado: https://severo.mdiasolutions.tech/webhook/telegram → OK
🟢 Severo iniciado — canais: ['whatsapp', 'telegram']
```

---

## Task 7: Push final e rebuild EasyPanel

- [ ] **Step 1: Push da branch**

```bash
cd /c/Users/Dell/argos
git push
```

- [ ] **Step 2: Rebuild no EasyPanel**

No EasyPanel → projeto `n8n` → serviço `oc-argos-md` → **Deploy**.

O rebuild vai pegar:
- `session_store.py` com `_TABLE = "severo_sessions"`
- `.env` com `BASE_URL=https://severo.mdiasolutions.tech` (atualizar antes do rebuild)

- [ ] **Step 3: Atualizar .env no diretório do EasyPanel**

```bash
sed -i 's|BASE_URL=https://argos.mdiasolutions.tech|BASE_URL=https://severo.mdiasolutions.tech|' \
  /etc/easypanel/projects/n8n/oc-argos-md/code/.env
```

- [ ] **Step 4: Teste final completo**

```bash
# Health check
curl -sk https://severo.mdiasolutions.tech/health

# Verificar logs de startup
docker service logs n8n_oc-argos-md --raw --tail 15
```

Esperado:
```json
{"status":"ok","canais":["whatsapp","telegram"]}
```
```
🤖 Telegram webhook registrado: https://severo.mdiasolutions.tech/webhook/telegram → OK
🟢 Severo iniciado — canais: ['whatsapp', 'telegram']
```

- [ ] **Step 5: Testar no Telegram** — mandar mensagem no bot e confirmar resposta com memória entre mensagens.

---

## Checklist de Revisão

- [x] Logger renomeado em todos os 6 arquivos
- [x] `_TABLE` atualizado para `severo_sessions`
- [x] Variável `argos` → `severo` em graph.py e main.py
- [x] Prompt atualiza nome do agente para "Severo"
- [x] Testes atualizados
- [x] Tabela Supabase migrada (dados preservados)
- [x] Traefik roteando `severo.mdiasolutions.tech`
- [x] `BASE_URL` atualizado no container e no .env do EasyPanel
- [x] Telegram webhook re-registrado com novo domínio
- [ ] GitHub repo renomeado (fazer manualmente em Settings)
- [ ] Atualizar `UAZAPI_TOKEN` e `UAZAPI_INSTANCE` quando integração WhatsApp for ativada
