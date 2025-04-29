import pytest
from napari_sbem_viewer._models.live_viewer import LiveViewer
import numpy as np
from tifffile import imwrite


class MockTiff:
    def __init__(self, filename, metadata={}, shape=(10, 10)):
        self.filename = filename
        self.shape = shape
        default_metadata = {
            'Pixels': {
                'PhysicalSizeX': 100,
                'PhysicalSizeXUnit': 'nm',
                'PhysicalSizeY': 0.2,
                'PhysicalSizeYUnit': 'µm',
            },
            'Plane': {
                'PositionX': 5,
                'PositionXUnit': 'mm',
                'PositionY': 10,
                'PositionYUnit': 'µm',
                'PositionZ': 15,
                'PositionZUnit': 'µm',
            }
        }
        # Merge default_metadata with provided metadata, giving priority to provided values
        self.metadata = default_metadata.copy()
        for key, value in metadata.items():
            if key in self.metadata and isinstance(value, dict):
                self.metadata[key].update(value)
            else:
                self.metadata[key] = value


@pytest.fixture
def mock_tiff_dir(tmp_path):
    def _mock_tiff_dir(mock_tiffs: list[MockTiff]):
        mock_tiff_dir = tmp_path / "mock_tiff_dir"
        if not mock_tiff_dir.exists():
            mock_tiff_dir.mkdir()
            imwrite('grab.tif', np.zeros((5, 5)))  # simulate grab file during SEM acquisition
        for mock_tiff in mock_tiffs:
            mock_tiff_file = str(mock_tiff_dir / mock_tiff.filename)
            data = np.zeros(mock_tiff.shape, dtype=np.uint8)
            imwrite(mock_tiff_file, data, metadata=mock_tiff.metadata, ome=True)
        return str(mock_tiff_dir)
    return _mock_tiff_dir


@pytest.fixture
def live_viewer(mocker):
    mock_napari_viewer = mocker.MagicMock()
    return LiveViewer(mock_napari_viewer, "test_layer")


def test_init_one_image(mock_tiff_dir, live_viewer):
    mock_tiff = MockTiff("test_image.tif", shape=(10, 10))
    with pytest.raises(ValueError, match="Image directory must contain at least 2 images."):
        live_viewer.init_images(mock_tiff_dir([mock_tiff]))
        
        
def test_init_images(mock_tiff_dir, live_viewer):
    mock_tiffs = [
        MockTiff("test_image_1.tif", shape=(10, 10), metadata={'Plane': {'PositionZ': 0.1}}),
        MockTiff("test_image_2.tif", shape=(10, 10), metadata={'Plane': {'PositionZ': 0.2}}),
        MockTiff("test_image_3.tif", shape=(10, 10), metadata={'Plane': {'PositionZ': 0.25}}),
        MockTiff("test_image_4.tif", shape=(10, 10), metadata={'Plane': {'PositionZ': 0.3}}),
    ]
    mock_image_dir = mock_tiff_dir(mock_tiffs)
    live_viewer.init_images(mock_image_dir)
    assert live_viewer.layer.data.shape == (3, 10, 10)
    assert live_viewer.watching == False
    assert live_viewer.image_dir == mock_image_dir
    assert live_viewer.image_shapes == [(10, 10)]
    assert live_viewer.pixel_size_x == 0.1
    assert live_viewer.pixel_size_y == 0.2
    assert live_viewer.pixel_size_z == 0.1
    assert live_viewer.position_x == 5000.
    assert live_viewer.position_y == 10.
    assert live_viewer.position_z == 0.1
    assert live_viewer.size_x == 1.
    assert live_viewer.size_y == 2.
    assert live_viewer.dtype == np.uint8
    assert live_viewer.layer is not None
    assert live_viewer.added_files == set(['test_image_1.tif', 'test_image_2.tif', 'test_image_4.tif'])
    assert live_viewer.skipped_files == set(['test_image_3.tif'])
    

def test_init_incorrect_shape(mock_tiff_dir, live_viewer):
    mock_tiffs = [
        MockTiff("test_image_1.tif", shape=(10, 10), metadata={'Plane': {'PositionZ': 0.1}}),
        MockTiff("test_image_2.tif", shape=(9, 10), metadata={'Pixels': {'PositionZ': 0.2}}),
    ]
    with pytest.raises(ValueError, match="All images must have same shape."):
        live_viewer.init_images(mock_tiff_dir(mock_tiffs))
        

def test_init_incorrect_z_spacing(mock_tiff_dir, live_viewer):
    mock_tiffs = [
        MockTiff("test_image_1.tif", shape=(10, 10), metadata={'Plane': {'PositionZ': 0.1}}),
        MockTiff("test_image_2.tif", shape=(10, 10), metadata={'Plane': {'PositionZ': 0.15}}),
        MockTiff("test_image_3.tif", shape=(10, 10), metadata={'Plane': {'PositionZ': 0.3}}),
    ]
    with pytest.raises(ValueError, match="Inconsitent Z spacing between images. Expected: 0.20, Got: 0.30"):
        live_viewer.init_images(mock_tiff_dir(mock_tiffs))
        
        
def test_append_image(mock_tiff_dir, live_viewer):
    mock_tiffs = [
        MockTiff("test_image_1.tif", shape=(10, 10), metadata={'Plane': {'PositionZ': 0.1}}),
        MockTiff("test_image_2.tif", shape=(10, 10), metadata={'Plane': {'PositionZ': 0.2}})
    ]
    mock_image_dir = mock_tiff_dir(mock_tiffs)
    live_viewer.init_images(mock_image_dir)
    
    new_mock_tiffs = [
        MockTiff("test_image_3.tif", shape=(10, 10), metadata={'Plane': {'PositionZ': 0.23}}),
        MockTiff("test_image_4.tif", shape=(10, 10), metadata={'Plane': {'PositionZ': 0.3}}),
    ]
    mock_tiff_dir(new_mock_tiffs)
        
    for tiff in live_viewer._get_images_from_dir():
        live_viewer.append(tiff)

    assert live_viewer.added_files == set(['test_image_1.tif', 'test_image_2.tif', 'test_image_4.tif'])  
    assert live_viewer.skipped_files == set(['test_image_3.tif'])
    assert live_viewer.layer.data.shape == (3, 10, 10)
    assert live_viewer.watching == False
    assert live_viewer.image_dir == mock_image_dir
    assert live_viewer.image_shapes == [(10, 10)]
    assert live_viewer.pixel_size_x == 0.1
    assert live_viewer.pixel_size_y == 0.2
    assert live_viewer.pixel_size_z == 0.1
    assert live_viewer.position_x == 5000.
    assert live_viewer.position_y == 10.
    assert live_viewer.position_z == 0.1
    assert live_viewer.size_x == 1.
    assert live_viewer.size_y == 2.
    assert live_viewer.dtype == np.uint8
    assert live_viewer.layer is not None
    