"""
CAPTCHA CNN Training Script
=============================
Trains the CaptchaCNN model on synthetic CAPTCHA data.
Designed to run both locally and on Google Colab.

Usage:
    Local:  python -m captcha_model.train
    Colab:  See train_colab.ipynb

Features:
    - Automatic GPU detection (CUDA / MPS / CPU)
    - Training + validation with metrics logging
    - Early stopping with patience
    - Learning rate scheduling
    - Model checkpoint saving
    - Training curves visualization
"""

import os
import sys
import time
import json
import argparse

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, random_split
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend for server/Colab
import matplotlib.pyplot as plt

# Handle imports for both direct run and module run
try:
    from captcha_model.dataset import (
        SyntheticCaptchaDataset, CAPTCHA_LENGTH, NUM_CLASSES,
        IMG_HEIGHT, IMG_WIDTH, IDX_TO_CHAR
    )
    from captcha_model.model import CaptchaCNN, count_parameters
except ImportError:
    from dataset import (
        SyntheticCaptchaDataset, CAPTCHA_LENGTH, NUM_CLASSES,
        IMG_HEIGHT, IMG_WIDTH, IDX_TO_CHAR
    )
    from model import CaptchaCNN, count_parameters


def get_device():
    """Detect the best available device."""
    if torch.cuda.is_available():
        device = torch.device('cuda')
        print(f"🚀 Using GPU: {torch.cuda.get_device_name(0)}")
    elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
        device = torch.device('mps')
        print("🍎 Using Apple MPS")
    else:
        device = torch.device('cpu')
        print("💻 Using CPU")
    return device


def compute_accuracy(outputs, labels):
    """
    Compute per-character and full-sequence accuracy.

    Args:
        outputs: List of 5 tensors, each (batch, 36)
        labels:  Tensor of shape (batch, 5)

    Returns:
        char_acc: Per-character accuracy (0.0 to 1.0)
        seq_acc:  Full-sequence accuracy (0.0 to 1.0)
    """
    batch_size = labels.size(0)
    correct_chars = 0
    total_chars = 0
    correct_sequences = 0

    # Stack predictions: (5, batch) -> compare with labels
    preds = []
    for i, out in enumerate(outputs):
        _, pred = out.max(dim=1)  # (batch,)
        preds.append(pred)
        correct_chars += (pred == labels[:, i]).sum().item()
        total_chars += batch_size

    # Full sequence accuracy
    preds = torch.stack(preds, dim=1)  # (batch, 5)
    correct_sequences = (preds == labels).all(dim=1).sum().item()

    char_acc = correct_chars / total_chars
    seq_acc = correct_sequences / batch_size

    return char_acc, seq_acc


def train_one_epoch(model, dataloader, criterion, optimizer, device):
    """Train for one epoch."""
    model.train()
    running_loss = 0.0
    total_char_acc = 0.0
    total_seq_acc = 0.0
    num_batches = 0

    for images, labels in dataloader:
        images = images.to(device)
        labels = labels.to(device)

        optimizer.zero_grad()

        outputs = model(images)  # List of 5 tensors

        # Sum of cross-entropy losses for each character position
        loss = sum(
            criterion(outputs[i], labels[:, i])
            for i in range(CAPTCHA_LENGTH)
        )

        loss.backward()
        optimizer.step()

        running_loss += loss.item()
        char_acc, seq_acc = compute_accuracy(outputs, labels)
        total_char_acc += char_acc
        total_seq_acc += seq_acc
        num_batches += 1

    avg_loss = running_loss / num_batches
    avg_char_acc = total_char_acc / num_batches
    avg_seq_acc = total_seq_acc / num_batches

    return avg_loss, avg_char_acc, avg_seq_acc


def validate(model, dataloader, criterion, device):
    """Validate the model."""
    model.eval()
    running_loss = 0.0
    total_char_acc = 0.0
    total_seq_acc = 0.0
    num_batches = 0

    with torch.no_grad():
        for images, labels in dataloader:
            images = images.to(device)
            labels = labels.to(device)

            outputs = model(images)

            loss = sum(
                criterion(outputs[i], labels[:, i])
                for i in range(CAPTCHA_LENGTH)
            )

            running_loss += loss.item()
            char_acc, seq_acc = compute_accuracy(outputs, labels)
            total_char_acc += char_acc
            total_seq_acc += seq_acc
            num_batches += 1

    avg_loss = running_loss / num_batches
    avg_char_acc = total_char_acc / num_batches
    avg_seq_acc = total_seq_acc / num_batches

    return avg_loss, avg_char_acc, avg_seq_acc


