from datetime import timedelta, datetime
from sqlalchemy.orm import Session
import app.models as m
from app.forecast import calculate_forecast

def generate_recommendations(db: Session, user_id: int):
    recommendations = []
    products = db.query(m.Product).filter(m.Product.owner_id == user_id).all()

    now = datetime.now()
    soon_threshold = timedelta(days=3)  # можно вынести в настройки

    for product in products:
        batches = [b for b in product.batches if b.status not in [m.BatchStatus.consumed, m.BatchStatus.discarded]]

        # Use soon: партии, у которых expires_at скоро
        for b in batches:
            if b.expires_at and b.expires_at - now <= soon_threshold:
                recommendations.append({
                    "type": "use_soon",
                    "priority": "high",
                    "product_id": product.id,
                    "batch_id": b.id,
                    "message": f"Используйте {product.name} до {b.expires_at.date()}",
                    "expires_at": b.expires_at.date(),
                })

        # Buy: если остаток ниже минимального
        current_stock = sum(b.quantity_remaining for b in batches)
        if current_stock < product.minimum_stock:
            recommendations.append({
                "type": "buy",
                "priority": "medium",
                "product_id": product.id,
                "message": f"Докупить {product.name}",
                "recommended_quantity": product.minimum_stock - current_stock,
            })

        # Waste risk: если прогноз показывает, что не успеем использовать до истечения
        forecast = calculate_forecast(db, product.id)
        if forecast["estimated_depletion_date"]:
            for b in batches:
                if b.expires_at and forecast["estimated_depletion_date"] < b.expires_at.date():
                    recommendations.append({
                        "type": "waste_risk",
                        "priority": "high",
                        "product_id": product.id,
                        "message": f"Риск потери: не успеете использовать {product.name} до {b.expires_at.date()}",
                        "expected_unused_quantity": b.quantity_remaining,
                    })
                    break

    return recommendations