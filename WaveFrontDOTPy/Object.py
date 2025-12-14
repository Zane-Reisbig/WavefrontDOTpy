from __future__ import annotations

from datetime import datetime
import enum
import os
import pathlib
from typing import Callable

######## START-Vars


class FACE_SHAPE_IDENTIFIER(enum.Enum):
    VERTEX_ONLY = 0
    VERTEX_AND_TEXTURE = 1
    VERTEX_AND_NORMAL = 2
    VERTEX_AND_TEXTURE_AND_NORMAL = 3


class TAG_IDENTIFIER(enum.Enum):
    OBJECT = 0
    VERTEX = 1
    VERTEX_NORMAL = 2
    VERTEX_TEXTURE = 3
    SMOOTH_SHADE = 4
    GROUP = 5
    MTL_LIB = 6
    USE_MTL_LIB = 7
    LINE_ELEMENT = 97
    POLYGONAL_FACE_ELEMENT = 98
    PARAMETER_SPACE_VERTEX = 99


TAG_IDENTIFIER_CHARACTERS = {
    "o": TAG_IDENTIFIER.OBJECT,
    "v": TAG_IDENTIFIER.VERTEX,
    "vn": TAG_IDENTIFIER.VERTEX_NORMAL,
    "vt": TAG_IDENTIFIER.VERTEX_TEXTURE,
    "vp": TAG_IDENTIFIER.PARAMETER_SPACE_VERTEX,
    "f": TAG_IDENTIFIER.POLYGONAL_FACE_ELEMENT,
    "l": TAG_IDENTIFIER.LINE_ELEMENT,
    "s": TAG_IDENTIFIER.SMOOTH_SHADE,
    "g": TAG_IDENTIFIER.GROUP,
    "mtllib": TAG_IDENTIFIER.MTL_LIB,
    "usemtl": TAG_IDENTIFIER.USE_MTL_LIB,
}

# for exportin'
TAG_IDENTIFIER_TO_STRING = {v: k for k, v in TAG_IDENTIFIER_CHARACTERS.items()}

######## END-Vars
######## START-Exceptions


class UnknownTagException(Exception):
    def __init__(self, offendingTag: str, *args):
        super().__init__(
            f'Failed to parse line "{offendingTag}"\nREASON: Unknown Tag', *args
        )


class ShapeException(Exception):
    def __init__(self, offendingTag: str, *args):
        super().__init__(
            f'Failed to parse line "{offendingTag}"\nREASON: Unknown Data Shape', *args
        )


######## END-Exceptions
######## START-Classes


class TokenConsumers:
    @staticmethod
    def consumeTagAndReturnLeftover(_input: str) -> str:
        tagCanidate = _input[: _input.find(" ")].strip()

        if TAG_IDENTIFIER_CHARACTERS.get(tagCanidate) is None:
            raise UnknownTagException(tagCanidate)

        return _input[len(tagCanidate) :].strip()

    @staticmethod
    def consumeAndReturnTag(_input: str) -> TAG_IDENTIFIER:
        tagCanidate = _input[: _input.find(" ")].strip()

        if (tagID := TAG_IDENTIFIER_CHARACTERS.get(tagCanidate)) is None:
            raise UnknownTagException(tagCanidate)

        return tagID

    @staticmethod
    def consumeToNextSpace(_input: str) -> str:
        nextSpace = _input.find(" ")
        return _input[:nextSpace]


