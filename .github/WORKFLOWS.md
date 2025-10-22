# GitHub Actions Workflows Documentation

Este documento descreve os workflows de CI/CD configurados para testar e monitorar o sistema de deploy do Amazon Gemini Scraper.

## 📋 Visão Geral

O projeto possui três workflows principais:

1. **Deployment Testing** - Testa o sistema de deploy completo
2. **Railway Preview** - Fornece informações para deploys de preview
3. **Production Health Check** - Monitora a saúde do deploy em produção

## 🔄 Workflow: Deployment Testing

**Arquivo**: `.github/workflows/deployment-test.yml`

### Quando é Executado

- Push para branches `main` ou `develop`
- Pull requests para `main` ou `develop`
- Manualmente via workflow_dispatch

### Jobs Executados

#### 1. **Validate Configuration**
Valida arquivos de configuração do projeto:
- Sintaxe do Dockerfile
- docker-compose.yml
- railway.json (JSON válido)
- Arquivos obrigatórios (requirements.txt, Dockerfile, etc.)
- Variáveis de ambiente no .env.example

#### 2. **Docker Build Test**
- Constrói a imagem Docker usando BuildX
- Usa cache do GitHub para acelerar builds
- Verifica o tamanho da imagem final
- **Nota**: Usa `PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1` para build mais rápido em CI

#### 3. **Application Health Test**
Testa a aplicação com serviços reais:
- Sobe Redis e MongoDB como serviços do GitHub Actions
- Instala dependências Python
- Instala navegadores Playwright
- Inicia a aplicação
- Testa endpoints:
  - `/` - Root endpoint
  - `/api/v1/health` - Health check
  - `/api/v1/health/live` - Liveness probe
  - `/api/v1/health/ready` - Readiness probe
  - `/api/v1/info` - API info
  - `/api/v1/docs` - Swagger UI
  - `/api/v1/openapi.json` - OpenAPI schema

#### 4. **Docker Compose Test**
- Testa o ambiente completo com docker-compose
- Sobe Redis e MongoDB
- Constrói e inicia o container da aplicação
- Verifica status dos containers
- Testa health check de dentro do container

#### 5. **Security Dependency Check**
- Verifica vulnerabilidades conhecidas usando `safety`
- Audita dependências usando `pip-audit`
- Identifica pacotes desatualizados

#### 6. **Railway Deployment Readiness**
Verifica se o projeto está pronto para deploy no Railway:
- Valida presença de arquivos necessários (railway.json, Dockerfile)
- Verifica documentação de variáveis de ambiente
- Confirma que PORT é tratado corretamente
- Gera checklist de prontidão

#### 7. **Test Summary**
- Resume resultados de todos os testes
- Falha se testes críticos falharem
- Fornece relatório consolidado

### Como Interpretar Resultados

✅ **Todos verdes**: Sistema pronto para deploy
⚠️ **Amarelos**: Avisos, mas não crítico
❌ **Vermelhos**: Problemas que precisam ser corrigidos

### Tempo de Execução

- **Total**: ~15-20 minutos
- Build Docker: ~5-7 minutos (com cache)
- Testes de aplicação: ~3-5 minutos
- Docker Compose: ~5-7 minutos
- Outros: ~2-3 minutos

## 🔍 Workflow: Railway Preview

**Arquivo**: `.github/workflows/railway-preview.yml`

### Quando é Executado

- Quando pull requests são abertos/atualizados
- Manualmente via workflow_dispatch

### Funcionalidade

Este workflow fornece:
- Informações sobre deploy de preview no Railway
- Checklist de arquivos necessários
- Estimativa de recursos necessários
- Checklist de segurança

### Como Usar

1. O workflow roda automaticamente em PRs
2. Revise as informações fornecidas
3. Use como guia para configurar preview deployments no Railway

### Habilitando Preview Deployments no Railway

```bash
# Via Railway Dashboard:
1. Vá para Project Settings
2. Ative "Deploy on PR"
3. Configure environment variables para preview

# Via Railway CLI:
railway up --detach
```

## 🏥 Workflow: Production Health Check

**Arquivo**: `.github/workflows/health-check.yml`

### Quando é Executado

- A cada 6 horas automaticamente (via cron)
- Manualmente com URL customizada

### Funcionalidade

#### Job: Health Check
Verifica a saúde do deployment:
- Root endpoint (`/`)
- Health endpoint (`/api/v1/health`)
- Status da aplicação (healthy/unhealthy)
- Conectividade de bancos de dados (MongoDB, Redis)
- Acessibilidade da documentação API
- Tempo de resposta
- Endpoints críticos da API

#### Job: Performance Check
- Executa múltiplas requisições
- Calcula tempo médio de resposta
- Classifica performance:
  - Excelente: < 1s
  - Boa: < 3s
  - Aceitável: < 5s
  - Precisa melhorias: > 5s

### Alertas Automáticos

Se o health check falhar:
- Cria issue automaticamente no GitHub
- Issue inclui:
  - Timestamp da falha
  - URL do deployment
  - Link para logs do workflow
  - Passos para investigação
  - Comandos de troubleshooting

### Configuração de URL

Para usar com seu deployment:

1. **Via Secrets do GitHub**:
```bash
# Adicione em Settings > Secrets and Variables > Actions
DEPLOYMENT_URL=https://seu-app.railway.app
```

2. **Via workflow_dispatch**:
- Vá em Actions > Production Health Check
- Clique em "Run workflow"
- Insira a URL do seu deployment

## 🛠️ Troubleshooting

### Build Falhando

**Problema**: Docker build timeout ou falha

