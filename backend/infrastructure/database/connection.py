import psycopg2
from config import DB_CONFIG

def get_db_connection():
    """Estabelece conexão com o banco de dados PostgreSQL."""
    conn = psycopg2.connect(
        host=DB_CONFIG["host"],
        database=DB_CONFIG["database"],
        user=DB_CONFIG["user"],
        password=DB_CONFIG["password"],
        port=DB_CONFIG["port"]
    )
    conn.autocommit = True
    return conn