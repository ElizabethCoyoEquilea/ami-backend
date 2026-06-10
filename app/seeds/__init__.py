from app.core.database import SessionLocal
from app.seeds.especialidades_seed import seed_especialidades
from app.seeds.roles_seed import seed_roles
from app.seeds.usuarios_seed import seed_usuarios


def run_seeds() -> None:
    db = SessionLocal()
    try:
        seed_roles(db)
        seed_especialidades(db)
        seed_usuarios(db)
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
