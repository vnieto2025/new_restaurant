"""
Row Level Security de PostgreSQL como segunda capa de aislamiento entre empresas (ADR-002, ADR-023).

- Toda tabla con empresa_id tiene la política "aislamiento_empresa", forzada también para el dueño.
- Con app.empresa_id fijado (peticiones de una empresa) solo se ven y escriben filas de esa empresa.
- Sin fijarlo (ingreso, consola de plataforma, resolver el token de un QR) la política no restringe.

Se ejecuta desde seed.py con el usuario dueño de las tablas.
"""
from sqlalchemy import text, inspect
from Config.db import BASE

POLITICA = "aislamiento_empresa"
CONDICION = (
    "coalesce(current_setting('app.empresa_id', true), '') = '' "
    "OR empresa_id = nullif(current_setting('app.empresa_id', true), '')::bigint"
)


def tablas_de_empresa():
    return sorted(nombre for nombre, tabla in BASE.metadata.tables.items() if "empresa_id" in tabla.columns)


def literal(valor: str):
    return "'" + str(valor).replace("'", "''") + "'"


def configurar(admin_engine, app_user=None, app_pass=None):
    with admin_engine.begin() as conn:
        existentes = set(inspect(conn).get_table_names())
        tablas = [t for t in tablas_de_empresa() if t in existentes]

        for tabla in tablas:
            conn.execute(text(f'ALTER TABLE "{tabla}" ENABLE ROW LEVEL SECURITY'))
            conn.execute(text(f'ALTER TABLE "{tabla}" FORCE ROW LEVEL SECURITY'))
            conn.execute(text(f'DROP POLICY IF EXISTS {POLITICA} ON "{tabla}"'))
            conn.execute(text(f'CREATE POLICY {POLITICA} ON "{tabla}" USING ({CONDICION}) WITH CHECK ({CONDICION})'))

        if app_user:
            existe = conn.execute(text("SELECT 1 FROM pg_roles WHERE rolname = :r"), {"r": app_user}).first()
            accion = "ALTER" if existe else "CREATE"
            conn.execute(text(f'{accion} ROLE "{app_user}" LOGIN PASSWORD {literal(app_pass)} NOSUPERUSER NOBYPASSRLS'))
            base = conn.execute(text("SELECT current_database()")).scalar()
            conn.execute(text(f'GRANT CONNECT ON DATABASE "{base}" TO "{app_user}"'))
            conn.execute(text(f'GRANT USAGE ON SCHEMA public TO "{app_user}"'))
            conn.execute(text(f'GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO "{app_user}"'))
            conn.execute(text(f'GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO "{app_user}"'))
    return tablas