class Parsers:

    @staticmethod
    def consumeTagAndReturnLeftoverAsType[T](
        line: str, typeFactory: Callable[[str], T], delimter: str = " "
    ) -> list[T]:
        line = TokenConsumers.consumeTagAndReturnLeftover(line)

        normalizedSpacing = " ".join(line.split())
        tokens = normalizedSpacing.split(delimter)
        vals = [typeFactory(i) for i in tokens]

        return vals

    @staticmethod
    def vertexOnlyParser(line: str):
        vals = Parsers.consumeTagAndReturnLeftoverAsType(line, float)
        return Vertex(*vals)

    @staticmethod
    def vertexTextureParser(line: str):
        vals = Parsers.consumeTagAndReturnLeftoverAsType(line, float)
        return VertexTexture(*vals)

    @staticmethod
    def vertexNormalParser(line: str):
        vals = Parsers.consumeTagAndReturnLeftoverAsType(line, float)
        return VertexNormal(*vals)

    __faceShapeParserMap = {
        FACE_SHAPE_IDENTIFIER.VERTEX_ONLY: vertexOnlyParser,
    }

    @staticmethod
    def faceShapeToParser[T](
        shape: FACE_SHAPE_IDENTIFIER,
    ) -> Callable[[str], T]:
        return Parsers.__faceShapeParserMap.get(shape)  # type: ignore

    @staticmethod
    def getFaceDataStyle(line: str):
        assert (
            TokenConsumers.consumeAndReturnTag(line)
            is TAG_IDENTIFIER.POLYGONAL_FACE_ELEMENT
        ), f'Line: "{line}" is not a face tag'

        if "//" in line:
            return FACE_SHAPE_IDENTIFIER.VERTEX_AND_NORMAL

        rawValues = TokenConsumers.consumeTagAndReturnLeftover(line)
        normalizedSpacing = " ".join(rawValues.split())
        nextVal = TokenConsumers.consumeToNextSpace(normalizedSpacing)

        if "/" in normalizedSpacing:
            trySplit = len(nextVal.split("/"))
            if trySplit == 2:
                return FACE_SHAPE_IDENTIFIER.VERTEX_AND_TEXTURE
            elif trySplit == 3:
                return FACE_SHAPE_IDENTIFIER.VERTEX_AND_TEXTURE_AND_NORMAL

        if nextVal is not None:
            canBeInt = None
            try:
                canBeInt = int(nextVal)
            except:
                pass

            if canBeInt is not None:
                return FACE_SHAPE_IDENTIFIER.VERTEX_ONLY

        raise ShapeException(line)

    class Faces:
        @staticmethod
        def vertexTextureNormalParser(line: str):
            line = TokenConsumers.consumeTagAndReturnLeftover(line)
            normalizedSpacing = " ".join(line.split())
            triplets = normalizedSpacing.split(" ")

            accum: list[VertexIndexer] = []
            for item in triplets:
                indicies = [int(index) for index in item.split("/")]

                if len(indicies) != 3:
                    raise ShapeException(
                        f'{item}\nExpected Shape: "{repr(FACE_SHAPE_IDENTIFIER.VERTEX_AND_TEXTURE_AND_NORMAL)}"'
                    )

                indexer = VertexIndexer(*indicies)
                indexer.outputShape = (
                    FACE_SHAPE_IDENTIFIER.VERTEX_AND_TEXTURE_AND_NORMAL
                )

                accum.append(indexer)

            return accum

        @staticmethod
        def vertexTextureParser(line: str):
            line = TokenConsumers.consumeTagAndReturnLeftover(line)
            normalizedSpacing = " ".join(line.split())
            pairs = normalizedSpacing.split(" ")

            indexers: list[VertexIndexer] = []
            for item in pairs:
                indices = [int(i) for i in item.split("/")]

                if len(indices) != 2:
                    raise ShapeException(
                        f'{item}\nExpected Shape: "{repr(FACE_SHAPE_IDENTIFIER.VERTEX_AND_TEXTURE)}"'
                    )

                indexer = VertexIndexer(*indices, vertexNormalIndex=0)
                indexer.outputShape = FACE_SHAPE_IDENTIFIER.VERTEX_AND_TEXTURE
                indexers.append(indexer)

            return indexers

        @staticmethod
        def vertexAndNormalParser(line: str):
            line = TokenConsumers.consumeTagAndReturnLeftover(line)
            normalizedSpacing = " ".join(line.split())
            pairs = normalizedSpacing.split(" ")

            indexers: list[VertexIndexer] = []
            for item in pairs:
                indices = [int(i) for i in item.split("//")]

                if len(indices) != 2:
                    raise ShapeException(
                        f'{item}\nExpected Shape: "{repr(FACE_SHAPE_IDENTIFIER.VERTEX_AND_NORMAL)}"'
                    )

                indexer = VertexIndexer(indices[0], 0, indices[1])
                indexer.outputShape = FACE_SHAPE_IDENTIFIER.VERTEX_AND_NORMAL
                indexers.append(indexer)

            return indexers

        @staticmethod
        def vertexOnlyParser(line: str):
            line = TokenConsumers.consumeTagAndReturnLeftover(line)
            normalizedSpacing = " ".join(line.split())
            indices = [int(i) for i in normalizedSpacing.split(" ")]

            indexers: list[VertexIndexer] = []
            for idx in indices:
                indexer = VertexIndexer(idx, 0, 0)
                indexer.outputShape = FACE_SHAPE_IDENTIFIER.VERTEX_ONLY
                indexers.append(indexer)

            return indexers


