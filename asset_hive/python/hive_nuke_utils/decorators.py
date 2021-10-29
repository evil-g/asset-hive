# Third party
import nuke


def undo(func):
    """
    Nuke Undo decorator

    Args:
        func (function): Function to execute with Undo block
    """
    def wrapper(*args):
        with nuke.Undo():
            try:
                func(*args)
            except Exception:
                import traceback
                traceback.print_exc()

        return

    return wrapper