def plot_training_curves(history, save_path):
    """Plot and save training curves."""
    fig, axes = plt.subplots(1, 3, figsize=(18, 5))

    epochs = range(1, len(history['train_loss']) + 1)

    # Loss
    axes[0].plot(epochs, history['train_loss'], 'b-', label='Train Loss')
    axes[0].plot(epochs, history['val_loss'], 'r-', label='Val Loss')
    axes[0].set_title('Loss', fontsize=14, fontweight='bold')
    axes[0].set_xlabel('Epoch')
    axes[0].set_ylabel('Loss')
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)

    # Character Accuracy
    axes[1].plot(epochs, history['train_char_acc'], 'b-', label='Train')
    axes[1].plot(epochs, history['val_char_acc'], 'r-', label='Validation')
    axes[1].set_title('Per-Character Accuracy', fontsize=14, fontweight='bold')
    axes[1].set_xlabel('Epoch')
    axes[1].set_ylabel('Accuracy')
    axes[1].legend()
    axes[1].grid(True, alpha=0.3)

    # Sequence Accuracy
    axes[2].plot(epochs, history['train_seq_acc'], 'b-', label='Train')
    axes[2].plot(epochs, history['val_seq_acc'], 'r-', label='Validation')
    axes[2].set_title('Full-Sequence Accuracy', fontsize=14, fontweight='bold')
    axes[2].set_xlabel('Epoch')
    axes[2].set_ylabel('Accuracy')
    axes[2].legend()
    axes[2].grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"📊 Training curves saved to: {save_path}")


