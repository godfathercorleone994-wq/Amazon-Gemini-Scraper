# Amazon Gemini Scraper - Telegram Bot

Bot do Telegram para rastreamento de preços da Amazon com extração de dados alimentada por IA usando Google Gemini, OpenAI e outros provedores de IA.

> 🇧🇷 **[Guia Rápido em Português](TELEGRAM_BOT_PT.md)** | 📖 **[Referência de Comandos](COMANDOS.md)**

## Features

- 🤖 Extração de dados de produtos alimentada por IA usando Gemini, OpenAI e HuggingFace
- 🌐 Web scraping avançado com Playwright (anti-detecção)
- 📊 Rastreamento e análise de preços
- 🔔 Notificações instantâneas via Telegram
- 📈 Monitoramento em tempo real
- 🗄️ MongoDB para persistência de dados
- 🚀 Redis para cache e performance
- 💬 Interface interativa via Telegram
- 🎯 Alertas de preço personalizados

## Tech Stack

- **Bot Interface**: python-telegram-bot
- **AI/ML**: Google Gemini, OpenAI, HuggingFace Transformers
- **Scraping**: Playwright, BeautifulSoup, Cloudscraper
- **Database**: MongoDB (Atlas), Redis
- **Monitoring**: Sentry
- **Deployment**: Python Script (pode rodar em qualquer servidor)

## Quick Start

### Prerequisites

- Python 3.11+
- MongoDB Atlas account (ou MongoDB local)
- Redis (ou Redis Cloud)
- Google Gemini API key (obrigatório)
- Telegram Bot Token (obrigatório)
- OpenAI API key (opcional)

### Configuração

1. **Clone o repositório**
```bash
git clone https://github.com/godfathercorleone994-wq/Amazon-Gemini-Scraper.git
cd Amazon-Gemini-Scraper
```

2. **Crie seu Bot no Telegram**
   - Abra o Telegram e procure por @BotFather
   - Envie o comando `/newbot`
   - Siga as instruções para criar seu bot
   - Copie o token que o BotFather fornecer

3. **Configure as variáveis de ambiente**

Copie `.env.example` para `.env` e preencha suas credenciais:

```bash
cp .env.example .env
```

Variáveis obrigatórias:
- `TELEGRAM_BOT_TOKEN` - Token do seu bot do Telegram (obrigatório)
- `MONGODB_ATLAS_URI` - String de conexão do MongoDB
- `REDIS_URL` - URL de conexão do Redis
- `GEMINI_API_KEY` - Chave da API do Google Gemini

Variáveis opcionais:
- `OPENAI_API_KEY` - Chave da API OpenAI
- `SENDGRID_API_KEY` - Para notificações por email
- `DISCORD_WEBHOOK_URL` - Para notificações no Discord
- `SENTRY_DSN` - Para rastreamento de erros

### Instalação e Execução

1. **Instale as dependências:**
```bash
pip install -r requirements.txt
playwright install chromium
```

2. **Execute o bot:**
```bash
python bot_main.py
```

3. **Comece a usar:**
   - Abra o Telegram
   - Procure pelo seu bot usando o nome que você definiu
   - Envie `/start` para começar
   - Envie `/help` para ver todos os comandos disponíveis

## Comandos do Bot

### Comandos Principais

- `/start` - Inicia o bot e registra o usuário
- `/help` - Mostra ajuda detalhada sobre todos os comandos
- `/scrape [URL]` - Extrai informações de um produto da Amazon
- `/track [URL] [preço]` - Rastreia um produto e define alerta de preço
- `/list` - Lista todos os produtos que você está rastreando
- `/stop [ASIN]` - Para de rastrear um produto específico
- `/alerts` - Gerencia seus alertas de preço
- `/stats` - Mostra estatísticas dos seus rastreamentos

### Exemplos de Uso

**Extrair informações de um produto:**
```
/scrape https://amazon.com/dp/B08N5WRWNW
```

**Rastrear produto com alerta de preço:**
```
/track https://amazon.com/dp/B08N5WRWNW 79.99
```

**Enviar apenas o link:**
Você também pode simplesmente enviar um link da Amazon e o bot perguntará o que fazer.

**Listar produtos rastreados:**
```
/list
```

**Parar rastreamento:**
```
/stop B08N5WRWNW
```

## Funcionalidades

### Extração de Dados com IA
O bot usa Google Gemini (e opcionalmente OpenAI) para extrair informações estruturadas de produtos da Amazon, incluindo:
- Título do produto
- Preço atual
- Avaliações e número de reviews
- Descrição
- Imagens
- Especificações técnicas
- Disponibilidade

### Rastreamento de Preços
- Configure alertas de preço para produtos específicos
- Receba notificações instantâneas quando o preço cair
- Acompanhe múltiplos produtos simultaneamente
- Histórico de preços (em desenvolvimento)

### Interface Intuitiva
- Comandos simples e diretos
- Botões inline para ações rápidas
- Mensagens formatadas com emojis e Markdown
- Imagens dos produtos nas respostas

## Deployment em Produção

### Opção 1: Servidor Linux (VPS)

1. **Configure o servidor:**
```bash
sudo apt update
sudo apt install python3.11 python3-pip redis-server
```

