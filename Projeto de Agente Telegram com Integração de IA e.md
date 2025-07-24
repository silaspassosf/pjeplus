<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" class="logo" width="120"/>

### Projeto de Agente Telegram com Integração de IA e Busca Web

Olá! Baseado na sua solicitação, elaborei um projeto robusto em Python para criar um agente (bot) no Telegram que lê mensagens em um chat (privado ou grupo), processa-as usando a API do OpenAI para gerar respostas concisas e complementa as informações com buscas web via Perplexity Pro. O bot será especializado em fornecer respostas inteligentes, resumidas e enriquecidas com dados da web, evitando respostas longas ou irrelevantes.

O projeto usa bibliotecas padrão como `python-telegram-bot` para o Telegram, `openai` para o OpenAI e `requests` para integrar com a API do Perplexity (já que você tem uma conta Pro, que dá acesso à API para buscas avançadas)[^1][^2][^3]. Ele é assíncrono para melhor desempenho e inclui tratamento de erros para robustez.

#### Requisitos

- **APIs Necessárias**:
    - Chave API do OpenAI (você já tem).
    - Chave API do Perplexity Pro (obtenha no dashboard da Perplexity; é similar à do OpenAI)[^4].
    - Token do Bot Telegram (crie via BotFather no Telegram)[^1][^2].
- **Bibliotecas Python**:
    - `python-telegram-bot` (instale com `pip install python-telegram-bot`).
    - `openai` (instale com `pip install openai`).
    - `requests` (geralmente já instalado, mas verifique com `pip install requests`).
- **Ambiente**:
    - Python 3.9+.
    - Para rodar localmente ou deploy (ex.: Heroku ou VPS para 24/7)[^5].
- **Configurações no Telegram**:
    - Adicione o bot como administrador no grupo para ler todas as mensagens (desative o modo de privacidade via BotFather com `/setprivacy` para "Disable")[^6][^7][^8].
    - O bot não lê mensagens de outros bots por limitação do Telegram[^9][^10].


#### Instruções de Configuração

1. Crie um bot no Telegram: Busque "BotFather", use `/newbot` e copie o token.
2. Desative o modo de privacidade: No BotFather, use `/mybots` > Seu bot > Bot Settings > Group Privacy > Turn off[^6][^11].
3. Crie um arquivo `.env` para armazenar chaves (use `python-dotenv` para carregar: `pip install python-dotenv`):

```
TELEGRAM_TOKEN=seu_token_telegram
OPENAI_API_KEY=sua_chave_openai
PERPLEXITY_API_KEY=sua_chave_perplexity
```

4. Rode o código com `python main.py`.

#### Código do Projeto

Aqui está o código completo e especializado. Ele cria um bot que:

- Lê mensagens em chats privados ou grupos (se admin).
- Usa OpenAI para analisar e resumir a mensagem.
- Complementa com busca web no Perplexity para dados atualizados.
- Responde de forma concisa, com citações de fontes.

Salve como `main.py`:

```python
import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
from openai import OpenAI
from dotenv import load_dotenv
import requests
import json

# Carrega variáveis de ambiente
load_dotenv()

# Configurações
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
PERPLEXITY_API_KEY = os.getenv('PERPLEXITY_API_KEY')

# Inicializa OpenAI
openai_client = OpenAI(api_key=OPENAI_API_KEY)

# Configura logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Função para busca web via Perplexity API
def search_web_perplexity(query):
    url = "https://api.perplexity.ai/chat/completions"
    payload = {
        "model": "llama-3.1-sonar-large-32k-online",
        "messages": [{"role": "user", "content": query}],
        "max_tokens": 150,
        "temperature": 0.5
    }
    headers = {
        "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
        "Content-Type": "application/json"
    }
    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        result = response.json()
        return result['choices'][^0]['message']['content']
    except Exception as e:
        logger.error(f"Erro na busca Perplexity: {e}")
        return "Erro ao buscar dados na web."

# Função para processar mensagem com OpenAI
def process_with_openai(message_text):
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": "Forneça uma resposta concisa e complemente com fatos da web se necessário."},
                      {"role": "user", "content": message_text}]
        )
        return response.choices[^0].message.content
    except Exception as e:
        logger.error(f"Erro no OpenAI: {e}")
        return "Erro ao processar com IA."

# Handler para mensagens
async def handle_message(update: Update, context: CallbackContext):
    message_text = update.message.text
    chat_id = update.message.chat_id
    
    # Processa com OpenAI
    ai_response = process_with_openai(message_text)
    
    # Complementa com busca web se a resposta indicar necessidade (ex.: "busque mais")
    if "busque" in ai_response.lower() or "mais info" in ai_response.lower():
        web_info = search_web_perplexity(message_text)
        ai_response += f"\n\nComplemento da web: {web_info}"
    
    # Envia resposta concisa
    await update.message.reply_text(ai_response[:500] + "..." if len(ai_response) > 500 else ai_response)  # Limita a 500 chars para concisão

# Handler para comando /start
async def start(update: Update, context: CallbackContext):
    await update.message.reply_text("Olá! Envie uma mensagem e eu responderei com info concisa, complementada pela web se necessário.")

def main():
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Inicia polling
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
```

Este código é robusto: inclui logging, tratamento de exceções e limitação de tamanho de resposta para concisão[^1][^2][^3]. Ele lê mensagens automaticamente em grupos se o bot for admin[^6][^8].

#### Como Funciona