**Soluções**:
```bash
# 1. Limpar cache do GitHub Actions
# Vá em Settings > Actions > Caches > Delete

# 2. Verificar Dockerfile localmente
docker build -t test .

# 3. Verificar espaço em disco
docker system df
docker system prune
```

### Testes de Aplicação Falhando

**Problema**: App não inicia ou health checks falham

**Soluções**:
```bash
# 1. Verificar logs do workflow no GitHub Actions

# 2. Testar localmente
python -m uvicorn api.main:app --reload

# 3. Verificar variáveis de ambiente
cat .env.example

# 4. Testar conexões de banco
# MongoDB
mongosh "mongodb://admin:password@localhost:27017"

# Redis
redis-cli ping
```

### Health Check Falhando em Produção

**Problema**: Health check periódico falha

**Soluções**:
```bash
# 1. Verificar logs no Railway
railway logs

# 2. Testar endpoints manualmente
curl https://seu-app.railway.app/api/v1/health

# 3. Verificar status dos serviços
railway status

# 4. Verificar variáveis de ambiente
railway variables
```

### Docker Compose Falhando

**Problema**: Serviços não iniciam corretamente

**Soluções**:
```bash
# 1. Validar docker-compose.yml
docker-compose config

# 2. Verificar logs
docker-compose logs app
docker-compose logs mongodb
docker-compose logs redis

# 3. Reiniciar serviços
docker-compose down -v
docker-compose up -d
```

## 📊 Métricas e Monitoramento

### Métricas Coletadas

Os workflows coletam:
- ✅ Status de build (sucesso/falha)
- ✅ Tempo de build
- ✅ Tamanho da imagem Docker
- ✅ Tempo de resposta da API
- ✅ Status de health checks
- ✅ Conectividade de serviços
- ✅ Vulnerabilidades de segurança

### Visualizando Métricas

1. **GitHub Actions Tab**:
   - Vá em Actions
   - Selecione workflow
   - Visualize histórico e logs

2. **Railway Dashboard**:
   - Veja métricas em tempo real
   - Monitore uso de recursos
   - Analise logs de deploy

## 🔒 Segurança

### Secrets Necessários

Configure em Settings > Secrets and Variables > Actions:

```bash
# Opcional para health checks
DEPLOYMENT_URL=https://seu-app.railway.app

# Nota: Nunca adicione API keys ou secrets aqui!
# Use Railway para gerenciar secrets de produção
```

### Boas Práticas

- ✅ Nunca comite secrets no código
- ✅ Use Railway para gerenciar secrets
- ✅ Revise relatórios de segurança
- ✅ Mantenha dependências atualizadas
- ✅ Use variáveis de teste em CI
- ✅ Valide configurações antes do deploy

## 🚀 Próximos Passos

### Após Configurar os Workflows

1. **Teste o Deployment Testing**:
```bash
git push origin main
# Aguarde workflow completar
# Revise resultados no GitHub Actions
```

2. **Configure Health Checks**:
```bash
# Adicione secret DEPLOYMENT_URL
# Aguarde próxima execução ou execute manualmente
```

3. **Monitore Regularmente**:
- Revise issues criadas automaticamente
- Monitore tempo de resposta
- Verifique vulnerabilidades de segurança

### Melhorias Futuras

- [ ] Integrar testes E2E
- [ ] Adicionar testes de carga
- [ ] Configurar alerts via Slack/Discord
- [ ] Implementar deploys automáticos
- [ ] Adicionar análise de código estático
- [ ] Configurar code coverage reporting

## 📚 Recursos Adicionais

### Documentação Relacionada

- [README.md](../README.md) - Documentação geral do projeto
- [RAILWAY_DEPLOYMENT.md](../RAILWAY_DEPLOYMENT.md) - Guia de deploy no Railway
- [DEPLOYMENT_FIXES_SUMMARY.md](../DEPLOYMENT_FIXES_SUMMARY.md) - Histórico de correções

### Links Úteis

- [GitHub Actions Docs](https://docs.github.com/en/actions)
- [Railway Docs](https://docs.railway.app)
- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)
- [FastAPI Deployment](https://fastapi.tiangolo.com/deployment/)

## 💡 Dicas

### Desenvolvimento Local

```bash
# Executar testes que os workflows executam

# 1. Validar Docker
docker run --rm -i hadolint/hadolint < Dockerfile

# 2. Validar docker-compose
docker-compose config

# 3. Testar build
docker build -t test .

# 4. Testar aplicação
uvicorn api.main:app --reload

# 5. Verificar segurança
pip install safety
safety check -r requirements.txt
```

### Debug de Workflows

```bash
# 1. Ativar debug no GitHub Actions
# Settings > Secrets > New secret
# Name: ACTIONS_STEP_DEBUG
# Value: true

# 2. Re-executar workflow com debug ativado

# 3. Revisar logs detalhados
```

### Performance

```bash
# Acelerar builds com cache

# 1. Workflows já usam cache do GitHub
# 2. Para Docker local, use BuildKit
export DOCKER_BUILDKIT=1
docker build -t test .

# 3. Para melhor performance em CI
# Considere usar Docker layer caching
```

## 🤝 Contribuindo

Para melhorar os workflows:

1. Fork o repositório
2. Crie branch para mudanças
3. Teste localmente
4. Abra Pull Request
5. Aguarde review e merge

## 📞 Suporte

Problemas ou dúvidas:
- Abra issue no GitHub
- Consulte documentação
- Revise logs dos workflows
- Verifique Railway dashboard

---

**Última atualização**: 2025-10-22

Para mais informações, consulte a [documentação principal](../README.md).
