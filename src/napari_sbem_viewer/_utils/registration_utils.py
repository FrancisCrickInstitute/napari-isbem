import cv2
import numpy as np
from scipy.spatial.transform import Rotation
from scipy.ndimage import affine_transform
import SimpleITK as sitk
from sklearn.linear_model import RANSACRegressor
from napari.layers import Image, Layer
from scipy.spatial.transform import Rotation as R


def rotation_matrix_from_zy_zx_angles(zy_angle, zx_angle):
    mat = np.eye(4)
    mat[:3, :3] = R.from_euler('zyx', [zy_angle, zx_angle, 0], degrees=True).as_matrix()
    return mat


def is_rotation_matrix(matrix):
    """
    Check if the supplied 4x4 matrix is a pure rotation matrix.
    
    Parameters:
    matrix (np.ndarray): A 4x4 transformation matrix.
    
    Returns:
    bool: True if the matrix represents only a rotation, False otherwise.
    """
    if matrix.shape != (4, 4):
        return False
    # Extract the upper-left 3x3 submatrix
    rotation_matrix = matrix[:3, :3]
    
    # Check if the upper-left 3x3 submatrix is orthogonal
    should_be_identity = np.dot(rotation_matrix.T, rotation_matrix)
    identity = np.eye(3)
    if not np.allclose(should_be_identity, identity):
        return False
    
    # Check if the determinant of the upper-left 3x3 submatrix is 1
    if not np.isclose(np.linalg.det(rotation_matrix), 1.0):
        return False
    
    # Check the last row and last column
    if not np.allclose(matrix[3, :], [0, 0, 0, 1]):
        return False
    
    if not np.allclose(matrix[:, 3], [0, 0, 0, 1]):
        return False
    
    return True


def is_2d_affine_matrix(matrix):
    if matrix.shape != (4, 4):
        return False
    
    # Check if the matrix doesn't include rotation through z-axis
    if not np.allclose(matrix[0, 1:3], [0, 0]):
        return False
    
    if not np.allclose(matrix[1:, 0], [0, 0, 0]):
        return False
    
    if not np.allclose(matrix[3, :], [0, 0, 0, 1]):
        return False

    return True


def rotate_image_3d_sitk(image, quaternion, interpolator='linear'):
    image_sitk = sitk.GetImageFromArray(image.astype(np.float32))
    transform = sitk.VersorTransform(list(quaternion))
    image_center = np.array(image_sitk.GetSize()) / 2.0
    transform.SetCenter(image_center)
    if interpolator == 'nearest':
        interpolator = sitk.sitkNearestNeighbor
    elif interpolator == 'linear':
        interpolator = sitk.sitkLinear
    image_rotated = sitk.Resample(image_sitk, transform, interpolator, 0.0, image_sitk.GetPixelID())
    return sitk.GetArrayFromImage(image_rotated).astype(image.dtype)


def find_bounds(image_shape, affine_matrix, offset=None):
    bounds = np.asarray([[0, 0, 0, 1], 
                         [0, image_shape[1], 0, 1], 
                         [image_shape[0], 0, 0, 1], 
                         [0, 0, image_shape[2], 1],
                         [image_shape[0], image_shape[1], 0, 1],
                         [image_shape[0], 0, image_shape[2], 1],
                         [0, image_shape[1], image_shape[2], 1],
                         [image_shape[0], image_shape[1], image_shape[2], 1]])
    if offset is not None:
        offset = np.asarray(offset)
        assert len(offset) == 3
        offset = np.append(offset, 0)
        bounds += offset
    transformed_bounds = np.dot(affine_matrix, bounds.T).T
    min_bound = np.min(transformed_bounds, axis=0)[:-1]
    max_bound = np.max(transformed_bounds, axis=0)[:-1]
    return min_bound, max_bound


def add_scale_to_transform_matrix(matrix, scale):
    assert len(scale) == 3
    assert matrix.shape == (4, 4)
    return matrix @ np.diag([*[s for s in scale], 1])


def permute_matrix(matrix):
    # Permute a transformation matrix from ZYX to XYZ order or vice versa
    return matrix[np.ix_([2, 1, 0, 3], [2, 1, 0, 3])]

def transform_image_3d_sitk(image, transformation_matrix, interpolator='linear'):
    # Find the image bounds after transformation
    min_coords, max_coords = find_bounds(image.shape, transformation_matrix)
    # Calculate the inverse transform and perform the transformation for use with sitk
    transformation_matrix = np.linalg.inv(transformation_matrix)
    transformation_matrix_xyz = permute_matrix(transformation_matrix)
    
    # Create the sitk image and transformation objects
    image_sitk = sitk.GetImageFromArray(image.astype(np.float32))
    transform = sitk.AffineTransform(3)
    transform.SetMatrix(transformation_matrix_xyz[:3, :3].flatten())
    translation_vector = transformation_matrix_xyz[:3, 3]
    transform.SetTranslation(translation_vector)
    transform.SetCenter([0, 0, 0])
    
    # Set the interpolator
    if interpolator == 'nearest':
        interpolator = sitk.sitkNearestNeighbor
    elif interpolator == 'linear':
        interpolator = sitk.sitkLinear
        
    # Use the max and min bounds to calculate the output size and origin
    output_size = [int(max_coord - min_coord) for min_coord, max_coord in zip(min_coords, max_coords)][::-1]
    output_origin = min_coords.astype(np.float64).tolist()[::-1]
    
    # Perform the transformation
    image_transformed = sitk.Resample(image_sitk, 
                                      output_size,
                                      transform, 
                                      interpolator,
                                      output_origin)
    return sitk.GetArrayFromImage(image_transformed).astype(image.dtype), min_coords


