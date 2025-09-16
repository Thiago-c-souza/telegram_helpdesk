from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "sqlite:///./telegram.db"
ENGINE = create_engine(DATABASE_URL, connect_args={"check_same_thread":False})

@event.listens_for(ENGINE, "connect")
def _set_sqlite_progma(dbapi_conn, connection_record):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_key=ON")
    cursor.close()

SessionLocal = sessionmaker(bind=ENGINE, autoflush=False, autocommit=False)