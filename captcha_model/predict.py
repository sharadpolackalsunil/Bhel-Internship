"""
CAPTCHA Prediction / Inference Module
========================================
Loads a trained CaptchaCNN model and provides a unified interface
for solving CAPTCHA images.

Features:
    - Primary: CNN-based prediction with confidence scoring
    - Fallback: pytesseract OCR when CNN confidence is low
    - Handles file paths, bytes, numpy arrays, and PIL images
"""

import os
import torch
import numpy as np
from PIL import Image

try:
    from captcha_model.model import CaptchaCNN
    from captcha_model.preprocess import preprocess_captcha, preprocess_for_tesseract
    from captcha_model.dataset import (
        NUM_CLASSES, CAPTCHA_LENGTH, IDX_TO_CHAR, CHARSET, IMG_HEIGHT, IMG_WIDTH
    )
except ImportError:
    from model import CaptchaCNN
    from preprocess import preprocess_captcha, preprocess_for_tesseract
    from dataset import (
        NUM_CLASSES, CAPTCHA_LENGTH, IDX_TO_CHAR, CHARSET, IMG_HEIGHT, IMG_WIDTH
    )


class CaptchaSolver:
    """
    Unified CAPTCHA solver with CNN primary + OCR fallback.

    Usage:
        solver = CaptchaSolver('saved_models/captcha_cnn.pth')
        text, confidence = solver.solve('captcha.png')
        print(f"Predicted: {text} (confidence: {confidence:.2f})")
    """

    def __init__(self, model_path=None, confidence_threshold=0.7, device=None):
        """
        Args:
            model_path: Path to trained model checkpoint (.pth).
                        If None, uses only the OCR fallback.
            confidence_threshold: Minimum per-character confidence to trust CNN.
                                  Below this, falls back to pytesseract.
            device: torch device. Auto-detected if None.
        """
        self.confidence_threshold = confidence_threshold
        self.model = None
        self.device = device

        if device is None:
            if torch.cuda.is_available():
                self.device = torch.device('cuda')
            else:
                self.device = torch.device('cpu')

        # Load CNN model if path provided
        if model_path and os.path.exists(model_path):
            self._load_model(model_path)
            print(f"✅ CNN model loaded from: {model_path}")
        else:
            print("⚠️  No CNN model loaded. Using OCR fallback only.")

        # Check pytesseract availability
        self.tesseract_available = False
        try:
            import pytesseract
            self.tesseract_available = True
        except ImportError:
            print("ℹ️  pytesseract not installed. OCR fallback disabled.")

    def _load_model(self, model_path):
        """Load trained model from checkpoint."""
        checkpoint = torch.load(model_path, map_location=self.device,
                                weights_only=False)

        # Get model config from checkpoint
        config = checkpoint.get('config', {})
        num_classes = config.get('num_classes', NUM_CLASSES)
        captcha_length = config.get('captcha_length', CAPTCHA_LENGTH)

        self.model = CaptchaCNN(
            num_classes=num_classes,
            captcha_length=captcha_length
        )
        self.model.load_state_dict(checkpoint['model_state_dict'])
        self.model = self.model.to(self.device)
        self.model.eval()

    def solve(self, image_input, use_fallback=True):
        """
        Solve a CAPTCHA image.

        Args:
            image_input: File path (str), raw bytes, numpy array, or PIL Image.
            use_fallback: Whether to use pytesseract if CNN confidence is low.

        Returns:
            (predicted_text, confidence): Tuple of prediction string and
                                          average confidence score (0.0 to 1.0).
        """
        # Try CNN first
        if self.model is not None:
            text, confidence = self._predict_cnn(image_input)

            # Check if confidence is acceptable
            if confidence >= self.confidence_threshold:
                return text, confidence
            else:
                print(f"  ⚠️  CNN confidence low ({confidence:.3f}). ", end="")
                if use_fallback and self.tesseract_available:
                    print("Trying OCR fallback...")
                    ocr_text = self._predict_ocr(image_input)
                    if ocr_text and len(ocr_text) == CAPTCHA_LENGTH:
                        return ocr_text, 0.5  # Fixed confidence for OCR
                    else:
                        print(f"  ⚠️  OCR returned '{ocr_text}'. Using CNN result.")
                        return text, confidence
                else:
                    return text, confidence

        # CNN not available, try OCR only
        if self.tesseract_available:
            ocr_text = self._predict_ocr(image_input)
            return ocr_text or "?????", 0.3

        raise RuntimeError("No prediction method available. "
                           "Load a CNN model or install pytesseract.")

    def _predict_cnn(self, image_input):
        """
        Predict using the CNN model.

        Returns:
            (text, avg_confidence): Prediction and average confidence.
        """
        # Preprocess
        tensor = preprocess_captcha(image_input)
        tensor = tensor.to(self.device)

        # Predict
        self.model.eval()
        with torch.no_grad():
            outputs = self.model(tensor)

            chars = []
            confidences = []
            for out in outputs:
                probs = torch.softmax(out, dim=1)
                conf, pred = probs.max(dim=1)
                chars.append(IDX_TO_CHAR[pred.item()])
                confidences.append(conf.item())

        text = ''.join(chars)
        avg_confidence = np.mean(confidences)

        return text, avg_confidence

    def _predict_ocr(self, image_input):
        """
        Predict using pytesseract OCR (fallback).

        Returns:
            Predicted text string (may be None if OCR fails).
        """
        try:
            import pytesseract

            # Preprocess specifically for tesseract
            processed_img = preprocess_for_tesseract(image_input)

            # Configure tesseract for alphanumeric uppercase only
            custom_config = (
                '--psm 7 '  # Single text line
                '-c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
            )

            text = pytesseract.image_to_string(
                processed_img, config=custom_config
            ).strip()

            # Clean up: remove spaces, ensure uppercase
            text = text.replace(' ', '').upper()

            # Filter to only valid characters
            text = ''.join(ch for ch in text if ch in CHARSET)

            return text if text else None

        except Exception as e:
            print(f"  ⚠️  OCR error: {e}")
            return None

    def solve_batch(self, image_inputs):
        """
        Solve multiple CAPTCHA images.

        Args:
            image_inputs: List of image inputs (paths, bytes, etc.)

        Returns:
            List of (text, confidence) tuples.
        """
        results = []
        for img in image_inputs:
            results.append(self.solve(img))
        return results


def load_solver(model_path=None):
    """
    Convenience function to create a CaptchaSolver.

    Args:
        model_path: Path to trained model. If None, searches default locations.

    Returns:
        CaptchaSolver instance.
    """
    if model_path is None:
        # Search common locations
        search_paths = [
            os.path.join(os.path.dirname(__file__), 'saved_models', 'captcha_cnn.pth'),
            os.path.join(os.getcwd(), 'captcha_model', 'saved_models', 'captcha_cnn.pth'),
            os.path.join(os.getcwd(), 'saved_models', 'captcha_cnn.pth'),
        ]
        for path in search_paths:
            if os.path.exists(path):
                model_path = path
                break

    return CaptchaSolver(model_path=model_path)


if __name__ == "__main__":
    import sys

    print("=" * 50)
    print("CAPTCHA Solver — Test")
    print("=" * 50)

    solver = load_solver()

    if len(sys.argv) > 1:
        # Solve image from command line argument
        image_path = sys.argv[1]
        text, confidence = solver.solve(image_path)
        print(f"\nImage:      {image_path}")
        print(f"Prediction: {text}")
        print(f"Confidence: {confidence:.4f}")
    else:
        print("\nUsage: python -m captcha_model.predict <image_path>")
        print("  or:  from captcha_model.predict import CaptchaSolver")
