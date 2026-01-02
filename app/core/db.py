import psycopg2
from psycopg2.pool import ThreadedConnectionPool
from contextlib import contextmanager
from app.core.config import settings
from psycopg2.extras import RealDictCursor


# 1. 커넥션 풀 생성 (멀티스레드 안전)
pool = ThreadedConnectionPool(
    minconn=1,
    maxconn=10,
    host=settings.DB_HOST,
    port=settings.DB_PORT,
    database=settings.DB_NAME,
    user=settings.DB_USER,
    password=settings.DB_PASSWORD,
)

# 2. Context Manager 하나만 있으면 됩니다.
@contextmanager
def get_db_connection():
    """
    Service Layer에서 with 문과 함께 사용
    """
    conn = pool.getconn()
    conn.autocommit = False

    conn.cursor_factory = RealDictCursor

    try:
        yield conn      # 여기서 Service 로직이 실행됨
        conn.commit()   # 문제 없으면 커밋
    except Exception:
        conn.rollback() # 에러 나면 롤백
        raise           # 에러를 다시 던져서 상위에서 알 수 있게 함
    finally:
        pool.putconn(conn) # 성공하든 실패하든 커넥션은 무조건 반납