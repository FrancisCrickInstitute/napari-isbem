# Storing layers

The plugin uses a variety of napari layers that are shared across the entire widget: e.g. the targeting image layer (XRM image), the EM image layer (SEM overviews), and the labels layer (for ROIs).
The `LayerModel` class stores this information and is used by each model to access the data. The class also handles adding the layers to the napari viewer and sending events when the layers and added or removed.
These events are used by the models to show / hide parts of the UI depending on what images have been added, for example, when the targeting layer is added, the `TargetingController` class activates the `AddLabels` view.
