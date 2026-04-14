from app.core.database import SessionLocal
from app.seeds.roles_seed import seed_roles


def run_seeds() -> None:
    db = SessionLocal()
    try:
        seed_roles(db)
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
