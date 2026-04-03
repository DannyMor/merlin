from __future__ import annotations

import uvicorn
from fastapi import FastAPI

app = FastAPI(title="Merlin API", version="0.1.0")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


def main() -> None:
    uvicorn.run(
        "merlin.services.api:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
    )


if __name__ == "__main__":
    main()
