import logging
from typing import Union
from PIL import Image
import numpy as np

logger = logging.getLogger("app.rag.preprocessing")

try:
    import cv2
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False


def deskew_image(gray_img: np.ndarray, max_angle: float = 45.0) -> np.ndarray:
    """
    Detects skew angle from text contours and rotates the image back to horizontal.
    Only corrects if detected skew is between 0.5 and max_angle degrees.
    """
    if not HAS_CV2:
        return gray_img

    try:
        # Invert colors: text becomes white, background black
        thresh = cv2.threshold(gray_img, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)[1]

        # Find coordinates of all text pixels
        coords = np.column_stack(np.where(thresh > 0))
        if coords.shape[0] < 50:
            return gray_img

        # Compute minimum bounding rectangle
        rect = cv2.minAreaRect(coords)
        angle = rect[-1]

        # OpenCV minAreaRect returns angle in [-90, 0)
        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle

        # Only deskew if non-trivial angle
        if 0.5 <= abs(angle) <= max_angle:
            (h, w) = gray_img.shape[:2]
            center = (w // 2, h // 2)
            M = cv2.getRotationMatrix2D(center, angle, 1.0)
            rotated = cv2.warpAffine(
                gray_img, M, (w, h),
                flags=cv2.INTER_CUBIC,
                borderMode=cv2.BORDER_REPLICATE
            )
            return rotated

        return gray_img

    except Exception as e:
        logger.debug(f"Deskew skipped due to error: {e}")
        return gray_img


def enhance_contrast(gray_img: np.ndarray) -> np.ndarray:
    """
    Enhances contrast using Contrast Limited Adaptive Histogram Equalization (CLAHE).
    Provides balanced contrast enhancement without over-amplifying noise.
    """
    if not HAS_CV2:
        return gray_img

    try:
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        return clahe.apply(gray_img)
    except Exception as e:
        logger.debug(f"Contrast enhancement failed: {e}")
        return gray_img


def denoise_image(gray_img: np.ndarray) -> np.ndarray:
    """Applies fast median blur to reduce salt-and-pepper scan noise."""
    if not HAS_CV2:
        return gray_img

    try:
        return cv2.medianBlur(gray_img, 3)
    except Exception as e:
        logger.debug(f"Denoise failed: {e}")
        return gray_img


def preprocess_image(
    image: Union[Image.Image, np.ndarray],
    enhance: bool = True,
    denoise: bool = True,
    deskew: bool = True
) -> np.ndarray:
    """
    Full image preprocessing pipeline for scanned document pages before OCR.
    1. Converts image to numpy grayscale.
    2. Applies contrast enhancement (CLAHE).
    3. Denoises subtle scanning artifacts.
    4. Deskews rotation.
    Returns uint8 numpy array ready for OCR engines.
    """
    try:
        # 1. Convert to numpy array
        if isinstance(image, Image.Image):
            # Convert to grayscale first if color
            if image.mode != "L":
                gray_pil = image.convert("L")
            else:
                gray_pil = image
            arr = np.array(gray_pil, dtype=np.uint8)
        elif isinstance(image, np.ndarray):
            if len(image.shape) == 3 and image.shape[2] == 3:
                if HAS_CV2:
                    arr = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
                else:
                    arr = np.mean(image, axis=2).astype(np.uint8)
            else:
                arr = image.copy()
        else:
            raise ValueError(f"Unsupported image type: {type(image)}")

        # 2. Denoise
        if denoise:
            arr = denoise_image(arr)

        # 3. Enhance Contrast
        if enhance:
            arr = enhance_contrast(arr)

        # 4. Deskew
        if deskew:
            arr = deskew_image(arr)

        return arr

    except Exception as exc:
        logger.warning(f"Image preprocessing encountered an error, falling back to raw image: {exc}")
        if isinstance(image, Image.Image):
            return np.array(image.convert("L"))
        return image
