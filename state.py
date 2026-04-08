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
