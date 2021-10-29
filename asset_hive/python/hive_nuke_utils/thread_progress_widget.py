from __future__ import print_function
# Third party
from Qt import QtCore, QtWidgets


class ThreadProgressWidget(QtWidgets.QDialog):
    """
    Dialog to show an animated progress bar.
    Cancel button to kill a process.
    """
    def __init__(self, thread, parent=None, msg="Processing..."):
        super(ThreadProgressWidget, self).__init__(parent=parent)

        # Set up UI
        self.setWindowTitle("Run Command")
        self.setMinimumWidth(250)

        # Main layout
        self.main_layout = QtWidgets.QVBoxLayout()

        # Label
        self.label = QtWidgets.QLabel(msg)
        self.main_layout.addWidget(self.label)

        # Progress bar
        self.progress_bar = QtWidgets.QProgressBar()
        self.main_layout.addWidget(self.progress_bar)

        # Set layout
        self.setLayout(self.main_layout)

        # Set progress range
        self.min = 0
        self.max = 10
        self.progress_bar.setRange(self.min, self.min)

        # Cancel button
        self.cancel = QtWidgets.QPushButton("Cancel")
        self.cancel.setMaximumWidth(150)
        self.main_layout.addWidget(self.cancel, alignment=QtCore.Qt.AlignRight)

        # Connections
        self.cancel.clicked.connect(self.kill)

        # Process thread
        self.thread = thread

    def kill(self):
        """Terminate process"""
        try:
            self.thread.kill()
        except AttributeError as e:
            print("Failed to kill thread: '{0}'".format(e))

        self.close()
