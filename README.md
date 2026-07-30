# Inventory Manager — Менеджер домашних запасов

Backend-сервис для учёта продуктов и бытовых товаров: партии, списания, прогноз расхода, рекомендации, уведомления.

## Стек

- Python 3.11+
- FastAPI
- SQLAlchemy + SQLite (для запуска без PostgreSQL)
- Alembic (миграции)
- JWT (авторизация)
- Pytest (тесты)

## Установка и запуск

1. Клонируй репозиторий.
2. Создай виртуальное окружение:
   bash
   python -m venv myenv
   # Windows PowerShell:
   .\myenv\Scripts\Activate.ps1

Установи зависимости:

bash
pip install -r requirements.txt

Скопируй .env.example в .env и заполни значения:

env

DATABASE_URL=sqlite:///./db.sqlite3
SECRET_KEY=supersecretkey1234567890123456789012
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
EXPIRING_SOON_DAYS=3

Примени миграции:

bash
alembic upgrade head

Запусти сервер:

bash
uvicorn app.main:app --reload
Swagger UI: http://localhost:8000/docs

Примеры запросов (curl)

Регистрация

bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"password"}'

Вход

bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=testuser&password=password"

Создать товар

bash
curl -X POST http://localhost:8000/products \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"name":"Молоко","category":"dairy","default_unit":"liter","minimum_stock":2}'

Добавить партию

bash
curl -X POST http://localhost:8000/products/1/batches \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "quantity":2,
    "purchased_at":"2026-07-25",
    "expires_at":"2026-08-02",
    "storage_location":"fridge",
    "price":3.4
  }'

Списать товар

bash
curl -X POST http://localhost:8000/products/1/consume \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"quantity":0.5,"strategy":"expires_first","comment":"Завтрак"}'

Прогноз

bash
curl http://localhost:8000/products/1/forecast \
  -H "Authorization: Bearer YOUR_TOKEN"

Тесты

bash
pytest

Особенности реализации

Идемпотентность: поддерживается через idempotency_key в операциях.
Конкурентность: все изменения происходят в рамках одной транзакции.
Прогноз и рекомендации: на основе истории списаний.
Уведомления: генерируются фоновым заданием раз в сутки.

Миграции

Создать миграцию: alembic revision --autogenerate -m "Description"
Применить: alembic upgrade head

Фоновые задачи

Реализованы как синхронная функция daily_background_job.