"""
MITS Gwalior Result Scraper — Main Orchestrator
===================================================
Runs the complete pipeline:
    1. Check/load trained CAPTCHA model
    2. Scrape results from the live portal
    3. Process and export data to CSV/Excel

Usage:
    python main.py                       # Full pipeline
    python main.py --train-only          # Only train the model
    python main.py --scrape-only         # Only scrape (model must exist)
    python main.py --export-only         # Only export (raw data must exist)
    python main.py --branch BTAD BTAI    # Scrape specific branches
    python main.py --no-headless         # Show browser window
"""

import os
import sys
import argparse

# Project root
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

MODEL_PATH = os.path.join(PROJECT_ROOT, 'captcha_model', 'saved_models',
                          'captcha_cnn.pth')


def step_train(config=None):
    """Step 1: Train the CAPTCHA CNN model."""
    print("\n" + "🔧" * 30)
    print("  PHASE 2: Training CAPTCHA CNN Model")
    print("🔧" * 30)

    from captcha_model.train import train

    if config is None:
        config = {
            'num_epochs': 30,
            'batch_size': 64,
            'learning_rate': 1e-3,
            'num_train': 50000,
            'num_val': 5000,
            'patience': 7,
            'save_dir': os.path.join(PROJECT_ROOT, 'captcha_model', 'saved_models'),
        }

    model, history = train(config)
    return model


def step_scrape(model_path=None, headless=True, branch_filter=None,
                resume=True):
    """Step 2: Scrape results from the portal."""
    print("\n" + "🌐" * 30)
    print("  PHASE 3: Scraping Results from Portal")
    print("🌐" * 30)

    from scraper.scraper import run_scraper

    if model_path is None:
        model_path = MODEL_PATH

    results = run_scraper(
        model_path=model_path,
        headless=headless,
        branch_filter=branch_filter,
        resume=resume,
    )
    return results


def step_export(raw_path=None):
    """Step 3: Process and export data."""
    print("\n" + "📊" * 30)
    print("  PHASE 4: Processing & Exporting Data")
    print("📊" * 30)

    from data_processor.export import run_export

    csv_path = os.path.join(PROJECT_ROOT, 'data', 'results.csv')
    xlsx_path = os.path.join(PROJECT_ROOT, 'data', 'results.xlsx')

    df = run_export(
        raw_path=raw_path,
        csv_path=csv_path,
        xlsx_path=xlsx_path,
    )
    return df


def main():
    parser = argparse.ArgumentParser(
        description="MITS Gwalior Result Scraper — Complete Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                         # Full pipeline (train → scrape → export)
  python main.py --train-only            # Only train the CNN model
  python main.py --scrape-only           # Only scrape (needs trained model)
  python main.py --export-only           # Only export (needs raw data)
  python main.py --branch BTAD           # Scrape only AI & DS branch
  python main.py --no-headless           # Show browser while scraping
  python main.py --epochs 50 --lr 0.001  # Custom training params
        """
    )

    # Mode selection
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument('--train-only', action='store_true',
                            help='Only train the model')
    mode_group.add_argument('--scrape-only', action='store_true',
                            help='Only run the scraper')
    mode_group.add_argument('--export-only', action='store_true',
                            help='Only process and export data')

    # Training params
    parser.add_argument('--epochs', type=int, default=30,
                        help='Training epochs (default: 30)')
    parser.add_argument('--batch-size', type=int, default=64,
                        help='Training batch size (default: 64)')
    parser.add_argument('--lr', type=float, default=1e-3,
                        help='Learning rate (default: 0.001)')
    parser.add_argument('--train-size', type=int, default=50000,
                        help='Training dataset size (default: 50000)')

    # Scraper params
    parser.add_argument('--model', type=str, default=None,
                        help='Path to trained model (.pth)')
    parser.add_argument('--no-headless', action='store_true',
                        help='Show browser window')
    parser.add_argument('--branch', type=str, nargs='+',
                        choices=['BTAD', 'BTAM', 'BTAI'],
                        help='Scrape specific branches')
    parser.add_argument('--no-resume', action='store_true',
                        help='Start scraping from scratch')

    # Export params
    parser.add_argument('--raw-input', type=str, default=None,
                        help='Path to raw results JSON for export')

    args = parser.parse_args()

    print("=" * 60)
    print("  MITS Gwalior Result Scraper — Portfolio Project")
    print("  OCR + Deep Learning + Automated Data Extraction")
    print("=" * 60)

    if args.train_only:
        # Train only
        config = {
            'num_epochs': args.epochs,
            'batch_size': args.batch_size,
            'learning_rate': args.lr,
            'num_train': args.train_size,
            'num_val': 5000,
            'patience': 7,
            'save_dir': os.path.join(PROJECT_ROOT, 'captcha_model',
                                     'saved_models'),
        }
        step_train(config)

    elif args.scrape_only:
        # Scrape only
        model_path = args.model or MODEL_PATH
        if not os.path.exists(model_path):
            print(f"⚠️  Model not found at: {model_path}")
            print("   Run training first: python main.py --train-only")
            print("   Or provide a model: python main.py --scrape-only --model path/to/model.pth")
            sys.exit(1)

        step_scrape(
            model_path=model_path,
            headless=not args.no_headless,
            branch_filter=args.branch,
            resume=not args.no_resume,
        )

    elif args.export_only:
        # Export only
        step_export(raw_path=args.raw_input)

    else:
        # Full pipeline
        print("\n📋 Running full pipeline: Train → Scrape → Export\n")

        # Step 1: Check if model exists, train if needed
        model_path = args.model or MODEL_PATH
        if not os.path.exists(model_path):
            print("📦 No trained model found. Starting training...")
            config = {
                'num_epochs': args.epochs,
                'batch_size': args.batch_size,
                'learning_rate': args.lr,
                'num_train': args.train_size,
                'num_val': 5000,
                'patience': 7,
                'save_dir': os.path.join(PROJECT_ROOT, 'captcha_model',
                                         'saved_models'),
            }
            step_train(config)
        else:
            print(f"✅ Model found: {model_path}")

        # Step 2: Scrape
        step_scrape(
            model_path=model_path,
            headless=not args.no_headless,
            branch_filter=args.branch,
            resume=not args.no_resume,
        )

        # Step 3: Export
        step_export()

    print("\n✅ Pipeline complete!")


if __name__ == "__main__":
    main()
