import pytest
from datetime import date
from app.models import BatchStatus

def test_add_batch_and_consume(client, db, token):
    headers = {"Authorization": f"Bearer {token}"}

    # Создаём товар
    p = client.post(
        "/products",
        json={"name": "Рис", "category": "grain", "default_unit": "kg", "minimum_stock": 1},
        headers=headers,
    ).json()
    pid = p["id"]

    # Добавляем партию
    b = client.post(
        f"/products/{pid}/batches",
        json={
            "quantity": 2.0,
            "purchased_at": "2026-07-25",
            "expires_at": "2026-08-05",
            "storage_location": "cupboard",
            "price": 100.0,
        },
        headers=headers,
    ).json()
    bid = b["id"]

    # Проверяем, что остаток обновился
    prod = client.get(f"/products?search=Рис", headers=headers).json()[0]
    assert prod["current_stock"] == 2.0

    # Списываем часть
    resp = client.post(
        f"/products/{pid}/consume",
        json={"quantity": 0.5, "strategy": "expires_first"},
        headers=headers,
    )
    assert resp.status_code == 200
    prod2 = client.get(f"/products?search=Рис", headers=headers).json()[0]
    assert abs(prod2["current_stock"] - 1.5) < 0.01


def test_consume_insufficient_stock(client, db, token):
    headers = {"Authorization": f"Bearer {token}"}

    p = client.post(
        "/products",
        json={"name": "Сахар", "category": "grain", "default_unit": "kg", "minimum_stock": 0},
        headers=headers,
    ).json()
    pid = p["id"]

    client.post(
        f"/products/{pid}/batches",
        json={
            "quantity": 1.0,
            "purchased_at": "2026-07-25",
            "expires_at": None,
            "storage_location": "cupboard",
            "price": 50.0,
        },
        headers=headers,
    )

    resp = client.post(
        f"/products/{pid}/consume",
        json={"quantity": 2.0, "strategy": "expires_first"},
        headers=headers,
    )
    assert resp.status_code == 400
    data = resp.json()
    assert data.get("code") == "INSUFFICIENT_STOCK"


def test_discard_batch(client, db, token):
    headers = {"Authorization": f"Bearer {token}"}

    p = client.post(
        "/products",
        json={"name": "Чай", "category": "beverage", "default_unit": "package", "minimum_stock": 0},
        headers=headers,
    ).json()
    pid = p["id"]

    b = client.post(
        f"/products/{pid}/batches",
        json={
            "quantity": 1.0,
            "purchased_at": "2026-07-01",
            "expires_at": "2026-08-01",
            "storage_location": "cupboard",
            "price": 80.0,
        },
        headers=headers,
    ).json()
    bid = b["id"]

    resp = client.post(
        f"/products/{pid}/batches/{bid}/discard",
        json={"quantity": 1.0, "reason": "expired"},
        headers=headers,
    )
    assert resp.status_code == 200

    prod = client.get(f"/products?search=Чай", headers=headers).json()[0]
    assert prod["current_stock"] == 0.0