import cv2
import numpy as np
from scipy.spatial.transform import Rotation
from scipy.ndimage import affine_transform
import SimpleITK as sitk


def quaternion_from_vectors(v1, v2):
    k_cos_theta = np.dot(v1, v2)
    k = np.linalg.norm(v1) * np.linalg.norm(v2)
    return (*np.cross(v1, v2), k + k_cos_theta)


def axis_angle_from_vectors(v1, v2):
    # Calculate the rotation axis
    axis = np.cross(v1, v2)
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

    # Compute the rotation axis
    axis = np.cross(vec1, vec2)
    axis /= np.linalg.norm(axis)

    # Compute the rotation angle (in radians)
    angle = np.arccos(np.dot(vec1, vec2))

    # Compute the rotation matrix
    cos_theta = np.cos(angle)
    sin_theta = np.sin(angle)
    rot_mat = np.array([[cos_theta + axis[0]**2 * (1 - cos_theta), 
                         axis[0] * axis[1] * (1 - cos_theta) - axis[2] * sin_theta,
                         axis[0] * axis[2] * (1 - cos_theta) + axis[1] * sin_theta],
                        [axis[1] * axis[0] * (1 - cos_theta) + axis[2] * sin_theta,
                         cos_theta + axis[1]**2 * (1 - cos_theta),
                         axis[1] * axis[2] * (1 - cos_theta) - axis[0] * sin_theta],
                        [axis[2] * axis[0] * (1 - cos_theta) - axis[1] * sin_theta,
                         axis[2] * axis[1] * (1 - cos_theta) + axis[0] * sin_theta,
                         cos_theta + axis[2]**2 * (1 - cos_theta)]])
    return rot_mat


def matrix_from_axis_angle(angle, axis):
    """ Compute rotation matrix from axis-angle.
    This is called exponential map or Rodrigues' formula.
    Returns
    -------
    R : array-like, shape (3, 3)
        Rotation matrix
    """
    ux, uy, uz = axis
    c = np.cos(angle)
    s = np.sin(angle)
    ci = 1.0 - c
    R = np.array([[ci * ux * ux + c,
                   ci * ux * uy - uz * s,
                   ci * ux * uz + uy * s],
                  [ci * uy * ux + uz * s,
                   ci * uy * uy + c,
                   ci * uy * uz - ux * s],
                  [ci * uz * ux - uy * s,
                   ci * uz * uy + ux * s,
                   ci * uz * uz + c],
                  ])

    # This is equivalent to
    # R = (np.eye(3) * np.cos(angle) +
    #      (1.0 - np.cos(angle)) * a[:3, np.newaxis].dot(a[np.newaxis, :3]) +
    #      cross_product_matrix(a[:3]) * np.sin(angle))

    return R
        
        
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


def rotate_image_3d_sitk(image, quaternion):
    image_sitk = sitk.GetImageFromArray(image.astype(np.float32))
    transform = sitk.VersorTransform(list(quaternion))
    image_center = np.array(image_sitk.GetSize()) / 2.0
    transform.SetCenter(image_center)
    image_rotated = sitk.Resample(image_sitk, transform, sitk.sitkLinear, 0.0, image_sitk.GetPixelID())
    return sitk.GetArrayFromImage(image_rotated).astype(image.dtype)


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
