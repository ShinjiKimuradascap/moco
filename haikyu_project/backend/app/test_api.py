from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .database import Base, get_db
from .main import app
import pytest

# テスト用DB設定 (メモリ内 SQLite)
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_api.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

def setup_module():
    Base.metadata.create_all(bind=engine)

def teardown_module():
    Base.metadata.drop_all(bind=engine)

def test_read_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to Haikyu!! Clone API"}

def test_create_user_and_get_status():
    # ユーザーを事前作成 (本来はCreateUser APIがあるべきだが、今は手動で入れるかAPIを想定)
    from .models import User
    db = TestingSessionLocal()
    user = User(name="Test User", free_wings=1000, gold=1000, stamina=100)
    db.add(user)
    db.commit()
    db.refresh(user)
    user_id = user.id
    db.close()

    response = client.get(f"/api/v1/user/status?user_id={user_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test User"
    assert data["free_wings"] == 1000

def test_gacha_draw():
    # User ID 1 (前テストで作成済み想定だが独立させる)
    from .models import User
    db = TestingSessionLocal()
    user = User(name="Gacha User", free_wings=3000, gold=0, stamina=100, mileage=0)
    db.add(user)
    db.commit()
    user_id = user.id
    db.close()

    response = client.post("/api/v1/gacha/draw", json={"user_id": user_id, "times": 10})
    assert response.status_code == 200
    data = response.json()
    assert len(data["results"]) == 10
    assert "new_mileage" in data

if __name__ == "__main__":
    # 手動実行用
    setup_module()
    try:
        test_read_root()
        print("Root test passed")
        test_create_user_and_get_status()
        print("User status test passed")
        test_gacha_draw()
        print("Gacha test passed")
    finally:
        teardown_module()
