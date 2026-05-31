"""
CAPTCHA CNN Model
==================
A multi-head Convolutional Neural Network for recognizing 5-character
alphanumeric CAPTCHAs from the MITS Gwalior result portal.

Architecture:
    Input:  Grayscale image (1 × 80 × 200)
    Feature Extractor:  4 Conv blocks (Conv → BN → ReLU → MaxPool)
    Classifier:  5 parallel FC heads, each predicting one character (36 classes)
    Output: 5 probability distributions over 36 characters
"""

import torch
import torch.nn as nn
import torch.nn.functional as F

from captcha_model.dataset import NUM_CLASSES, CAPTCHA_LENGTH, IMG_HEIGHT, IMG_WIDTH


class ConvBlock(nn.Module):
    """Convolution → BatchNorm → ReLU → MaxPool block."""

    def __init__(self, in_channels, out_channels, kernel_size=3, padding=1):
        super().__init__()
        self.conv = nn.Conv2d(in_channels, out_channels,
                              kernel_size=kernel_size, padding=padding)
        self.bn = nn.BatchNorm2d(out_channels)
        self.pool = nn.MaxPool2d(2, 2)

    def forward(self, x):
        x = self.conv(x)
        x = self.bn(x)
        x = F.relu(x, inplace=True)
        x = self.pool(x)
        return x


class CaptchaCNN(nn.Module):
    """
    Multi-head CNN for 5-character CAPTCHA recognition.

    Each head independently predicts one character position,
    allowing the model to learn position-specific features.

    Input:  (batch, 1, 80, 200)
    Output: list of 5 tensors, each (batch, 36)
    """

    def __init__(self, num_classes=NUM_CLASSES, captcha_length=CAPTCHA_LENGTH,
                 dropout_rate=0.3):
        super().__init__()

        self.captcha_length = captcha_length
        self.num_classes = num_classes

        # Feature extractor: 4 conv blocks
        # Input: (1, 80, 200) → after 4 pools of /2 each → (256, 5, 12)
        self.features = nn.Sequential(
            ConvBlock(1, 32),     # (32, 40, 100)
            ConvBlock(32, 64),    # (64, 20, 50)
            ConvBlock(64, 128),   # (128, 10, 25)
            ConvBlock(128, 256),  # (256, 5, 12)
        )

        # Calculate flattened feature size
        # After 4 MaxPool(2,2): 80→40→20→10→5 (height), 200→100→50→25→12 (width)
        self._flat_size = 256 * 5 * 12  # = 15,360

        # Shared fully-connected layer
        self.shared_fc = nn.Sequential(
            nn.Linear(self._flat_size, 1024),
            nn.ReLU(inplace=True),
            nn.Dropout(dropout_rate),
            nn.Linear(1024, 512),
            nn.ReLU(inplace=True),
            nn.Dropout(dropout_rate),
        )

        # 5 independent classification heads — one per character position
        self.heads = nn.ModuleList([
            nn.Linear(512, num_classes)
            for _ in range(captcha_length)
        ])

    def forward(self, x):
        """
        Args:
            x: Input tensor of shape (batch, 1, 80, 200)

        Returns:
            List of 5 tensors, each of shape (batch, 36) — raw logits
        """
        # Extract features
        x = self.features(x)

        # Flatten
        x = x.view(x.size(0), -1)

        # Shared FC layers
        x = self.shared_fc(x)

        # Each head predicts one character
        outputs = [head(x) for head in self.heads]

        return outputs

    def predict(self, x):
        """
        Predict CAPTCHA text from image tensor.

        Args:
            x: Input tensor of shape (batch, 1, 80, 200)

        Returns:
            predictions: Tensor of shape (batch, 5) — predicted char indices
            confidences: Tensor of shape (batch, 5) — confidence per character
        """
        self.eval()
        with torch.no_grad():
            outputs = self.forward(x)

            predictions = []
            confidences = []
            for out in outputs:
                probs = F.softmax(out, dim=1)
                conf, pred = probs.max(dim=1)
                predictions.append(pred)
                confidences.append(conf)

            predictions = torch.stack(predictions, dim=1)  # (batch, 5)
            confidences = torch.stack(confidences, dim=1)   # (batch, 5)

        return predictions, confidences


