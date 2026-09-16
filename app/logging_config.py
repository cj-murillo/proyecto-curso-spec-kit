import logging
import sys

FORMATO = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"


def configurar_logging(nivel: str = "INFO") -> None:
    logging.basicConfig(
        level=getattr(logging, nivel.upper(), logging.INFO),
        format=FORMATO,
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stdout,
    )
