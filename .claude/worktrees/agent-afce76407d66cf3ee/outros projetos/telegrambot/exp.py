# Script para exportar as últimas 300 mensagens de todos os grupos do Telegram usando Pyrogram
# Requer: pip install pyrogram tgcrypto


import os
import asyncio
from pyrogram import Client
from pyrogram.errors import FloodWait
from PIL import Image
import subprocess

API_ID = int(os.getenv("TELE_ID") or "123456")  # Use a variável de ambiente TELE_ID
API_HASH = os.getenv("TELE_HASH") or "coloque_sua_api_hash_aqui"  # Use a variável de ambiente TELE_HASH
SESSION_NAME = "exporter"
EXPORT_DIR = "exported_groups"

os.makedirs(EXPORT_DIR, exist_ok=True)

async def export_groups():
    async with Client(SESSION_NAME, api_id=API_ID, api_hash=API_HASH) as app:
        print("Listando todos os chats encontrados:")
        from pyrogram.enums import ChatType
        async for dialog in app.get_dialogs():
            chat = dialog.chat
            chat_name = getattr(chat, 'title', None) or getattr(chat, 'first_name', '') or str(chat.id)
            chat_type = getattr(chat, 'type', None)
            print(f"\n---\n[INÍCIO] Exportando chat: {chat_name} (tipo: {chat_type}, id: {chat.id})")
            # Log detalhado do tipo
            print(f"  [DEBUG] chat.type: {chat_type} | type.name: {getattr(chat_type, 'name', str(chat_type))}")
            # Corrigir checagem para Enum
            if chat_type in (ChatType.SUPERGROUP, ChatType.GROUP, ChatType.CHANNEL, ChatType.PRIVATE):
                # Remove caracteres inválidos para nomes de pastas no Windows
                invalid_chars = '<>:"/\\|?*'
                safe_name = chat_name
                for c in invalid_chars:
                    safe_name = safe_name.replace(c, '_')
                safe_name = safe_name.replace(' ', '_')
                chat_dir = os.path.join(EXPORT_DIR, safe_name)
                mensagens_path = os.path.join(chat_dir, "mensagens.txt")
                if os.path.exists(mensagens_path):
                    print(f"[PULANDO] Chat '{chat_name}' já exportado em '{chat_dir}'.")
                    continue
                os.makedirs(chat_dir, exist_ok=True)
                messages = []
                media_count = 0
                msg_count = 0
                try:
                    async for msg in app.get_chat_history(chat.id, limit=300):
                        msg_count += 1
                        msg_ref = f"[{msg.date}] {msg.from_user.first_name if msg.from_user else ''}: "
                        # Texto
                        if msg.text:
                            messages.append(msg_ref + msg.text)
                        # Imagem
                        if msg.photo:
                            media_count += 1
                            photo_path = os.path.join(chat_dir, f"photo_{msg.id}.jpg")
                            print(f"  [BAIXANDO IMAGEM] msg_id={msg.id} para {photo_path}")
                            try:
                                await msg.download(file_name=photo_path)
                            except FloodWait as e:
                                print(f"  [FLOODWAIT] Esperando {e.value} segundos...")
                                await asyncio.sleep(e.value)
                                await msg.download(file_name=photo_path)
                            # Compressão JPEG
                            try:
                                img = Image.open(photo_path)
                                img = img.convert('RGB')
                                img.save(photo_path, 'JPEG', quality=70, optimize=True)
                                print(f"    [COMPRESSÃO] Imagem comprimida: {photo_path}")
                            except Exception as e:
                                print(f"    [ERRO] Compressão da imagem falhou: {e}")
                            messages.append(msg_ref + f"[IMAGEM: {os.path.basename(photo_path)}]")
                        # Vídeo
                        if msg.video:
                            media_count += 1
                            video_path = os.path.join(chat_dir, f"video_{msg.id}.mp4")
                            print(f"  [BAIXANDO VÍDEO] msg_id={msg.id} para {video_path}")
                            try:
                                await msg.download(file_name=video_path)
                            except FloodWait as e:
                                print(f"  [FLOODWAIT] Esperando {e.value} segundos...")
                                await asyncio.sleep(e.value)
                                await msg.download(file_name=video_path)
                            # Compressão de vídeo via ffmpeg
                            compressed_path = os.path.join(chat_dir, f"video_{msg.id}_compressed.mp4")
                            try:
                                cmd = [
                                    "ffmpeg", "-y", "-i", video_path,
                                    "-b:v", "800k", "-bufsize", "800k", "-maxrate", "800k",
                                    "-preset", "veryfast", "-c:a", "aac", "-b:a", "96k",
                                    compressed_path
                                ]
                                print(f"    [COMPRESSÃO] Comprimindo vídeo: {video_path} -> {compressed_path}")
                                subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                                os.replace(compressed_path, video_path)
                                print(f"    [COMPRESSÃO] Vídeo comprimido: {video_path}")
                            except Exception as e:
                                print(f"    [ERRO] Compressão do vídeo falhou: {e}")
                            messages.append(msg_ref + f"[VIDEO: {os.path.basename(video_path)}]")
                        if msg_count % 50 == 0:
                            print(f"  [PROGRESSO] {msg_count} mensagens processadas...")
                except Exception as e:
                    print(f"  [ERRO] Falha ao exportar mensagens do chat {chat_name}: {e}")
                # Salva o log de mensagens com referências
                filename = os.path.join(chat_dir, "mensagens.txt")
                with open(filename, "w", encoding="utf-8") as f:
                    f.write("\n".join(reversed(messages)))
                print(f"[FIM] Chat: {chat_name} | {msg_count} mensagens | {media_count} mídias | Salvo em {filename}")
            else:
                print(f"[IGNORADO] Chat {chat_name} (tipo: {chat_type}) não é exportável.")

if __name__ == "__main__":
    print("Iniciando exportação dos grupos do Telegram...")
    tele_id = os.getenv('TELE_ID')
    tele_hash = os.getenv('TELE_HASH')
    print(f"TELE_ID: {tele_id if tele_id else '[NÃO DEFINIDA]'}")
    print(f"TELE_HASH: {tele_hash[:6]+'...' if tele_hash else '[NÃO DEFINIDA]'}")
    print(f"API_ID usado: {API_ID}")
    print(f"API_HASH usado: {API_HASH[:6]}..." if API_HASH else "API_HASH usado: [NÃO DEFINIDA]")
    asyncio.run(export_groups())
    print("Concluído!")