class CaptchaCRNN(nn.Module):
    """
    Alternative CRNN architecture using LSTM for sequence modeling.
    More robust for CAPTCHAs with variable spacing or overlapping characters.

    Uses CNN feature extraction + bidirectional LSTM + CTC-compatible output.
    """

    def __init__(self, num_classes=NUM_CLASSES, hidden_size=256, num_layers=2):
        super().__init__()

        self.num_classes = num_classes

        # CNN feature extractor (same as CaptchaCNN but fewer pools on width)
        self.features = nn.Sequential(
            ConvBlock(1, 32),     # (32, 40, 100)
            ConvBlock(32, 64),    # (64, 20, 50)
            ConvBlock(64, 128),   # (128, 10, 25)
            ConvBlock(128, 256),  # (256, 5, 12)
        )

        # Map CNN features to sequence: collapse height, keep width as time steps
        # After conv: (batch, 256, 5, 12) → reshape to (batch, 256*5, 12) → (batch, 12, 1280)
        self.rnn_input_size = 256 * 5  # 1280

        # Bidirectional LSTM
        self.rnn = nn.LSTM(
            input_size=self.rnn_input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
            bidirectional=True,
            dropout=0.3 if num_layers > 1 else 0.0,
        )

        # Output projection: hidden_size*2 (bidirectional) → num_classes
        self.fc = nn.Linear(hidden_size * 2, num_classes)

    def forward(self, x):
        """
        Args:
            x: Input tensor of shape (batch, 1, 80, 200)

        Returns:
            output: Tensor of shape (batch, time_steps, num_classes) — logits
        """
        batch_size = x.size(0)

        # CNN features
        x = self.features(x)  # (batch, 256, 5, 12)

        # Reshape: merge channel and height, use width as time
        x = x.permute(0, 3, 1, 2)   # (batch, 12, 256, 5)
        x = x.reshape(batch_size, 12, -1)  # (batch, 12, 1280)

        # RNN
        x, _ = self.rnn(x)  # (batch, 12, hidden*2)

        # Project to class scores
        x = self.fc(x)  # (batch, 12, num_classes)

        return x


def get_model(model_type='cnn', **kwargs):
    """
    Factory function to create the appropriate model.

    Args:
        model_type: 'cnn' for multi-head CNN, 'crnn' for CRNN with LSTM.
        **kwargs: Additional arguments passed to the model constructor.

    Returns:
        nn.Module: The initialized model.
    """
    if model_type == 'cnn':
        return CaptchaCNN(**kwargs)
    elif model_type == 'crnn':
        return CaptchaCRNN(**kwargs)
    else:
        raise ValueError(f"Unknown model type: {model_type}. Use 'cnn' or 'crnn'.")


def count_parameters(model):
    """Count the number of trainable parameters in a model."""
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


if __name__ == "__main__":
    print("=" * 50)
    print("CAPTCHA CNN Model — Architecture Summary")
    print("=" * 50)

    # Create model and test with dummy input
    model = CaptchaCNN()
    dummy_input = torch.randn(2, 1, IMG_HEIGHT, IMG_WIDTH)

    outputs = model(dummy_input)
    print(f"\nModel type: CaptchaCNN (Multi-Head)")
    print(f"Input shape:  {dummy_input.shape}")
    print(f"Output heads: {len(outputs)}")
    print(f"Each head:    {outputs[0].shape}")
    print(f"Parameters:   {count_parameters(model):,}")

    # Test prediction
    preds, confs = model.predict(dummy_input)
    print(f"\nPredictions shape: {preds.shape}")
    print(f"Confidences shape: {confs.shape}")

    # Also test CRNN
    crnn = CaptchaCRNN()
    crnn_out = crnn(dummy_input)
    print(f"\nCRNN output shape: {crnn_out.shape}")
    print(f"CRNN parameters:   {count_parameters(crnn):,}")
