# Dataset inicial para avaliação do sistema RAG
# Contém perguntas, respostas esperadas (ground truth) e referências de página do documento original.

evaluation_dataset = [
    {
        "question": "O que é Conhecimento Tradicional Associado?",
        "ground_truth_answer": """O Conhecimento Tradicional Associado (CTA) se refere ao conhecimento tradicional associado aos recursos genéticos da biodiversidade, ou seja, ao conhecimento desenvolvido pelos povos indígenas e comunidades tradicionais sobre o uso dos recursos naturais, incluindo plantas, animais e micro-organismos. Esse conhecimento é resultado da experiência e sabedoria acumuladas ao longo do tempo por essas comunidades em relação à biodiversidade. No contexto da Lei nº 13.123/2015, o acesso ao Conhecimento Tradicional Associado é definido como a pesquisa ou desenvolvimento tecnológico realizado sobre conhecimento tradicional associado ao patrimônio genético, que possibilite ou facilite o acesso ao patrimônio genético.""",
        "reference_page": None # Contexto não encontrado/especificado claramente
    },
    {
        "question": "Empresas de Pequeno Porte entram no CGen?",
        "ground_truth_answer": """O CGen é o Conselho de Gestão do Patrimônio Genético responsável por coordenar o assunto de acesso ao patrimônio genético e ao conhecimento tradicional associado. Já o SisGen é o Sistema Nacional de Gestão do Patrimônio Genético e do Conhecimento Tradicional Associado, ferramenta que deve ser utilizada por aquele que deseja cumprir a Lei 13.123/2015. As empresas de pequeno porte que realizam atividades de acesso possuem obrigações perante a Lei e devem utilizar o SisGen. Para saber mais sobre quando e como realizar o cadastro, consultar itens 36, 45, 46 e 48 do Guia Orientativo da ABIHPEC.""",
        "reference_page": 1 # Página incerta (1 ou 2), usando a primeira como referência inicial
    },
    {
        "question": "Empresas de Pequeno Porte devem se cadastrar?",
        "ground_truth_answer": """Sim, o cadastro realizado perante ao SisGen deve ser realizado por qualquer pessoa física ou jurídica que realize acesso ao patrimônio genético ou conhecimento tradicional associado, independentemente do porte da empresa. Para saber mais sobre quando e como realizar o cadastro, consultar itens 36, 45, 46 e 48 do Guia Orientativo da ABIHPEC.""",
        "reference_page": 1 # Página incerta (1 ou 2), usando a primeira como referência inicial
    },
    {
        "question": "Empresas de Pequeno Porte devem realizar a repartição de benefícios?",
        "ground_truth_answer": """Não, de acordo com o art. 17, §5o, inciso I da Lei 13.123/2015 e art. 54, inciso II, do Decreto no 8772, as microempresas e empresas de pequeno porte estão isentas da repartição de benefícios. Por outro lado, não estão isentas de outras obrigações, como cadastrar e notificar. Mais informações consultar item no 36 e 48 do Guia Orientativo da ABIHPEC.""",
        "reference_page": 1 # Página incerta (1 ou 2), usando a primeira como referência inicial
    },
    {
        "question": "Onde posso encontrar a lista de insumos?",
        "ground_truth_answer": """Não existe uma lista de espécies consideradas patrimônio genético brasileiro nem mesmo de matérias-primas oriundas da biodiversidade brasileira. Não existe a pretensão de se criar uma uma lista oficial. O Ministério da Agricultura, Pecuária e Abastecimento (MAPA) criou duas listas que indicam as espécies exóticas que adquiriram ou não características distintivas próprias no Brasil, contudo não são extensas e legalmente podem ser revistas a qualquer hora, tendo já sido questionadas por alguns setores, portanto, não trazem a segurança jurídica necessária. Para classificação como biodiversidade brasileira é necessário um estudo de classificação das áreas de distribuição e ocorrência da espécie. Mais informações consultar o item no 12 do Guia Informativo da ABIHPEC.""",
        "reference_page": 1 # Página incerta (1 ou 2), usando a primeira como referência inicial
    },
    # Adicione mais exemplos aqui conforme necessário
]

# Exemplo de como acessar os dados:
# first_question = evaluation_dataset[0]["question"]
# first_answer = evaluation_dataset[0]["ground_truth_answer"]
