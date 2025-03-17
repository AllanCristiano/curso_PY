import openpyxl
from openpyxl import Workbook

def salvar_em_planilha(nome_arquivo, numero_pedido, data_deposito, pagamentos):
    """
    Salva as informações em uma planilha.
    Se a planilha já existir, adiciona novas linhas. Caso contrário, cria uma nova.
    """
    try:
        # Tenta abrir a planilha existente
        workbook = openpyxl.load_workbook(nome_arquivo)
        sheet = workbook.active
        print("Planilha existente carregada.")
    except FileNotFoundError:
        # Se o arquivo não existe, cria um novo
        workbook = Workbook()
        sheet = workbook.active
        # Adiciona cabeçalhos
        sheet.append(["Número do Pedido", "Data do Depósito", "Valor", "Data do Pagamento"])
        print("Nova planilha criada.")

    # Adiciona as informações à planilha
    for pagamento, data_pagamento in pagamentos:
        sheet.append([numero_pedido, data_deposito, pagamento, data_pagamento])
        print(f"Linha adicionada: {numero_pedido}, {data_deposito}, {pagamento}, {data_pagamento}")

    # Salva a planilha
    workbook.save(nome_arquivo)
    print(f"Planilha salva com sucesso em: {nome_arquivo}")

# Código de teste
if __name__ == "__main__":
    nome_arquivo = "teste_planilha.xlsx"  # Nome da planilha
    numero_pedido = "BR 10 2025 001846 2"  # Número do pedido de teste
    data_deposito = "30/01/2025"  # Data de depósito de teste
    pagamentos = [
        ("R$ 118.00", "15/03/2021"),
        ("R$ 118.00", "17/02/2022"),
        ("R$ 118.00", "15/02/2023")
    ]

    # Testa a função
    salvar_em_planilha(nome_arquivo, numero_pedido, data_deposito, pagamentos)
