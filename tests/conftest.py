import os
import tempfile
from pathlib import Path
import pytest
from unittest.mock import patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
from app.main import app
from app.database import Base, get_db

# --- Патч хеширования (теперь это страховка, если TEST не сработает) ---
def _fake_hash(password: str) -> str:
    return f"fakehash_{password}"

@pytest.fixture(autouse=True)
def mock_password_hash():
    with patch("app.auth.get_password_hash", _fake_hash):
        yield

# --- Фикстура БД ---
@pytest.fixture(scope="function")
def db():
    tmp_file = tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False)
    db_path = tmp_file.name
    tmp_file.close()

    engine = create_engine(f"sqlite:///{db_path}", echo=False, future=True)

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = TestingSessionLocal()

    try:
        yield session
    finally:
        session.close()
        engine.dispose()
        if Path(db_path).exists():
            try:
                os.remove(db_path)
            except PermissionError:
                pass

# --- Клиент с подменой get_db ---
@pytest.fixture
def client(db):
    # Подменяем get_db на возврат тестовой сессии
    def override_get_db():
        yield db

    # Важно: импортируй get_db из того места, где он объявлен как зависимость
    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()

# --- Токен ---
@pytest.fixture
def token(client, db):
    resp = client.post("/auth/register", json={"username": "testuser", "password": "password"})
    assert resp.status_code == 200, f"Регистрация упала: {resp.text}"
    return resp.json()["access_token"]