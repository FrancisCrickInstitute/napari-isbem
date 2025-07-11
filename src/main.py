import napari

from napari_isbem._widgets import SBEMViewerWidget

if __name__ == '__main__':
    # OVERVIEW_DIR = '/Users/rossg/sbemimage/EM04652/overviews/ov000/'
    # ROI_STACK = 'test_labels3.tif'
    # ROI_STACK = '/Users/rossg/Documents/MRC-MM/example_data/kidney/EM04652_slice015/EM04652_02_slice015_ROIsfor3view_mask.tif'
    # X_RAY_STACK = '/Users/rossg/Documents/MRC-MM/example_data/kidney/EM04652_slice015/EM04652_2_slice15_2048x2048x146x16bit.ome.zarr'

    X_RAY_STACK = '/Users/rossg/Documents/MRC-MM/example_data/kidney/EM04652_slice018/EM04652_02_slice018_resinHiTT.ome.zarr'
    ROI_STACK = '/Users/rossg/Documents/MRC-MM/example_data/kidney/EM04652_slice018/EM04652_02_slice018_ROI_mask_modified.tif'
    # ROI_STACK = '/Users/rossg/Projects/napari-sbem-viewer/example_broken_labels.tif'
    # OVERVIEW_DIR = '/Users/rossg/Documents/MRC-MM/example_data/kidney/EM04652_slice018/EM04652_2_slice18/overviews/ov000'
    OVERVIEW_DIR = '/Users/rossg/sbemimage/EM04652/overviews/ov000'
    TRANSFORM_TXT = '/Users/rossg/Documents/MRC-MM/example_data/kidney/EM04652_slice018/napari_transform_edit.txt'

    viewer = napari.Viewer()
    main_widget = SBEMViewerWidget(viewer)
    viewer.window.add_dock_widget(main_widget)

    # Configure acquisition widget
    main_widget.acquisition_view.acquisition_settings.fine_thickness_spinbox.setValue(
        50
    )
    main_widget.acquisition_view.tcp_settings.start_server_button.click()
    main_widget.acquisition_model.live_viewer.start_watching(OVERVIEW_DIR)

    # Configure targeting widget
    main_widget.layer_model.import_targeting_image(X_RAY_STACK)
    main_widget.targeting_model.upload_existing_labels(ROI_STACK)

    main_widget.registration_model.load_transform(TRANSFORM_TXT)

    napari.run()
