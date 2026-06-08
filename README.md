# napari-isbem

<!-- [![License MIT](https://img.shields.io/pypi/l/napari-isbem.svg?color=green)](https://github.com/FrancisCrickInstitute/napari-isbem/raw/main/LICENSE) -->
<!-- [![PyPI](https://img.shields.io/pypi/v/napari-isbem.svg?color=green)](https://pypi.org/project/napari-isbem) -->
<!-- [![Python Version](https://img.shields.io/pypi/pyversions/napari-isbem.svg?color=green)](https://python.org) -->
[![tests](https://github.com/FrancisCrickInstitute/napari-isbem/workflows/tests/badge.svg)](https://github.com/FrancisCrickInstitute/napari-isbem/actions)
<!-- [![codecov](https://codecov.io/gh/FrancisCrickInstitute/napari-isbem/branch/main/graph/badge.svg)](https://codecov.io/gh/FrancisCrickInstitute/napari-isbem) -->
<!-- [![napari hub](https://img.shields.io/endpoint?url=https://api.napari-hub.org/shields/napari-isbem)](https://napari-hub.org/plugins/napari-isbem) -->

A [napari] plugin to enable targeted imaging in [SBEMimage]. Regions of interest identified in X-Ray Microscopy (XRM) (or other correlative modality) images can be registered to the SBF-SEM data, and the plugin communicates with SBEMimage over TCP to automatically update acquisition regions in real-time. Read the [documentation] for more information.

----------------------------------

## Version Compatibility

`napari-isbem` communicates with SBEMimage over TCP — they do not necessarily need to be run in the same Python environment. You need compatible versions of each:

| napari-isbem | SBEMimage | Notes |
|---|---|---|
| v0.2.1+ | ≥ [2026.06](https://github.com/SBEMimage/SBEMimage/releases/tag/2026.06) | Recommended |
| v0.2.0 | 2026.02.06 dev ([`3754ef9`](https://github.com/SBEMimage/SBEMimage/tree/3754ef96bc19426995bcfae012410a90a2b5f0ae)) | Breaking change from v0.1.0 |
| v0.1.0 | 2025.11.14 dev ([`58e36a5`](https://github.com/SBEMimage/SBEMimage/tree/58e36a5f55d4cbc0b4f18b6db780f4808a6520d4)) | Initial release |

> **Important:** v0.2.0 introduced a breaking change in the SBEMimage metadata format. napari-isbem v0.2.x is **not** compatible with earlier SBEMimage versions, and v0.1.0 is **not** compatible with later ones.

## Installation

### Installing napari

Create a Python 3.12 environment with napari installed (skip this step if you are already a napari user and have napari installed in your environment).

Using Python with [uv]:

```
uv venv napari-isbem --python 3.12
source napari-isbem/bin/activate
uv pip install 'napari[all]==0.5' qtpy
```

Using conda:

```
conda create -n napari-isbem python=3.12 napari=0.5 pyqt -c conda-forge
conda activate napari-isbem
```

### Installing the plugin

```
# with uv
uv pip install napari-isbem
# with pip/conda
pip install napari-isbem
```

Launch with

```
napari -w napari-isbem
```

### SBEMimage

SBEMimage is installed separately (it is not a Python package dependency of napari-isbem). See the [SBEMimage installation guide](https://sbemimage.readthedocs.io/en/latest/installation.html) or clone from the [SBEMimage repository](https://github.com/SBEMimage/SBEMimage).

More detailed instructions for all scenarios can be found in the [installation documentation](https://FrancisCrickInstitute.github.io/napari-isbem/installation/).

## Usage

To get started, follow the step by step illustrated [user guide](USER_GUIDE.md). For more detailed information on the features and settings, see the [full documentation](https://FrancisCrickInstitute.github.io/napari-isbem).

## Contributing

Contributions are very welcome. Tests can be run with [tox]; please ensure
the coverage at least stays the same before you submit a pull request.

## License

Distributed under the terms of the [MIT] license,
"napari-isbem" is free and open source software.

## Issues

If you encounter any problems, please [file an issue] along with a detailed description.

[napari]: https://napari.org/
[SBEMimage]: sbemimage.readthedocs.io
[documentation]: https://FrancisCrickInstitute.github.io/napari-isbem
[tox]: https://tox.readthedocs.io/en/latest/
[uv]: https://docs.astral.sh/uv/pip/environments/
[pip]: https://pypi.org/project/pip/
[PyPI]: https://pypi.org/
[MIT]: http://opensource.org/licenses/MIT
[file an issue]: https://github.com/FrancisCrickInstitute/napari-isbem/issues
