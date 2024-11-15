import cv2
import numpy as np
from scipy.spatial.transform import Rotation
from scipy.ndimage import affine_transform
import SimpleITK as sitk
from sklearn.linear_model import RANSACRegressor
from napari.layers import Image, Layer


def quaternion_from_vectors(v1, v2):
    k_cos_theta = np.dot(v1, v2)
    k = np.linalg.norm(v1) * np.linalg.norm(v2)
    return (*np.cross(v1, v2), k + k_cos_theta)


def axis_angle_from_vectors(v1, v2):
    # Calculate the rotation axis
    axis = np.cross(v1, v2)
    if np.linalg.norm(axis) == 0:
        return np.array(v1), 0
    
    axis /= np.linalg.norm(axis)

    # Calculate the angle of rotation
    angle = np.arccos(np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2)))

    return axis, angle


def line_parametric_equation(p1, p2, t):
    # Given two points p1 and p2, calculate the point p on the line between p1 and p2 at parameter t
    t = np.clip(t, 0, 1)
    return p1 + t * (p2 - p1)


def calculate_t(p1, p2, p):
    # Given two points p1 and p2, and a point p, calculate the parameter t such that p = p1 + t(p2 - p1)
    # e.g. how far along the line p1 to p2 is p
    v = p2 - p1
    w = p - p1
    return np.dot(w, v) / np.dot(v, v)
    
    
def find_intersections(b0, b1, p, v):
    intersection_points = []
    for point in [b0, b1]:
        for direction in [[1, 0, 0], [0, 1, 0], [0, 0, 1]]:
            dot_product = np.dot(v, direction)
            distance_to_plane = np.dot(point - p, direction)
            t = distance_to_plane / dot_product
            intersection_point = p + t * v
            # if the intersection point is within the bounds of the plane, add it to the list
            if np.all(b0 <= intersection_point) and np.all(intersection_point <= b1):
                intersection_points.append(intersection_point)
    return intersection_points


def rotation_matrix_from_vectors(vec1, vec2):
    """Compute the rotation matrix to rotate vec1 onto vec2."""
    # Normalize vectors
    vec1 = vec1 / np.linalg.norm(vec1)
    vec2 = vec2 / np.linalg.norm(vec2)

    axis, angle = axis_angle_from_vectors(vec1, vec2)

    return rotation_matrix_from_axis_angle(axis, angle)


def rotation_matrix_from_zy_zx_angles(zy_angle, zx_angle):
    transform_matrix_zy = np.asarray([
    [np.cos(np.radians(zy_angle)), -np.sin(np.radians(zy_angle)), 0, 0],
    [np.sin(np.radians(zy_angle)), np.cos(np.radians(zy_angle)), 0, 0],
    [0, 0, 1, 0],
    [0, 0, 0, 1]
    ])
    transform_matrix_zx = np.asarray([
        [np.cos(np.radians(zx_angle)), 0, np.sin(np.radians(zx_angle)), 0],
        [0, 1, 0, 0],
        [-np.sin(np.radians(zx_angle)), 0, np.cos(np.radians(zx_angle)), 0],
        [0, 0, 0, 1]
    ])
    return transform_matrix_zy @ transform_matrix_zx


def rotation_matrix_from_axis_angle(axis, angle):
    """
    Convert an axis and an angle into a 4x4 transformation matrix.
    
    Parameters:
    axis (array-like): A 3-element array-like structure representing the rotation axis.
    angle (float): The rotation angle in radians.
    
    Returns:
    np.ndarray: A 4x4 transformation matrix.
    """
    axis = np.array(axis)
    axis = axis / np.linalg.norm(axis)  # Normalize the axis
    x, y, z = axis
    c = np.cos(angle)
    s = np.sin(angle)
    t = 1 - c
    
    # Create the rotation matrix
    rotation_matrix = np.array([
        [t*x*x + c,   t*x*y - s*z, t*x*z + s*y, 0],
        [t*x*y + s*z, t*y*y + c,   t*y*z - s*x, 0],
        [t*x*z - s*y, t*y*z + s*x, t*z*z + c,   0],
        [0,           0,           0,           1]
    ])
    
    return rotation_matrix


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


def decompose_rotation_matrix(matrix):
    # return the angles of rotation around the x-axis (zy direction) and around the y-axis (zx direction)
    return -np.arcsin(matrix[0, 1]), -np.arcsin(matrix[2, 0])
        
        
