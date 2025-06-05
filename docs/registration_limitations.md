# Registration limitations

The registration between the targeting layer and the EM overviews layer is done in three parts. 

1. The targeting image is rotated to align the z-axes of both image stacks. 
2. The image is translated to align the stacks in the z dimension.
3. A 2D affine transform is computed between two corresponding z slices.

These three steps cannot be displayed with a single affine transform as the rotation step would require non-orthogonal slicing (not supported in napari as of v0.5.6).
To get around this, the rotation step is done separately by reslicing the entire 3D image into a new rotated array (by applying the transform with SITK).
As the z-translation and 2D affine steps are restricted to orthogonal slicing, these can be directly applied to the image layer's `affine.affine_matrix` parameter.

The original unrotated targeting and labels layers are stored in the `LayerModel` class. 
To avoid editing labels on the rotated labels array, editing labels is disabled if the image has been rotated.

When a transform is saved, the rotation transform stored in the `AlignPlanes` model is combined with the rotated layer's `affine.affine_matrix` transform to create a single transform matrix containing the three registration steps.
When the transform is loaded in the plugin, the rotation transform is extracted with matrix decomposition and the two parts are applied separately.
