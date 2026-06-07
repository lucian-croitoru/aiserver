import uvicorn
from sdxl.models import init_models
from sdxl.app import app


if __name__ == "__main__":
    init_models()
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8113,
        log_level="info"
    )
