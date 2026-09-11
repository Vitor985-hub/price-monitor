# Resumo Técnico — RPA de Monitoramento de Preços

## 1. Contexto

Desenvolver um sistema de automação (RPA) para a empresa do autor, cujo negócio envolve a venda de cosméticos em e-commerce.

O objetivo principal é monitorar os preços de produtos comercializados por concorrentes, permitindo acompanhar a variação de preços ao longo do tempo com uma visão centralizada.

**Prioridades do sistema:**
- Simplicidade
- Confiabilidade
- Baixo custo
- Facilidade de manutenção
- Facilidade de uso para pessoas com pouco conhecimento técnico
- Arquitetura organizada e escalável, sem overengineering

**Fora de escopo por enquanto:** IA/LLMs. O projeto usa regras determinísticas e técnicas tradicionais de processamento de dados. IA só será considerada futuramente se surgir uma necessidade real que não possa ser resolvida por regras convencionais.

## 2. Arquitetura

| Camada | Tecnologia |
|---|---|
| Backend | Python |
| API | FastAPI |
| Scraping (HTML estático) | Requests/HTTPX + BeautifulSoup |
| Scraping (páginas dinâmicas) | Playwright |
| Banco de dados | PostgreSQL |
| ORM | SQLAlchemy |
| Agendamento | APScheduler ou cron |
| Frontend | React |
| Infraestrutura | Docker + Docker Compose |

Fluxo geral:

```
React Frontend → FastAPI API → Services → Scrapers → Lojas concorrentes
                        ↓
                   PostgreSQL
                        ↑
                   Scheduler
```

**Decisão de arquitetura:** sistema monolítico modular, com responsabilidades bem separadas. Sem microsserviços neste momento.

## 3. Estrutura do Projeto

```
price-monitor/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── routes/
│   │   │   │   ├── products.py
│   │   │   │   ├── monitoring.py
│   │   │   │   ├── prices.py
│   │   │   │   └── settings.py
│   │   │   └── schemas/
│   │   ├── database/
│   │   │   ├── connection.py
│   │   │   └── models.py
│   │   ├── scrapers/
│   │   │   ├── base.py
│   │   │   ├── concorrente_a.py
│   │   │   └── concorrente_b.py
│   │   ├── services/
│   │   │   ├── product_search.py
│   │   │   ├── product_matching.py
│   │   │   └── price_monitor.py
│   │   ├── scheduler/
│   │   │   └── jobs.py
│   │   └── main.py
│   ├── tests/
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/        # inclui página de Configurações
│   │   ├── services/
│   │   └── App.jsx
│   ├── package.json
│   └── Dockerfile
├── docker-compose.yml
├── .env
├── .env.example
├── .gitignore
└── README.md
```

A estrutura pode ser ajustada durante o desenvolvimento, evitando complexidade desnecessária.

## 4. Fluxo Principal — Estratégia Híbrida

O sistema combina busca por nome (para descoberta) com URL fixa (para monitoramento contínuo):

```
Nome do produto
      ↓
Pesquisa nos concorrentes
      ↓
Resultados candidatos
      ↓
Matching (regras determinísticas + similaridade textual)
      ↓
Confirmação humana
      ↓
URL do produto é salva
      ↓
Monitoramento contínuo pela URL
```

**Etapa 1 — Pesquisa:** o usuário cadastra nome, marca e (opcionalmente) EAN do produto. O sistema pesquisa nos sites dos concorrentes configurados, evitando cadastro manual de URLs.

**Etapa 2 — Identificação e validação:** a pesquisa pode retornar vários candidatos. O sistema compara resultados usando regras determinísticas (EAN, SKU, marca, nome, volume/peso, categoria) e similaridade textual (ex: biblioteca `rapidfuzz`). O sistema **não assume automaticamente** que o primeiro resultado é o correto — o usuário confirma quais resultados realmente correspondem.

Depois que uma URL é validada, ela é reutilizada diretamente nas próximas coletas — não é necessário repetir a busca por nome a cada monitoramento.

## 5. Monitoramento

```
URL cadastrada → Scheduler → Scraper correspondente → Preço atual → PostgreSQL → Histórico
```

O histórico armazena cada coleta (não é necessário, por ora, otimizar removendo preços repetidos).

## 6. Modelagem de Dados

**products** — produto da empresa
- id, name, brand, ean, created_at

**monitored_products** — produto sendo monitorado em um concorrente específico (1:N com `products`)
- id, product_id, competitor, url, active, created_at

**price_history** — histórico de coletas (1:N com `monitored_products`)
- id, monitored_product_id, price, collected_at

