from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

app = FastAPI(
    debug=True,
    title="Ai documentation Helper lightweight server",
    default_response_class=JSONResponse,
    version="0.0.1",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_headers=["*"],
    allow_methods=["*"],
    allow_credentials=True,
)


@app.on_event("startup")
async def lifespan():
    pass


@app.get(path="/", description="Healthcheck router", response_class=JSONResponse)
async def healthcheck() -> JSONResponse:
    try:
        JSONResponse(
            content={"msg": "The server is healthy", "healthy": True}, status_code=200
        )
    except Exception:
        JSONResponse(content={"msg": "Error occured"}, status_code=500)
