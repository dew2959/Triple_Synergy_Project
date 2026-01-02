import psycopg2
from psycopg2.pool import SimpleConnectionPool
from psycopg2.extras import RealDictCursor
from app.core.config import settings

pool = SimpleConnectionPool(
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
