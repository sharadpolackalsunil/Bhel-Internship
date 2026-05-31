"""
OpenCV Image Preprocessing Pipeline
======================================
Prepares CAPTCHA images for CNN inference.
Handles real-world CAPTCHA images from the MITS portal:
    - Convert to grayscale
    - Denoise with Gaussian blur
    - Binarize with Otsu's thresholding
    - Morphological operations (remove noise dots)
    - Resize to model input dimensions
    - Normalize to [-1, 1]
"""

import cv2
import numpy as np
import torch
from PIL import Image

try:
    from captcha_model.dataset import IMG_HEIGHT, IMG_WIDTH
except ImportError:
    from dataset import IMG_HEIGHT, IMG_WIDTH


def preprocess_captcha(image_input, return_debug=False):
    """
    Full preprocessing pipeline for a CAPTCHA image.

    Args:
        image_input: One of:
            - str: file path to image
            - bytes: raw image bytes
            - np.ndarray: OpenCV image (BGR)
            - PIL.Image: PIL image
        return_debug: If True, returns intermediate images for debugging.

    Returns:
        tensor: Preprocessed image tensor (1, 1, H, W) ready for model input.
        debug_images: (optional) dict of intermediate processing steps.
    """
    debug = {}

    # Step 0: Load image into numpy array (BGR)
    if isinstance(image_input, str):
        img = cv2.imread(image_input)
        if img is None:
            raise FileNotFoundError(f"Could not read image: {image_input}")
    elif isinstance(image_input, bytes):
        nparr = np.frombuffer(image_input, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    elif isinstance(image_input, Image.Image):
        img = cv2.cvtColor(np.array(image_input), cv2.COLOR_RGB2BGR)
    elif isinstance(image_input, np.ndarray):
        img = image_input.copy()
    else:
        raise TypeError(f"Unsupported image type: {type(image_input)}")

    if return_debug:
        debug['original'] = img.copy()

    # Step 1: Convert to grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    if return_debug:
        debug['grayscale'] = gray.copy()

    # Step 2: Gaussian blur to reduce noise
    blurred = cv2.GaussianBlur(gray, (3, 3), 0)
    if return_debug:
        debug['blurred'] = blurred.copy()

    # Step 3: Otsu's thresholding for binarization
    # This automatically finds the optimal threshold
    _, binary = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    if return_debug:
        debug['binary'] = binary.copy()

    # Step 4: Morphological operations to clean up noise
    # Remove small noise dots with opening (erosion + dilation)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
    cleaned = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel, iterations=1)

    # Fill small gaps in characters with closing (dilation + erosion)
    kernel2 = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
    cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_CLOSE, kernel2, iterations=1)
    if return_debug:
        debug['cleaned'] = cleaned.copy()

    # Step 5: Resize to model input dimensions
    resized = cv2.resize(cleaned, (IMG_WIDTH, IMG_HEIGHT),
                         interpolation=cv2.INTER_AREA)
    if return_debug:
        debug['resized'] = resized.copy()

    # Step 6: Normalize to [-1, 1] (matching training normalization)
    normalized = resized.astype(np.float32) / 255.0
    normalized = (normalized - 0.5) / 0.5  # Map [0,1] -> [-1,1]

    # Step 7: Convert to PyTorch tensor (1, 1, H, W)
    tensor = torch.from_numpy(normalized).unsqueeze(0).unsqueeze(0)

    if return_debug:
        return tensor, debug
    return tensor


def preprocess_for_tesseract(image_input):
    """
    Preprocess image specifically for pytesseract OCR fallback.
    Tesseract works best with clean, high-contrast, upscaled images.

    Args:
        image_input: File path, bytes, numpy array, or PIL Image.

    Returns:
        PIL.Image: Preprocessed image ready for pytesseract.
    """
    # Load into numpy
    if isinstance(image_input, str):
        img = cv2.imread(image_input)
    elif isinstance(image_input, bytes):
        nparr = np.frombuffer(image_input, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    elif isinstance(image_input, Image.Image):
        img = cv2.cvtColor(np.array(image_input), cv2.COLOR_RGB2BGR)
    elif isinstance(image_input, np.ndarray):
        img = image_input.copy()
    else:
        raise TypeError(f"Unsupported image type: {type(image_input)}")

    # Convert to grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Upscale 2x for better OCR accuracy
    h, w = gray.shape
    upscaled = cv2.resize(gray, (w * 2, h * 2), interpolation=cv2.INTER_CUBIC)

    # Sharpen
    kernel = np.array([[-1, -1, -1],
                       [-1,  9, -1],
                       [-1, -1, -1]])
    sharpened = cv2.filter2D(upscaled, -1, kernel)

    # Threshold
    _, binary = cv2.threshold(sharpened, 0, 255,
                              cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    # Invert if text is white on black (ensure black text on white background)
    # Check if more than 50% of pixels are dark
    if np.mean(binary) < 127:
        binary = cv2.bitwise_not(binary)

    # Remove noise
    kernel_morph = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
    cleaned = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel_morph)

    # Add white border (helps Tesseract)
    bordered = cv2.copyMakeBorder(cleaned, 10, 10, 10, 10,
                                   cv2.BORDER_CONSTANT, value=255)

    # Convert back to PIL for pytesseract
    return Image.fromarray(bordered)


def visualize_preprocessing(image_path, save_path=None):
    """
    Visualize all preprocessing steps for debugging.

    Args:
        image_path: Path to CAPTCHA image.
        save_path: Optional path to save the visualization.
    """
    import matplotlib.pyplot as plt

    tensor, debug = preprocess_captcha(image_path, return_debug=True)

    steps = list(debug.items())
    fig, axes = plt.subplots(1, len(steps) + 1, figsize=(3 * (len(steps) + 1), 3))

    for i, (name, img) in enumerate(steps):
        if len(img.shape) == 3:
            axes[i].imshow(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
        else:
            axes[i].imshow(img, cmap='gray')
        axes[i].set_title(name, fontsize=10)
        axes[i].axis('off')

    # Show final tensor
    final = tensor.squeeze().numpy()
    final_display = (final * 0.5 + 0.5)  # De-normalize for display
    axes[-1].imshow(final_display, cmap='gray')
    axes[-1].set_title('final_tensor', fontsize=10)
    axes[-1].axis('off')

    plt.tight_layout()
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"Saved preprocessing visualization to: {save_path}")
    else:
        plt.show()
    plt.close()


if __name__ == "__main__":
    print("Preprocessing pipeline ready.")
    print(f"Target size: {IMG_WIDTH}x{IMG_HEIGHT} pixels")
    print(f"Output: Tensor shape (1, 1, {IMG_HEIGHT}, {IMG_WIDTH})")
