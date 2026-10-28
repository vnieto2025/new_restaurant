import sqlalchemy
from sqlalchemy import event, text
from sqlalchemy.orm import sessionmaker, declarative_base, Session
import os
from dotenv import load_dotenv

BASE = declarative_base()
load_dotenv()

host = os.getenv("DB_HOST")
port = os.getenv("DB_PORT")
db_name = os.getenv("DB_NAME")


def make_engine(user, passwd):
    connect_url = sqlalchemy.engine.url.URL.create(
        "postgresql+psycopg",
        username=user,
        password=passwd,
        host=host,
        port=int(port),
        database=db_name,
    )
    # pool_pre_ping evita errores con conexiones que Postgres ya cerró.
    # Las fechas se guardan y se leen en UTC (RG-08); cada restaurante las muestra en su zona horaria.
    return sqlalchemy.create_engine(
        connect_url,
        pool_pre_ping=True,
        connect_args={"options": "-c timezone=UTC"},
    )


# Dueño de las tablas: crea el esquema, corre migraciones y configura RLS (seed.py)
admin_engine = make_engine(os.getenv("DB_USER"), os.getenv("DB_PASS"))

# La aplicación usa un rol sin privilegios especiales para que Row Level Security la limite (ADR-023).
# Un superusuario de Postgres se salta RLS, por eso no se usa en producción.
APP_USER = os.getenv("DB_APP_USER")
engine = make_engine(APP_USER, os.getenv("DB_APP_PASS")) if APP_USER else admin_engine

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@event.listens_for(Session, "after_begin")
def fijar_empresa(session, transaction, connection):
    """ Cada transacción de una petición de empresa fija app.empresa_id: la base de datos
        rechaza filas de otra empresa aunque una consulta olvide filtrar (RG-16). """
    empresa_id = session.info.get("empresa_id")
    if empresa_id:
        connection.execute(text("SELECT set_config('app.empresa_id', :empresa, true)"), {"empresa": str(empresa_id)})


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
