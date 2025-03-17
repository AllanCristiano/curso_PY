import re
import asyncio
import openpyxl
from openpyxl import Workbook
from playwright.async_api import async_playwright

# Função para salvar informações em uma planilha
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

async def handle_anuidades(new_page, nome_arquivo):
    """
    Extrai o número do pedido, verifica se inicia com 'br51' ou 'mu'
    e, com base nisso, clica em "Próximo" ou tenta abrir o modal de anuidades.
    Caso o modal seja aberto, extrai os valores das anuidades e as datas.
    Salva os dados mesmo se não houver anuidades.
    """
    # Extrai o número do pedido
    pedido_text = await new_page.text_content('font.marcador')
    pedido_text = pedido_text.strip().lower()
    print(f"Número do pedido: {pedido_text}")

    # Localiza a célula contendo a "Data do Depósito" e extrai o texto da data
    try:
        deposit_date_element = await new_page.locator('td:has-text("Data do Depósito:") + td font.normal').text_content()
        deposit_date = deposit_date_element.strip()  # Remove espaços desnecessários
        print(f"Data do Depósito encontrada: {deposit_date}")
    except Exception as e:
        print("Erro ao extrair a Data do Depósito:", e)
        deposit_date = "Data não encontrada"

    pagamentos = []  # Lista para armazenar os pagamentos e suas datas

    if pedido_text.startswith('br51') or pedido_text.startswith('mu'):
        await new_page.wait_for_selector('a.titulo')
        await new_page.get_by_text("Próximo").click()
    else:
        if await new_page.locator("#botaoModal").is_visible():
            print("Abrindo o modal...")
            await new_page.click("#botaoModal")

            await new_page.wait_for_selector("#textoModalAnuidade", state="attached", timeout=30000)
            modal_text = await new_page.text_content("#textoModalAnuidade")

            # Regex para pegar todos os valores
            values = re.findall(r"Valor: R\$ ?\$?([\d.,]+)", modal_text)
            print(f"Valores encontrados: {values}")

            # Regex para pegar todas as datas de pagamento
            datas_pagamento = re.findall(r"Data Pagamento: (\d{2}/\d{2}/\d{4})", modal_text)
            print(f"Datas de Pagamento encontradas: {datas_pagamento}")

            # Emparelha os valores e as datas em uma lista de tuplas
            pagamentos = list(zip(values, datas_pagamento))
            print(f"Pagamentos prontos para salvar: {pagamentos}")

            await new_page.click('span.close')
        else:
            print("Modal de anuidades não foi encontrado.")
            await new_page.get_by_text("Próximo").click()

    # Salvar os dados mesmo se não houver pagamentos
    if not pagamentos:
        print("Nenhuma anuidade encontrada, salvando sem pagamentos.")
        pagamentos = [("Sem anuidade", "Sem data")]  # Placeholder para ausência de anuidades

    salvar_em_planilha(nome_arquivo, pedido_text, deposit_date, pagamentos)

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        # Abre o site desejado
        url = "https://busca.inpi.gov.br/pePI/jsp/patentes/PatenteSearchBasico.jsp"
        await page.goto(url)
        print("Página carregada com sucesso!")

        # Clica no link que abre uma nova guia e captura a nova página
        async with page.expect_popup() as popup_info:
            await page.click('a[href="/pePI/servlet/LoginController?action=login"]')
        new_page = await popup_info.value
        await new_page.wait_for_load_state()
        print("Nova guia aberta:", new_page.url)

        # Lida com o elemento <area>
        area_href = await new_page.get_attribute('area[href*="PatenteSearchBasico.jsp"]', 'href')
        if area_href:
            full_url = new_page.url.split('/pePI')[0] + area_href
            print("Navegando para o URL do elemento <area>:", full_url)
            await new_page.goto(full_url)
        else:
            print("Elemento <area> não encontrado ou sem atributo href.")

        # Preenche o input na nova guia
        cnpj_ufs = "13.031.547/0001-04"
        await new_page.wait_for_selector('input[name="ExpressaoPesquisa"]')
        await new_page.fill('input[name="ExpressaoPesquisa"]', cnpj_ufs)
        print("Input preenchido com sucesso!")

        # Seleciona a opção no <select>
        await new_page.wait_for_selector('select[name="Coluna"]')
        await new_page.eval_on_selector('select[name="Coluna"]', """(el) => {
            el.value = 'CpfCnpjDepositante';
            el.dispatchEvent(new Event('change', { bubbles: true }));
        }""")

        # Clica no botão de pesquisa
        await new_page.wait_for_selector('input[name="botao"]')
        await new_page.click('input[name="botao"]')

        # Define o nome do arquivo da planilha
        nome_arquivo = "dados_pagamentos.xlsx"

        # Clica no primeiro link
        await new_page.wait_for_selector('#tituloContext a')
        first_link = new_page.locator('#tituloContext a').first
        await first_link.click()

        leitura = 20  # Número de leituras
        while leitura > 0:  # Loop para realizar no máximo 20 leituras
            try:
                # Processa as anuidades
                await handle_anuidades(new_page, nome_arquivo)

                # Vai para as próximas patentes
                await new_page.wait_for_selector('a.titulo:has-text("Próximo")', state="visible", timeout=20000)
                await new_page.get_by_text("Próximo").click()

            except Exception as e:
                print("Erro ao processar ou o botão 'Próximo' não está mais presente. Encerrando loop.")
                print("Erro:", e)
                break

        # Aguarda um tempo para visualização
        await asyncio.sleep(10)
        await browser.close()

asyncio.run(main())
