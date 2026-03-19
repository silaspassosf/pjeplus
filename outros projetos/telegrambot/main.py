import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
from openai import OpenAI
from dotenv import load_dotenv

# Carrega variáveis de ambiente
env_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(env_path)


TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# Teste: printar parte da chave para debug (NUNCA compartilhe o print!)
print(f"OPENAI_API_KEY carregada: {OPENAI_API_KEY[:8]}...{OPENAI_API_KEY[-4:]}")

openai_client = OpenAI(api_key=OPENAI_API_KEY)

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

def process_with_openai(message_text):
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": "Forneça uma resposta concisa e complemente com fatos da web se necessário."},
                      {"role": "user", "content": message_text}]
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Erro no OpenAI: {e}")
        return "Erro ao processar com IA."

async def handle_message(update: Update, context: CallbackContext):
    message_text = update.message.text
    chat_id = update.message.chat_id
    ai_response = process_with_openai(message_text)
    await update.message.reply_text(ai_response[:500] + "..." if len(ai_response) > 500 else ai_response)

async def start(update: Update, context: CallbackContext):
    await update.message.reply_text("Olá! Envie uma mensagem e eu responderei com info concisa, complementada pela web se necessário.")

def main():
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
