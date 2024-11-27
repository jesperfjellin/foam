#!/usr/bin/env python3

"""
Foam is a command-line tool for tracking and restoring the state of folders. It can be used as a lightweight alternative
to git tracking for managing folder contents during development or testing workflows.

USAGE:
    foam track [options] [folders...]
        --list       List currently tracked folders
        --undo       Clear all tracked folders
        [folders...] Specify one or more folders to track

    foam reset
        Reset all tracked folders to their previously saved state.

DESCRIPTION:
    - 'track': Tracks the current state of specified folders. You can list or clear tracked folders using options.
    - 'reset': Resets folders to the last tracked state, restoring all files and directories to their original condition.

EXAMPLES:
    Track folders:
        foam track /path/to/folder1 /path/to/folder2

    List tracked folders:
        foam track --list

    Clear all tracked folders:
        foam track --undo

    Reset folders:
        foam reset
"""

import sys
import os
import stat
import shutil
import argparse
from pathlib import Path

WRITE_PERMISSION = stat.S_IWRITE if sys.platform.startswith('win') else stat.S_IWUSR
BACKUP_DIR = Path.home() / '.foam_backup'

def ensure_backup_dir():
    """Create and properly hide the backup directory."""
    if not BACKUP_DIR.exists():
        BACKUP_DIR.mkdir(parents=True)
        if sys.platform.startswith('win'):
            import ctypes
            ctypes.windll.kernel32.SetFileAttributesW(str(BACKUP_DIR), 2)  # Hidden attribute

def remove_readonly(func, path, _):
    """Handle removal of read-only files."""
    try:
        os.chmod(path, WRITE_PERMISSION)
        func(path)
    except Exception as e:
        print(f"Warning: Could not remove {path}: {e}")

def track(folders):
    if BACKUP_DIR.exists():
        try:
            shutil.rmtree(BACKUP_DIR, onerror=remove_readonly)
        except Exception as e:
            print(f"Failed to clear existing backup directory: {e}")
            return
            
    ensure_backup_dir()
    
    for folder in folders:
        folder_path = Path(folder).resolve()
        if folder_path.exists() and folder_path.is_dir():
            try:
                relative_path = folder_path.relative_to(folder_path.anchor)
            except ValueError as ve:
                print(f"Error: {ve}")
                continue
            
            # Platform-specific anchor handling
            if sys.platform.startswith('win'):
                anchor = folder_path.anchor.rstrip(':\\')
            else:
                anchor = folder_path.anchor.rstrip('/')
            
            dest = BACKUP_DIR / anchor / relative_path
            dest.parent.mkdir(parents=True, exist_ok=True)
            
            try:
                def copy_with_permissions(src, dst, symlinks=True):
                    if os.path.isdir(src):
                        shutil.copytree(src, dst, symlinks=symlinks)
                    else:
                        shutil.copy2(src, dst, follow_symlinks=symlinks)
                    if not os.path.islink(dst):  # Don't modify symlink permissions
                        os.chmod(dst, os.stat(dst).st_mode | WRITE_PERMISSION)
                
                shutil.copytree(
                    folder_path, 
                    dest,
                    copy_function=copy_with_permissions,
                    symlinks=True
                )
                print(f"Tracked folder: {folder_path} -> {dest}")
            except Exception as e:
                print(f"Failed to track {folder_path}: {e}")
        else:
            print(f"Folder {folder} does not exist or is not a directory.")
    
    print("Folders have been tracked.")

