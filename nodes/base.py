"""
Factory de nós do Argos.

Cada nó segue o mesmo ciclo:
  1. Monta contexto (SystemMessage + histórico)
  2. Invoca o modelo
  3. Processa tool calls:
     - avancar_fase   → atualiza state["fase"]
     - registrar_lead → atualiza nome_lead / nome_clinica
     - action tools   → executa, adiciona ToolMessage, re-invoca
  4. Retorna apenas os novos campos/mensagens (add_messages cuida do append)
"""

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


def create_agent_node(fase_nome: str):
    """
    Retorna um nó LangGraph para a fase indicada.
    O nó invoca o modelo com o system prompt correto e processa
    qualquer tool call antes de retornar o estado atualizado.
    """

    def node(state: dict) -> dict:
        system_prompt = get_prompt_fase(fase_nome)
        base_messages = [SystemMessage(content=system_prompt)] + list(state["messages"])

        new_messages: list = []
        updates: dict = {}
        current_messages = base_messages

        for iteration in range(MAX_TOOL_ITERATIONS):
            response: AIMessage = _model_with_tools.invoke(current_messages + new_messages)
            new_messages.append(response)

            tool_calls = getattr(response, "tool_calls", []) or []
            if not tool_calls:
                break  # sem tools → resposta final

            tool_messages: list[ToolMessage] = []
            has_action_tools = False

            for tc in tool_calls:
                name: str = tc["name"]
                args: dict = tc["args"]
                tid: str = tc["id"]

                # ── Ferramentas de roteamento ───────────────────────
                if name == "avancar_fase":
                    proxima = args.get("proxima_fase", state["fase"])
                    updates["fase"] = proxima
                    tool_messages.append(ToolMessage(
                        content=f"Fase avançada para: {proxima}",
                        tool_call_id=tid,
                    ))
                    logger.info("[ARGOS] avancar_fase → %s", proxima)

                elif name == "registrar_lead":
                    updates["nome_lead"] = args.get("nome_lead")
                    updates["nome_clinica"] = args.get("nome_clinica")
                    tool_messages.append(ToolMessage(
                        content="Dados do lead registrados com sucesso.",
                        tool_call_id=tid,
                    ))
                    logger.info("[ARGOS] registrar_lead → %s / %s",
                                args.get("nome_lead"), args.get("nome_clinica"))

                # ── Ferramentas de ação ─────────────────────────────
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
                    logger.info("[ARGOS] gerar_link_pagamento → %s",
                                updates.get("link_pagamento"))

                elif name == "criar_instancia_whatsapp":
                    has_action_tools = True
                    result = _execute(name, args)
                    if isinstance(result, dict):
                        updates["token_gerado"] = result.get("token", "")
                    tool_messages.append(ToolMessage(
                        content=str(result),
                        tool_call_id=tid,
                    ))
                    logger.info("[ARGOS] criar_instancia_whatsapp → token=%s",
                                updates.get("token_gerado"))

                elif name == "verificar_conexao_whatsapp":
                    has_action_tools = True
                    result = _execute(name, args)
                    if isinstance(result, dict):
                        updates["conexao_estabelecida"] = result.get("conectado", False)
                    tool_messages.append(ToolMessage(
                        content=str(result),
                        tool_call_id=tid,
                    ))
                    logger.info("[ARGOS] verificar_conexao_whatsapp → %s",
                                updates.get("conexao_estabelecida"))

                elif name == "contornar_objecoes":
                    has_action_tools = True
                    result = _execute(name, args)
                    tool_messages.append(ToolMessage(
                        content=str(result),
                        tool_call_id=tid,
                    ))

                else:
                    tool_messages.append(ToolMessage(
                        content=f"Tool '{name}' processada.",
                        tool_call_id=tid,
                    ))

            new_messages.extend(tool_messages)

            # Se apenas ferramentas de roteamento foram chamadas,
            # o modelo já gerou sua resposta em `content` → encerra loop
            if not has_action_tools:
                break

            # Há ferramentas de ação → re-invocar para gerar resposta
            # incorporando os resultados das tools
            if iteration == MAX_TOOL_ITERATIONS - 1:
                logger.warning("[ARGOS] MAX_TOOL_ITERATIONS atingido na fase %s", fase_nome)

        # Monta o retorno — só os deltas (add_messages faz o append)
        return {
            "messages": new_messages,
            "fase": updates.get("fase", state["fase"]),
            **{k: v for k, v in updates.items() if k != "fase"},
        }

    node.__name__ = f"node_{fase_nome}"
    return node