2. **Clone e configure:**
```bash
git clone https://github.com/godfathercorleone994-wq/Amazon-Gemini-Scraper.git
cd Amazon-Gemini-Scraper
pip install -r requirements.txt
playwright install chromium
```

3. **Configure o .env com suas credenciais**

4. **Execute com systemd:**
Crie um arquivo `/etc/systemd/system/telegram-bot.service`:
```ini
[Unit]
Description=Amazon Scraper Telegram Bot
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/Amazon-Gemini-Scraper
Environment="PATH=/path/to/venv/bin"
ExecStart=/path/to/venv/bin/python bot_main.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Inicie o serviço:
```bash
sudo systemctl enable telegram-bot
sudo systemctl start telegram-bot
sudo systemctl status telegram-bot
```

### Opção 2: Docker

1. **Usando apenas o Dockerfile:**
```bash
docker build -t amazon-scraper-bot .
docker run -d --name bot --env-file .env amazon-scraper-bot python bot_main.py
```

### Opção 3: Heroku

1. **Crie um Procfile:**
```
worker: python bot_main.py
```

2. **Deploy:**
```bash
heroku create your-bot-name
heroku config:set TELEGRAM_BOT_TOKEN=your-token
heroku config:set MONGODB_ATLAS_URI=your-mongodb-uri
heroku config:set REDIS_URL=your-redis-url
heroku config:set GEMINI_API_KEY=your-gemini-key
git push heroku main
heroku ps:scale worker=1
```

### Opção 4: Railway

1. **Conecte seu repositório no Railway**
2. **Configure as variáveis de ambiente**
3. **O Railway detectará automaticamente o Python e executará o bot**

## Monitoramento

### Logs
O bot registra todas as ações e erros. Para visualizar logs em tempo real:
```bash
tail -f logs/app.log
```

### Estatísticas
Use o comando `/stats` no bot para ver suas estatísticas pessoais.

## Troubleshooting

### Bot não responde
- Verifique se o `TELEGRAM_BOT_TOKEN` está correto
- Confirme que o bot está rodando: `ps aux | grep bot_main`
- Verifique os logs: `tail -f logs/app.log`

### Erro ao extrair produtos
- Verifique se o `GEMINI_API_KEY` está configurado
- Confirme que o Playwright está instalado: `playwright install chromium`
- Teste o link manualmente no navegador

### Problemas de conexão com MongoDB
- Verifique se o `MONGODB_ATLAS_URI` está correto
- Confirme que o MongoDB Atlas permite conexões do seu IP
- Teste a conexão: `mongosh "sua-connection-string"`

### Problemas com Redis
- Verifique se o Redis está rodando: `redis-cli ping` (deve retornar PONG)
- Confirme o `REDIS_URL` no .env
- Se usar Redis Cloud, verifique as credenciais

## Project Structure

```
.
├── bot_main.py             # Main Telegram Bot entry point
├── api/                    # FastAPI application (legacy, pode ser removido)
│   ├── routes/            # API routes
│   └── middleware/        # Middleware (rate limiting, auth)
├── core/                  # Core scraping logic
│   ├── scraper_agent.py   # Playwright scraper
│   ├── gemini_extractor.py # AI extraction
│   └── fallback_extractors.py
├── models/                # Pydantic models
├── storage/               # Database clients
│   ├── mongodb_client.py
│   ├── redis_cache.py
│   └── s3_storage.py
├── features/              # Additional features
│   ├── analysis/
│   ├── dashboard/
│   └── notifications/
│       └── telegram_bot.py # Telegram bot helper
├── utils/                 # Utilities
├── config/                # Configuration
│   └── settings.py
├── scripts/               # Utility scripts
├── Dockerfile             # Docker configuration
├── requirements.txt       # Python dependencies
└── .env.example          # Environment variables template
```

## Security

- 🔐 Telegram Bot Token seguro
- 🛡️ Validação de comandos e inputs
- ⚡ Rate limiting integrado
- 🔒 Armazenamento seguro de credenciais
- 📊 Logging de todas as ações

## Performance

- ⚡ Redis caching para requisições frequentes
- 🔄 Async/await para operações I/O
- 🎯 Connection pooling para databases
- 🚀 Processamento paralelo quando possível

## Contribuindo

1. Fork o repositório
2. Crie sua branch de feature
3. Commit suas mudanças
4. Push para a branch
5. Crie um Pull Request

## Troubleshooting Adicional

### Playwright Installation Issues

Se os navegadores do Playwright falharem ao instalar:
```bash
playwright install chromium --with-deps
```

### MongoDB Connection Issues

Certifique-se de que:
- O MongoDB Atlas permite conexões do seu IP
- A string de conexão inclui as credenciais
- O acesso à rede está configurado no Atlas

### Redis Connection Issues

Verifique:
- Formato da URL do Redis: `redis://user:password@host:port/db`
- O serviço Redis está rodando
- O firewall permite a conexão

## License

MIT License - see LICENSE file for details

## Support

Para dúvidas e problemas:
- Abra uma issue no GitHub
- Envie `/help` no bot para ver a documentação
- Revise os logs para detalhes de erros

## Agradecimentos

- Google Gemini AI para extração de dados
- Playwright para web scraping
- python-telegram-bot para a interface do bot
- MongoDB e Redis para armazenamento de dados
