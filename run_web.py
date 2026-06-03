#!/usr/bin/env python3
from __future__ import annotations

import uvicorn


def main() -> None:
    uvicorn.run("scsp.web_api:app", host="0.0.0.0", port=8000, reload=False)


if __name__ == "__main__":
    main()
