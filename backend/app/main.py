# Temporary entrypoint; replaced by the full app factory in Task 4.
from fastapi import FastAPI

app = FastAPI(title="AI Analytics Dashboard")


@app.get("/api/health")
async def health() -> dict:
    return {"status": "ok"}
