from fastapi import FastAPI

app = FastAPI(title="Haikyu!! Clone API")

@app.get("/")
async def root():
    return {"message": "Welcome to Haikyu!! Clone Backend (Haidori Clone)"}
