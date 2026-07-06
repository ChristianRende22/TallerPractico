import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.models.user import User

import app.models  # noqa: F401  (registra modelos en Base.metadata)
from app.database import Base, get_db
from app.main import create_app


@pytest.fixture
def db_engine():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _fk(dbapi_connection, _record):
        dbapi_connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session(db_engine):
    TestingSessionLocal = sessionmaker(bind=db_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        
@pytest.fixture(autouse=True)
def seed_users(db_session):
    """
    Seed requerido por Spec 0.
    Todos los tests tendrán disponibles:
        - Ana (id=1)
        - Luis (id=2)
    """

    if db_session.get(User, 1) is None:
        db_session.add(
            User(
                id=1,
                name="Ana",
                email="ana@example.com",
            )
        )

    if db_session.get(User, 2) is None:
        db_session.add(
            User(
                id=2,
                name="Luis",
                email="luis@example.com",
            )
        )

    db_session.commit()

@pytest.fixture
def client(db_engine):
    TestingSessionLocal = sessionmaker(bind=db_engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)
