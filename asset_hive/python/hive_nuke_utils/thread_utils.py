# Standard
import subprocess
import threading

# Third party
import nuke
from Qt import QtWidgets


class NuketThread(threading.Thread):
    """
    Execute a nuke -t command in its own thread
    """
    def __init__(self, cmd, progress_bar=None):
        super(NuketThread, self).__init__()

        # Command to run
        self._cmd = r"{0}".format(cmd)

        # Initialize
        self._proc = subprocess.Popen(self._cmd, shell=True)
        self._out = ""
        self._err = ""

        # Widget
        self.widget = progress_bar

    @property
    def proc(self):
        """Return thread process"""
        return self._proc

    def run(self):
        """
        Execute command
        """
        try:
            self._out, self._err = self.proc.communicate()
        except Exception:
            import traceback
            traceback.print_exc()
            raise

    def results(self):
        return self._out, self._err


def watch_thread(nuket_thread, widget, alert=True):
    """
    When the Nuke -t thread is finished, close
    the specified widget and return the results

    Args:
        nuket_thread (threading.Thread)
    """
    # Poll until the command is finished
    while nuket_thread.proc.poll() is None:
        continue

    # Close parent widget
    try:
        widget.close()
    # Widget already deleted
    except RuntimeError:
        pass

    # Show popup in main thread
    if alert:
        parent = widget.parent()
        out, err = nuket_thread.results()
        nuke.executeInMainThread(show_msg, args=(out, err, parent))


def show_msg(out, err, parent=None):
    """
    Show message popup

    Args:
        out (str): Stdout from command
        err (str): Stderr from command
        parent (QtWidgets.QWidget): Parent widget for message box

    Returns: None
    """
    if err:
        QtWidgets.QMessageBox().critical(
            parent, "Error", "An error occurred: {0}".format(err))
    else:
        QtWidgets.QMessageBox().information(
            parent, "Success!", "Complete!")
