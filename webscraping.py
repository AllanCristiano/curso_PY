import re
import asyncio
from playwright.async_api import async_playwright
# pip install playwright

# Variável global para armazenar o último número de pedido
ultimo_pedido = None

# Função para verificar e clicar no pedido no tbody
async def check_and_click_pedido(page, ultimo_pedido):
    try:
        # Localiza todos os links dentro do tbody com id 'tituloContext'
        links = page.locator('#tituloContext a')

        # Itera por cada link e verifica se algum corresponde ao `ultimo_pedido`
        count = await links.count()
        for i in range(count):
            link_text = await links.nth(i).text_content()
            link_text = link_text.strip()  # Remove espaços desnecessários
            print(f"Verificando link: {link_text}")

            # Compara com o número do último pedido
            if ultimo_pedido in link_text:
                print(f"Pedido {ultimo_pedido} encontrado! Clicando no link...")
                await links.nth(i).click()  # Clica no link correspondente
                return True  # Retorna após o clique

        print(f"Pedido {ultimo_pedido} NÃO encontrado no tbody.")
        return False
    except Exception as e:
        print(f"Erro ao verificar e clicar no tbody: {e}")
        return False


async def handle_anuidades(new_page, num):
    """
    Extrai o número do pedido, verifica se inicia com 'br51' ou 'mu'
    e, com base nisso, clica em "Próximo" ou tenta abrir o modal de anuidades.
    Caso o modal seja aberto, extrai os valores das anuidades usando regex.
    """
    global ultimo_pedido  # Permite modificar a variável global
    pedido_text = await new_page.text_content('font.marcador')
    pedido_text = pedido_text.strip().lower()
    print(f"{num} Número do pedido: {pedido_text}")

    # Atualiza o último número de pedido acessado
    ultimo_pedido = pedido_text
    print(f"Último pedido registrado: {ultimo_pedido}")

    if pedido_text.startswith('br51') or pedido_text.startswith('mu'):
        await new_page.wait_for_selector('a.titulo')
        await new_page.get_by_text("Próximo").click()
    else:
        if await new_page.locator("#botaoModal").is_visible():
            await new_page.click("#botaoModal")

            await new_page.wait_for_selector("#textoModalAnuidade", state="attached", timeout=30000)
            modal_text = await new_page.text_content("#textoModalAnuidade")
            print("Texto do modal:")
            print(modal_text)

            #Regex para pegar todos os valores
            values = re.findall(r"Valor: R\$ ?\$?([\d.,]+)", modal_text)
            print("Valores encontrados:", values)

            # Clique no "X" para fechar o modal
            await new_page.click('span.close')

        else:
            print("Anuidades não foram encontradas")
            await new_page.wait_for_selector('a.titulo')
            await new_page.get_by_text("Próximo").click()


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

        if ultimo_pedido == None:
            # Clica no primeiro link
            await new_page.wait_for_selector('#tituloContext a')
            first_link = new_page.locator('#tituloContext a').first
            await first_link.click()
            num = 0

        while True:
            num += 1
            try:
                if new_page.url == "https://busca.inpi.gov.br/pePI/":
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

                    # busca quem foi o ultimo
                    await check_and_click_pedido(new_page, ultimo_pedido)
                # Vai para as proximas patentes
                await new_page.wait_for_selector('a.titulo:has-text("Próximo")', state="visible", timeout=20000)
                await handle_anuidades(new_page, num)
            except Exception as e:
                print("O botão 'Próximo' não está mais presente. Encerrando loop.")
                print("Erro:", e)
                break

        # Aguarda um tempo para visualização
        await asyncio.sleep(10)
        await browser.close()

asyncio.run(main())
