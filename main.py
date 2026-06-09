"""
MITS Gwalior Result Scraper  Main Orchestrator
===================================================
Runs the complete pipeline:
    1. Scrape results from the live portal using TrOCR
    2. Process and export data to CSV/Excel

Usage:
    python main.py                       # Full pipeline (Scrape + Export)
    python main.py --scrape-only         # Only scrape
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

MODEL_PATH = os.path.join(PROJECT_ROOT, 'captcha_model', 'trocr_model')


def step_scrape(model_path=None, headless=True, branch_filter=None,
                resume=True):
    """Step 1: Scrape results from the portal."""
    print("\n" + "=" * 30)
    print("  PHASE 1: Scraping Results from Portal")
    print("=" * 30)

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
    """Step 2: Process and export data."""
    print("\n" + "=" * 30)
    print("  PHASE 2: Processing & Exporting Data")
    print("=" * 30)

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
        description="MITS Gwalior Result Scraper  Complete Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                         # Full pipeline (scrape + export)
  python main.py --scrape-only           # Only scrape
  python main.py --export-only           # Only export (needs raw data)
  python main.py --branch BTAD           # Scrape only AI & DS branch
  python main.py --no-headless           # Show browser while scraping
        """
    )

    # Mode selection
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument('--scrape-only', action='store_true',
                            help='Only run the scraper')
    mode_group.add_argument('--export-only', action='store_true',
                            help='Only process and export data')

    # Scraper params
    parser.add_argument('--model', type=str, default=None,
                        help='Path to TrOCR model directory')
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

    # IUMS params
    parser.add_argument('--mode', type=str, choices=['result', 'iums'], default='result',
                        help='Target portal to scrape: "result" for MITS Result, "iums" for IUMS portal')
    parser.add_argument('--enrollment', type=str, help='Student enrollment for IUMS mode')
    parser.add_argument('--password', type=str, help='Student password for IUMS mode')
    parser.add_argument('--bulk-csv', type=str, help='Path to CSV with enrollment,password for bulk IUMS scraping')

    args = parser.parse_args()

    print("=" * 60)
    print("  MITS Gwalior Result Scraper  Project")
    print("  OCR (TrOCR) + Automated Data Extraction")
    print("=" * 60)

    model_path = args.model or MODEL_PATH

    if args.mode == 'iums':
        from scraper.iums_scraper import run_iums_scraper
        
        creds = []
        if args.enrollment and args.password:
            creds.append({'enrollment': args.enrollment, 'password': args.password})
        elif args.bulk_csv:
            if not os.path.exists(args.bulk_csv):
                print(f" Bulk CSV not found: {args.bulk_csv}")
                sys.exit(1)
            import csv
            with open(args.bulk_csv, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if 'enrollment' in row and 'password' in row:
                        creds.append(row)
        else:
            template_path = os.path.join(PROJECT_ROOT, 'data', 'iums_credentials.csv')
            if not os.path.exists(template_path):
                os.makedirs(os.path.dirname(template_path), exist_ok=True)
                with open(template_path, 'w') as f:
                    f.write("enrollment,password\n")
            print(f"\n Error: Please provide --enrollment and --password, or --bulk-csv.")
            print(f" An empty template has been created at {template_path}")
            sys.exit(1)
            
        run_iums_scraper(
            credentials_list=creds,
            model_path=model_path,
            headless=not args.no_headless
        )
    else:
        if args.scrape_only:
            step_scrape(
                model_path=model_path,
                headless=not args.no_headless,
                branch_filter=args.branch,
                resume=not args.no_resume,
            )
        elif args.export_only:
            step_export(raw_path=args.raw_input)
        else:
            print("\n Running full pipeline: Scrape -> Export\n")
            step_scrape(
                model_path=model_path,
                headless=not args.no_headless,
                branch_filter=args.branch,
                resume=not args.no_resume,
            )
            step_export()

    print("\n Pipeline complete!")


if __name__ == "__main__":
    main()
