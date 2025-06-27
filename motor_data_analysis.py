#!/usr/bin/env python3
"""
Complete Motor Data Analysis Script
Downloads PostHog Motor Data events and generates histogram visualizations
"""

import subprocess
import sys
import argparse
import os
from pathlib import Path

def run_command(command, description):
    """Run a command and handle errors"""
    print(f"\n{'='*60}")
    print(f"🚀 {description}")
    print(f"{'='*60}")
    
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=False)
        print(f"✅ {description} completed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed with exit code {e.returncode}")
        return False
    except Exception as e:
        print(f"❌ {description} failed with error: {str(e)}")
        return False

def main():
    parser = argparse.ArgumentParser(
        description='Complete Motor Data Analysis - Downloads PostHog data and creates histograms',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                                    # Use default person ID
  %(prog)s -p "person-id-here"               # Specific person ID
  %(prog)s -t "2025-06-24T18:54:03"         # Specific timestamp
  %(prog)s -i                                # Interactive mode
  %(prog)s -l                                # List available events only
        """
    )
    
    # Add all the same arguments as GetPostHog.py
    parser.add_argument('--person-id', '-p', 
                       default="01977b53-4d47-73f1-bafc-b30395922351",
                       help='Person ID to fetch Motor Data for')
    parser.add_argument('--session-id', '-s',
                       default="0197a378-6343-73cc-af1e-873f9e6f8fb7", 
                       help='Session ID (optional)')
    parser.add_argument('--timestamp', '-t',
                       help='Specific timestamp to fetch (ISO format, e.g., 2024-01-15T10:30:00Z)')
    parser.add_argument('--interactive', '-i',
                       action='store_true',
                       help='Interactive mode - prompt for person ID and event selection')
    parser.add_argument('--list-events', '-l',
                       action='store_true',
                       help='List all Motor Data events for the person with timestamps')
    parser.add_argument('--skip-histograms', 
                       action='store_true',
                       help='Skip histogram generation (only download CSV data)')
    
    args = parser.parse_args()
    
    print("🎯 Motor Data Complete Analysis")
    print("📊 This script will:")
    print("   1. Download Motor Data from PostHog")
    print("   2. Generate histogram visualizations")
    print()
    
    # Build the GetPostHog.py command
    get_posthog_cmd = ["python3", "scripts/GetPostHog.py"]
    
    if args.person_id != "01977b53-4d47-73f1-bafc-b30395922351":
        get_posthog_cmd.extend(["-p", args.person_id])
    if args.session_id != "0197a378-6343-73cc-af1e-873f9e6f8fb7":
        get_posthog_cmd.extend(["-s", args.session_id])
    if args.timestamp:
        get_posthog_cmd.extend(["-t", args.timestamp])
    if args.interactive:
        get_posthog_cmd.append("-i")
    if args.list_events:
        get_posthog_cmd.append("-l")
    
    get_posthog_cmd_str = " ".join(f'"{arg}"' if " " in arg else arg for arg in get_posthog_cmd)
    
    # Step 1: Download PostHog data
    if not run_command(get_posthog_cmd_str, "Downloading Motor Data from PostHog"):
        print("\n❌ Failed to download PostHog data. Stopping.")
        sys.exit(1)
    
    # If we're just listing events, stop here
    if args.list_events:
        print("\n✅ Event listing complete!")
        sys.exit(0)
    
    # Skip histograms if requested
    if args.skip_histograms:
        print("\n⏭️  Skipping histogram generation (--skip-histograms flag)")
        sys.exit(0)
    
    # Step 2: Generate histograms
    if not run_command("python3 scripts/create_histograms.py", "Generating histogram visualizations"):
        print("\n❌ Failed to generate histograms.")
        sys.exit(1)
    
    # Success summary
    print(f"\n{'='*60}")
    print("🎉 COMPLETE ANALYSIS FINISHED SUCCESSFULLY!")
    print(f"{'='*60}")
    print("📁 Generated files:")
    
    # List CSV files
    csv_files = list(Path(".").glob("posthog_event_*.csv"))
    for csv_file in sorted(csv_files):
        file_size = csv_file.stat().st_size / 1024
        print(f"   📄 {csv_file} ({file_size:.1f} KB)")
    
    # List histogram files
    histogram_dir = Path("histograms")
    if histogram_dir.exists():
        png_files = list(histogram_dir.glob("*_numeric_values.png"))
        data_files = list(histogram_dir.glob("*_numeric_values.csv"))
        
        for file in sorted(png_files + data_files):
            file_size = file.stat().st_size / 1024
            print(f"   📊 {file} ({file_size:.1f} KB)")
    
    print("\n🔍 To view histograms, check the 'histograms/' folder")
    print("💡 To analyze different person/timestamp, run with different arguments")

if __name__ == "__main__":
    main() 