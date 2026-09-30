# Eliminar Menções Restantes de "Argos" no Projeto Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Eliminar todas as menções residuais de "Argos" no projeto Severó — arquivos ativos do código, scripts de deploy, configuração, repositório GitHub e diretório local — para que o nome "Argos" deixe de aparecer em qualquer ponto de contato (logs, builds, clones).

**Architecture:** Substituição cirúrgica em 3 frentes: (1) **arquivos ativos** do código (`.env.example`, `deploy.sh`) — limpeza pura; (2) **repositório git** — rename remoto no GitHub + atualização do remote local + decisão sobre o nome do diretório local; (3) **docs históricos** (planos/specs antigos) — opção explícita de manter como registro ou arquivar com warning. Cada task gera commit independente; nenhuma quebra produção (todos os caminhos ativos já apontam para `severo`).

**Tech Stack:** Bash, Python (sed), git, GitHub web UI.

---

## Mapa de Arquivos / Pontos de Atualização

### Camada 1 — Arquivos ativos (devem ser limpos)

| Arquivo | Linhas com "argos" | O que fazer |
|---|---|---|
| `.env.example` | 8 | `UAZAPI_INSTANCE=argos` → `UAZAPI_INSTANCE=severo` |
| `deploy.sh` | 3, 9, 10, 11, 16, 71, 104 | Renomear marca, repo URL, paths, service name |

### Camada 2 — Identidade externa (rename one-shot)

| Recurso | De | Para |
|---|---|---|
| Repositório GitHub | `MykeMDGuimaraes/argos` | `MykeMDGuimaraes/severo` |
| `git remote origin` local | `https://github.com/MykeMDGuimaraes/argos.git` | `https://github.com/MykeMDGuimaraes/severo.git` |
| Diretório local de dev | `C:\Users\Dell\argos` | `C:\Users\Dell\severo` |

### Camada 3 — Docs históricos (decisão de design)

Esses arquivos **contam a história** do rename. Mexer reescreve registro.

| Arquivo | Status sugerido |
|---|---|
| `docs/superpowers/plans/2026-04-07-argos-hardening.md` | **Manter intacto** (plano original do hardening, antes do rename) |
| `docs/superpowers/specs/2026-04-07-argos-hardening-design.md` | **Manter intacto** (spec original) |
| `docs/superpowers/plans/2026-05-11-rename-argos-to-severo.md` | **Manter intacto** (plano que executou o rename) |

A Task 6 oferece a opção de arquivar para `docs/archive/` se o MD quiser sumir com qualquer string "argos" da árvore.

---

## Pré-condições (verificar antes de começar)

- [ ] **Branch limpa:** `cd /c/Users/Dell/argos && git status` retorna `nothing to commit, working tree clean`
- [ ] **Branch correta:** `git branch --show-current` retorna `feat/hardening-multichannel` (ou outra branch de feature, não `main`)
- [ ] **Backup mental:** os arquivos da Camada 1 não são copiados para a imagem Docker em runtime (só `.env`, `code`), então mudar `.env.example` e `deploy.sh` **não quebra produção**

---

## Task 1: Limpar `.env.example`

**Files:**
- Modify: `.env.example:8`

- [ ] **Step 1: Ler o arquivo**

```bash
cd /c/Users/Dell/argos
cat .env.example
```

Esperado: linha 8 contém `UAZAPI_INSTANCE=argos`.

- [ ] **Step 2: Aplicar substituição**

```bash
sed -i 's/^UAZAPI_INSTANCE=argos$/UAZAPI_INSTANCE=severo/' .env.example
```

- [ ] **Step 3: Verificar**

```bash
grep -n "argos" .env.example
```

Esperado: saída vazia.

```bash
grep -n "UAZAPI_INSTANCE" .env.example
```

Esperado: `8:UAZAPI_INSTANCE=severo`

- [ ] **Step 4: Commit**

```bash
git add .env.example
git commit -m "chore: atualizar UAZAPI_INSTANCE default no .env.example para severo"
```

---

## Task 2: Limpar `deploy.sh`

**Files:**
- Modify: `deploy.sh:3, 9, 10, 11, 16, 71, 104`

Este script é o deploy legacy (systemd em `/opt/argos`). Hoje a VPS roda via EasyPanel/Docker Swarm, mas o script ainda está no repo e qualquer um clonando pode rodar — precisa apontar para o nome novo.

- [ ] **Step 1: Aplicar todas as substituições com sed**

```bash
cd /c/Users/Dell/argos

sed -i 's|# Argos — Deploy Script|# Severo — Deploy Script|' deploy.sh
sed -i 's|REPO="https://github.com/MykeMDGuimaraes/argos.git"|REPO="https://github.com/MykeMDGuimaraes/severo.git"|' deploy.sh
sed -i 's|APP_DIR="/opt/argos"|APP_DIR="/opt/severo"|' deploy.sh
sed -i 's|SERVICE_NAME="argos"|SERVICE_NAME="severo"|' deploy.sh
sed -i 's|🤖 Argos — Deploy Automático|🤖 Severo — Deploy Automático|' deploy.sh
sed -i 's|Description=Argos — Agente Conversacional Dia Solutions|Description=Severo — Agente Conversacional Dia Solutions|' deploy.sh
sed -i 's|  2\. Inicie o Argos:|  2. Inicie o Severo:|' deploy.sh
```

