from pathlib import Path

import uvicorn
from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from backend.routes import router
from backend.service import PrescriptionNotFound
from backend.storage import StoreCorrupted

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"

app = FastAPI(title="Quando")
app.include_router(router)


@app.exception_handler(RequestValidationError)
def handle_request_validation_error(request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=400, content={"detail": jsonable_encoder(exc.errors())})


@app.exception_handler(PrescriptionNotFound)
def handle_prescription_not_found(request: Request, exc: PrescriptionNotFound):
    return JSONResponse(
        status_code=404, content={"detail": f"prescription {exc.args[0]} not found"}
    )


@app.exception_handler(StoreCorrupted)
def handle_store_corrupted(request: Request, exc: StoreCorrupted):
    return JSONResponse(status_code=500, content={"detail": str(exc)})


if FRONTEND_DIR.is_dir():
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
