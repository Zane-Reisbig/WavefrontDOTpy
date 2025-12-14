# WaveFrontDOTpy

Lightweight Wavefront OBJ parser/exporter library.

## Features

-   Parse OBJ lines into structured objects (vertices, normals, textures, faces) via [`WaveFrontDOTPy.Object.decode`](WaveFrontDOTPy/Object.py).
-   Export parsed objects back to `.obj` with [`WaveFrontDOTPy.Object.WaveObj.export`](WaveFrontDOTPy/Object.py).

## Usage

```py
from WaveFrontDOTPy import WaveObj, TokenConsumers, UnknownTagException
from WaveFrontDOTPy.Object import decode

objects = decode("object/SomeModel.obj")
first = objects[0]
first.export("object/SomeModel_copy.obj")
```

## Running Tests

the .vscode directory is included cuz i set up a unit test as the main thing

```sh
python -m unittest -v
```

## Notes

-   Groups are not supported (Yet.)
-   Lines are not supported (?Yet?)