- [ ] **Step 2: Verificar**

```bash
grep -ni "argos" deploy.sh
```

Esperado: saída vazia.

- [ ] **Step 3: Sanity check da sintaxe bash**

```bash
bash -n deploy.sh
```

Esperado: nenhum output (script sintaticamente válido).

- [ ] **Step 4: Commit**

```bash
git add deploy.sh
git commit -m "chore: renomear referências argos → severo em deploy.sh (repo, paths, service name)"
```

---

## Task 3: Renomear repositório no GitHub (manual via web UI)

**Files:** Nenhum local — operação remota.

- [ ] **Step 1: Acessar Settings do repo**

Navegar para: `https://github.com/MykeMDGuimaraes/argos/settings`

- [ ] **Step 2: Renomear**

- Em **General → Repository name** alterar de `argos` para `severo`
- Clicar **Rename**

GitHub mantém redirect automático de `argos` → `severo` por um tempo, mas é melhor atualizar o remote local imediatamente (próxima task).

- [ ] **Step 3: Confirmar acesso ao novo URL**

```bash
curl -sI https://github.com/MykeMDGuimaraes/severo | grep -i "^HTTP"
```

Esperado: `HTTP/2 200` (ou redirect 301 que resolve para 200).

---

## Task 4: Atualizar `git remote` local para apontar para o novo repo

**Files:**
- Modify: `.git/config` (via `git remote set-url`, não editar a mão)

- [ ] **Step 1: Atualizar o remote**

```bash
cd /c/Users/Dell/argos
git remote set-url origin https://github.com/MykeMDGuimaraes/severo.git
```

- [ ] **Step 2: Verificar**

```bash
git remote -v
```

Esperado:
```
origin	https://github.com/MykeMDGuimaraes/severo.git (fetch)
origin	https://github.com/MykeMDGuimaraes/severo.git (push)
```

- [ ] **Step 3: Teste de conectividade — fetch**

```bash
git fetch origin
```

Esperado: sem erro de autenticação; pode mostrar `From https://github.com/MykeMDGuimaraes/severo` e branches.

- [ ] **Step 4: Push das duas commits anteriores no novo remote**

```bash
git push origin feat/hardening-multichannel
```

Esperado: push aceito.

---

## Task 5: Renomear o diretório local de dev (Windows)

⚠️ **Pré-requisito:** fechar qualquer editor (VS Code, Cursor, etc.) que esteja com `C:\Users\Dell\argos` aberto, **antes** de renomear. Caso contrário o Windows bloqueia o move.

**Files:** Nenhum (operação de filesystem).

- [ ] **Step 1: Verificar que não há processo segurando a pasta**

PowerShell:
```powershell
Get-Process | Where-Object { $_.Path -like "*\argos\*" }
```

Esperado: sem output. Se houver processo, fechar antes de prosseguir.

- [ ] **Step 2: Renomear o diretório**

PowerShell (executar como usuário Dell, **fora** da pasta argos):
```powershell
cd C:\Users\Dell
Rename-Item -Path "argos" -NewName "severo"
```

Esperado: sem erro.

- [ ] **Step 3: Validar git ainda funciona após move**

```bash
cd /c/Users/Dell/severo
git status
git log --oneline -3
```

Esperado: git reconhece a pasta normalmente.

- [ ] **Step 4: (Opcional) Atualizar atalhos / hooks que apontam para o caminho antigo**

Procurar referências em configs de IDE:
```powershell
Select-String -Path $env:USERPROFILE\.vscode\* -Pattern "C:\\Users\\Dell\\argos" -SimpleMatch -ErrorAction SilentlyContinue
```

Se houver matches, ajustar manualmente.

---

## Task 6: Decisão sobre docs históricos (Argos hardening + rename plan)

**Files (afetados se escolher arquivar):**
- `docs/superpowers/plans/2026-04-07-argos-hardening.md`
- `docs/superpowers/specs/2026-04-07-argos-hardening-design.md`
- `docs/superpowers/plans/2026-05-11-rename-argos-to-severo.md`

Esses arquivos contam **o que aconteceu** — são registro histórico. Mexer no conteúdo (substituir argos→severo) reescreve a história. As duas opções:

### Opção A — MANTER intacto (recomendado)

Não fazer nada. Esses docs são registro do passado: existe arqueológico de que o projeto se chamou Argos. Vantagem: rastreabilidade da decisão de rename. Skip esta task.

### Opção B — ARQUIVAR para `docs/archive/`

Move docs para subpasta arquivada (sem alterar conteúdo). Faz `argos` desaparecer da árvore "ativa" mas preserva o registro.

