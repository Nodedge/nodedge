from collections import OrderedDict

from PyQt5.QtWidgets import *
from PyQt5 import QtGui

from nodeledge.ack_serializable import AckSerializable


class AckNodeWidget(QWidget, AckSerializable):
    def __init__(self, node, parent=None):
        super().__init__(parent)
        self.node = node

        self.initUI()

    def initUI(self):
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.layout)

        self.layout.addWidget(AckTextEdit("X3"))

    def setEditingFlag(self, value):
        self.node.scene.graphicsScene.views()[0].editingFlag = value

    def serialize(self):
        return OrderedDict([

        ])

    def deserialize(self, data, hashmap={}):
        return False


class AckTextEdit(QTextEdit):

    def focusInEvent(self, e: QtGui.QFocusEvent) -> None:
        super().parentWidget().setEditingFlag(True)
        super().focusInEvent(e)

    def focusOutEvent(self, e: QtGui.QFocusEvent) -> None:
        super().parentWidget().setEditingFlag(False)
        super().focusOutEvent(e)