**settings** — configuração do sistema (novo, ver seção 7)
- id, scrape_frequency_minutes (ou cron_expression), updated_at

Um produto pode ter várias entradas em `monitored_products` (um por concorrente monitorado).

## 7. Configuração da Frequência do Scheduler

**Decisão:** a frequência de coleta não é estática no código — é configurável pela própria empresa, através de uma seção dedicada no frontend.

- **Banco:** tabela/registro `settings` guardando a frequência atual.
- **Representação:** priorizar opções amigáveis na UI (ex: "a cada 15 min / 30 min / 1h / 6h / 12h / 24h" ou um horário fixo tipo "todos os dias às ___"), evitando expor cron diretamente para usuários sem conhecimento técnico. Internamente isso é traduzido para a configuração real do agendador.
- **Backend:** endpoints `GET /settings` e `PUT /settings`. O `APScheduler` precisa suportar reconfiguração em tempo de execução (remover/recriar o job ou usar `reschedule_job`) sem exigir reiniciar a aplicação.
- **Frontend:** nova seção de "Configurações" com o campo de frequência, podendo mostrar também "próxima execução prevista" e "última execução".

## 8. Status das Coletas

Uma coleta pode ter diferentes resultados, não apenas "preço encontrado" ou "não encontrado":

`SUCCESS`, `PRICE_NOT_FOUND`, `PRODUCT_UNAVAILABLE`, `NOT_FOUND`, `BLOCKED`, `TIMEOUT`, `ERROR`

Erros de scraping nunca devem ser interpretados como preço zero ou outro valor inválido. O frontend deve exibir claramente o status da última coleta (ex: 🟢 sucesso / ⚠️ falha).

## 9. Scrapers

Cada concorrente possui seu próprio scraper, com uma classe/interface base para padronizar o comportamento:

```
scrapers/
├── base.py
├── concorrente_a.py
├── concorrente_b.py
└── concorrente_c.py
```

- HTML estático → `requests`/`httpx` + `BeautifulSoup`
- Conteúdo via JavaScript → `Playwright` (usar apenas quando necessário, evitando uso indiscriminado)

## 10. API

Endpoints iniciais esperados:

```
GET  /products
GET  /products/{id}
POST /products
POST /products/search
GET  /products/{id}/history

GET    /monitoring
POST   /monitoring
DELETE /monitoring/{id}

GET /settings
PUT /settings
```

A API não deve conter lógica pesada de scraping diretamente nas rotas — rotas chamam services, que chamam scrapers/banco.

## 11. Frontend

Pensado para usuários sem conhecimento técnico — não precisam entender scraper, API, banco, scheduler, HTTP ou Playwright.

Telas previstas:
- Produtos cadastrados e concorrentes monitorados
- Preço atual, histórico e variação de preço
- Status da última coleta e erros
- Resultados de pesquisa para validação/confirmação
- **Configurações** (frequência do scheduler)

## 12. Segurança e Configuração

- Credenciais via variáveis de ambiente (`.env`), nunca no código
- `.env` fora do Git; `.env.example` com nomes das variáveis, sem valores reais

## 13. Docker

`docker-compose.yml` inicial com PostgreSQL, backend e frontend, facilitando instalação local e futura implantação na infraestrutura da empresa.

## 14. Cuidados com Scraping

Antes de implementar cada concorrente: verificar `robots.txt`, verificar Termos de Serviço, respeitar rate limits, evitar excesso de requisições, tratar timeout/erros HTTP/mudanças no HTML.

## 15. Fora de Escopo Inicial

Não adicionar sem necessidade real: LLM, OpenAI API, Ollama, embeddings, banco vetorial, microsserviços, Redis, Kafka, Kubernetes, arquitetura distribuída, filas complexas.

## 16. Evolução Futura

**Fase 1 (MVP):** cadastro → pesquisa por nome → resultados → confirmação → URL salva → monitoramento → histórico.

**Fase 2:** alertas de queda de preço, comparação entre concorrentes, filtros, dashboard, exportação de dados, melhorias no matching, monitoramento de disponibilidade.

**Fase 3:** automação mais avançada, incluindo IA — apenas se métodos determinísticos não forem suficientes e houver justificativa de custo-benefício.

## 17. Princípio do Projeto

> Nome para descobrir. URL para monitorar. Regras para identificar. Humano para validar quando houver dúvida.

Simples para o usuário final, tecnicamente organizado para facilitar manutenção e evolução. Nenhuma funcionalidade deve existir apenas por ser tecnicamente interessante — toda funcionalidade resolve uma necessidade real da empresa.
