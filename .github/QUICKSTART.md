# Guia Rápido - GitHub Actions para Deploy

Este guia te ajudará a começar rapidamente com os workflows de CI/CD do projeto.

## 🚀 O Que Foi Criado

Foram criados 3 workflows automatizados:

### 1. 🧪 **Deployment Testing** (Teste de Deploy)
- **Arquivo**: `.github/workflows/deployment-test.yml`
- **Quando roda**: Automaticamente em push/PR para `main` ou `develop`
- **O que faz**: Testa todo o sistema de deploy

### 2. 🔍 **Railway Preview** (Preview de Deploy)
- **Arquivo**: `.github/workflows/railway-preview.yml`
- **Quando roda**: Automaticamente em Pull Requests
- **O que faz**: Fornece informações para deploy de preview

### 3. 💓 **Health Check** (Verificação de Saúde)
- **Arquivo**: `.github/workflows/health-check.yml`
- **Quando roda**: A cada 6 horas + manualmente
- **O que faz**: Monitora a saúde do deploy em produção

## ✅ Primeiros Passos

### 1. Visualizar os Workflows

Após fazer merge deste PR:

1. Vá para a aba **Actions** no GitHub
2. Você verá os 3 workflows listados
3. Clique em qualquer um para ver detalhes

### 2. Testar o Deployment Testing

O workflow já está rodando automaticamente! Para testar manualmente:

```bash
# 1. Vá em Actions > Deployment Testing
# 2. Clique em "Run workflow"
# 3. Selecione branch e execute
# 4. Aguarde ~15-20 minutos
# 5. Revise os resultados
```

### 3. Configurar Health Check (Opcional)

Para monitorar seu deploy em produção:

1. **Faça deploy no Railway primeiro** (se ainda não fez)
2. **Configure a URL do deploy**:
   ```bash
   # No GitHub, vá em:
   # Settings > Secrets and Variables > Actions > New repository secret
   
   # Nome: DEPLOYMENT_URL
   # Valor: https://seu-app.railway.app
   ```

3. **Execute manualmente**:
   - Vá em Actions > Production Health Check
   - Clique em "Run workflow"
   - Insira sua URL
   - Execute e veja os resultados

## 📊 Interpretando os Resultados

### ✅ Status Verde (Success)
- Tudo funcionando corretamente
- Pode fazer deploy com segurança

### ⚠️ Status Amarelo (Warning)
- Avisos encontrados
- Revise, mas não é crítico

### ❌ Status Vermelho (Failed)
- Problemas encontrados
- **NÃO faça deploy**
- Revise os logs e corrija

## 🔧 O Que Cada Workflow Testa

### Deployment Testing Verifica:

✅ **Configuração**
- Dockerfile está correto?
- docker-compose.yml é válido?
- railway.json está OK?
- Arquivos necessários existem?

✅ **Docker Build**
- Imagem constrói sem erros?
- Tamanho da imagem é aceitável?
- Build usa cache corretamente?

✅ **Aplicação**
- App inicia corretamente?
- Health checks funcionam?
- API está acessível?
- Documentação carrega?

✅ **Serviços**
- MongoDB conecta?
- Redis funciona?
- Celery inicializa?

✅ **Segurança**
- Dependências têm vulnerabilidades?
- Pacotes estão atualizados?

✅ **Railway**
- Configuração está completa?
- PORT é tratado corretamente?
- Variáveis de ambiente documentadas?

### Health Check Monitora:

💓 **Endpoints**
- `/` - Página inicial
- `/api/v1/health` - Status da aplicação
- `/api/v1/docs` - Documentação

💓 **Serviços**
- MongoDB está conectado?
- Redis está ativo?

💓 **Performance**
- Tempo de resposta < 3s?
- Aplicação responde consistentemente?

## 🐛 Problemas Comuns e Soluções

### Problema: Build Docker falha

**Sintomas**: Job "Docker Build Test" vermelho

**Soluções**:
```bash
# 1. Teste localmente
docker build -t test .

# 2. Verifique Dockerfile
cat Dockerfile

# 3. Limpe cache
docker system prune -a
```

### Problema: Testes de aplicação falham

**Sintomas**: Job "Application Health Test" vermelho

**Soluções**:
```bash
# 1. Teste localmente
uvicorn api.main:app --reload

# 2. Verifique logs no workflow
# Vá em Actions > Workflow falhado > Application Health Test

# 3. Verifique dependências
pip install -r requirements.txt
```