- [ ] **Step 1 (Opção B): Criar pasta de arquivo**

```bash
cd /c/Users/Dell/severo  # nome novo após Task 5
mkdir -p docs/archive
```

- [ ] **Step 2 (Opção B): Mover arquivos com git mv (preserva histórico)**

```bash
git mv docs/superpowers/plans/2026-04-07-argos-hardening.md docs/archive/
git mv docs/superpowers/specs/2026-04-07-argos-hardening-design.md docs/archive/
git mv docs/superpowers/plans/2026-05-11-rename-argos-to-severo.md docs/archive/
```

- [ ] **Step 3 (Opção B): Criar README de arquivo**

Criar `docs/archive/README.md` com conteúdo:

```markdown
# Archive

Documentos preservados como registro histórico. Conteúdo não foi alterado.

- `2026-04-07-argos-hardening.md` — plano original do hardening, escrito quando o projeto se chamava Argos.
- `2026-04-07-argos-hardening-design.md` — spec original do hardening.
- `2026-05-11-rename-argos-to-severo.md` — plano que executou o rename Argos → Severo.
```

```bash
cat > docs/archive/README.md << 'EOF'
# Archive

Documentos preservados como registro histórico. Conteúdo não foi alterado.

- `2026-04-07-argos-hardening.md` — plano original do hardening, escrito quando o projeto se chamava Argos.
- `2026-04-07-argos-hardening-design.md` — spec original do hardening.
- `2026-05-11-rename-argos-to-severo.md` — plano que executou o rename Argos → Severo.
EOF
```

- [ ] **Step 4 (Opção B): Verificar**

```bash
ls docs/archive/
```

Esperado: 4 arquivos (3 .md + README).

```bash
grep -rni "argos" --include="*.md" docs/superpowers/
```

Esperado: saída vazia (todos os docs históricos saíram dessa subárvore).

- [ ] **Step 5 (Opção B): Commit**

```bash
git add docs/
git commit -m "chore: arquivar docs históricos do projeto Argos em docs/archive/"
```

---

## Task 7: Varredura final — confirmar que nenhum arquivo ativo menciona argos

**Files:** Nenhum (só verificação).

- [ ] **Step 1: Varrer todo o repo (excluindo docs/archive e .git)**

```bash
cd /c/Users/Dell/severo  # ou /c/Users/Dell/argos se pulou Task 5

grep -rni "argos" \
    --exclude-dir=.git \
    --exclude-dir=__pycache__ \
    --exclude-dir=.pytest_cache \
    --exclude-dir=archive \
    --include="*.py" --include="*.txt" --include="*.md" --include="*.sh" \
    --include="*.example" --include="Dockerfile" --include="*.yaml" \
    --include="*.yml" --include=".env*"
```

Esperado:
- Se escolheu **Opção A** (manter docs): só aparecem os 3 docs históricos em `docs/superpowers/plans/` e `docs/superpowers/specs/` + este próprio plano (`2026-05-20-erase-remaining-argos-mentions.md`).
- Se escolheu **Opção B** (arquivar): saída totalmente vazia exceto este plano que está sendo executado.

- [ ] **Step 2: Confirmar que testes seguem passando**

```bash
python -m pytest tests/ -v 2>&1 | tail -10
```

Esperado: `27 passed` (ou mais).

- [ ] **Step 3: Confirmar health do app em produção (não afetado)**

```bash
curl -sk https://severo.mdiasolutions.tech/health
```

Esperado: `{"status":"ok","canais":["whatsapp","telegram"]}`

---

## Task 8: Push final

- [ ] **Step 1: Push de todas as commits desta sessão**

```bash
cd /c/Users/Dell/severo  # ou caminho antigo
git push origin feat/hardening-multichannel
```

Esperado: push aceito; commits aparecem em `https://github.com/MykeMDGuimaraes/severo/commits/feat/hardening-multichannel`.

- [ ] **Step 2: Verificar no GitHub**

Abrir: `https://github.com/MykeMDGuimaraes/severo`

Confirmar:
- Nome do repo: **severo**
- Branch `feat/hardening-multichannel` com os commits novos
- `deploy.sh` no GitHub mostra `REPO="https://github.com/MykeMDGuimaraes/severo.git"`
- `.env.example` no GitHub mostra `UAZAPI_INSTANCE=severo`

---

## Checklist de Revisão Final

- [ ] `.env.example` linha 8 = `UAZAPI_INSTANCE=severo`
- [ ] `deploy.sh` sem string "argos" em nenhuma linha
- [ ] GitHub repo renomeado para `severo`
- [ ] `git remote -v` aponta para `severo.git`
- [ ] Diretório local renomeado (ou conscientemente mantido como `argos`)
- [ ] Docs históricos: decidiu manter ou arquivar (e executou)
- [ ] Suite de testes: 27/27 passando
- [ ] Health da prod: `200 OK`
- [ ] Push para `feat/hardening-multichannel` no novo remote
