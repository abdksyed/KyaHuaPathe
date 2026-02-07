from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import JSONResponse

from src.telegram.bot import start_bot, stop_bot

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Start the Telegram bot
    await start_bot()
    yield
    # Shutdown: Stop the Telegram bot gracefully
    await stop_bot()


# app init
app = FastAPI(lifespan=lifespan)


@app.get("/monitor")
async def serverRunning():
    response = {"status": "running", "data": "Pathe is Up!"}
    return JSONResponse(content=response)


@app.get("/health")
async def healthCheck():
    response = {"status": "healthy", "data": "Pathe is Up!"}
    return JSONResponse(content=response)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=7347, reload=True)