def reset(folders=None):
    if not BACKUP_DIR.exists():
        print("No tracked folders to reset.")
        return

    if folders:
        print("The reset command does not accept any arguments. To reset all tracked folders, use 'foam reset' without arguments.")
        return

    paths_to_reset = []
    tracked_roots = []

    for backup_drive_path in BACKUP_DIR.iterdir():
        if backup_drive_path.is_dir():
            for backup_folder_path in backup_drive_path.iterdir():
                if backup_folder_path.is_dir():
                    relative_path = backup_folder_path.relative_to(BACKUP_DIR)
                    if sys.platform.startswith('win'):
                        drive = relative_path.parts[0] + ':\\'
                        root_path = Path(drive, *relative_path.parts[1:])
                    else:
                        root_path = Path('/') / Path(*relative_path.parts)
                    tracked_roots.append((root_path, backup_folder_path))

    stats = {
        'directories': set(),
        'root_dirs': set(),
        'files': 0,
        'errors': 0
    }

    for root_path, root_backup_path in tracked_roots:
        stats['root_dirs'].add(str(root_path))

        for backup_path in root_backup_path.rglob('*'):
            relative_path = backup_path.relative_to(root_backup_path)
            original_path = root_path / relative_path
            paths_to_reset.append((root_path, original_path, backup_path))

            if backup_path.is_dir() and not backup_path.is_symlink():
                stats['directories'].add(str(original_path))
            elif backup_path.is_file() or backup_path.is_symlink():
                stats['files'] += 1

    for root_path, original_path, backup_path in paths_to_reset:
        if original_path == root_path:
            continue

        if original_path.exists():
            try:
                if original_path.is_file() or original_path.is_symlink():
                    original_path.unlink()
                else:
                    shutil.rmtree(original_path)
            except Exception as e:
                print(f"Error: Could not prepare {original_path} for restore: {e}")
                stats['errors'] += 1
                continue

        try:
            if backup_path.is_file() or backup_path.is_symlink():
                original_path.parent.mkdir(parents=True, exist_ok=True)
                if backup_path.is_symlink():
                    os.symlink(os.readlink(backup_path), original_path)
                else:
                    shutil.copy2(backup_path, original_path)
            else:
                original_path.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            print(f"Error: Could not restore {original_path}: {e}")
            stats['errors'] += 1

    # Removed the backup cleanup code from here

    print(f"Reset complete:")
    actual_dirs = len(stats['directories']) - len(stats['root_dirs'])
    print(f"  • Restored {actual_dirs} directories")
    print(f"  • Restored {stats['files']} files")
    if stats['errors'] > 0:
        print(f"  • Encountered {stats['errors']} errors")

def list_tracked_folders():
    if not BACKUP_DIR.exists():
        print("No folders are currently being tracked.")
        return
    
    print("Currently tracked folders:")
    for backup_path in BACKUP_DIR.iterdir():
        if backup_path.is_dir():
            for subfolder in backup_path.iterdir():
                if subfolder.is_dir():
                    relative_path = subfolder.relative_to(BACKUP_DIR)
                    if sys.platform.startswith('win'):
                        drive = relative_path.parts[0] + ':\\'
                        original_path = Path(drive, *relative_path.parts[1:])
                    else:
                        original_path = Path('/') / Path(*relative_path.parts)
                    print(f"  • {original_path}")

def undo_tracking():
    if not BACKUP_DIR.exists():
        print("No folders are currently being tracked.")
        return
    
    try:
        shutil.rmtree(BACKUP_DIR, onerror=remove_readonly)
        print("Successfully cleared all tracked folders.")
    except Exception as e:
        print(f"Error while clearing tracked folders: {e}")

def main():
    parser = argparse.ArgumentParser(description='Foam - Folder Tracking Tool')
    subparsers = parser.add_subparsers(dest='command', required=True)

    track_parser = subparsers.add_parser('track', help='Track folders')
    track_group = track_parser.add_mutually_exclusive_group()
    
    track_group.add_argument('--list', action='store_true', help='List currently tracked folders')
    track_group.add_argument('--undo', action='store_true', help='Clear all tracked folders')
    track_parser.add_argument('folders', nargs='*', help='Folders to track')

    subparsers.add_parser('reset', help='Reset folders to tracked state')

    args = parser.parse_args()

    if args.command == 'track':
        if args.list:
            list_tracked_folders()
        elif args.undo:
            undo_tracking()
        elif args.folders:
            track(args.folders)
        else:
            track_parser.print_help()
    elif args.command == 'reset':
        reset()
    else:
        parser.print_help()

if __name__ == '__main__':
    main()