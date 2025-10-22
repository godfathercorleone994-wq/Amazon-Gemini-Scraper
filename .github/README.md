# GitHub Actions & CI/CD

Bem-vindo ao sistema de CI/CD do Amazon Gemini Scraper! 🚀

## 📋 Índice

- [Começar Rapidamente](#-começar-rapidamente)
- [Workflows Disponíveis](#-workflows-disponíveis)
- [Documentação](#-documentação)
- [Status dos Workflows](#-status-dos-workflows)

## 🚀 Começar Rapidamente

Novo aqui? Comece por aqui:

👉 **[QUICKSTART.md](QUICKSTART.md)** - Guia rápido de 5 minutos

## 🔄 Workflows Disponíveis

### 1. Deployment Testing
**Arquivo**: `workflows/deployment-test.yml`

Testa completamente o sistema de deploy:
- ✅ Valida configurações
- ✅ Build Docker
- ✅ Testes de aplicação
- ✅ Docker Compose
- ✅ Verificação de segurança
- ✅ Prontidão para Railway

**Quando roda**: Push/PR para `main` ou `develop`

### 2. Railway Preview
**Arquivo**: `workflows/railway-preview.yml`

Fornece informações para deploys de preview:
- ✅ Checklist de arquivos
- ✅ Estimativas de recursos
- ✅ Validações de segurança

**Quando roda**: Pull Requests

### 3. Production Health Check
**Arquivo**: `workflows/health-check.yml`

Monitora a saúde do deploy em produção:
- ✅ Health endpoints
- ✅ Conectividade de serviços
- ✅ Métricas de performance
- ✅ Alertas automáticos

**Quando roda**: A cada 6 horas + manual

## 📚 Documentação

### Para Iniciantes
- 📖 [QUICKSTART.md](QUICKSTART.md) - Comece aqui!

### Documentação Completa
- 📖 [WORKFLOWS.md](WORKFLOWS.md) - Documentação detalhada de todos os workflows

### Documentação do Projeto
- 📖 [README.md](../README.md) - Documentação geral
- 📖 [RAILWAY_DEPLOYMENT.md](../RAILWAY_DEPLOYMENT.md) - Guia de deploy
- 📖 [DEPLOYMENT_FIXES_SUMMARY.md](../DEPLOYMENT_FIXES_SUMMARY.md) - Histórico de correções

## 📊 Status dos Workflows

Veja o status atual dos workflows:

```
Actions → Selecione workflow → Veja histórico
```

### Como Interpretar

- ✅ **Verde (Success)**: Tudo OK
- ⚠️ **Amarelo (Warning)**: Avisos, não crítico
- ❌ **Vermelho (Failed)**: Problemas encontrados
- 🔵 **Azul (Running)**: Executando agora
- ⚪ **Cinza (Pending)**: Na fila

## 🎯 O Que Cada Workflow Testa

### Deployment Testing

| Job | O Que Verifica |
|-----|----------------|
| Validate Configuration | Arquivos de config, syntax, completude |
| Docker Build Test | Build da imagem, cache, tamanho |
| Application Health Test | Startup, endpoints, health checks |
| Docker Compose Test | Ambiente completo, integração |
| Security Check | Vulnerabilidades, dependências |
| Railway Readiness | Prontidão para deploy no Railway |
| Test Summary | Consolidação de resultados |

### Health Check

| Job | O Que Monitora |
|-----|----------------|
| Health Check | Endpoints, serviços, response time |
| Performance Check | Métricas, tempo médio de resposta |

## 🔧 Configuração

### Secrets Necessários

Configure em: `Settings → Secrets and Variables → Actions`

```bash
# Opcional - para health checks de produção
DEPLOYMENT_URL=https://seu-app.railway.app
```

### Variáveis de Ambiente

Nenhuma variável adicional necessária. Os workflows usam:
- Variáveis do GitHub (automáticas)
- Valores de teste (definidos nos workflows)
- Secrets (opcionais, para produção)

## 🚀 Como Usar

### Execução Automática

Os workflows rodam automaticamente:
- **Deployment Testing**: Em todo push/PR
- **Railway Preview**: Em pull requests
- **Health Check**: A cada 6 horas

### Execução Manual

1. Vá em **Actions**
2. Selecione o workflow
3. Clique em **Run workflow**
4. Selecione branch/parâmetros
5. Clique em **Run workflow**

### Executar Localmente

Use [act](https://github.com/nektos/act):

```bash
# Instalar
brew install act

# Executar job específico
act -j validate-config

# Executar workflow completo
act push
```

## 🐛 Troubleshooting

### Workflow Falhou?

1. **Clique no workflow com falha**
2. **Expanda o job vermelho**
3. **Veja os logs detalhados**
4. **Identifique o erro**
5. **Corrija e faça novo commit**

### Problemas Comuns

| Problema | Solução |
|----------|---------|
| Docker build timeout | Limpe cache ou reduza imagem |
| App não inicia | Verifique variáveis de ambiente |
| Health check falha | Verifique URL do deployment |
| Dependências com vulnerabilidades | Atualize requirements.txt |

Veja mais em: [WORKFLOWS.md - Troubleshooting](WORKFLOWS.md#-troubleshooting)

## 📈 Métricas

Os workflows coletam e reportam:

- ⏱️ Tempo de build
- 📦 Tamanho da imagem Docker
- 🏥 Status de health
- 📊 Tempo de resposta
- 🔒 Vulnerabilidades encontradas
- ✅ Taxa de sucesso dos testes

## 🔔 Notificações

### Receber Alertas

Configure notificações:
1. `Settings → Notifications`
2. Ative **Actions**
3. Escolha método (email, web, mobile)

### Issues Automáticas

O Health Check cria issues automaticamente se:
- ❌ Deployment está inacessível
- ❌ Health checks falham
- ❌ Serviços estão offline

## 🎓 Aprendendo Mais

### Tutoriais
- [GitHub Actions Docs](https://docs.github.com/en/actions)
- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)
- [Railway Docs](https://docs.railway.app)

### Exemplos
- Veja os logs dos workflows
- Estude os arquivos YAML
- Experimente modificações

## 🤝 Contribuindo

Quer melhorar os workflows?

1. Fork o repositório
2. Crie branch para mudanças
3. Edite arquivos `.github/workflows/*.yml`
4. Teste suas mudanças
5. Abra Pull Request

### Sugestões de Melhorias

- [ ] Adicionar testes E2E
- [ ] Integrar testes de carga
- [ ] Notificações via Slack/Discord
- [ ] Deploy automático para staging
- [ ] Code coverage reporting
- [ ] Análise de código estático

## 📞 Suporte

Precisa de ajuda?

- 📖 **Documentação**: Leia [WORKFLOWS.md](WORKFLOWS.md)
- 🐛 **Bug**: Abra uma issue
- 💬 **Pergunta**: Use GitHub Discussions
- 📧 **Contato**: Veja README principal

## 📅 Changelog

### 2025-10-22 - Criação Inicial

Criados 3 workflows completos:
- ✅ Deployment Testing
- ✅ Railway Preview
- ✅ Production Health Check

Incluindo:
- 7 jobs de teste
- Validações de segurança
- Monitoramento automático
- Documentação completa

## 📝 Notas

### Custos

- **Repos públicos**: Grátis e ilimitado
- **Repos privados**: 2000 min/mês no free tier
- **Uso estimado**: ~25 min por execução completa

### Otimizações

Os workflows já incluem:
- ✅ Cache de Docker layers
- ✅ Cache de dependências pip
- ✅ Execução paralela de jobs
- ✅ Skip de browsers Playwright em CI

### Limitações

- Build Docker: ~5-7 minutos (Playwright)
- Testes de aplicação: requerem serviços
- Health check: requer deployment ativo

## 🌟 Recursos

### Badges

Adicione ao seu README:

```markdown
![Deployment Tests](https://github.com/godfathercorleone994-wq/Amazon-Gemini-Scraper/workflows/Deployment%20Testing/badge.svg)
```

### Dashboards

Veja métricas em:
- GitHub Actions tab
- Insights → Community
- Graphs → Contributors

## 🎯 Próximos Passos

1. ✅ Leia [QUICKSTART.md](QUICKSTART.md)
2. ✅ Veja workflows em ação
3. ✅ Configure health checks
4. ✅ Faça deploy no Railway
5. ✅ Monitore automaticamente

---

**Versão**: 1.0.0
**Data**: 2025-10-22
**Mantenedor**: GitHub Copilot

Para mais informações, consulte a [documentação completa](WORKFLOWS.md).

🚀 **Happy Deploying!**
