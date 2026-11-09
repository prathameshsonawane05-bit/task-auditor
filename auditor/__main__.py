"""Allow `python -m auditor`."""

from auditor.cli import app


def main() -> None:
    app()


if __name__ == "__main__":
    main()