class Vertex[T = float]:
    X: T
    Y: T
    Z: T
    W: T

    def __init__(self, X: T, Y: T, Z: T, W: T = 1.0) -> None:
        self.X = X
        self.Y = Y
        self.Z = Z
        self.W = W


class VertexNormal[T = float]:
    X: T
    Y: T
    Z: T

    def __init__(self, X: T, Y: T, Z: T) -> None:
        self.X = X
        self.Y = Y
        self.Z = Z


class VertexTexture[T = float]:
    X: T
    Y: T
    W: T

    def __init__(self, X: T, Y: T, W: T = 0.0) -> None:
        self.X = X
        self.Y = Y
        self.W = W


class VertexIndexer:
    outputShape: FACE_SHAPE_IDENTIFIER
    vertexIndex: int
    vertexTextureIndex: int
    vertexNormalIndex: int
    linkedMaterial: str | None

    def __init__(
        self, vertexIndex: int, vertexTextureIndex: int, vertexNormalIndex: int
    ):
        self.vertexIndex = vertexIndex
        self.vertexTextureIndex = vertexTextureIndex
        self.vertexNormalIndex = vertexNormalIndex
        self.linkedMaterial = None


class VertexParameterSpace[T = float]:
    pass


class FaceInformation:
    indexers: list[list[VertexIndexer]]

    def __init__(self):
        self.indexers = []