def get_transformation_matrix_2d(moving_points, fixed_points):
    # convert coordinates from (y, x) to (x, y)
    fixed_points = fixed_points[:, ::-1]
    moving_points = moving_points[:, ::-1]
    Rt, _ = cv2.estimateAffine2D(moving_points, fixed_points)
    Rt = np.vstack([[Rt[0, 0], Rt[0, 1], Rt[1, 2]], 
                    [Rt[1, 0], Rt[1, 1], Rt[0, 2]], 
                    [0, 0, 1]])
    return Rt


def get_transformation_matrix_slices(reverse, z_offset, pts_fixed, pts_moving, scale=None):
    T = np.eye(4)
    
    # scale transformation to offset the x and y scaling
    if scale is not None:
        T[1, 1] = scale[0]
        T[2, 2] = scale[1]
    
    if reverse:
        T[0, 0] *= -1  # flip z-axis
    
    if z_offset != 0:
        T[0, 3] -= z_offset  # shift image to align with fixed image
    
    if pts_fixed is not None and pts_moving is not None:
        T_2d = get_transformation_matrix_2d(pts_moving, pts_fixed)
        rotation = np.arctan2(T_2d[1, 0], T_2d[0, 0])
        scale_x = T_2d[0, 0] / np.cos(rotation)
        scale_y = T_2d[1, 1] / np.cos(rotation)
        translation_x = T_2d[1, 2]
        translation_y = T_2d[0, 2]
        
        rotate_T = np.eye(4)
        rotate_T[1, 1] = np.cos(rotation)
        rotate_T[1, 2] = np.sin(rotation)
        rotate_T[2, 1] = -np.sin(rotation)
        rotate_T[2, 2] = np.cos(rotation)
        
        scale_T = np.eye(4)
        scale_T[1, 1] = scale_y
        scale_T[2, 2] = scale_x
        
        translate_T = np.eye(4)
        translate_T[2, 3] = translation_x
        translate_T[1, 3] = translation_y

        T = np.matmul(scale_T, T)
        T = np.matmul(rotate_T, T)
        T = np.matmul(translate_T, T)
    
    return T


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


def transform_image_3d(image, transformation_matrix):
    transformation_matrix = np.linalg.inv(transformation_matrix)
    return affine_transform(image, transformation_matrix, output_shape=image.shape)


def rotate_image_3d(image, angle, axis):
    # Create rotation object
    rotation = Rotation.from_rotvec(angle * axis)

    # Calculate center of rotation
    center = np.array(image.shape) / 2

    # Calculate translation to ensure the rotated image fits within the original image
    max_translation = np.ceil(np.sqrt(np.sum(center ** 2)))
    translation = max_translation - center

    # Define transformation matrix (rotation + translation)
    transformation_matrix = np.identity(4)
    transformation_matrix[:3, :3] = rotation.as_matrix()
    # transformation_matrix[:3, 3] = translation
    corners = np.array([[0, 0, 0],
                        [0, image.shape[0], 0],
                        [image.shape[1], 0, 0],
                        [0, 0, image.shape[2]],
                        [image.shape[1], image.shape[0], 0],
                        [image.shape[1], 0, image.shape[2]],
                        [0, image.shape[0], image.shape[2]],
                        [image.shape[1], image.shape[0], image.shape[2]]])
    transformed_corners = np.dot(transformation_matrix[:3, :3], corners.T).T + center
    min_corner = np.min(transformed_corners, axis=0)
    max_corner = np.max(transformed_corners, axis=0)
    transformation_matrix[:3, 3] = -min_corner
    output_shape = np.ceil(max_corner - min_corner).astype(int)
    
    # Apply the transformation to the image
    rotated_image = affine_transform(image, transformation_matrix, output_shape=output_shape).astype(image.dtype)
    rotated_image = rotated_image / 65535
    return rotated_image


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


def rotate_layer(layer, v1, v2):
    layer_type = 'image' if isinstance(layer, Image) else 'labels'
    interpolator = 'linear' if layer_type == 'image' else 'nearest'
    quaternion = quaternion_from_vectors(v1, v2)
    if isinstance(layer.data, np.ndarray):
        rotated_data = rotate_image_3d_sitk(layer.data, quaternion, interpolator)
    else:
        rotated_data = []
        for pyramid_level in layer.data:
            rotated_data.append(rotate_image_3d_sitk(pyramid_level.compute(), quaternion, interpolator))
    rotated_layer = Layer.create(rotated_data, {'scale': layer.scale, 'name': layer.name + ' (rotated)'}, layer_type)
    return rotated_layer
