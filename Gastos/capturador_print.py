"""Capturador Automático de Prints de Tela para PDF -> Google Drive.

Como funciona:
1. Deixe este script rodando no terminal.
2. Na tela do computador, aperte o atalho padrão do Windows: Win + Shift + S
3. Selecione com o mouse a área do comprovante.
4. O script detecta a imagem na área de transferência, converte para PDF e
   salva automaticamente em 'H:\\Meu Drive\\GASTOS\\' com nome timestamped.
5. Um bipe sonoro confirma a gravação a cada print capturado.

Uso:
  py GASTOS/capturador_print.py
  py GASTOS/capturador_print.py --prefixo "comprovante"
  py GASTOS/capturador_print.py --destino "H:\\Meu Drive\\GASTOS"
"""
import argparse
import hashlib
import io
import os
import sys
import time
import winsound
from datetime import datetime

import fitz  # PyMuPDF
from PIL import Image, ImageGrab

DESTINO_PADRAO = r"H:\Meu Drive\GASTOS"


def emitir_som_sucesso():
    try:
        winsound.MessageBeep(winsound.MB_OK)
    except Exception:
        pass


def calcular_hash_imagem(img):
    try:
        return hashlib.md5(img.tobytes()).hexdigest()
    except Exception:
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return hashlib.md5(buf.getvalue()).hexdigest()


def converter_imagem_para_pdf_bytes(img):
    """Converte um objeto PIL.Image em bytes de PDF nítido e otimizado via PyMuPDF."""
    img_rgb = img.convert("RGB")
    buf_img = io.BytesIO()
    img_rgb.save(buf_img, format="PNG", optimize=True)
    raw_img = buf_img.getvalue()

    w, h = img_rgb.size
    doc = fitz.open()
    page = doc.new_page(width=w, height=h)
    page.insert_image(fitz.Rect(0, 0, w, h), stream=raw_img)
    pdf_bytes = doc.tobytes(garbage=4, deflate=True)
    doc.close()
    return pdf_bytes


def salvar_print_como_pdf(img, pasta_destino, prefixo="print", contador=None):
    os.makedirs(pasta_destino, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    sufixo_cnt = f"_{contador:02d}" if contador is not None else ""
    nome_arquivo = f"{prefixo}_{ts}{sufixo_cnt}.pdf"
    caminho_final = os.path.join(pasta_destino, nome_arquivo)

    # Evita colisão se tirar dois prints no mesmo segundo
    idx_extra = 1
    while os.path.exists(caminho_final):
        nome_arquivo = f"{prefixo}_{ts}{sufixo_cnt}_{idx_extra}.pdf"
        caminho_final = os.path.join(pasta_destino, nome_arquivo)
        idx_extra += 1

    pdf_bytes = converter_imagem_para_pdf_bytes(img)
    with open(caminho_final, "wb") as f:
        f.write(pdf_bytes)

    return nome_arquivo, caminho_final, len(pdf_bytes)


def iniciar_monitoramento(pasta_destino, prefixo="print"):
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    print("\n" + "=" * 65)
    print("📸 CAPTURADOR AUTOMÁTICO DE PRINTS PARA PDF -> GOOGLE DRIVE")
    print("=" * 65)
    print(f"📁 Pasta Destino : {pasta_destino}")
    print(f"🏷️  Prefixo       : {prefixo}_<data_hora>.pdf")
    print("-" * 65)
    print("🚀 COMO USAR:")
    print("   1. Pressione  Win + Shift + S  (Recorte do Windows)")
    print("   2. Selecione a área do comprovante na tela.")
    print("   3. Assim que soltar o mouse, o PDF é salvo direto no Drive!")
    print("   4. Um som de bipe confirmará o salvamento.")
    print("   (Para encerrar, feche a janela ou pressione Ctrl + C)")
    print("=" * 65 + "\n")

    if not os.path.exists(pasta_destino):
        print(f"⚠️  Atenção: A pasta '{pasta_destino}' não foi encontrada.")
        print("   Verifique se o Google Drive para Desktop está em execução e conectado.\n")

    ultimo_hash = None
    # Inicializa com o que já estiver no clipboard para não salvar lixo anterior
    try:
        clip_inicial = ImageGrab.grabclipboard()
        if isinstance(clip_inicial, Image.Image):
            ultimo_hash = calcular_hash_imagem(clip_inicial)
    except Exception:
        pass

    contador = 0
    print("👀 Monitorando área de transferência... Aguardando prints...")

    while True:
        try:
            time.sleep(0.4)
            clip = ImageGrab.grabclipboard()

            # Caso 1: Imagem direta no clipboard (Win + Shift + S, PrintScreen, copiar imagem)
            if isinstance(clip, Image.Image):
                h = calcular_hash_imagem(clip)
                if h != ultimo_hash:
                    ultimo_hash = h
                    contador += 1
                    nome, caminho, tamanho_bytes = salvar_print_como_pdf(
                        clip, pasta_destino, prefixo=prefixo, contador=contador
                    )
                    kb = tamanho_bytes // 1024 or 1
                    emitir_som_sucesso()
                    hora_agora = datetime.now().strftime("%H:%M:%S")
                    print(f"   [{hora_agora}] 🟢 Captura #{contador:02d} salva com sucesso!")
                    print(f"            📄 {nome} ({kb} KB)")
                    print(f"            💾 {caminho}\n")

            # Caso 2: Arquivo(s) de imagem copiado(s) no Windows Explorer
            elif isinstance(clip, list) and clip:
                for arq_path in clip:
                    if isinstance(arq_path, str) and arq_path.lower().endswith(
                        (".png", ".jpg", ".jpeg", ".bmp", ".webp")
                    ):
                        if os.path.isfile(arq_path):
                            try:
                                with Image.open(arq_path) as img_arq:
                                    h = calcular_hash_imagem(img_arq)
                                    if h != ultimo_hash:
                                        ultimo_hash = h
                                        contador += 1
                                        nome, caminho, tamanho_bytes = salvar_print_como_pdf(
                                            img_arq, pasta_destino, prefixo=prefixo, contador=contador
                                        )
                                        kb = tamanho_bytes // 1024 or 1
                                        emitir_som_sucesso()
                                        hora_agora = datetime.now().strftime("%H:%M:%S")
                                        print(f"   [{hora_agora}] 🟢 Arquivo convertido e salvo:")
                                        print(f"            📄 {nome} ({kb} KB) [de {os.path.basename(arq_path)}]\n")
                            except Exception:
                                pass

        except KeyboardInterrupt:
            print("\n🛑 Monitoramento encerrado pelo usuário. Total de capturas salvas:", contador)
            break
        except Exception as e:
            # Protege contra travamento temporário do clipboard por outros apps
            time.sleep(0.5)


def main():
    parser = argparse.ArgumentParser(description="Captura prints e salva direto como PDF no Google Drive.")
    parser.add_argument("--destino", default=DESTINO_PADRAO, help="Pasta de destino onde salvar os PDFs")
    parser.add_argument("--prefixo", default="print", help="Prefixo do nome do arquivo (ex: print, comprovante, pix)")
    args = parser.parse_args()

    iniciar_monitoramento(pasta_destino=args.destino, prefixo=args.prefixo)


if __name__ == "__main__":
    main()
