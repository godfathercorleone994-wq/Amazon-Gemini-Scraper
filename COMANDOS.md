# 🤖 Referência Rápida de Comandos

## Comandos Básicos

### `/start`
Inicia o bot e registra seu usuário.
```
/start
```

### `/help`
Mostra ajuda detalhada com todos os comandos disponíveis.
```
/help
```

## Extração de Dados

### `/scrape [URL]`
Extrai informações completas de um produto da Amazon.

**Exemplo:**
```
/scrape https://www.amazon.com/dp/B08N5WRWNW
```

**Retorna:**
- ✅ Título do produto
- 💰 Preço atual
- ⭐ Avaliação (rating)
- 📊 Número de reviews
- 🏷️ ASIN
- 📝 Descrição
- 🖼️ Imagem (se disponível)

## Rastreamento de Preços

### `/track [URL] [preço_alvo]`
Adiciona um produto para rastreamento e define um alerta de preço.

**Exemplos:**
```
# Com preço alvo
/track https://www.amazon.com/dp/B08N5WRWNW 79.99

# Sem preço alvo (você pode definir depois)
/track https://www.amazon.com/dp/B08N5WRWNW
```

**O que acontece:**
- 🎯 Produto é adicionado à sua lista
- 🔔 Você receberá alertas quando o preço cair
- 📊 Histórico de preços é mantido
- ⚡ Notificações instantâneas no Telegram

### `/list`
Lista todos os produtos que você está rastreando.

```
/list
```

**Mostra:**
- 📦 Nome de cada produto
- 💰 Preço atual
- 🎯 Seu preço alvo
- 🏷️ ASIN do produto

### `/stop [ASIN]`
Para de rastrear um produto específico.

**Exemplo:**
```
/stop B08N5WRWNW
```

💡 **Dica:** Use `/list` para ver os ASINs dos seus produtos.

## Gerenciamento de Alertas

### `/alerts`
Mostra o gerenciamento dos seus alertas de preço.

```
/alerts
```

**Informações:**
- 📊 Número de alertas ativos
- ⚙️ Configurações de notificação
- 🔔 Status dos alertas

### `/stats`
Mostra estatísticas dos seus rastreamentos.

```
/stats
```

**Exibe:**
- 📦 Total de produtos rastreados
- 🔔 Alertas configurados
- 📈 Atividade recente

## Uso Direto

### Enviar apenas o link
Você pode simplesmente enviar um link da Amazon e o bot perguntará o que fazer!

**Exemplo:**
```
https://www.amazon.com/dp/B08N5WRWNW
```

**O bot responderá com:**
- 🔍 Opção para extrair dados
- 🎯 Opção para rastrear

## Dicas de Uso

### ✅ Boas Práticas

1. **Use URLs completas**
   ```
   ✅ https://www.amazon.com/dp/B08N5WRWNW
   ❌ B08N5WRWNW
   ```

2. **Formato de preço**
   ```
   ✅ 79.99
   ✅ 150.00
   ❌ R$ 79,99
   ❌ $79.99
   ```

3. **Verifique seus produtos regularmente**
   ```
   /list  # Ver lista atualizada
   /stats # Ver estatísticas
   ```

### 💡 Atalhos

- Após enviar um link, use os botões inline para ações rápidas
- Use o histórico do Telegram para repetir comandos
- Marque mensagens importantes com ⭐

### 🔔 Sobre Notificações

Você receberá notificações quando:
- ✅ O preço cair abaixo do seu alvo
- ✅ Houver uma grande promoção (>20% de desconto)
- ✅ O produto voltar ao estoque (se estava indisponível)

### ⚙️ Configurações Padrão

- Máximo de produtos: **20 por usuário**
- Frequência de verificação: **A cada 1 hora**
- Notificações: **Instantâneas**
- Cache de dados: **1 hora**

## Solução de Problemas

### Bot não responde?
```
1. Verifique se o bot está online
2. Tente /start novamente
3. Aguarde alguns segundos e tente novamente
```

### Erro ao extrair produto?
```
1. Verifique se o link está correto
2. Certifique-se de que é um produto da Amazon
3. Alguns produtos podem ter proteção anti-bot
4. Tente novamente em alguns minutos
```

### Preço não atualiza?
```
1. Use /list para ver o último preço
2. O bot atualiza a cada 1 hora
3. Você receberá notificação quando houver mudança
```

## Exemplos Completos

### Exemplo 1: Rastrear Echo Dot
```
# Passo 1: Extrair dados
/scrape https://www.amazon.com/dp/B08N5WRWNW

# Passo 2: Rastrear com preço alvo
/track https://www.amazon.com/dp/B08N5WRWNW 49.99

# Passo 3: Ver na lista
/list
```

### Exemplo 2: Gerenciar múltiplos produtos
```
# Adicionar vários produtos
/track https://www.amazon.com/dp/B08N5WRWNW 49.99
/track https://www.amazon.com/dp/B0B4Z1234Y 89.99
/track https://www.amazon.com/dp/B0C5X6789Z 129.99

# Ver todos
/list

# Parar um específico
/stop B0B4Z1234Y

# Ver estatísticas
/stats
```

### Exemplo 3: Workflow completo
```
1. Envie link: https://www.amazon.com/dp/B08N5WRWNW
2. Clique em "🔍 Extrair Dados"
3. Veja as informações
4. Clique em "🎯 Rastrear Produto"
5. Defina o preço alvo: 79.99
6. Aguarde notificações!
```

## Limites e Restrições

### Limites do Bot
- ✅ Produtos simultâneos: 20
- ✅ Extrações por dia: Ilimitado
- ✅ Notificações: Ilimitadas

### Limites das APIs
- ⚠️ Gemini API: 60 requisições/minuto
- ⚠️ Scraping: Respeita robots.txt
- ⚠️ MongoDB Free: 512MB

## Suporte

### Precisa de ajuda?
1. Use `/help` no bot
2. Leia este guia
3. Consulte [TELEGRAM_BOT_PT.md](TELEGRAM_BOT_PT.md)
4. Abra uma issue no GitHub

### Reportar bugs
```
1. Descreva o problema
2. Inclua o comando usado
3. Anexe screenshot se possível
4. Mencione mensagem de erro
```

## Privacidade e Segurança

- 🔒 Seus dados são armazenados de forma segura
- 🔒 Não compartilhamos suas informações
- 🔒 Você pode deletar seus dados a qualquer momento
- 🔒 Bot não tem acesso a outras conversas

---

**Última atualização:** Outubro 2024  
**Versão do Bot:** 1.0.0

Para mais informações, visite: [README.md](README.md)
