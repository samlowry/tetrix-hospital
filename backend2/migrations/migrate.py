import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from core.config import get_settings

settings = get_settings()

def get_db_connection():
    print(f"Connecting to database: {settings.POSTGRES_DB} at {settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}")
    conn = psycopg2.connect(
        dbname=settings.POSTGRES_DB,
        user=settings.POSTGRES_USER,
        password=settings.POSTGRES_PASSWORD,
        host=settings.POSTGRES_HOST,
        port=settings.POSTGRES_PORT
    )
    print("Connected successfully")
    return conn

def ensure_migrations_table(conn):
    """Создаем таблицу для отслеживания миграций если её нет"""
    print("Checking migrations table...")
    with conn.cursor() as cur:
        # Проверяем существование таблицы
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'migrations'
            );
        """)
        table_exists = cur.fetchone()[0]
        print(f"Migrations table exists: {table_exists}")
        
        if not table_exists:
            print("Creating migrations table...")
            cur.execute("""
                CREATE TABLE migrations (
                    id serial PRIMARY KEY,
                    name varchar(255) NOT NULL UNIQUE,
                    applied_at timestamp DEFAULT CURRENT_TIMESTAMP
                );
            """)
            conn.commit()
            print("Migrations table created")

def get_applied_migrations(conn):
    """Получаем список примененных миграций"""
    print("Getting list of applied migrations...")
    with conn.cursor() as cur:
        cur.execute("SELECT name FROM migrations")
        applied = {row[0] for row in cur.fetchall()}
        print(f"Found {len(applied)} applied migrations: {applied}")
        return applied

def apply_migration(conn, file_path, file_name):
    """Применяем одну миграцию"""
    print(f"\nApplying migration: {file_name}")
    print(f"Reading file: {file_path}")
    
    with open(file_path, 'r') as f:
        full_sql = f.read()
    
    # Разделяем UP и DOWN части
    parts = full_sql.split('-- DOWN')
    up_sql = parts[0].replace('-- UP', '').strip()
    
    print(f"Executing UP SQL:\n{up_sql}\n")
    try:
        with conn.cursor() as cur:
            print("Executing migration SQL...")
            cur.execute(up_sql)
            print("Recording migration in migrations table...")
            cur.execute("INSERT INTO migrations (name) VALUES (%s)", (file_name,))
        conn.commit()
        print(f"Migration {file_name} applied successfully")
    except Exception as e:
        conn.rollback()
        print(f"Error applying migration {file_name}:")
        print(str(e))
        raise

def run_migrations():
    """Запускаем все неприменённые миграции"""
    print("\nStarting migrations...")
    conn = get_db_connection()
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    
    try:
        ensure_migrations_table(conn)
        applied = get_applied_migrations(conn)
        
        # Получаем список SQL файлов
        migrations_dir = os.path.join(os.path.dirname(__file__), 'sql')
        print(f"\nScanning migrations directory: {migrations_dir}")
        files = sorted([f for f in os.listdir(migrations_dir) if f.endswith('.sql')])
        print(f"Found migration files: {files}")
        
        for file_name in files:
            if file_name not in applied:
                file_path = os.path.join(migrations_dir, file_name)
                apply_migration(conn, file_path, file_name)
            else:
                print(f"Skipping already applied migration: {file_name}")
    
    finally:
        print("\nClosing database connection")
        conn.close()

if __name__ == '__main__':
    run_migrations() 