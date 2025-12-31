#!/usr/bin/env python3
"""
Lab 2 Cleanup Utility
=====================
Cleans up batch results, temporary files, and prepares for a fresh evaluation run.

Usage:
    python tools/cleanup.py              # Interactive mode - asks confirmation
    python tools/cleanup.py --force      # Force cleanup without asking
    python tools/cleanup.py --dry-run    # Show what would be deleted
"""

import argparse
import glob
import os
import shutil


def get_files_to_clean():
    """Get list of files that would be cleaned up."""
    files = {
        "batch_results": glob.glob("reports/batches/batch_*_results.json"),
        "batch_reports": glob.glob("reports/batches/batch_*_report.html"),
        "batch_summaries": glob.glob("reports/batches/batch_summary*.json"),
        "temp_configs": glob.glob("reports/batches/_temp_config_*.yaml"),
        "temp_tests": glob.glob("_generated/batch_*_temp.yaml"),
        "merged_results": ["reports/merged_results.json"] if os.path.exists("reports/merged_results.json") else [],
    }
    return files


def print_files_summary(files: dict):
    """Print summary of files to be cleaned."""
    total = 0
    print("\n📁 Files to clean:\n")
    
    for category, file_list in files.items():
        if file_list:
            print(f"   {category}:")
            for f in file_list[:3]:  # Show first 3
                print(f"      - {f}")
            if len(file_list) > 3:
                print(f"      ... and {len(file_list) - 3} more")
            total += len(file_list)
    
    print(f"\n   Total files: {total}")
    return total


def cleanup(force: bool = False, dry_run: bool = False):
    """Perform cleanup of batch files."""
    files = get_files_to_clean()
    total = print_files_summary(files)
    
    if total == 0:
        print("\n✅ Nothing to clean up - workspace is already clean!\n")
        return
    
    if dry_run:
        print("\n🔍 DRY RUN - No files were actually deleted\n")
        return
    
    if not force:
        response = input("\n⚠️  Delete these files? [y/N]: ").strip().lower()
        if response != 'y':
            print("❌ Cleanup cancelled\n")
            return
    
    # Perform cleanup
    deleted = 0
    for file_list in files.values():
        for filepath in file_list:
            try:
                os.remove(filepath)
                deleted += 1
            except Exception as e:
                print(f"   ⚠️  Could not delete {filepath}: {e}")
    
    print(f"\n✅ Cleaned up {deleted} files")
    print("   Ready for a fresh evaluation run!\n")
    
    # Show next steps
    print("📋 Next steps:")
    print("   source .env && python run_batches_simple.py \\")
    print("     --config promptfooconfig_gemini_free_tier.yaml \\")
    print("     --batch-size 2 --delay 180\n")


def main():
    parser = argparse.ArgumentParser(
        description="Clean up batch evaluation files for a fresh run"
    )
    parser.add_argument("--force", "-f", action="store_true", 
                       help="Force cleanup without confirmation")
    parser.add_argument("--dry-run", "-n", action="store_true",
                       help="Show what would be deleted without actually deleting")
    
    args = parser.parse_args()
    
    print("\n" + "=" * 50)
    print("🧹 LAB 2 CLEANUP UTILITY")
    print("=" * 50)
    
    cleanup(force=args.force, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
