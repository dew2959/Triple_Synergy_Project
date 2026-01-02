import psycopg2
from psycopg2.pool import ThreadedConnectionPool
from psycopg2.extras import RealDictCursor
from app.core.config import settings

pool = ThreadedConnectionPool(
    minconn=1,
    maxconn=10,
    host=settings.DB_HOST,
    port=settings.DB_PORT,
    database=settings.DB_NAME,
    user=settings.DB_USER,
    password=settings.DB_PASSWORD,
)

def get_connection():
    conn = pool.getconn()
    conn.autocommit = False
    return conn

def release_connection(conn):
    pool.putconn(conn)

# ⭐ 핵심: 안전한 트랜잭션 헬퍼
def with_connection(fn):
    """
    Repository 함수에서 사용
    """
    def wrapper(*args, **kwargs):
        conn = get_connection()
        try:
            result = fn(conn, *args, **kwargs)
            conn.commit()
            return result
        except Exception:
            conn.rollback()
            raise
        finally:
            release_connection(conn)
    return wrapper
