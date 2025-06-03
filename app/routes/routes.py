from fastapi import FastAPI

from app.routes import auth, books, readers


def include_routers(app: FastAPI):
    app.include_router(auth.router)
    app.include_router(books.router)
    app.include_router(readers.router)

