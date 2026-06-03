#!/usr/bin/env python3
"""
Semantic Versioning update utility for the Bytefight2026Engine.

Usage:
    python semver_update.py patch "Fix beacon placement bug"
    python semver_update.py minor "Add new feature X"
    python semver_update.py major "Breaking API change"
    python utils/semver_update.py delete 1.0.0

This script:
1. Reads the current version from VERSION file
2. Bumps the version according to the specified type (patch, minor, major)
3. Updates the CHANGELOG.md with the new entry
4. Optionally creates a git tag
"""

import sys
import os
from datetime import datetime
import subprocess
from pathlib import Path


def read_version(version_file):
    """Read the current version from VERSION file."""
    with open(version_file, 'r') as f:
        return f.read().strip()


def write_version(version_file, version):
    """Write the updated version to VERSION file."""
    with open(version_file, 'w') as f:
        f.write(version + '\n')


def parse_version(version_str):
    """Parse semantic version string into (major, minor, patch)."""
    parts = version_str.split('.')
    if len(parts) != 3:
        raise ValueError(f"Invalid version format: {version_str}. Expected: X.Y.Z")
    try:
        return tuple(map(int, parts))
    except ValueError:
        raise ValueError(f"Version components must be integers: {version_str}")


def bump_version(version_str, bump_type):
    """Bump the version according to the bump type."""
    major, minor, patch = parse_version(version_str)
    
    if bump_type == 'major':
        major += 1
        minor = 0
        patch = 0
    elif bump_type == 'minor':
        minor += 1
        patch = 0
    elif bump_type == 'patch':
        patch += 1
    else:
        raise ValueError(f"Invalid bump type: {bump_type}. Must be: patch, minor, or major")
    
    return f"{major}.{minor}.{patch}"


def update_changelog(changelog_file, version, message):
    """Update the CHANGELOG.md with the new version entry."""
    date = datetime.now().strftime('%Y-%m-%d')
    
    # Read existing content
    with open(changelog_file, 'r') as f:
        content = f.read()
    
    # Find the position to insert after "All notable changes" description
    lines = content.split('\n')
    insert_pos = 0
    
    # Find the line with "All notable changes" and insert after it
    for i, line in enumerate(lines):
        if 'All notable changes' in line:
            insert_pos = i + 1
            break
    
    # Create new version entry
    new_entry = f"\n## [{version}] - {date}\n\n### Changed\n- {message}\n"
    
    # Insert the new entry
    lines.insert(insert_pos + 1, new_entry)
    
    # Write back
    with open(changelog_file, 'w') as f:
        f.write('\n'.join(lines))


def create_git_tag(version):
    """Create a git tag for the version."""
    try:
        tag_name = f"v{version}"
        subprocess.run(['git', 'tag', tag_name], check=True, capture_output=True)
        print(f"✓ Created git tag: {tag_name}")
    except subprocess.CalledProcessError as e:
        print(f"⚠ Warning: Could not create git tag: {e.stderr.decode()}")
    except FileNotFoundError:
        print("⚠ Warning: git not found, skipping tag creation")


def get_versions_from_changelog(changelog_file):
    """Extract all version numbers from the CHANGELOG.md file."""
    versions = []
    with open(changelog_file, 'r') as f:
        for line in f:
            if line.startswith('## ['):
                # Extract version from format: ## [1.0.0] - YYYY-MM-DD
                version_str = line.split('[')[1].split(']')[0]
                versions.append(version_str)
    return versions


def get_highest_version(versions):
    """Get the highest semantic version from a list of version strings."""
    if not versions:
        return None
    
    # Parse and sort versions
    parsed = []
    for v in versions:
        try:
            major, minor, patch = parse_version(v)
            parsed.append((major, minor, patch, v))
        except ValueError:
            continue
    
    if not parsed:
        return None
    
    # Sort by major, minor, patch in descending order
    parsed.sort(reverse=True)
    return parsed[0][3]  # Return the version string