def train(config=None):
    """
    Main training function.

    Args:
        config: Dict with training hyperparameters. If None, uses defaults.
    """
    # Default config
    if config is None:
        config = {}

    num_train = config.get('num_train', 50000)
    num_val = config.get('num_val', 5000)
    batch_size = config.get('batch_size', 64)
    num_epochs = config.get('num_epochs', 30)
    learning_rate = config.get('learning_rate', 1e-3)
    weight_decay = config.get('weight_decay', 1e-5)
    patience = config.get('patience', 7)
    save_dir = config.get('save_dir', os.path.join(
        os.path.dirname(os.path.abspath(__file__)), 'saved_models'
    ))

    os.makedirs(save_dir, exist_ok=True)
    device = get_device()

    print("\n" + "=" * 60)
    print("CAPTCHA CNN — Training Configuration")
    print("=" * 60)
    print(f"  Training samples:   {num_train:,}")
    print(f"  Validation samples: {num_val:,}")
    print(f"  Batch size:         {batch_size}")
    print(f"  Epochs:             {num_epochs}")
    print(f"  Learning rate:      {learning_rate}")
    print(f"  Weight decay:       {weight_decay}")
    print(f"  Early stopping:     patience={patience}")
    print(f"  Save directory:     {save_dir}")
    print(f"  Device:             {device}")
    print("=" * 60)

    # Create datasets
    print("\n📦 Generating synthetic datasets...")
    train_dataset = SyntheticCaptchaDataset(
        num_samples=num_train, add_noise=True, add_lines=False
    )
    val_dataset = SyntheticCaptchaDataset(
        num_samples=num_val, add_noise=True, add_lines=False
    )

    train_loader = DataLoader(
        train_dataset, batch_size=batch_size, shuffle=True,
        num_workers=0, pin_memory=True if device.type == 'cuda' else False
    )
    val_loader = DataLoader(
        val_dataset, batch_size=batch_size, shuffle=False,
        num_workers=0, pin_memory=True if device.type == 'cuda' else False
    )

    # Create model
    model = CaptchaCNN(num_classes=NUM_CLASSES, captcha_length=CAPTCHA_LENGTH)
    model = model.to(device)
    print(f"\n🏗️  Model parameters: {count_parameters(model):,}")

    # Loss, optimizer, scheduler
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(
        model.parameters(), lr=learning_rate, weight_decay=weight_decay
    )
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, mode='min', factor=0.5, patience=5, verbose=True
    )

    # Training history
    history = {
        'train_loss': [], 'val_loss': [],
        'train_char_acc': [], 'val_char_acc': [],
        'train_seq_acc': [], 'val_seq_acc': [],
    }

    # Early stopping
    best_val_loss = float('inf')
    best_val_seq_acc = 0.0
    epochs_without_improvement = 0
    best_model_path = os.path.join(save_dir, 'captcha_cnn.pth')

    print("\n🏋️  Starting training...\n")
    total_start = time.time()

    for epoch in range(1, num_epochs + 1):
        epoch_start = time.time()

        # Train
        train_loss, train_char_acc, train_seq_acc = train_one_epoch(
            model, train_loader, criterion, optimizer, device
        )

        # Validate
        val_loss, val_char_acc, val_seq_acc = validate(
            model, val_loader, criterion, device
        )

        # Update scheduler
        scheduler.step(val_loss)

        # Record history
        history['train_loss'].append(train_loss)
        history['val_loss'].append(val_loss)
        history['train_char_acc'].append(train_char_acc)
        history['val_char_acc'].append(val_char_acc)
        history['train_seq_acc'].append(train_seq_acc)
        history['val_seq_acc'].append(val_seq_acc)

        elapsed = time.time() - epoch_start
        lr = optimizer.param_groups[0]['lr']

        print(
            f"Epoch {epoch:02d}/{num_epochs} │ "
            f"Loss: {train_loss:.4f}/{val_loss:.4f} │ "
            f"Char Acc: {train_char_acc:.4f}/{val_char_acc:.4f} │ "
            f"Seq Acc: {train_seq_acc:.4f}/{val_seq_acc:.4f} │ "
            f"LR: {lr:.6f} │ "
            f"Time: {elapsed:.1f}s"
        )

        # Check for improvement
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            best_val_seq_acc = val_seq_acc
            epochs_without_improvement = 0

            # Save best model
            checkpoint = {
                'epoch': epoch,
                'model_state_dict': model.state_dict(),
                'optimizer_state_dict': optimizer.state_dict(),
                'val_loss': val_loss,
                'val_char_acc': val_char_acc,
                'val_seq_acc': val_seq_acc,
                'config': {
                    'num_classes': NUM_CLASSES,
                    'captcha_length': CAPTCHA_LENGTH,
                    'img_height': IMG_HEIGHT,
                    'img_width': IMG_WIDTH,
                },
            }
            torch.save(checkpoint, best_model_path)
            print(f"  ✅ Saved best model (val_seq_acc: {val_seq_acc:.4f})")
        else:
            epochs_without_improvement += 1
            if epochs_without_improvement >= patience:
                print(f"\n⚠️  Early stopping triggered (no improvement for {patience} epochs)")
                break

    total_time = time.time() - total_start
    print("\n" + "=" * 60)
    print("Training Complete!")
    print("=" * 60)
    print(f"  Total time:         {total_time:.1f}s ({total_time/60:.1f} min)")
    print(f"  Best val loss:      {best_val_loss:.4f}")
    print(f"  Best val seq acc:   {best_val_seq_acc:.4f}")
    print(f"  Model saved to:     {best_model_path}")

    # Plot training curves
    curves_path = os.path.join(save_dir, 'training_curves.png')
    plot_training_curves(history, curves_path)

    # Save training history
    history_path = os.path.join(save_dir, 'training_history.json')
    with open(history_path, 'w') as f:
        json.dump(history, f, indent=2)
    print(f"📋 Training history saved to: {history_path}")

    return model, history


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train CAPTCHA CNN")
    parser.add_argument('--epochs', type=int, default=30, help='Number of epochs')
    parser.add_argument('--batch-size', type=int, default=64, help='Batch size')
    parser.add_argument('--lr', type=float, default=1e-3, help='Learning rate')
    parser.add_argument('--train-size', type=int, default=50000, help='Training samples')
    parser.add_argument('--val-size', type=int, default=5000, help='Validation samples')
    parser.add_argument('--patience', type=int, default=7, help='Early stopping patience')
    parser.add_argument('--save-dir', type=str, default=None, help='Model save directory')
    args = parser.parse_args()

    config = {
        'num_epochs': args.epochs,
        'batch_size': args.batch_size,
        'learning_rate': args.lr,
        'num_train': args.train_size,
        'num_val': args.val_size,
        'patience': args.patience,
    }
    if args.save_dir:
        config['save_dir'] = args.save_dir

    train(config)
