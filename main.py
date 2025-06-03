from fastapi import FastAPI

from app.routes.routes import include_routers

app = FastAPI()

include_routers(app)
