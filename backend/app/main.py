jfrom fastapi import FastAPI

from app.database.connection import Base, engine

# Cria as tabelas no banco caso ainda não existam.
# Quando o projeto crescer, isso deve ser substituído por migrations (Alembic).
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Price Monitor API")


@app.get("/health")
def health_check():
    return {"status": "ok"}


# As rotas de products, monitoring, prices e settings entram aqui,
# via app.include_router(...), conforme forem implementadas.
