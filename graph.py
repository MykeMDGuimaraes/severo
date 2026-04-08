from langgraph.graph import StateGraph, END
from state import AgentState
from nodes import (
    node_qualificacao,
    node_aprofundamento,
    node_oferta,
    node_pagamento,
    node_confirmacao,
    node_conexao,
    node_estabelecida,
)

# Mapeamento fase → nó
FASE_PARA_NO = {
    "qualificacao_lead":      "qualificacao_lead",
    "aprofundamento_da_dor":  "aprofundamento_da_dor",
    "apresentacao_da_oferta": "apresentacao_da_oferta",
    "gerar_link_pagamento":   "gerar_link_pagamento",
    "confirmacao_pagamento":  "confirmacao_pagamento",
    "instrucao_conexao":      "instrucao_conexao",
    "conexao_estabelecida":   "conexao_estabelecida",
}


def _rotear_entrada(state: dict) -> str:
    """
    Roteador de entrada: decide qual nó executar baseado na fase atual.
    Chamado UMA vez por invocação — o nó executa e vai direto ao END.
    Isso garante que o grafo para após cada mensagem do lead,
    evitando encadeamento automático de nós (que causaria N chamadas
    ao modelo sem esperar resposta do usuário).
    """
    fase = state.get("fase", "qualificacao_lead")
    return FASE_PARA_NO.get(fase, END)


def criar_grafo() -> StateGraph:
    grafo = StateGraph(AgentState)

    # ── Registrar nós ──────────────────────────────────────────────
    grafo.add_node("qualificacao_lead",      node_qualificacao)
    grafo.add_node("aprofundamento_da_dor",  node_aprofundamento)
    grafo.add_node("apresentacao_da_oferta", node_oferta)
    grafo.add_node("gerar_link_pagamento",   node_pagamento)
    grafo.add_node("confirmacao_pagamento",  node_confirmacao)
    grafo.add_node("instrucao_conexao",      node_conexao)
    grafo.add_node("conexao_estabelecida",   node_estabelecida)

    # ── Roteador de entrada (nó passthrough sem custo) ─────────────
    # __inicio__ lê state["fase"] e roteia para o nó correto.
    # Após o nó executar, vai direto ao END — sem encadeamento.
    grafo.add_node("__inicio__", lambda state: {})
    grafo.set_entry_point("__inicio__")
    grafo.add_conditional_edges("__inicio__", _rotear_entrada)

    # ── Todos os nós terminam após executar ────────────────────────
    # O grafo para aqui. A próxima mensagem do lead inicia nova invocação
    # e __inicio__ roteia para a fase correta (que pode ter avançado).
    for no in FASE_PARA_NO.values():
        grafo.add_edge(no, END)

    return grafo.compile()


# Instância global do agente compilado
argos = criar_grafo()
