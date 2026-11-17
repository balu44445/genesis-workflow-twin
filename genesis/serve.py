"""Production entry point for the bounded public demo."""
import os

import uvicorn


def main():
    os.environ.setdefault("GENESIS_PUBLIC_MODE", "true")
    if os.environ.get("RENDER_EXTERNAL_HOSTNAME"):
        os.environ.setdefault("GENESIS_PUBLIC_HOST", os.environ["RENDER_EXTERNAL_HOSTNAME"])
    uvicorn.run(
        "genesis.public:public_app",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", "10000")),
        workers=1,
        proxy_headers=True,
        forwarded_allow_ips=os.environ.get("GENESIS_FORWARDED_ALLOW_IPS", "127.0.0.1"),
    )


if __name__ == "__main__":
    main()