class WaveObj:
    name: str
    isSmoothShaded: bool
    raw: list[str]
    verticies: list[Vertex]
    vertexNormals: list[VertexNormal]
    vertexTextures: list[VertexTexture]
    parameterSpaceVertices: list[VertexParameterSpace]
    linkedMTLLibs: list[str]
    faces: FaceInformation

    def __init__(self, name: str) -> None:
        self.name = name
        self.raw = []
        self.verticies = []
        self.vertexNormals = []
        self.vertexTextures = []
        self.parameterSpaceVertices = []
        self.linkedMTLLibs = []
        self.faces = FaceInformation()

    def export(self, absoluteFilePath: str | pathlib.Path):

        def floatBackDecAmount(number: float, amount: int = 6):
            return f"{number:.{amount}f}"

        path = str(absoluteFilePath)

        if not path.endswith(".obj"):
            path = f"{path}.obj"

        with open(path, "w") as file:
            file.write("# Exported with WavefrontDOTpy\n")
            file.write(f"# Exported at: {datetime.now()}\n")
            file.write("\n")

            # Write mtllibs if any
            for mtl in self.linkedMTLLibs:
                file.write(
                    f"{TAG_IDENTIFIER_TO_STRING[TAG_IDENTIFIER.MTL_LIB]} {mtl}\n"
                )
            file.write("\n")

            # Write object name
            file.write(
                f"{TAG_IDENTIFIER_TO_STRING[TAG_IDENTIFIER.OBJECT]} {self.name}\n"
            )
            file.write("\n")

            # Write vertices
            for v in self.verticies:
                file.write(
                    f"{TAG_IDENTIFIER_TO_STRING[TAG_IDENTIFIER.VERTEX]} {floatBackDecAmount(v.X)} {floatBackDecAmount(v.Y)} {floatBackDecAmount(v.Z)}"
                    + (
                        f" {floatBackDecAmount(v.W)}"
                        if hasattr(v, "W") and v.W != 1.0
                        else ""
                    )
                    + "\n"
                )
            file.write("\n")

            # Write vertex textures
            for vt in self.vertexTextures:
                file.write(
                    f"{TAG_IDENTIFIER_TO_STRING[TAG_IDENTIFIER.VERTEX_TEXTURE]} {floatBackDecAmount(vt.X)} {floatBackDecAmount(vt.Y)}\n"
                )

            # Write vertex normals
            for vn in self.vertexNormals:
                file.write(
                    f"{TAG_IDENTIFIER_TO_STRING[TAG_IDENTIFIER.VERTEX_NORMAL]} {floatBackDecAmount(vn.X)} {floatBackDecAmount(vn.Y)} {floatBackDecAmount(vn.Z)}\n"
                )

            # Write smooth shading if set
            if hasattr(self, "isSmoothShaded"):
                file.write(
                    f"{TAG_IDENTIFIER_TO_STRING[TAG_IDENTIFIER.SMOOTH_SHADE]} {1 if getattr(self, 'isSmoothShaded', False) else 0}\n"
                )
            file.write("\n")

            # Write faces
            for face in self.faces.indexers:
                if not face:
                    continue

                shaper = face[0]
                shape = shaper.outputShape

                if shaper.linkedMaterial is not None:
                    file.write(
                        f"{TAG_IDENTIFIER_TO_STRING[TAG_IDENTIFIER.USE_MTL_LIB]} {shaper.linkedMaterial}\n"
                    )

                if shape == FACE_SHAPE_IDENTIFIER.VERTEX_AND_TEXTURE_AND_NORMAL:
                    face_str = " ".join(
                        f"{vi.vertexIndex}/{vi.vertexTextureIndex}/{vi.vertexNormalIndex}"
                        for vi in face
                    )

                elif shape == FACE_SHAPE_IDENTIFIER.VERTEX_AND_TEXTURE:
                    face_str = " ".join(
                        f"{vi.vertexIndex}/{vi.vertexTextureIndex}" for vi in face
                    )
                elif shape == FACE_SHAPE_IDENTIFIER.VERTEX_AND_NORMAL:
                    face_str = " ".join(
                        f"{vi.vertexIndex}//{vi.vertexNormalIndex}" for vi in face
                    )
                elif shape == FACE_SHAPE_IDENTIFIER.VERTEX_ONLY:
                    face_str = " ".join(f"{vi.vertexIndex}" for vi in face)
                else:
                    raise ShapeException(f'EXPORT ERROR\nShape "{shape}" unknown?!?!')

                file.write(
                    f"{TAG_IDENTIFIER_TO_STRING[TAG_IDENTIFIER.POLYGONAL_FACE_ELEMENT]} {face_str}\n"
                )

            file.write("\n")
            file.write("# EOF")


######## END-Classes
######## START-Methods


def readFileLines(path: str) -> list[str]:
    lines: list[str] | None = None
    with open(path) as target:
        lines = target.readlines()

    return lines


def getLines(source: str | pathlib.Path):
    lines: list[str] | None = None

    if isinstance(source, pathlib.Path):
        if not os.path.exists(source):
            raise FileNotFoundError(f'Failed to find file using path "{source}"')

        lines = readFileLines(str(source))

    elif isinstance(source, str):
        lines = source.splitlines()

    else:
        raise Exception(f'Failed to parse "{type(source)}" as string or Path!')

    return lines


