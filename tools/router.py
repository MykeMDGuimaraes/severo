from langchain_core.tools import tool


@tool
def avancar_fase(proxima_fase: str) -> str:
    """
    Sinaliza ao grafo LangGraph que a fase atual terminou
    e qual é a próxima fase a ser executada.

    Fases válidas:
    - aprofundamento_da_dor
    - apresentacao_da_oferta
    - gerar_link_pagamento
    - confirmacao_pagamento
    - instrucao_conexao
    - conexao_estabelecida
    - encerrado
    """
    return f"AVANCAR_PARA:{proxima_fase}"


@tool
def registrar_lead(nome_lead: str, nome_clinica: str) -> str:
    """
    Registra o nome do lead e da clínica no sistema assim que
    forem coletados na conversa. Chame assim que tiver ambos os dados.
    """
    return f"REGISTRADO:{nome_lead}:{nome_clinica}"


@tool
def contornar_objecoes(texto_objecao: str) -> str:
    """
    Recebe o texto exato da objeção do lead e retorna
    a resposta calibrada para contornar sem pressão.
    """
    objecoes = {
        "caro": (
            "Entendo. Pensa assim: um único procedimento que você recupera "
            "já vale 20x isso. O diagnóstico mostra exatamente onde estão "
            "esses pacientes — essa semana."
        ),
        "pensar": (
            "Claro, sem problema. Só lembrando: enquanto você pensa, "
            "pacientes continuam chegando e sumindo sem você saber onde. "
            "O link fica ativo — pode usar quando quiser."
        ),
        "funciona": (
            "Pergunta justa. Já analisamos dezenas de clínicas e em todas "
            "encontramos oportunidades que não estavam visíveis. "
            "Se não identificarmos nada na sua — devolvemos o valor. Sem burocracia."
        ),
        "tempo": (
            "Do seu lado são menos de 3 minutos: você só conecta o WhatsApp "
            "da clínica via código de pareamento. O sistema faz o resto enquanto você atende."
        ),
        "garantia": (
            "100% garantido. Se não identificarmos nenhuma oportunidade na sua clínica, "
            "devolvemos o valor integral. Sem burocracia, sem perguntas."
        ),
    }
    texto_lower = texto_objecao.lower()
    for chave, resposta in objecoes.items():
        if chave in texto_lower:
            return resposta
    return (
        "Entendo sua dúvida. Me conta um pouco mais sobre o que está "
        "pesando na sua decisão — quero ter certeza que faz sentido para você."
    )
