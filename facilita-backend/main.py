from fastapi import FastAPI
from auth_routes import auth_router

app = FastAPI()

@app.get('/')
async def read_root():
    return {"Facilita ENEM"}
app.include_router(auth_router)