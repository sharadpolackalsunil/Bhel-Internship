"""
Synthetic CAPTCHA Dataset Generator
====================================
Generates training data that mimics the MITS Gwalior portal CAPTCHA style:
- 5 uppercase alphanumeric characters (A-Z, 0-9)
- Bold black text on white/light background
- Slight noise and distortion for realism

Designed for PyTorch DataLoader integration and Google Colab compatibility.
"""

import os
import random
import string
from io import BytesIO

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import torch
from torch.utils.data import Dataset
import torchvision.transforms as transforms

# Character set: uppercase letters + digits (36 classes)
CHARSET = string.ascii_uppercase + string.digits  # 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
NUM_CLASSES = len(CHARSET)  # 36
CAPTCHA_LENGTH = 5
IMG_WIDTH = 200
IMG_HEIGHT = 80

# Mapping: character -> index and index -> character
CHAR_TO_IDX = {ch: idx for idx, ch in enumerate(CHARSET)}
IDX_TO_CHAR = {idx: ch for idx, ch in enumerate(CHARSET)}


def get_font(size=40):
    """
    Get a bold font. Tries system fonts first, falls back to default.
    Works on both Windows (local) and Linux (Colab).
    """
    font_paths = [
        # Windows fonts
        "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/impact.ttf",
        "C:/Windows/Fonts/consolab.ttf",
        # Linux / Colab fonts
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
        "/usr/share/fonts/truetype/ubuntu/Ubuntu-Bold.ttf",
    ]
    for path in font_paths:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    # Fallback to default bitmap font
    return ImageFont.load_default()


def generate_captcha_image(text=None, add_noise=True, add_lines=False):
    """
    Generate a single CAPTCHA image mimicking MITS Gwalior portal style.

    Args:
        text: Optional specific text. If None, generates random 5-char string.
        add_noise: Whether to add salt-and-pepper noise.
        add_lines: Whether to add distortion lines.

    Returns:
        (PIL.Image, str): The CAPTCHA image and its text label.
    """
    if text is None:
        text = ''.join(random.choices(CHARSET, k=CAPTCHA_LENGTH))

    # Create white background image
    img = Image.new('RGB', (IMG_WIDTH, IMG_HEIGHT), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)

    # Get a bold font with slight size variation
    font_size = random.randint(36, 44)
    font = get_font(font_size)

    # Calculate text positioning - spread characters with slight random offsets
    # This mimics the portal's spaced-out character style
    total_char_width = 0
    char_widths = []
    for ch in text:
        bbox = font.getbbox(ch)
        w = bbox[2] - bbox[0]
        char_widths.append(w)
        total_char_width += w

    spacing = random.randint(2, 6)
    total_width = total_char_width + spacing * (CAPTCHA_LENGTH - 1)
    x_start = (IMG_WIDTH - total_width) // 2

    x_cursor = x_start
    for i, ch in enumerate(text):
        # Slight vertical jitter per character
        y_offset = random.randint(-4, 4)
        y_pos = (IMG_HEIGHT - font_size) // 2 + y_offset

        # Character color: mostly black, slight variation
        r = random.randint(0, 30)
        g = random.randint(0, 30)
        b = random.randint(0, 30)

        draw.text((x_cursor, y_pos), ch, fill=(r, g, b), font=font)
        x_cursor += char_widths[i] + spacing

    # Add noise to simulate the portal's CAPTCHA imperfections
    if add_noise:
        img_array = np.array(img)

        # Salt-and-pepper noise (sparse)
        num_noise_pixels = random.randint(50, 200)
        for _ in range(num_noise_pixels):
            x = random.randint(0, IMG_WIDTH - 1)
            y = random.randint(0, IMG_HEIGHT - 1)
            if random.random() > 0.5:
                img_array[y, x] = [0, 0, 0]  # Black dot
            else:
                img_array[y, x] = [200, 200, 200]  # Gray dot

        img = Image.fromarray(img_array)

    # Optional: add crossing lines (light distortion)
    if add_lines:
        draw = ImageDraw.Draw(img)
        for _ in range(random.randint(1, 3)):
            x1 = random.randint(0, IMG_WIDTH)
            y1 = random.randint(0, IMG_HEIGHT)
            x2 = random.randint(0, IMG_WIDTH)
            y2 = random.randint(0, IMG_HEIGHT)
            gray = random.randint(100, 180)
            draw.line([(x1, y1), (x2, y2)], fill=(gray, gray, gray), width=1)

    # Slight blur for realism
    if random.random() < 0.3:
        img = img.filter(ImageFilter.GaussianBlur(radius=0.5))

    return img, text


