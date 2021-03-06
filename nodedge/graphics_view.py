# -*- coding: utf-8 -*-
"""
Graphics View module containing :class:`~nodedge.graphics_view.GraphicsView`
and :class:`~nodedge.graphics_view.DragMode` classes.
"""

import logging
from typing import Callable, List, Optional

from PySide2.QtCore import QEvent, QPointF, Qt, Signal
from PySide2.QtGui import QDragEnterEvent, QDropEvent, QKeyEvent, QMouseEvent, QPainter
from PySide2.QtWidgets import QGraphicsItem, QGraphicsView, QWidget

from nodedge.edge_dragging import EdgeDragging, EdgeDraggingMode
from nodedge.graphics_cut_line import CutLine
from nodedge.graphics_edge import GraphicsEdge
from nodedge.graphics_scene import GraphicsScene
from nodedge.graphics_socket import GraphicsSocket
from nodedge.node import Node
from nodedge.utils import dumpException

#: Distance when click on socket to enable `Drag Edge`
EDGE_START_DRAG_THRESHOLD = 40

DEBUG_MMB_SCENE_ITEMS = True


class GraphicsView(QGraphicsView):
    """:class:`~nodedge.graphics_view.GraphicsView` class."""

    #: Signal emitted when cursor position on the `Scene` has changed
    scenePosChanged = Signal(int, int)

    def __init__(self, graphicsScene: GraphicsScene, parent: Optional[QWidget] = None):
        """
        :param graphicsScene: reference to the
            :class:`~nodedge.graphics_scene.GraphicsScene`
        :type graphicsScene: :class:`~nodedge.graphics_scene.GraphicsScene`
        :param parent: parent widget
        :type parent: ``Optional[QWidget]``
        """
        super().__init__(graphicsScene, parent)

        self.__logger = logging.getLogger(__name__)
        self.__logger.setLevel(logging.INFO)

        self.graphicsScene: GraphicsScene = graphicsScene
        self.initUI()

        self.setScene(self.graphicsScene)

        self.zoomInFactor: float = 1.25
        self.zoomClamp: bool = True
        self.zoomStep: int = 1
        self.zoomRange: List[int] = [0, 10]
        self.zoom: float = 10

        self.lastSceneMousePos: QPointF = QPointF()

        self.lastLMBClickScenePos: Optional[QPointF] = None
        self.editingFlag: bool = False
        self.rubberBandDraggingRectangle: bool = False

        self.edgeDragging: EdgeDragging = EdgeDragging(self)
        self.cutLine: CutLine = CutLine(self)

        self._dragEnterListeners: List[Callable] = []
        self._dropListeners: List[Callable] = []

    def __str__(self):
        rep = "\n||||Scene:"
        rep += "\n||||Nodes:"
        for node in self.graphicsScene.scene.nodes:
            rep += f"\n||||{node}"

        rep += "\n||||Edges:"
        for edge in self.graphicsScene.scene.edges:
            rep += f"\n||||{edge}"
        rep += "\n||||"

        return rep

    def initUI(self):
        """
        Set up this :class:`~nodedge.graphics_view.GraphicsView`.
        """
        self.setRenderHint(
            QPainter.Antialiasing
            or QPainter.HighQualityAntialiasing
            or QPainter.TextAntialiasing
            or QPainter.SmoothPixmapTransform
        )
        self.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)

        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setDragMode(QGraphicsView.RubberBandDrag)

        self.setAcceptDrops(True)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        """
        Handle Qt's mouse's drag enter event.

        Call all the listeners of that event.

        :param event: Mouse drag enter event
        :type event: ``QDragEnterEvent.py``
        """
        for callback in self._dragEnterListeners:
            callback(event)

    def dropEvent(self, event: QDropEvent) -> None:
        """
        Handle Qt's mouse's drop event.

        Call all the listeners of that event.

        :param event: Mouse drop event
        :type event: ``QDropEvent.py``
        """
        for callback in self._dropListeners:
            callback(event)

    def addDragEnterListener(self, callback: Callable[[QDragEnterEvent], None]):
        """
        Register callback for `Drag Enter` event.

        :param callback: callback function
        """
        self._dragEnterListeners.append(callback)

    def addDropListener(self, callback: Callable[[QDropEvent], None]):
        """
        Register callback for `Drop` event.

        :param callback: callback function
        """
        self._dropListeners.append(callback)

    def mousePressEvent(self, event: QMouseEvent):
        """
        Dispatch Qt's `mousePressEvent` to corresponding function below.
        """
        if event.button() == Qt.MiddleButton:
            self.middleMouseButtonPress(event)
        elif event.button() == Qt.LeftButton:
            try:
                self.leftMouseButtonPress(event)
            except Exception as e:
                dumpException(e)
        elif event.button() == Qt.RightButton:
            self.rightMouseButtonPress(event)
        else:
            super().mousePressEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        """
        Dispatch Qt's mouseReleaseEvent to corresponding function below.
        """
        if event.button() == Qt.MiddleButton:
            self.middleMouseButtonRelease(event)
        if event.button() == Qt.LeftButton:
            self.leftMouseButtonRelease(event)
        if event.button() == Qt.RightButton:
            self.rightMouseButtonRelease(event)
        else:
            super().mouseReleaseEvent(event)

    def leftMouseButtonPress(self, event: QMouseEvent):
        """
        Handle when the left mouse button is pressed.
        """
        try:
            item: Optional[QGraphicsItem] = self.getItemAtClick(event)
            self.__logger.debug(f"Selected object class: {item.__class__.__name__}")

            self.lastLMBClickScenePos = self.mapToScene(event.pos())

            self.__logger.debug("LMB " + GraphicsView.debugModifiers(event) + f"{item}")

            if event.modifiers() & Qt.ShiftModifier:
                event.ignore()
                fakeEvent: QMouseEvent = QMouseEvent(
                    QEvent.MouseButtonPress,
                    event.localPos(),
                    event.screenPos(),
                    Qt.LeftButton,
                    event.buttons() | Qt.LeftButton,
                    event.modifiers() | Qt.ControlModifier,
                )
                super().mousePressEvent(fakeEvent)
                return

            self.edgeDragging.update(item)
            modifiedEvent = self.cutLine.update(event)

            if modifiedEvent is not None:
                super().mouseReleaseEvent(modifiedEvent)
            else:
                super().mousePressEvent(event)

            if item is None:
                self.rubberBandDraggingRectangle = True

        except Exception as e:
            dumpException(e)

    def leftMouseButtonRelease(self, event: QMouseEvent):
        """
        Handle when left mouse button is released.
        """
        item = self.getItemAtClick(event)

        try:
            if event.modifiers() & Qt.ShiftModifier:
                event.ignore()
                fakeEvent = QMouseEvent(
                    event.type(),
                    event.localPos(),
                    event.screenPos(),
                    Qt.LeftButton,
                    Qt.NoButton,
                    event.modifiers() | Qt.ControlModifier,
                )
                super().mouseReleaseEvent(fakeEvent)
                return

            if self.edgeDragging.mode == EdgeDraggingMode.EDGE_DRAG:
                if self.distanceBetweenClickAndReleaseIsOff(event):
                    if isinstance(item, GraphicsSocket):
                        graphicsSocket: GraphicsSocket = item
                        ret = self.edgeDragging.endEdgeDragging(graphicsSocket)
                        if ret:
                            return

            self.cutLine.update(event)

            if self.rubberBandDraggingRectangle:
                self.rubberBandDraggingRectangle = False
                selectedItems = self.graphicsScene.selectedItems()
                if selectedItems != self.graphicsScene.scene.lastSelectedItems:
                    if not selectedItems:
                        self.graphicsScene.itemsDeselected.emit()  # type: ignore
                    else:
                        self.graphicsScene.itemSelected.emit()  # type: ignore
                return
        except Exception as e:
            dumpException(e)

        super().mouseReleaseEvent(event)

    def middleMouseButtonPress(self, event: QMouseEvent):
        """
        Handle when middle mouse button is pressed.
        """
        # Debug logging
        item = self.getItemAtClick(event)

        if DEBUG_MMB_SCENE_ITEMS:
            if item is None:
                if event.modifiers() & Qt.SHIFT:
                    lastSelectedItems = self.graphicsScene.scene.lastSelectedItems
                    self.__logger.info(
                        f"\n||||Last selected items: {lastSelectedItems}",
                    )
                    return
                self.__logger.info(self)
                return
            elif isinstance(item, GraphicsSocket):
                self.__logger.info(
                    f"\n||||{item.socket} connected to \n||||{item.socket.edges}"
                )
                return
            elif isinstance(item, GraphicsEdge):
                log = f"\n||||{item.edge} connects"
                log += (
                    f"\n||||{item.edge.sourceSocket.node} \n||||"
                    f"{item.edge.targetSocket.node}"
                )
                self.__logger.info(log)
                return

        # Faking event to enable mouse dragging the scene
        release_event = QMouseEvent(
            QEvent.MouseButtonRelease,
            event.localPos(),
            event.screenPos(),
            Qt.LeftButton,
            Qt.NoButton,
            event.modifiers(),
        )
        super().mouseReleaseEvent(release_event)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        fake_event = QMouseEvent(
            event.type(),
            event.localPos(),
            event.screenPos(),
            Qt.LeftButton,
            event.buttons() | Qt.LeftButton,
            event.modifiers(),
        )
        super().mousePressEvent(fake_event)

    def middleMouseButtonRelease(self, event: QMouseEvent):
        """
        Handle when middle mouse button is released.
        """
        fake_event = QMouseEvent(
            event.type(),
            event.localPos(),
            event.screenPos(),
            Qt.LeftButton,
            event.buttons() | Qt.LeftButton,
            event.modifiers(),
        )
        super().mouseReleaseEvent(fake_event)
        self.setDragMode(QGraphicsView.RubberBandDrag)

    def rightMouseButtonPress(self, event: QMouseEvent):
        """
        Handle when right mouse button was pressed
        """
        super().mousePressEvent(event)

    def rightMouseButtonRelease(self, event: QMouseEvent):
        """
        Handle when right mouse button is released.
        """
        super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """
        Overridden Qt's ``mouseMoveEvent`` handling Scene/View logic

        :param event: Qt's mouse event
        :type event: ``QMouseEvent.py``
        """
        eventScenePos = self.mapToScene(event.pos())

        if self.edgeDragging.mode == EdgeDraggingMode.EDGE_DRAG:
            if (
                self.edgeDragging.dragEdge is not None
                and self.edgeDragging.dragEdge.graphicsEdge is not None
            ):
                self.edgeDragging.dragEdge.graphicsEdge.targetPos = eventScenePos
                self.edgeDragging.dragEdge.graphicsEdge.update()
            else:
                self.__logger.debug("Dragging edge does not exist.")

        self.cutLine.update(event)

        self.lastSceneMousePos = eventScenePos
        # noinspection PyUnresolvedReferences
        self.scenePosChanged.emit(  # type: ignore
            int(eventScenePos.x()), int(eventScenePos.y())
        )

        super().mouseMoveEvent(event)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """
        Handle key shortcuts, for example to display the scene's history in the console.

        :param event: Qt's Key event
        :type event: ``QKeyEvent.py``
        """

        # if event.key() == Qt.Key_Delete: if not self.editingFlag:
        # self.deleteSelected() else: super().keyPressEvent(event) elif event.key()
        # == Qt.Key_S and event.modifiers() & Qt.ControlModifier:
        # self.graphicsScene.scene.saveToFile("graph.json") elif event.key() ==
        # Qt.Key_O and event.modifiers() & Qt.ControlModifier:
        # self.graphicsScene.scene.loadFromFile("graph.json") elif event.key() ==
        # Qt.Key_1: self.graphicsScene.scene.history.store("A") elif event.key() ==
        # Qt.Key_2: self.graphicsScene.scene.history.store("B") elif event.key() ==
        # Qt.Key_3: self.graphicsScene.scene.history.store("C") elif event.key() ==
        # Qt.Key_Z and event.modifiers() & Qt.ControlModifier \ and not
        # event.modifiers() & Qt.ShiftModifier:
        # self.graphicsScene.scene.history.undo() elif event.key() == Qt.Key_Z and
        # event.modifiers() & Qt.ControlModifier and event.modifiers() &
        # Qt.ShiftModifier: self.graphicsScene.scene.history.redo()
        if event.key() == Qt.Key_H:
            self.__logger.info(f"{self.graphicsScene.scene.history}")

        else:
            super().keyPressEvent(event)

    def wheelEvent(self, event):
        """
        Overridden Qt's ``wheelEvent``.
        This handles zooming.
        """
        zoomIn = event.angleDelta().y() > 0
        self.updateZoom(zoomIn)
        self.__logger.debug(
            f"Scale: {self.matrix().m11()}, "
            f"Zoom factor: {self.zoomInFactor}, "
            f"Zoom level: {self.zoom}"
        )

    def updateZoom(self, zoomIn: bool = True):
        # Compute zoom factor
        zoomOutFactor = 1.0 / self.zoomInFactor
        # Compute zoom
        if zoomIn:
            zoomFactor = self.zoomInFactor
            self.zoom += self.zoomStep
        else:
            zoomFactor = zoomOutFactor
            self.zoom -= self.zoomStep
        clamped = False
        if self.zoom < self.zoomRange[0]:
            self.zoom = self.zoomRange[0]
            clamped = True
        elif self.zoom > self.zoomRange[1]:
            self.zoom = self.zoomRange[1]
            clamped = True
        # Set scene scale
        if not clamped or self.zoomClamp is False:
            self.scale(zoomFactor, zoomFactor)

    def deleteSelected(self):
        """
        Shortcut for safe deleting every object selected in the
        :class:`~nodedge.scene.Scene`.
        """
        for item in self.graphicsScene.selectedItems():
            if isinstance(item, GraphicsEdge):
                item.edge.remove()
            elif hasattr(item, "node"):
                node: Node = item.node
                node.remove()

        self.graphicsScene.scene.history.store("Delete selected objects.")

    def getItemAtClick(self, event: QMouseEvent):
        """
        Return the object on which the user clicked/released the mouse button.

        :param event: Qt's mouse or key event
        :type event: ``QMouseEvent.py``
        :return: Graphical item present at the clicked/released position.
        :rtype: ``QGraphicsItem`` | ``None``
        """
        pos = event.pos()
        return self.itemAt(pos)

    def distanceBetweenClickAndReleaseIsOff(self, event: QMouseEvent) -> bool:
        """
        Measure if we are too far from the last mouse button click scene position.
        This is used for detection if the release is too far after the user clicked
        on a :class:`~nodedge.socket.Socket`

        :param event: Qt's mouse event
        :type event: ``QMouseEvent.py``
        :return: ``True`` if we released too far from where we clicked before, ``False``
            otherwise.
        :rtype: ``bool``
        """
        if self.lastLMBClickScenePos is None:
            return False
        newLMBClickPos: QPointF = self.mapToScene(event.pos())
        distScene = newLMBClickPos - self.lastLMBClickScenePos
        edgeStartDragThresholdSquared = EDGE_START_DRAG_THRESHOLD ** 2
        distSceneSquared = distScene.x() * distScene.x() + distScene.y() * distScene.y()
        if distSceneSquared < edgeStartDragThresholdSquared:
            self.__logger.debug(
                f"Squared distance between new and last LMB click: "
                f"{distSceneSquared} < {edgeStartDragThresholdSquared}"
            )
            return False
        else:
            return True

    @staticmethod
    def debugModifiers(event: QMouseEvent) -> str:
        """
        Get the name of the pressed modifier.

        :return: "CTRL" / "SHIFT" / "ALT"
        :rtype: ``str``
        """
        dlog = ""
        if event.modifiers() & Qt.ShiftModifier:
            dlog += "SHIFT "
        if event.modifiers() & Qt.ControlModifier:
            dlog += "CTRL "
        if event.modifiers() & Qt.AltModifier:
            dlog += "ALT "
        return dlog
