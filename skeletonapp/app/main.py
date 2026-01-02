from fastapi import FastAPI

from app.core.config import SettingsDep

app = FastAPI()


@app.get("/")
async def root(settings: SettingsDep):
    return {"message": f"App is running in {settings.environment} mode"}