def delete_version_from_changelog(changelog_file, version):
    """Delete a version entry and its changelog from the CHANGELOG.md file."""
    with open(changelog_file, 'r') as f:
        content = f.read()
    
    # Find the version header and delete it along with its content
    lines = content.split('\n')
    new_lines = []
    skip_until_next_version = False
    version_found = False
    preserve_blank_line = False
    
    for i, line in enumerate(lines):
        # Check if this is the version header we want to delete
        if line.startswith(f'## [{version}]'):
            skip_until_next_version = True
            version_found = True
            preserve_blank_line = True
            continue
        
        # If we're skipping, continue until we hit the next version header
        if skip_until_next_version:
            if line.startswith('## ['):
                skip_until_next_version = False
                # Preserve one blank line between "All notable changes" and first version
                if preserve_blank_line:
                    new_lines.append('')
                    preserve_blank_line = False
                new_lines.append(line)
            # else: skip this line (part of the version we're deleting)
        else:
            new_lines.append(line)
    
    # Clean up trailing whitespace
    while new_lines and new_lines[-1].strip() == '':
        new_lines.pop()
    new_lines.append('')  # Ensure file ends with newline
    
    if not version_found:
        return False
    
    with open(changelog_file, 'w') as f:
        f.write('\n'.join(new_lines))
    
    return True


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python semver_update.py <bump_type> <message>")
        print("    bump_type: patch, minor, or major")
        print("    message: Description of changes (e.g., 'Fix beacon placement bug')")
        print("")
        print("  python semver_update.py delete <version>")
        print("    version: Version number to delete from changelog (e.g., 1.0.1)")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    # Handle delete command
    if command == 'delete':
        if len(sys.argv) < 3:
            print("Usage: python semver_update.py delete <version>")
            print("  version: Version number to delete from changelog (e.g., 1.0.1)")
            sys.exit(1)
        
        version = sys.argv[2]
        repo_root = Path(__file__).parent.parent
        changelog_file = repo_root / 'CHANGELOG.md'
        version_file = repo_root / 'VERSION'
        
        if not changelog_file.exists():
            print(f"Error: CHANGELOG.md file not found at {changelog_file}")
            sys.exit(1)
        
        if delete_version_from_changelog(changelog_file, version):
            print(f"✓ Successfully deleted version {version} from CHANGELOG.md")
            
            # Update VERSION file to the highest remaining version
            remaining_versions = get_versions_from_changelog(changelog_file)
            if remaining_versions:
                highest_version = get_highest_version(remaining_versions)
                if highest_version:
                    write_version(version_file, highest_version)
                    print(f"✓ Updated VERSION file to {highest_version}")
            else:
                print("⚠ No remaining versions in CHANGELOG.md")
        else:
            print(f"⚠ Version {version} not found in CHANGELOG.md")
        
        return
    
    # Handle version bump command
    if len(sys.argv) < 3:
        print("Usage: python semver_update.py <bump_type> <message>")
        print("  bump_type: patch, minor, or major")
        print("  message: Description of changes (e.g., 'Fix beacon placement bug')")
        sys.exit(1)
    
    bump_type = command
    message = sys.argv[2]
    
    # Find the repo root (go up from utils directory)
    script_dir = Path(__file__).parent
    repo_root = script_dir.parent
    
    version_file = repo_root / 'VERSION'
    changelog_file = repo_root / 'CHANGELOG.md'
    
    # Validate files exist
    if not version_file.exists():
        print(f"Error: VERSION file not found at {version_file}")
        sys.exit(1)
    
    if not changelog_file.exists():
        print(f"Error: CHANGELOG.md file not found at {changelog_file}")
        sys.exit(1)
    
    try:
        # Read current version
        current_version = read_version(version_file)
        print(f"Current version: {current_version}")
        
        # Bump version
        new_version = bump_version(current_version, bump_type)
        print(f"Bumping {bump_type}: {current_version} → {new_version}")
        
        # Update VERSION file
        write_version(version_file, new_version)
        print(f"✓ Updated VERSION file")
        
        # Update CHANGELOG.md
        update_changelog(changelog_file, new_version, message)
        print(f"✓ Updated CHANGELOG.md")
        
        # Create git tag
        create_git_tag(new_version)
        
        print(f"\n✓ Version successfully updated to {new_version}")
        print("\nNext steps:")
        print(f"  1. Review the changes in VERSION and CHANGELOG.md")
        print(f"  2. Run: git add VERSION CHANGELOG.md")
        print(f"  3. Run: git commit -m 'Release {new_version}: {message}'")
        print(f"  4. Run: git push origin main --tags")
        
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