class SyntheticCaptchaDataset(Dataset):
    """
    PyTorch Dataset that generates synthetic CAPTCHA images on-the-fly.

    Each sample returns:
        - image: Tensor of shape (1, IMG_HEIGHT, IMG_WIDTH) — grayscale, normalized
        - label: Tensor of shape (CAPTCHA_LENGTH,) — character indices
    """

    def __init__(self, num_samples=50000, add_noise=True, add_lines=False,
                 transform=None):
        """
        Args:
            num_samples: Number of CAPTCHA images in the dataset.
            add_noise: Add salt-and-pepper noise.
            add_lines: Add distortion lines.
            transform: Optional torchvision transform for augmentation.
        """
        self.num_samples = num_samples
        self.add_noise = add_noise
        self.add_lines = add_lines

        # Default transform: grayscale → tensor → normalize
        if transform is None:
            self.transform = transforms.Compose([
                transforms.Grayscale(num_output_channels=1),
                transforms.Resize((IMG_HEIGHT, IMG_WIDTH)),
                transforms.ToTensor(),  # [0, 255] -> [0.0, 1.0]
                transforms.Normalize(mean=[0.5], std=[0.5]),  # -> [-1.0, 1.0]
            ])
        else:
            self.transform = transform

        # Pre-generate all texts for reproducibility
        self.texts = [
            ''.join(random.choices(CHARSET, k=CAPTCHA_LENGTH))
            for _ in range(num_samples)
        ]

    def __len__(self):
        return self.num_samples

    def __getitem__(self, idx):
        text = self.texts[idx]
        img, _ = generate_captcha_image(
            text=text,
            add_noise=self.add_noise,
            add_lines=self.add_lines
        )

        # Apply transforms
        img_tensor = self.transform(img)

        # Encode label: each character -> index
        label = torch.tensor(
            [CHAR_TO_IDX[ch] for ch in text],
            dtype=torch.long
        )

        return img_tensor, label

    @staticmethod
    def decode_prediction(indices):
        """Convert list of character indices back to string."""
        return ''.join([IDX_TO_CHAR[idx] for idx in indices])


def generate_dataset_to_disk(output_dir, num_images=1000, add_noise=True):
    """
    Generate CAPTCHA images and save to disk with labels.
    Useful for creating a fixed dataset for Colab upload.

    Directory structure:
        output_dir/
        ├── images/
        │   ├── 00000_ABCD1.png
        │   ├── 00001_XY2Z3.png
        │   └── ...
        └── labels.csv

    Args:
        output_dir: Directory to save images.
        num_images: Number of images to generate.
        add_noise: Whether to add noise.
    """
    import csv

    img_dir = os.path.join(output_dir, "images")
    os.makedirs(img_dir, exist_ok=True)

    labels_path = os.path.join(output_dir, "labels.csv")
    with open(labels_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["filename", "label"])

        for i in range(num_images):
            img, text = generate_captcha_image(add_noise=add_noise)
            filename = f"{i:05d}_{text}.png"
            img.save(os.path.join(img_dir, filename))
            writer.writerow([filename, text])

            if (i + 1) % 100 == 0:
                print(f"Generated {i + 1}/{num_images} images")

    print(f"\n✅ Dataset saved to: {output_dir}")
    print(f"   Images: {img_dir}")
    print(f"   Labels: {labels_path}")


class DiskCaptchaDataset(Dataset):
    """
    PyTorch Dataset that loads CAPTCHA images from disk.
    Useful for loading a pre-generated or real-world dataset.
    Expects filenames in format: XXXXX_LABEL.png
    """

    def __init__(self, image_dir, transform=None):
        self.image_dir = image_dir
        self.image_files = sorted([
            f for f in os.listdir(image_dir)
            if f.endswith(('.png', '.jpg', '.jpeg'))
        ])

        if transform is None:
            self.transform = transforms.Compose([
                transforms.Grayscale(num_output_channels=1),
                transforms.Resize((IMG_HEIGHT, IMG_WIDTH)),
                transforms.ToTensor(),
                transforms.Normalize(mean=[0.5], std=[0.5]),
            ])
        else:
            self.transform = transform

    def __len__(self):
        return len(self.image_files)

    def __getitem__(self, idx):
        filename = self.image_files[idx]
        img_path = os.path.join(self.image_dir, filename)

        # Extract label from filename: "00000_ABCD1.png" -> "ABCD1"
        label_text = filename.rsplit('.', 1)[0].split('_', 1)[1]

        img = Image.open(img_path).convert('RGB')
        img_tensor = self.transform(img)

        label = torch.tensor(
            [CHAR_TO_IDX[ch] for ch in label_text],
            dtype=torch.long
        )

        return img_tensor, label


if __name__ == "__main__":
    # Demo: generate sample images
    print("=" * 50)
    print("CAPTCHA Dataset Generator — Demo")
    print("=" * 50)

    # Generate and display info about a few samples
    for i in range(5):
        img, text = generate_captcha_image(add_noise=True)
        print(f"  Sample {i+1}: text='{text}', size={img.size}")

    # Generate a small disk dataset for testing
    demo_dir = os.path.join(os.path.dirname(__file__), "..", "data", "demo_captchas")
    generate_dataset_to_disk(demo_dir, num_images=20)
    print("\nDone! Check the data/demo_captchas/ directory.")
