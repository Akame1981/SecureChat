import os
import sys


def get_resource_path(relative_path: str) -> str:
    """Return absolute path to resource using project root as base.

    This works for development and when bundled with PyInstaller.
    """
    # If packaged by PyInstaller, resources are under _MEIPASS
    if getattr(sys, "_MEIPASS", False):
        base_path = sys._MEIPASS
    else:
        # utils/.. -> project root
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    return os.path.abspath(os.path.join(base_path, relative_path))
