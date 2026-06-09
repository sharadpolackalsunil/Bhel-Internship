"""
CAPTCHA Prediction / Inference Module
========================================
Loads the Microsoft TrOCR model to provide a unified interface
for solving CAPTCHA images.

Features:
    - Primary: TrOCR-based prediction
    - Auto-strips all whitespace from the prediction
    - Handles file paths, bytes, and PIL images
"""

import os
import torch
from PIL import Image
# pyrefly: ignore [missing-import]
from transformers import TrOCRProcessor, VisionEncoderDecoderModel

class CaptchaSolver:
    """
    Unified CAPTCHA solver with TrOCR.

    Usage:
        solver = CaptchaSolver()
        text, confidence = solver.solve('captcha.png')
        print(f"Predicted: {text} (confidence: {confidence:.2f})")
    """

    def __init__(self, model_path=None, confidence_threshold=0.65, device=None):
        """
        Args:
            model_path: Path to trained model directory.
            confidence_threshold: Kept for compatibility.
            device: torch device. Auto-detected if None.
        """
        if device is None:
            if torch.cuda.is_available():
                self.device = torch.device('cuda')
            else:
                self.device = torch.device('cpu')
        else:
            self.device = device

        if model_path is None:
            # Default to local trocr_model
            model_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'trocr_model')

        if os.path.exists(model_path):
            print(f" Loading TrOCR model from: {model_path}")
            self.processor = TrOCRProcessor.from_pretrained(model_path)
            self.model = VisionEncoderDecoderModel.from_pretrained(model_path)
        else:
            print(f"  Local model not found at {model_path}. Loading from huggingface hub...")
            self.processor = TrOCRProcessor.from_pretrained("microsoft/trocr-base-printed")
            self.model = VisionEncoderDecoderModel.from_pretrained("microsoft/trocr-base-printed")

        self.model = self.model.to(self.device)
        self.model.eval()

    def solve(self, image_input, use_fallback=False):
        """
        Solve a CAPTCHA image.

        Args:
            image_input: File path (str), raw bytes, numpy array, or PIL Image.
            use_fallback: Kept for compatibility, not used.

        Returns:
            (predicted_text, confidence): Tuple of prediction string and
                                          average confidence score (fixed 0.99 for TrOCR).
        """
        import io
        if isinstance(image_input, str):
            image = Image.open(image_input).convert("RGB")
        elif isinstance(image_input, bytes):
            image = Image.open(io.BytesIO(image_input)).convert("RGB")
        elif isinstance(image_input, Image.Image):
            image = image_input.convert("RGB")
        else:
            # For numpy arrays (if still passed from old preprocessing)
            image = Image.fromarray(image_input).convert("RGB")

        pixel_values = self.processor(image, return_tensors="pt").pixel_values.to(self.device)

        with torch.no_grad():
            generated_ids = self.model.generate(pixel_values)

        extracted_text = self.processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
        
        # Ensure no spaces and no periods
        cleaned_text = "".join(extracted_text.split()).replace('.', '')

        return cleaned_text, 0.99

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
    """
    return CaptchaSolver(model_path=model_path)


if __name__ == "__main__":
    import sys

    print("=" * 50)
    print("CAPTCHA Solver  Test")
    print("=" * 50)

    solver = load_solver()

    if len(sys.argv) > 1:
        image_path = sys.argv[1]
        text, confidence = solver.solve(image_path)
        print(f"\nImage:      {image_path}")
        print(f"Prediction: {text}")
        print(f"Confidence: {confidence:.4f}")
    else:
        print("\nUsage: python -m captcha_model.predict <image_path>")
        print("  or:  from captcha_model.predict import CaptchaSolver")
