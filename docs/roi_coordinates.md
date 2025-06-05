# ROI coordinates

The `ROIData` class is responsible for converting napari labels layers into bounding box coordinates that can be used to add grids in SBEMimage.
These ROIs are stored as `MaskROI` objects and include the bounding box coordinates relative to the centre of the overview image.
`ROIData.add_masks` finds the bounding boxes for each labeled object in the labels layer. 

Because the labels layer can have any 2D affine transform, these coordinates are transformed using the layer's `translation`, `affine_matrix` and `scale` properties.

To add a grid into SBEMimage, the `TCPServer.add_grid` method is used with the ROI ID (labels layer integer), ROI centre coordinates relative to the centre of the overview layer,
ROI width and height, and coordinates of the overview (using the metadata stored in `LiveViewer`).

Individual grid tiles can be activated depending on the shape of the object using the 3D mask stored in `MaskROI.mask`.
This mask is obtained by applying the above transformations to the original binary mask. 
Grid tiles can be activated using the `TCPServer.update_grid_tiles_with_mask` using the ROI ID and the current 2D slice from the 3D mask.
The 2D slice is obtained with the `MaskROI.get_current_slice` and the current z coordinate from SBEMimage.
