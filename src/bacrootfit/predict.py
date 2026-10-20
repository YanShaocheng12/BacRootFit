"""Unchanged numerical prediction recipe, exposed through the package interface."""
def main(argv=None):
    from .portable_reference import main as portable
    portable(argv)
