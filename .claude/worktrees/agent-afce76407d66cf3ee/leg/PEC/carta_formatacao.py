import logging
logger = logging.getLogger(__name__)

import re

from .carta_utils import _parse_data_ecarta, _somar_dias_uteis


def gerar_html_carta_para_juntada(dados):
    blocos_html = []

    for _, item in enumerate(dados, 1):
        html_bloco = '<p class="corpo" style="font-size: 12pt; line-height: normal; margin-left: 0px !important; text-align: justify !important; text-indent: 4.5cm;">'
        html_bloco += '&nbsp; &nbsp; '

        id_pje = item.get('ID_PJE', '')
        if id_pje:
            html_bloco += f'IID: {id_pje}<br>'

        rastreamento = item.get('RASTREAMENTO', '')
        if rastreamento:
            if rastreamento.startswith('http'):
                rastreamento_limpo = rastreamento.strip()
                codigo_match = re.search(r'codigo=([A-Z0-9]+)', rastreamento_limpo)
                codigo_display = codigo_match.group(1) if codigo_match else rastreamento_limpo
                html_bloco += f'OBJETO: <a target="_blank" rel="noopener noreferrer" href="{rastreamento_limpo}">{codigo_display}</a><br>'
            else:
                html_bloco += f'OBJETO: {rastreamento}<br>'

        destinatario = item.get('DESTINATARIO', '')
        if destinatario:
            html_bloco += f'DESTINATÁRIO: {destinatario}<br>'

        data_envio = item.get('DATA_ENVIO', '')
        if data_envio:
            html_bloco += f'DATA DO ENVIO: {data_envio}<br>'

        data_entrega = item.get('DATA_ENTREGA', '')
        if data_entrega:
            html_bloco += f'DATA DE ENTREGA: {data_entrega}<br>'

        status = item.get('STATUS', '')
        if status:
            html_bloco += f'RESULTADO: {status}<br>'

        if 'entregue' in status.lower():
            html_bloco += 'DEVOLVIDA? ( ) - Desmarcado significa ENTREGA CONFIRMADA.'

        html_bloco += '</p>'
        blocos_html.append(html_bloco)

    return '\n'.join(blocos_html)


def formatar_dados_ecarta(dados_mais_recentes, intimacoes_info, log=True):
    if not dados_mais_recentes:
        return "", "", ""

    prazo_texto = ""
    data_base_prazo = None

    datas_entrega_validas = []
    for item in dados_mais_recentes:
        data_entrega = _parse_data_ecarta(item.get('DATA_ENTREGA', ''))
        if data_entrega:
            datas_entrega_validas.append(data_entrega)

    if datas_entrega_validas:
        data_base_prazo = max(datas_entrega_validas)
    else:
        for item in dados_mais_recentes:
            data_base_prazo = _parse_data_ecarta(item.get('DATA_ENVIO', ''))
            if data_base_prazo:
                break

    if data_base_prazo:
        tem_devolvido = any(re.search(r'devolvid[oa]', item.get('STATUS', ''), re.IGNORECASE) for item in dados_mais_recentes)
        if tem_devolvido:
            prazo_texto = ""
        else:
            tem_alguma_desconsideracao = any(info.get('tem_desconsideracao') for info in intimacoes_info)
            if tem_alguma_desconsideracao:
                prazo_principal = _somar_dias_uteis(data_base_prazo, 15)
                prazo_secundario = _somar_dias_uteis(data_base_prazo, 8)
                if prazo_principal and prazo_secundario:
                    prazo_texto = f"Prazo: 15 dias ({prazo_principal.strftime('%d/%m/%Y')})"
            else:
                prazo_principal = _somar_dias_uteis(data_base_prazo, 8)
                prazo_secundario = _somar_dias_uteis(data_base_prazo, 15)
                if prazo_principal and prazo_secundario:
                    prazo_texto = f"Prazo: 8 dias ({prazo_principal.strftime('%d/%m/%Y')})"
            if not prazo_texto:
                prazo_8 = _somar_dias_uteis(data_base_prazo, 8)
                prazo_15 = _somar_dias_uteis(data_base_prazo, 15)
                if prazo_8 and prazo_15:
                    prazo_texto = f"Prazos: 15 ({prazo_15.strftime('%d/%m/%Y')}) - 08 ({prazo_8.strftime('%d/%m/%Y')})"

    html_para_juntada = gerar_html_carta_para_juntada(dados_mais_recentes)

    if prazo_texto:
        html_prazo = (
            '<p class="corpo" style="font-size: 12pt; line-height: normal; '
            'margin-left: 0px !important; text-align: justify !important; '
            'text-indent: 4.5cm;">&nbsp; &nbsp; '
            f'{prazo_texto}</p>'
        )
        html_para_juntada = f"{html_para_juntada}\n{html_prazo}" if html_para_juntada else html_prazo

    blocos_formatados = []
    for i, item in enumerate(dados_mais_recentes, 1):
        bloco = []
        bloco.append(f"    Id Pje: {item.get('ID_PJE', '')}")
        rastreamento = item.get('RASTREAMENTO', '')
        if rastreamento:
            if rastreamento.startswith('http'):
                rastreamento_limpo = rastreamento.strip()
                bloco.append(f'    Rastreamento: {rastreamento_limpo}')
            else:
                bloco.append(f"    Rastreamento: {rastreamento}")
        else:
            bloco.append("    Rastreamento: Indisponível")

        bloco.append(f"    Destinatário: {item.get('DESTINATARIO', '')}")
        bloco.append(f"    Data do envio: {item.get('DATA_ENVIO', '') if item.get('DATA_ENVIO') else 'Indisponível'}")
        bloco.append(f"    Data da entrega: {item.get('DATA_ENTREGA', '') if item.get('DATA_ENTREGA') else 'Indisponível'}")
        bloco.append(f"    Status: {item.get('STATUS', '')}")

        bloco_texto = '\n'.join(bloco)
        if i < len(dados_mais_recentes):
            bloco_texto += '\n' + '-' * 50

        blocos_formatados.append(bloco_texto)

    conteudo_final = '\n\n'.join(blocos_formatados)
    if prazo_texto:
        conteudo_final = (conteudo_final + '\n\n' if conteudo_final else '') + prazo_texto

    return conteudo_final, html_para_juntada, prazo_texto
