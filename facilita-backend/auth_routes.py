from fastapi import APIRouter

auth_router = APIRouter(prefix='/auth', tags=["auth_routes"])

@auth_router.get('/login')
def login():
    return {'Você acessou a rota de login'}