def offset_transform_matrix_z(mat, offset):
    """
    Create a transformation matrix to offset the z-axis of an image.
    Params:
        z_offset: float, the amount to offset the z-axis by
    Returns:
        mat: np.ndarray, a 4x4 transformation matrix
    """
    mat[0, 3] -= offset
    return mat
    

def flip_transform_matrix(mat, z_shape):
    """
    Create a transformation matrix to flip the z-axis of an image.
    Returns:
        mat: np.ndarray, a 4x4 transformation matrix
    """
    mat_flip = np.eye(4)
    mat_flip[0, 0] = -1
    mat_flip[0, 3] += z_shape
    mat = mat @ mat_flip
    return mat


def remove_outliers_ransac(src, dst):
    ransac = RANSACRegressor()
    ransac.fit(src, dst)
    
    inlier_mask = ransac.inlier_mask_
    src_filtered = src[inlier_mask]
    dst_filtered = dst[inlier_mask]
    
    return src_filtered, dst_filtered


def calculate_transform(src, dst, ndim, model_class, remove_outliers=False):
    """
    Use the specified model to calculata a transform between two sets of points.
    """
    if remove_outliers:
        src, dst = remove_outliers_ransac(src, dst)
    model = model_class(dimensionality=ndim)
    model.estimate(dst, src)
    return model


def calculate_z_transform(reference_points_layer, moving_points_layer, reverse_stack):
    """Calculate the transformation matrix required to shift the image in the Z-direction.

    Parameters
    ----------
    reference_points_layer : Points
        Napaari points layer containing the points in the reference image.
    moving_points_layer : Points
        Napari points layer containing the matched points in the moving image.
    reverse_stack : bool
        Whether or not the reverse the stack in the Z-direction.

    Returns
    -------
    transform matrix : ndarray
    """
    reference_z = reference_points_layer.data[-1][0]  # z value of the latest point
    moving_z = moving_points_layer.data[-1][0]
    if reverse_stack:
        z_offset = - moving_z - reference_z
    else:
        z_offset = moving_z - reference_z
    mat = np.identity(4)
    if reverse_stack:
        mat[0, 0] = -1
    mat[0, 3] -= z_offset
    return mat


def convert_affine_to_ndims(affine, target_ndim):
    """Either embed or slice an affine matrix to match the target ndims."""
    affine_matrix = np.asarray(affine)
    diff = np.shape(affine_matrix)[0] - 1 - target_ndim
    if diff == 0:
        out = affine_matrix
    elif diff < 0:
        # target is larger, so embed
        out = np.identity(target_ndim + 1)
        out[-diff:, -diff:] = affine_matrix
    else:  # diff > 0
        out = affine_matrix[diff:, diff:]

    return out


def calculate_normal(zy_degrees, zx_degrees):
    normal = np.asarray([[1], [0], [0]])
    rotation_matrix = rotation_matrix_from_zy_zx_angles(zy_degrees, zx_degrees)
    normal = rotation_matrix[:3, :3] @ normal
    return normal.T[0]


def transform_layer(layer, affine_transform):
    layer_type = 'image' if isinstance(layer, Image) else 'labels'
    interpolator = 'linear' if layer_type == 'image' else 'nearest'
    if layer.scale is not None:
        affine_transform = add_scale_to_transform_matrix(affine_transform, layer.scale)
    if isinstance(layer.data, np.ndarray):
        transformed_image, offset = transform_image_3d_sitk(layer.data, affine_transform, interpolator)
    else:
        transformed_image = []
        offset = None
        for i, pyramid_level in enumerate(layer.data):
            if i == 0:
                transform_level, offset = transform_image_3d_sitk(pyramid_level.compute(), affine_transform, interpolator)
            else:
                transform_level, _ = transform_image_3d_sitk(pyramid_level.compute(), affine_transform, interpolator)
            transformed_image.append(transform_level)   
    rotated_layer = Layer.create(transformed_image, {'scale': (1, 1, 1), 'name': layer.name, 'translate': offset}, layer_type)
    return rotated_layer


def decompose_transform(transform_matrix):
    zy_degrees, zx_degrees = zy_zx_angles_from_matrix(transform_matrix)
    rot_matrix = rotation_matrix_from_zy_zx_angles(zy_degrees, zx_degrees)
    affine_matrix_2d = transform_matrix @ np.linalg.inv(rot_matrix)
    affine_matrix_2d[np.abs(affine_matrix_2d) < 1e-6] = 0
    affine_matrix_2d[np.abs(affine_matrix_2d - 1) < 1e-6] = 1
    return rot_matrix, affine_matrix_2d


def zy_zx_angles_from_matrix(matrix):
    R_mat = enforce_orthogonality(matrix[:3, :3])
    R_mat = correct_rotation_matrix_for_flips(R_mat)
    euler_angles = R.from_matrix(R_mat).as_euler('zyx', degrees=True)
    return euler_angles[0], euler_angles[1]


def enforce_orthogonality(matrix):
    U, _, Vt = np.linalg.svd(matrix)
    return U @ Vt


def correct_rotation_matrix_for_flips(R_mat):
    flipped_axes = detect_flipped_axes(R_mat)
    R_mat[flipped_axes] *= -1
    return R_mat


def detect_flipped_axes(matrix):
    # Compute the dot product of each column with the unit vectors
    # Flipped axes will have a dot product close to -1
    return np.einsum('ij,ij->i', matrix, np.eye(3)) < -0.9
    