import logging

from nodedge.node import Node
from nodedge.blocks.block_content import BlockContent
from nodedge.blocks.graphics_block import GraphicsBlock
from nodedge.socket import LEFT_CENTER, RIGHT_CENTER


class Block(Node):
    iconPath = ""
    operationTitle = "Undefined"
    operationCode = 0
    contentLabel = ""
    contentLabelObjectName = "blockBackground"

    def __init__(self, scene, inputs=(2, 2), outputs=(1,)):
        super().__init__(scene, self.__class__.operationTitle, inputs, outputs)

        self.__logger = logging.getLogger(__file__)
        self.__logger.setLevel(logging.DEBUG)

    def initInnerClasses(self):
        self.content = BlockContent(self)
        self.graphicsNode = GraphicsBlock(self)

    def initSettings(self):
        super().initSettings()
        self._inputSocketPosition = LEFT_CENTER
        self._outputSocketPosition = RIGHT_CENTER

    def serialize(self):
        res = super().serialize()
        res["operationCode"] = self.__class__.operationCode
        return res

    def deserialize(self, data, hashmap={}, restoreId=True):
        # self.__logger.debug(f"Deserializing block {self.__class__.__name__}")
        res = super().deserialize(data, hashmap, restoreId)
        self.__logger.debug(f"Deserialized block {self.__class__.__name__}: {res}")

        return res
