import uvicorn
from config.index import PORT, IP

if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host=IP,
        port=PORT,
        reload=True
    )