### Problema: Health check falha em produção

**Sintomas**: Issue automática criada no GitHub

**Soluções**:
```bash
# 1. Verifique Railway logs
railway logs

# 2. Teste endpoint manualmente
curl https://seu-app.railway.app/api/v1/health

# 3. Verifique variáveis de ambiente
railway variables

# 4. Reinicie o serviço se necessário
railway restart
```

## 📚 Próximos Passos

### Depois de Configurar

1. ✅ **Faça um commit de teste**
   ```bash
   git commit --allow-empty -m "Test workflows"
   git push
   ```
   - Vá em Actions e veja os workflows rodando

2. ✅ **Revise os resultados**
   - Todos verdes? Ótimo!
   - Algum vermelho? Veja os logs e corrija

3. ✅ **Configure notificações**
   - Settings > Notifications
   - Ative "Actions" para receber alertas

4. ✅ **Faça deploy no Railway**
   - Siga o [guia de deploy](../RAILWAY_DEPLOYMENT.md)
   - Configure health check com sua URL
   - Monitore automaticamente

### Recursos Adicionais

- 📖 [Documentação Completa dos Workflows](.github/WORKFLOWS.md)
- 🚂 [Guia de Deploy no Railway](../RAILWAY_DEPLOYMENT.md)
- 📝 [README do Projeto](../README.md)
- 🔧 [Resumo de Correções](../DEPLOYMENT_FIXES_SUMMARY.md)

## 💡 Dicas Pro

### 1. Badges no README

Adicione badges para mostrar status dos workflows:

```markdown
![Deployment Tests](https://github.com/seu-usuario/seu-repo/workflows/Deployment%20Testing/badge.svg)
![Health Check](https://github.com/seu-usuario/seu-repo/workflows/Production%20Health%20Check/badge.svg)
```

### 2. Notificações Personalizadas

Configure Slack/Discord para receber alertas:
- Settings > Webhooks
- Configure URL do webhook
- Receba notificações em tempo real

### 3. Ambiente de Staging

Crie um ambiente de teste:
```bash
# 1. Crie branch staging
git checkout -b staging

# 2. Configure Railway para staging
railway env staging

# 3. Workflows testarão automaticamente
```

### 4. Cache de Build

Os workflows já usam cache para velocidade:
- Build Docker: cache de layers
- Python: cache de pip
- Resultado: builds até 5x mais rápidos

## 🎯 Checklist de Sucesso

Use este checklist para garantir que tudo está funcionando:

- [ ] Workflows aparecem na aba Actions
- [ ] Deployment Testing roda em push
- [ ] Todos os jobs passam (verde)
- [ ] Docker build completa sem erros
- [ ] Aplicação inicia corretamente
- [ ] Health checks funcionam
- [ ] Segurança OK (sem vulnerabilidades críticas)
- [ ] Railway configuração validada
- [ ] Health check de produção configurado (se já deployed)
- [ ] Notificações ativas

## ❓ Perguntas Frequentes

### Quanto tempo demora?

- **Deployment Testing**: ~15-20 minutos
- **Railway Preview**: ~1-2 minutos
- **Health Check**: ~2-3 minutos

### Isso consome minutos do GitHub?

Sim, mas:
- Repos públicos: ilimitado e grátis
- Repos privados: 2000 minutos/mês no free tier
- Estes workflows usam ~25 min por execução completa

### Posso desabilitar workflows?

Sim:
1. Vá em Actions
2. Selecione workflow
3. Clique em "..." > "Disable workflow"

### Como adicionar mais testes?

Edite os arquivos `.github/workflows/*.yml`:
1. Adicione steps ao job desejado
2. Commit e push
3. Workflow rodará automaticamente

### Posso rodar localmente?

Sim, usando [act](https://github.com/nektos/act):
```bash
# Instale act
brew install act  # ou outro método

# Execute workflow
act -j validate-config
```

## 🤝 Precisa de Ajuda?

- 🐛 **Bug ou erro**: Abra uma issue
- 💬 **Pergunta**: Use Discussions
- 📧 **Suporte**: Veja documentação ou contate o time
- 📖 **Mais info**: Leia [WORKFLOWS.md](WORKFLOWS.md)

---

**Criado em**: 2025-10-22
**Última atualização**: 2025-10-22

Aproveite os workflows automatizados! 🚀
