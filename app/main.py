from fastapi import FastAPI
from app.config import settings
from app.database import engine, Base
from app.api import auth, products, batches, operations
from app.api import recommendations as rec_api

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Inventory Manager", version="0.1.0")

app.include_router(auth.router, prefix="/auth")
app.include_router(products.router)
app.include_router(batches.router)
app.include_router(operations.router)
app.include_router(rec_api.router)

@app.get("/")
def root():
    return {"message": "Inventory Manager API is running. Docs: /docs"}