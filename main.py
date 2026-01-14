import uvicorn

from configs import get_settings

if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run(
        "app:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=False,
    )
