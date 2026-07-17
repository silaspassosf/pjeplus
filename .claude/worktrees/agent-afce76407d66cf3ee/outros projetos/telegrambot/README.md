# TelegramBot com IA (OpenAI)

Este bot lê mensagens do Telegram e responde de forma concisa usando OpenAI.

## Passo a Passo de Implementação

1. **Crie um bot no Telegram**
   - Converse com o [BotFather](https://t.me/botfather) e use `/newbot` para gerar o token.
   - Desative o modo de privacidade: `/mybots` > Seu bot > Bot Settings > Group Privacy > Turn off.

2. **Obtenha a chave de API do OpenAI**
   - OpenAI: https://platform.openai.com/api-keys

3. **Configure o arquivo `.env`**
   - Copie `.env.example` para `.env` e preencha com suas chaves:
     ```
     TELEGRAM_TOKEN=seu_token_telegram
     OPENAI_API_KEY=sua_chave_openai
     ```

4. **Instale as dependências**
   - No terminal, execute:
     ```
     pip install -r requirements.txt
     ```

5. **Execute o bot**
   - No terminal, execute:
     ```
     python main.py
     ```

6. **Adicione o bot ao grupo (opcional)**
   - Torne-o administrador para ler todas as mensagens.

## Observações
- O bot responde apenas a mensagens de texto.
- Limite de 500 caracteres por resposta para concisão.
- O código é assíncrono e robusto, com tratamento de erros e logging.

Se precisar de deploy 24/7, use VPS, Heroku ou similar.

---

Dúvidas? Consulte o código ou peça suporte!