- **Leitura de Mensagens**: O bot escuta todas as mensagens de texto (não comandos) via `MessageHandler`. Em grupos, certifique-se de que ele é admin e privacidade desativada[^7][^11].
- **Processamento com OpenAI**: Usa GPT-4o-mini para respostas concisas e inteligentes[^1][^2].
- **Complemento com Busca Web**: Integra Perplexity para buscas reais e atualizadas; o modelo "llama-3.1-sonar-large" é otimizado para consultas online[^4][^12].
- **Respostas Concisas**: Limita o texto para evitar sobrecarga; complementa apenas se necessário.


#### Dicas de Uso e Deploy

- **Teste**: Rode localmente e envie mensagens ao bot. Adicione-o a um grupo como admin.
- **Deploy 24/7**: Use Heroku (gratuito para básico) ou um VPS. Configure webhook em vez de polling para eficiência: modifique para `application.run_webhook`[^5].
- **Limitações**: Bots não leem mensagens de outros bots[^9]. Para buscas avançadas, ajuste o prompt no OpenAI. Monitore custos de API (OpenAI e Perplexity)[^1][^4].
- **Personalização**: Adicione mais comandos ou integre memória de conversas via OpenAI threads para contextos longos.

Se precisar de ajustes ou mais detalhes, me avise! Este projeto é baseado em práticas padrão de bots Telegram com IA[^2][^3].

<div style="text-align: center">⁂</div>

[^1]: https://first.institute/en/blog/telegram-chatbot-chatgpt-openai-python/

[^2]: https://www.toolify.ai/ai-news/build-a-python-telegram-bot-with-chatgpt-by-openai-520002

[^3]: https://dev.to/hayerhans/how-to-build-a-telegram-bot-with-chatgpt-integration-5elp

[^4]: https://www.save.day/blog-posts/telegram-search-bot

[^5]: https://github.com/AliAbdelaal/telegram-bot-tutorial

[^6]: https://stackoverflow.com/questions/38565952/how-to-receive-messages-in-group-chats-using-telegram-bot-api

[^7]: https://github.com/python-telegram-bot/python-telegram-bot/discussions/2780

[^8]: https://chatimize.com/telegram-bot-group/

[^9]: https://stackoverflow.com/questions/63903767/telegram-group-read-messages-from-another-bot

[^10]: https://community.latenode.com/t/making-my-telegram-bot-detect-and-read-messages-from-other-bots-in-group-chats/23554

[^11]: https://www.reddit.com/r/Telegram/comments/oru7d0/question_about_bots_can_their_creators_read_the/

[^12]: https://www.irjweb.com/AN APPLICATION ON TELEGRAM BOT SEARCH ENGINE USING PYTHON.pdf

[^13]: https://core.telegram.org/bots/api

[^14]: https://github.com/yagop/node-telegram-bot-api/issues/316

[^15]: https://github.com/python-telegram-bot/python-telegram-bot/discussions/3701

[^16]: https://community.latenode.com/t/is-it-possible-for-telegram-bots-to-view-channel-messages/11453

[^17]: https://www.youtube.com/watch?v=nLsdC4x1k-A

[^18]: https://www.make.com/en/integrations/google-search-console/telegram

[^19]: https://www.youtube.com/watch?v=mvX52dGDqXQ

[^20]: https://core.telegram.org/method/messages.getMessages

[^21]: https://buildship.com/integrations/apps/telegram-and-openai

[^22]: https://www.youtube.com/watch?v=Eg8XlIHMUt0

[^23]: https://stackoverflow.com/questions/66589700/is-there-a-way-for-a-telegram-bot-to-get-its-own-messages-that-it-has-sent-in-a

[^24]: https://pipedream.com/apps/telegram-bot-api/integrations/openai

[^25]: https://pipedream.com/apps/search-api/integrations/telegram-bot-api

[^26]: https://www.youtube.com/watch?v=dMH6q_NkY9w

[^27]: https://dev.to/endykaufman/how-to-receive-messages-in-group-chats-using-telegram-bot-app-without-full-access-in-telegram-bot-on-nestjs-4k6m

[^28]: https://community.openai.com/t/openai-assistant-api-and-telegram-bot/666406

[^29]: https://core.telegram.org/bots/features

[^30]: https://fleek-xyz-staging.on-fleek.app/guides/telegram-ai-agent

[^31]: https://www.reddit.com/r/TelegramBots/comments/gb09ut/bot_reading_and_reacting_to_group_messages/

[^32]: https://www.pabbly.com/connect/integrations/telegram-bot/google-search-console-pending-approval/

[^33]: https://community.make.com/t/get-telegram-watch-updates-bot-to-read-group-chat-messages/59390

[^34]: https://www.toolify.ai/ai-news/create-an-ai-chatbot-in-telegram-using-python-and-openai-api-1036787

[^35]: https://github.com/revenkroz/telegram-web-app-bot-example

[^36]: https://www.youtube.com/watch?v=dNIQgDVDt1k

[^37]: https://github.com/father-bot/chatgpt_telegram_bot

[^38]: https://stackoverflow.com/questions/71969343/use-telegram-bot-webapp-integration-in-groups

[^39]: https://stackoverflow.com/questions/56295761/how-to-get-a-message-from-telegram-groups-by-api/56311723

[^40]: https://stackoverflow.com/questions/67950025/i-built-a-webscraper-via-python-and-i-want-to-integrate-it-to-a-telegram-bot-but

[^41]: https://www.geeksforgeeks.org/python/create-a-telegram-bot-using-python/

[^42]: https://github.com/python-telegram-bot/python-telegram-bot

[^43]: https://github.com/eternnoir/pyTelegramBotAPI/issues/857

[^44]: https://www.youtube.com/watch?v=zxoco9TfNpw

[^45]: https://stackoverflow.com/questions/50571498/how-to-generate-information-from-telegram-using-a-python-based-telegram-bot-and

[^46]: https://community.latenode.com/t/enabling-message-sending-for-a-telegram-bot-in-group-chats/11452

