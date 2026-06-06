"""Renderer helpers for OKoffice creation and composition flows."""


def is_typst_available() -> bool:
    try:
        import typst
        return True
    except ImportError:
        return False

