# Installation

## Creating a conda environment

Before installing the plugin, create a fresh conda environment with python v3.12 and napari v0.5.

```
conda create -n napari-sbem-viewer python=3.12 napari=0.5 pyqt -c conda-forge
```

If conda is not installed, follow these [installation instructions](https://docs.conda.io/projects/conda/en/latest/user-guide/install/index.html).

After the environment is created, activate it with

```
conda activate napari-sbem-viewer
```

and test napari opens correctly from the command line with

```
napari
```

## Installing the plugin

After napari is successfully installed, the plugin can be installed directly from the Git repo:

```
pip install napari-sbem-viewer@git+https://github.com/FrancisCrickInstitute/napari-sbem-viewer.git
```

Once the installation is complete, open the plugin with

```
napari -w napari-sbem-viewer
```

## Development build

When developing the plugin, you can clone repository and install the package in editable mode with

```
git clone git@github.com:FrancisCrickInstitute/napari-sbem-viewer.git
cd napari-sbem-viewer
pip install -e .
```
