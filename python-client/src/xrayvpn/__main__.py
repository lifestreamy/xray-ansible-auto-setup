"""Enable `python -m xrayvpn` without a prior install."""

from xrayvpn.cli.main import app

if __name__ == "__main__":
    app()