def decode(sourcePath: str | pathlib.Path):
    lines = getLines(sourcePath)
    lines = [
        line
        for line in lines
        if not line.startswith("#") and line.strip() != "" and line.strip() != "\n"
    ]

    objects: list[WaveObj] = []
    mtlLibs: list[str] = []

    if isinstance(sourcePath, pathlib.Path):
        currentObject: WaveObj | None = WaveObj(sourcePath.stem)
    else:
        currentObject: WaveObj | None = WaveObj("object")

    lastUsedMaterial: str | None = None

    for line in lines:
        line = line.strip()
        tagType: TAG_IDENTIFIER = TokenConsumers.consumeAndReturnTag(line)

        match tagType:
            case TAG_IDENTIFIER.OBJECT:
                assert currentObject is not None, "Master Object Unbound!"
                name = TokenConsumers.consumeTagAndReturnLeftover(line)
                currentObject.name = name

            case TAG_IDENTIFIER.VERTEX:
                assert currentObject is not None, "Master Object Unbound!"
                vertex = Parsers.vertexOnlyParser(line)
                currentObject.verticies.append(vertex)

            case TAG_IDENTIFIER.VERTEX_NORMAL:
                assert currentObject is not None, "Master Object Unbound!"
                vertexNormal = Parsers.vertexNormalParser(line)
                currentObject.vertexNormals.append(vertexNormal)

            case TAG_IDENTIFIER.VERTEX_TEXTURE:
                assert currentObject is not None, "Master Object Unbound!"
                vertexTexture = Parsers.vertexTextureParser(line)
                currentObject.vertexTextures.append(vertexTexture)

            case TAG_IDENTIFIER.SMOOTH_SHADE:
                assert currentObject is not None, "Master Object Unbound!"
                raw = TokenConsumers.consumeTagAndReturnLeftover(line)
                currentObject.isSmoothShaded = int(raw) == 1

            case TAG_IDENTIFIER.MTL_LIB:
                libName = TokenConsumers.consumeTagAndReturnLeftover(line)
                mtlLibs.append(libName)

            case TAG_IDENTIFIER.USE_MTL_LIB:
                libName = TokenConsumers.consumeTagAndReturnLeftover(line)
                lastUsedMaterial = libName

            case TAG_IDENTIFIER.POLYGONAL_FACE_ELEMENT:
                assert currentObject is not None, "Master Object Unbound!"
                dataType = Parsers.getFaceDataStyle(line)

                match dataType:
                    case FACE_SHAPE_IDENTIFIER.VERTEX_AND_TEXTURE_AND_NORMAL:
                        indexers = Parsers.Faces.vertexTextureNormalParser(line)
                    case FACE_SHAPE_IDENTIFIER.VERTEX_AND_TEXTURE:
                        indexers = Parsers.Faces.vertexTextureParser(line)
                    case FACE_SHAPE_IDENTIFIER.VERTEX_AND_NORMAL:
                        indexers = Parsers.Faces.vertexAndNormalParser(line)
                    case FACE_SHAPE_IDENTIFIER.VERTEX_ONLY:
                        indexers = Parsers.Faces.vertexOnlyParser(line)
                    case _:
                        raise NotImplementedError(
                            """CURRENTLY IMPLEMENTED: 
FACE_SHAPE_IDENTIFIER.VERTEX_AND_TEXTURE_AND_NORMAL,
FACE_SHAPE_IDENTIFIER.VERTEX_AND_TEXTURE,
FACE_SHAPE_IDENTIFIER.VERTEX_AND_NORMAL"""
                        )

                if lastUsedMaterial is not None:

                    for indexer in indexers:
                        indexer.linkedMaterial = lastUsedMaterial

                currentObject.faces.indexers.append(indexers)

    if currentObject is not None:
        objects.append(currentObject)

    for object in objects:
        object.linkedMTLLibs = mtlLibs

    return objects


######## END-Methods
