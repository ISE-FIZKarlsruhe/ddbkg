from fastapi import FastAPI

api_gnd_werk = FastAPI()


@api_gnd_werk.get("/")
async def root():
    return {"message": "Hello World"}