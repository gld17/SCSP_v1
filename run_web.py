#!/usr/bin/env python3
from __future__ import annotations

import argparse


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    import uvicorn

    uvicorn.run("scsp.web_api:app", host="0.0.0.0", port=args.port, reload=False)


if __name__ == "__main__":
    main()
