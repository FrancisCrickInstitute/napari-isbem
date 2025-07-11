---
title: Overview
---

# napari-isbem

[`napari-isbem`](https://github.com/FrancisCrickInstitute/napari-isbem) is a napari plugin to enable targeted acquisition of samples in Serial Block-Face Scanning Electron Microscopy (SBF-SEM). Coordinates of regions of interest can be found using non-destructive X-Ray Microscopy (XRM) images. The plugin interfaces with the open-source acquisition software SBEMimage to update acquired sections in real-time during imaging.

The main workflow is described below:

1. In the [Targeting](targeting.md) tab, import the OME Zarr targeting image and create or import desired ROIs.
2. To view the SBF-SEM data, select the overview directory of the current SBEMimage project in the [Acquisition](acquisition.md) tab. The napari viewer is automaically updated when new images are acquired.
3. Align the targeting and SBF-SEM images in the [Registration](registration.md) tab to obtain ROI coordinates relative to the SBF-SEM data.
4. Start the TCP server in the [Acquisition](acquisition.md) tab and select the registered ROI layer. Continue the SBEMimage acquisition with `Use TCP` enabled to automatically image ROIs.
