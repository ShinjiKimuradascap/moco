from fastapi import FastAPI
from .database import engine, Base
from .api import router as api_router

# データベーステーブルの作成
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Haikyu!! Touch The Dream Clone API")

# APIルーターの登録
app.include_router(api_router, prefix="/api/v1")

@app.get("/")
def read_root():
    return {"message": "Welcome to Haikyu!! Clone API"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
