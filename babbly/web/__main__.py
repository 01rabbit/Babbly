import argparse

from babbly.web.server import serve


def main() -> None:
    parser = argparse.ArgumentParser(description="Babbly compact Situation surface (Web/EUD prototype)")
    parser.add_argument("--host", default="127.0.0.1", help="bind address (default: loopback)")
    parser.add_argument("--port", type=int, default=8787, help="port (default: 8787)")
    args = parser.parse_args()
    serve(host=args.host, port=args.port)


if __name__ == "__main__":
    main()
