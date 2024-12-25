import os
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from core.config import get_settings

settings = get_settings()

def get_db_connection():
    return psycopg2.connect(
        dbname=settings.POSTGRES_DB,
        user=settings.POSTGRES_USER,
        password=settings.POSTGRES_PASSWORD,
        host=settings.POSTGRES_HOST,
        port=settings.POSTGRES_PORT
    )

def ensure_migrations_table(conn):
    """Создаем таблицу для отслеживания миграций если её нет"""
    with conn.cursor() as cur:
        # Проверяем существование таблицы
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'migrations'
            );
        """)
        table_exists = cur.fetchone()[0]
        
        if not table_exists:
            cur.execute("""
                CREATE TABLE migrations (
                    id serial PRIMARY KEY,
                    name varchar(255) NOT NULL UNIQUE,
                    applied_at timestamp DEFAULT CURRENT_TIMESTAMP
                );
            """)
            conn.commit()

def get_applied_migrations(conn):
    """Получаем список примененных миграций"""
    with conn.cursor() as cur:
        cur.execute("SELECT name FROM migrations")
        return {row[0] for row in cur.fetchall()}

def apply_migration(conn, file_path, file_name):
    """Применяем одну миграцию"""
    print(f"Applying migration: {file_name}")
    
    with open(file_path, 'r') as f:
        sql = f.read()
    
    with conn.cursor() as cur:
        cur.execute(sql)
        cur.execute("INSERT INTO migrations (name) VALUES (%s)", (file_name,))
    
    conn.commit()
    print(f"Migration {file_name} applied successfully")

def run_migrations():
    """Запускаем все неприменённые миграции"""
    conn = get_db_connection()
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    
    try:
        ensure_migrations_table(conn)
        applied = get_applied_migrations(conn)
        
        # Получаем список SQL файлов
        migrations_dir = os.path.join(os.path.dirname(__file__), 'sql')
        files = sorted([f for f in os.listdir(migrations_dir) if f.endswith('.sql')])
        
        for file_name in files:
            if file_name not in applied:
                file_path = os.path.join(migrations_dir, file_name)
                apply_migration(conn, file_path, file_name)
    
    finally:
        conn.close()

if __name__ == '__main__':
    run_migrations() 