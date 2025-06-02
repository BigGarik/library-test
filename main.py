from fastapi import FastAPI

app = FastAPI()


@app.get("/")
def read_root():
    return {"message": "Library API is up and running!"}
