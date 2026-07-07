from .version import NAME


def log(surface, message):
    surface.log_message(f"[{NAME}] {message}")