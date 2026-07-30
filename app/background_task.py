from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app import models as m, recommendations

def daily_background_job(db: Session):
    """
    Идемпотентная фоновая задача (запускать 1 раз в сутки).
    - обновляет статусы партий (fresh/expiring_soon/expired)
    - генерирует/обновляет рекомендации
    - создаёт уведомления (если ещё нет за сегодня для этой комбинации)
    """
    now = datetime.now()
    threshold = timedelta(days=3)  # можно брать из settings.EXPIRING_SOON_DAYS

    # 1. Обновляем статусы партий
    batches = db.query(m.Batch).all()
    for b in batches:
        new_status = m.BatchStatus.fresh
        if b.quantity_remaining <= 0:
            new_status = m.BatchStatus.consumed
        elif b.expires_at:
            if now > b.expires_at:
                new_status = m.BatchStatus.expired
            elif now + threshold >= b.expires_at:
                new_status = m.BatchStatus.expiring_soon

        if b.status != new_status:
            b.status = new_status
            db.add(b)

    db.commit()

    # 2. Генерируем рекомендации и очищаем старые (упрощённо: перезаписываем)
    db.query(m.Recommendation).delete()
    recs = recommendations.generate_recommendations(db, None)  # если нужно по пользователям — циклом по User
    for r in recs:
        rec_obj = m.Recommendation(
            product_id=r["product_id"],
            rec_type=r["type"],
            priority=r["priority"],
            message=r["message"],
            expires_at=r.get("expires_at"),
            expected_unused_quantity=r.get("expected_unused_quantity"),
        )
        db.add(rec_obj)

    # 3. Создаём уведомления (идемпотентно: не дублируем за сутки)
    today_start = datetime.combine(now.date(), datetime.min.time())

    for user in db.query(m.User).all():
        # Уведомления: expiring_soon, expired, low_stock, waste_risk
        # Для простоты генерируем по тем же правилам, что и рекомендации
        user_recs = [r for r in recs if True]  # тут можно фильтровать по product.owner_id
        for r in user_recs:
            ntype = r["type"]
            existing = db.query(m.Notification).filter(
                m.Notification.user_id == user.id,
                m.Notification.notification_type == getattr(m.NotificationType, ntype.replace("_", ""), None),
                m.Notification.created_at >= today_start,
            ).first()
            if existing:
                continue  # уже есть уведомление за сегодня — идемпотентность

            msg = r["message"]
            nt = getattr(m.NotificationType, r["type"].replace("_", ""), m.NotificationType.will_run_out)
            notification = m.Notification(
                user_id=user.id,
                notification_type=nt,
                product_id=r.get("product_id"),
                batch_id=r.get("batch_id"),
                message=msg,
            )
            db.add(notification)

    db.commit()