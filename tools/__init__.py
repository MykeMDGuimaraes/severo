from .router import avancar_fase, contornar_objecoes, registrar_lead
from .whatsapp import criar_instancia_whatsapp, verificar_conexao_whatsapp
from .pagamento import gerar_link_pagamento

ALL_TOOLS = [
    avancar_fase,
    contornar_objecoes,
    registrar_lead,
    gerar_link_pagamento,
    criar_instancia_whatsapp,
    verificar_conexao_whatsapp,
]
