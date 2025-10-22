# 🤖 Bot do Telegram - Amazon Price Tracker

Bot do Telegram para rastrear preços de produtos da Amazon com inteligência artificial.

## 📋 Requisitos

- Python 3.11 ou superior
- Conta no MongoDB Atlas (gratuita)
- Conta no Redis Cloud (gratuita) ou Redis local
- Token do Bot do Telegram (gratuito)
- Chave da API do Google Gemini (gratuita)

## 🚀 Início Rápido

### Passo 1: Criar o Bot no Telegram

1. Abra o Telegram e procure por **@BotFather**
2. Envie o comando `/newbot`
3. Escolha um nome para seu bot (ex: "Meu Price Tracker")
4. Escolha um username único (ex: "meuprice_tracker_bot")
5. **Copie o token** que o BotFather fornecer (algo como: `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz`)

### Passo 2: Configurar MongoDB Atlas (Banco de Dados)

1. Acesse [MongoDB Atlas](https://www.mongodb.com/cloud/atlas/register)
2. Crie uma conta gratuita
3. Crie um cluster (escolha a opção FREE)
4. Em "Database Access", crie um usuário e senha
5. Em "Network Access", adicione `0.0.0.0/0` para permitir acesso de qualquer IP
6. Clique em "Connect" → "Connect your application"
7. **Copie a connection string** (algo como: `mongodb+srv://user:password@cluster.mongodb.net/`)

### Passo 3: Configurar Redis

**Opção A - Redis Cloud (Recomendado para iniciantes):**
1. Acesse [Redis Cloud](https://redis.com/try-free/)
2. Crie uma conta gratuita
3. Crie um banco de dados
4. **Copie a connection string** (algo como: `redis://default:password@host:port`)

**Opção B - Redis Local:**
```bash
# Ubuntu/Debian
sudo apt install redis-server
sudo systemctl start redis
# Sua URL será: redis://localhost:6379
```

### Passo 4: Obter Chave da API do Google Gemini

1. Acesse [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Faça login com sua conta Google
3. Clique em "Get API Key" ou "Create API Key"
4. **Copie a chave** (algo como: `AIzaSyxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`)

### Passo 5: Configurar o Projeto

1. **Clone o repositório:**
```bash
git clone https://github.com/godfathercorleone994-wq/Amazon-Gemini-Scraper.git
cd Amazon-Gemini-Scraper
```

2. **Copie o arquivo de exemplo:**
```bash
cp .env.example .env
```

3. **Edite o arquivo .env:**
```bash
nano .env
# ou use seu editor preferido
```

4. **Preencha com suas credenciais:**
```bash
# Bot do Telegram (OBRIGATÓRIO)
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz

# MongoDB (OBRIGATÓRIO)
MONGODB_ATLAS_URI=mongodb+srv://user:password@cluster.mongodb.net/?retryWrites=true&w=majority

# Redis (OBRIGATÓRIO)
REDIS_URL=redis://default:password@host:port

# Google Gemini (OBRIGATÓRIO)
GEMINI_API_KEY=AIzaSyxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

5. **Salve o arquivo** (Ctrl+O, Enter, Ctrl+X se estiver usando nano)

### Passo 6: Instalar e Executar

**Opção A - Usando o script de início (Recomendado):**
```bash
./start_bot.sh
```

**Opção B - Manualmente:**
```bash
# Criar ambiente virtual
python3 -m venv venv
source venv/bin/activate  # No Windows: venv\Scripts\activate

# Instalar dependências
pip install -r requirements.txt

# Instalar navegador do Playwright
playwright install chromium

# Executar o bot
python bot_main.py
```

### Passo 7: Usar o Bot

1. Abra o Telegram
2. Procure pelo nome do seu bot (o username que você escolheu)
3. Envie `/start` para começar
4. Envie `/help` para ver todos os comandos

## 📱 Comandos Disponíveis

- `/start` - Inicia o bot
- `/help` - Mostra ajuda
- `/scrape [URL]` - Extrai dados de um produto
- `/track [URL] [preço]` - Rastreia produto com alerta de preço
- `/list` - Lista produtos rastreados
- `/stop [ASIN]` - Para de rastrear produto
- `/alerts` - Gerencia alertas
- `/stats` - Mostra estatísticas

## 💡 Exemplos de Uso

**Extrair informações de um produto:**
```
/scrape https://www.amazon.com/dp/B08N5WRWNW
```

**Rastrear produto e receber alerta quando preço cair:**
```
/track https://www.amazon.com/dp/B08N5WRWNW 79.99
```

**Ou simplesmente envie o link:**
```
https://www.amazon.com/dp/B08N5WRWNW
```
O bot perguntará o que você quer fazer!

## 🔧 Solução de Problemas

### Bot não responde
```bash
# Verifique se está rodando
ps aux | grep bot_main

# Veja os logs
tail -f logs/app.log

# Teste o token
curl https://api.telegram.org/bot<SEU_TOKEN>/getMe
```

### Erro de importação
```bash
# Reinstale as dependências
pip install -r requirements.txt --force-reinstall
playwright install chromium
```

### Erro de conexão com MongoDB
- Verifique se a connection string está correta
- Confirme que adicionou `0.0.0.0/0` no Network Access do Atlas
- Teste a conexão: `mongosh "sua-connection-string"`

### Erro de conexão com Redis
```bash
# Teste o Redis
redis-cli ping
# Deve retornar: PONG

# Se não funcionar, inicie o Redis
sudo systemctl start redis
```

## 🌐 Deploy em Servidor

### VPS (DigitalOcean, Vultr, AWS, etc.)

1. **Conecte ao servidor:**
```bash
ssh usuario@seu-servidor-ip
```

2. **Clone e configure:**
```bash
git clone https://github.com/godfathercorleone994-wq/Amazon-Gemini-Scraper.git
cd Amazon-Gemini-Scraper
nano .env  # Configure suas credenciais
```

3. **Execute:**
```bash
./start_bot.sh
```

4. **Manter rodando em background:**
```bash
# Opção 1: screen
screen -S bot
./start_bot.sh
# Pressione Ctrl+A, depois D para desanexar

# Opção 2: tmux
tmux new -s bot
./start_bot.sh
# Pressione Ctrl+B, depois D para desanexar

# Opção 3: nohup
nohup python bot_main.py > bot.log 2>&1 &
```

### Heroku

1. **Crie um Procfile:**
```
worker: python bot_main.py
```

2. **Deploy:**
```bash
heroku create meu-bot-name
heroku config:set TELEGRAM_BOT_TOKEN=seu-token
heroku config:set MONGODB_ATLAS_URI=sua-uri
heroku config:set REDIS_URL=sua-url-redis
heroku config:set GEMINI_API_KEY=sua-chave
git push heroku main
heroku ps:scale worker=1
```

### Railway

1. Acesse [Railway.app](https://railway.app)
2. Faça login com GitHub
3. Clique em "New Project" → "Deploy from GitHub repo"
4. Selecione o repositório
5. Adicione as variáveis de ambiente
6. Deploy!

## 📊 Monitoramento

**Ver logs em tempo real:**
```bash
tail -f logs/app.log
```

**Ver status do bot:**
```bash
# Se rodando com systemd
sudo systemctl status telegram-bot

# Se rodando em screen
screen -r bot

# Se rodando em tmux
tmux attach -t bot
```

## 🆘 Suporte

- 📖 Documentação completa: [README.md](README.md)
- 🐛 Reportar bug: Abra uma issue no GitHub
- 💬 Dúvidas: Use as Discussions no GitHub

## 📝 Notas

- O bot usa Google Gemini para extrair dados, portanto você precisa de uma chave válida
- A conta gratuita do Gemini tem limites de requisições (60 por minuto)
- MongoDB Atlas free tier tem limite de 512MB
- Redis Cloud free tier tem limite de 30MB
- Todos os dados são armazenados de forma segura

## 🎉 Pronto!

Seu bot está funcionando! Agora você pode:
- Rastrear quantos produtos quiser
- Receber alertas instantâneos no Telegram
- Compartilhar o bot com amigos

**Importante:** Mantenha seu `.env` seguro e nunca compartilhe seus tokens!
