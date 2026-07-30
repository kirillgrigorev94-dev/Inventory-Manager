import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
from app.main import app
from app.database import Base, get_db
from app.config import settings

SQLALCHEMY_DATABASE_URL = "sqlite:///./test_db.sqlite3"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

# Переопределяем зависимости для тестов
app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(scope="function")
def db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    yield db
    db.close()
    os.remove("test_db.sqlite3")

@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c
        
@pytest.fixture
def token(client, db):
    # Регистрируем пользователя
    resp = client.post("/auth/register", json={"username": "testuser", "password": "password"})
    assert resp.status_code == 200
    return resp.json()["access_token"]