# Price Monitor

RPA para monitorar preços de produtos em e-commerces concorrentes.

## Como rodar (local, com Docker)

1. Copie `.env.example` para `.env` e ajuste a senha do banco:
   ```
   cp .env.example .env
   ```
2. Suba os containers:
   ```
   docker compose up --build
   ```
3. Backend disponível em `http://localhost:8000` (checar `/health`)
4. Frontend disponível em `http://localhost:5173` (a ser implementado)

## Estrutura

- `backend/` — API (FastAPI), scrapers, banco (SQLAlchemy/PostgreSQL), scheduler (APScheduler)
- `frontend/` — interface React

## Próximos passos

- [ ] Implementar rotas de `products` (CRUD + busca por nome)
- [ ] Implementar `product_matching` (regras determinísticas + rapidfuzz)
- [ ] Implementar primeiro scraper de exemplo (`scrapers/base.py` + um concorrente real)
- [ ] Implementar rota e job do `scheduler` com frequência configurável (`settings`)
- [ ] Estrutura inicial do frontend (React)
