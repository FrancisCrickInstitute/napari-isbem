# Installation

`napari-isbem` communicates with [SBEMimage](https://sbemimage.readthedocs.io) over TCP — they are typically run in separate Python environments (often on separate machines), but can share one if convenient. Either way, they are installed independently.

## Version Compatibility

| napari-isbem | SBEMimage | Notes |
|---|---|---|
| v0.2.1+ | ≥ 2026.xx (upcoming tagged release) | Recommended |
| v0.2.0 | 2026.02.06 dev ([`3754ef9`](https://github.com/SBEMimage/SBEMimage/tree/3754ef96bc19426995bcfae012410a90a2b5f0ae)) | Breaking change from v0.1.0 |
| v0.1.0 | 2025.11.14 dev ([`58e36a5`](https://github.com/SBEMimage/SBEMimage/tree/58e36a5f55d4cbc0b4f18b6db780f4808a6520d4)) | Initial release |

!!! warning
    v0.2.0 introduced a breaking change in the SBEMimage metadata format. napari-isbem v0.2.x is **not** compatible with earlier SBEMimage versions, and v0.1.0 is **not** compatible with later ones.

---

## napari-isbem

### 1. Set up a Python environment with napari

If you already have napari ≥ 0.5 installed in a Python 3.12 environment, skip to [step 2](#2-install-the-plugin).

#### Option A: Using conda

```
conda create -n napari-isbem python=3.12 napari=0.5 pyqt -c conda-forge
conda activate napari-isbem
```

If conda is not installed, follow these [installation instructions](https://docs.conda.io/projects/conda/en/latest/user-guide/install/index.html).

#### Option B: Using uv

```
uv venv napari-isbem --python 3.12
source napari-isbem/bin/activate
uv pip install 'napari[all]==0.5' qtpy
```

and test napari opens correctly from the command line with

```
napari
```

!!! note
    `napari[all]` includes the default Qt backend (PyQt5). If you need a different backend (e.g. PySide2 or PyQt6), see [Choosing a different Qt backend](https://napari.org/dev/getting_started/installation.html#choosing-a-different-qt-backend) in the napari docs.

### 2. Install the plugin

```
pip install napari-isbem
```

To pin a specific version (e.g. if you need to match a particular SBEMimage version):

```
pip install napari-isbem==0.2.0
```

Once the installation is complete, open the plugin with

```
napari -w napari-isbem
```

---

## SBEMimage

SBEMimage is **not** a Python dependency of napari-isbem — it is installed separately, possibly on a different machine (the one connected to the microscope).

### Already have SBEMimage installed?

Check that your version is compatible with your napari-isbem version using the [compatibility table](#version-compatibility) above.

### Need to install SBEMimage?

See the [SBEMimage installation guide](https://sbemimage.readthedocs.io/en/latest/installation.html) or clone from the [SBEMimage repository](https://github.com/SBEMimage/SBEMimage).

To check out a specific compatible commit (e.g. for napari-isbem v0.2.0):

```
git clone https://github.com/SBEMimage/SBEMimage.git
cd SBEMimage
git checkout 3754ef9
```

---

## Development build

When developing the plugin, you can clone repository and install the package in editable mode with

```
git clone git@github.com:FrancisCrickInstitute/napari-isbem.git
cd napari-isbem
pip install -e .
```
