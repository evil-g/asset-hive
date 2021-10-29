# -*- coding: utf-8 -*-
# Standard
import os

# Third party
from Qt import QtCore, QtGui, QtWidgets


class AutoCleanLineEdit(QtWidgets.QLineEdit):
    """
    Line edit that will clean input text
    Replace spaces with underscores in input text
    """
    def __init__(self, parent=None):
        """
        Initialize QLineEdit
        """
        super(AutoCleanLineEdit, self).__init__(parent=parent)

        # Clean callback
        self.textChanged.connect(self.clean_text)

    def clean_text(self, text):
        """
        Replace ' ' with '_' in input text
        """
        cursor_pos = self.cursorPosition()
        self.setText(text.replace(" ", "_"))
        self.setCursorPosition(cursor_pos)


class AutoCloseLineEdit(AutoCleanLineEdit):
    """
    Line edit that closes automatically if:
    1. ESC is pressed
    2. The widget loses focus, and none of its child widgets are visible

    Used by EditableModel when adding new list items.
    """
    closing_text = QtCore.Signal(object)
    cancelled = QtCore.Signal()
    closed = QtCore.Signal()

    def __init__(self, parent=None, force_close=False, remain_open=False):
        super(AutoCloseLineEdit, self).__init__(parent=parent)
        self.force_close = force_close
        self.remain_open = remain_open

        # Track double backspace
        self.double_backspace = False

    def keyReleaseEvent(self, event):
        """
        Key release override
        """
        # Close on ESC press
        if QtCore.Qt.Key_Escape == event.key():
            self.cancel()
            return True
        # Close on backspace when edit is empty
        elif event.key() in [QtCore.Qt.Key_Backspace]:
            # Double back press
            if self.double_backspace:
                self.cancel()
                return True
            # Next backspace
            elif not self.text():
                self.double_backspace = True
        # Return press, emit text at close
        elif QtCore.Qt.Key_Return == event.key():
            if self.text():
                if self.remain_open:
                    self.closing_text.emit(self.text())
                else:
                    self.close(closing_text=True)
            else:
                self.cancel()
            return True

        return QtWidgets.QLineEdit.keyReleaseEvent(self, event)

    def focusOutEvent(self, event):
        """
        Focus out override
        """
        # Close on focus out
        if not self.remain_open:
            # Check visibility of all children
            if not self.force_close:
                for child in self.children():
                    # print(child)
                    if isinstance(child, QtWidgets.QWidget) and \
                            not child.isHidden():
                        return QtWidgets.QLineEdit.focusOutEvent(self, event)
            # No child was visible
            self.cancel()
            return True

        return QtWidgets.QLineEdit.focusOutEvent(self, event)

    def cancel(self):
        """
        Cancel
        """
        self.cancelled.emit()
        self.close()

    def close(self, closing_text=False):
        """
        Close
        """
        if closing_text:
            self.closing_text.emit(self.text())

        self.double_backspace = False
        self.closed.emit()
        super(AutoCloseLineEdit, self).close()


class PlusTabBar(QtWidgets.QTabBar):

    def __init__(self, parent=None):
        """
        Tab bar widget with a '+' button after the last tab
        """
        super(PlusTabBar, self).__init__(parent=parent)

        # Add 'x' to remove tab
        self.setTabsClosable(True)

        # Add tab button
        self.plus_btn = QtWidgets.QPushButton("+", parent=self)
        self.plus_btn.setFixedSize(30, 30)
        self.repositionPlusButton()

    def sizeHint(self):
        """
        Size hint - add plus button width
        """
        size = QtWidgets.QTabBar.sizeHint(self)
        return QtCore.QSize(size.width() + 30, size.height())

    def resizeEvent(self, event):
        """
        Reposition button after resize event
        """
        QtWidgets.QTabBar.resizeEvent(self, event)
        self.repositionPlusButton()

    def tabLayoutChange(self):
        """
        Reposition button after tab layout change
        """
        QtWidgets.QTabBar.tabLayoutChange(self)
        self.repositionPlusButton()

    def repositionPlusButton(self):
        """
        Reposition plus button
        """
        size = sum([self.tabRect(i).width() for i in range(self.count())])
        height = self.geometry().top()
        width = self.width()

        if size > width:
            self.plus_btn.move(width - 60, height)
        else:
            self.plus_btn.move(size, height)


class FlashStatusBar(QtWidgets.QStatusBar):
    """
    Status line edit that will flash animated text
    """
    def __init__(self, parent=None):
        """
        Initialize line edit and add animations
        """
        super(FlashStatusBar, self).__init__(parent=parent)

        # No focus policy
        self.setFocusPolicy(QtCore.Qt.NoFocus)

        # Flash animation
        self.flash_effect = QtWidgets.QGraphicsOpacityEffect(self)
        self.flash_effect.setOpacity(0)

        self.setGraphicsEffect(self.flash_effect)

        self.flash_anim = QtCore.QSequentialAnimationGroup()

        # On anim
        on = QtCore.QPropertyAnimation(self.flash_effect, "opacity")
        on.setDuration(100)
        on.setStartValue(0)
        on.setEndValue(1)

        # Off anim
        off = QtCore.QPropertyAnimation(self.flash_effect, "opacity")
        off.setDuration(2000)
        off.setStartValue(1)
        off.setEndValue(0)

        # Add group
        self.flash_anim.addAnimation(on)
        self.flash_anim.addPause(12000)
        self.flash_anim.addAnimation(off)

        # Reset nav on finish
        self.flash_anim.finished.connect(self.reset)

    def showMessage(self, text, timeout=14100):
        """
        Set text and start animation
        """
        self.flash_anim.stop()
        super(FlashStatusBar, self).showMessage(text, timeout=timeout)
        self.flash_anim.start()

    def reset(self):
        """
        Reset text + opacity
        """
        self.clearMessage()
        self.flash_effect.setOpacity(0)


def get_feather_icon(name, color=None):
    """
    Get feather icon

    Args:
        name (str): Feature icon name
        color (tuple): QtGui.QColor input
    """
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
        __file__))), "vendor", "feathericons", "{0}.svg".format(name))

    if not os.path.isfile(path):
        raise ValueError("No icon found: {0}".format(path))

    px = QtGui.QPixmap(path)
    color_px = QtGui.QPixmap(px.size())
    if isinstance(color, QtGui.QColor):
        color_px.fill(color)
    else:
        color_px.fill(QtGui.QColor(*color))
    color_px.setMask(px.createMaskFromColor(QtCore.Qt.transparent))
    icon = QtGui.QIcon(color_px)

    return icon


def get_feather_button(name, color=None, wh=30):
    """
    Set up feather icon button
    """
    icon = get_feather_icon(name, color)

    button = QtWidgets.QPushButton()
    button.setIcon(icon)
    button.setMaximumWidth(wh)
    button.setMaximumHeight(wh)

    # No focus
    button.setFocusPolicy(QtCore.Qt.NoFocus)

    return button
