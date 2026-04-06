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


def _rotear(state: dict) -> str:
    """
    Decide para qual nó ir baseado no campo `fase` do estado.
    Se fase == 'encerrado' ou não reconhecida → END.
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

    # ── Ponto de entrada ───────────────────────────────────────────
    grafo.set_entry_point("qualificacao_lead")

    # ── Roteamento condicional (avanço de fase dentro da invocação) ─
    fases_com_avanco = [
        "qualificacao_lead",
        "aprofundamento_da_dor",
        "apresentacao_da_oferta",
        "gerar_link_pagamento",
        "confirmacao_pagamento",
        "instrucao_conexao",
    ]
    for fase in fases_com_avanco:
        grafo.add_conditional_edges(fase, _rotear)

    # Fase final sempre termina
    grafo.add_edge("conexao_estabelecida", END)

    return grafo.compile()


# Instância global do agente compilado
argos = criar_grafo()
