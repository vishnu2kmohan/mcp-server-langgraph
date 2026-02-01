#!/usr/bin/env python3
"""
Bulk fix Button variant violations.

Automatically fixes common Button variant issues:
1. Icon-only buttons missing variant="ghost" and size="icon"
2. Cancel/Close/Back buttons missing variant="secondary"
3. Delete/Remove buttons missing variant="danger"

Usage:
    python scripts/fix-button-variants.py --dry-run          # Preview changes
    python scripts/fix-button-variants.py                    # Apply fixes
    python scripts/fix-button-variants.py --file path.tsx    # Fix single file
"""

import argparse
import re
import sys
from pathlib import Path
from typing import NamedTuple


class Fix(NamedTuple):
    """A fix to apply."""

    line_num: int
    original: str
    fixed: str
    rule: str


# Lucide icon names (common ones used in the codebase)
LUCIDE_ICONS = {
    "X",
    "Check",
    "Copy",
    "Trash",
    "Trash2",
    "Edit",
    "Pencil",
    "Settings",
    "Plus",
    "Minus",
    "ChevronDown",
    "ChevronUp",
    "ChevronLeft",
    "ChevronRight",
    "ArrowLeft",
    "ArrowRight",
    "ArrowUp",
    "ArrowDown",
    "Search",
    "Filter",
    "MoreHorizontal",
    "MoreVertical",
    "Menu",
    "Close",
    "Refresh",
    "RefreshCw",
    "RotateCcw",
    "Download",
    "Upload",
    "Share",
    "Link",
    "ExternalLink",
    "Eye",
    "EyeOff",
    "Lock",
    "Unlock",
    "Star",
    "Heart",
    "Bell",
    "BellOff",
    "Play",
    "Pause",
    "Stop",
    "SkipForward",
    "SkipBack",
    "Volume",
    "VolumeX",
    "Maximize",
    "Maximize2",
    "Minimize",
    "Minimize2",
    "Fullscreen",
    "ZoomIn",
    "ZoomOut",
    "Home",
    "User",
    "Users",
    "Mail",
    "Send",
    "MessageSquare",
    "FileText",
    "Folder",
    "FolderOpen",
    "Save",
    "Clock",
    "Calendar",
    "AlertCircle",
    "AlertTriangle",
    "Info",
    "HelpCircle",
    "CheckCircle",
    "XCircle",
    "Loader",
    "Loader2",
    "Sparkles",
    "Wand",
    "Bot",
    "Brain",
    "Code",
    "Terminal",
    "Database",
    "Server",
    "Cloud",
    "Wifi",
    "WifiOff",
    "Power",
    "PowerOff",
    "Moon",
    "Sun",
    "Palette",
    "Sliders",
    "Tool",
    "Wrench",
    "Cog",
    "Grid",
    "List",
    "Table",
    "BarChart",
    "BarChart2",
    "LineChart",
    "PieChart",
    "TrendingUp",
    "TrendingDown",
    "Activity",
    "Zap",
    "Target",
    "Crosshair",
    "Map",
    "MapPin",
    "Navigation",
    "Compass",
    "Globe",
    "Flag",
    "Bookmark",
    "Tag",
    "Hash",
    "AtSign",
    "Paperclip",
    "Image",
    "Camera",
    "Video",
    "Mic",
    "MicOff",
    "Headphones",
    "Speaker",
    "Printer",
    "Clipboard",
    "ClipboardCheck",
    "ClipboardList",
    "Archive",
    "Package",
    "Box",
    "Gift",
    "ShoppingCart",
    "CreditCard",
    "DollarSign",
    "Percent",
    "Calculator",
    "Award",
    "Trophy",
    "Medal",
    "Crown",
    "Shield",
    "Key",
    "Fingerprint",
    "Scan",
    "QrCode",
    "Barcode",
    "Layers",
    "Layout",
    "Sidebar",
    "PanelLeft",
    "PanelRight",
    "Columns",
    "Rows",
    "Square",
    "Circle",
    "Triangle",
    "Hexagon",
    "Octagon",
    "Diamond",
    "Move",
    "Grab",
    "Hand",
    "Pointer",
    "MousePointer",
    "Cursor",
    "Type",
    "Bold",
    "Italic",
    "Underline",
    "Strikethrough",
    "AlignLeft",
    "AlignCenter",
    "AlignRight",
    "AlignJustify",
    "Indent",
    "Outdent",
    "ListOrdered",
    "ListUnordered",
    "Quote",
    "Heading1",
    "Heading2",
    "Heading3",
    "Code2",
    "Braces",
    "Brackets",
    "ToggleLeft",
    "ToggleRight",
    "SwitchCamera",
    "Repeat",
    "Shuffle",
    "CircleDot",
    "Disc",
    "Record",
    "Radio",
    "Tv",
    "Monitor",
    "Laptop",
    "Smartphone",
    "Tablet",
    "Watch",
    "Gamepad",
    "Keyboard",
    "Mouse",
    "Cpu",
    "HardDrive",
    "MemoryStick",
    "Usb",
    "Bluetooth",
    "Cast",
    "Airplay",
    "Rss",
    "Chrome",
    "Github",
    "Gitlab",
    "Twitter",
    "Facebook",
    "Instagram",
    "Linkedin",
    "Youtube",
    "Twitch",
    "Slack",
    "Discord",
    "Figma",
    "Dribbble",
}

# Build icon pattern
ICON_PATTERN = "|".join(sorted(LUCIDE_ICONS))


def find_line_number(content: str, pos: int) -> int:
    """Find line number for a position in content."""
    return content[:pos].count("\n") + 1


def fix_cancel_buttons(content: str) -> tuple[str, list[Fix]]:
    """Fix Cancel/Close/Back buttons missing variant='secondary'.

    Handles multi-line Button patterns like:
    <Button
      className="..."
      onClick={...}
    >
      Cancel
    </Button>
    """
    fixes = []

    # Multi-line pattern: <Button (without variant=) ... > Cancel|Close|etc </Button>
    # Uses DOTALL to match across lines
    pattern = re.compile(r"(<Button\b)([^>]*?)(\s*>\s*)(Cancel|Close|Back|Dismiss|No|Never mind)(\s*</Button>)", re.DOTALL)

    def replacer(match):
        button_start = match.group(1)
        attrs = match.group(2)
        close_bracket = match.group(3)
        text = match.group(4)
        button_end = match.group(5)

        # Skip if already has variant
        if "variant=" in attrs:
            return match.group(0)

        # Add variant="secondary" after <Button
        line_num = find_line_number(content, match.start())
        original = match.group(0).replace("\n", " ")[:60]
        fixes.append(
            Fix(line_num, original, f'<Button variant="secondary"...>{text}</Button>', "cancel-button-missing-secondary")
        )

        return f'{button_start} variant="secondary"{attrs}{close_bracket}{text}{button_end}'

    new_content = pattern.sub(replacer, content)
    return new_content, fixes


def fix_destructive_buttons(content: str) -> tuple[str, list[Fix]]:
    """Fix Delete/Remove buttons missing variant='danger'.

    Handles multi-line Button patterns.
    """
    fixes = []

    pattern = re.compile(r"(<Button\b)([^>]*?)(\s*>\s*)(Delete|Remove|Destroy|Discard)(\s*</Button>)", re.DOTALL)

    def replacer(match):
        button_start = match.group(1)
        attrs = match.group(2)
        close_bracket = match.group(3)
        text = match.group(4)
        button_end = match.group(5)

        if "variant=" in attrs:
            return match.group(0)

        line_num = find_line_number(content, match.start())
        original = match.group(0).replace("\n", " ")[:60]
        fixes.append(
            Fix(line_num, original, f'<Button variant="danger"...>{text}</Button>', "destructive-button-missing-danger")
        )

        return f'{button_start} variant="danger"{attrs}{close_bracket}{text}{button_end}'

    new_content = pattern.sub(replacer, content)
    return new_content, fixes


def fix_icon_buttons(content: str) -> tuple[str, list[Fix]]:
    """Fix icon-only buttons missing variant='ghost' and size='icon'.

    Handles patterns like:
    <Button className="..." onClick={...}>
      <X className="w-4 h-4" />
    </Button>
    """
    fixes = []

    # Build icon pattern for common Lucide icons
    icon_names = "|".join(sorted(LUCIDE_ICONS))

    # Multi-line pattern: <Button ...> <Icon .../> </Button>
    pattern = re.compile(rf"(<Button\b)([^>]*?)(\s*>\s*)(<({icon_names})\b[^/]*/>\s*)(</Button>)", re.DOTALL)

    def replacer(match):
        button_start = match.group(1)
        attrs = match.group(2)
        close_bracket = match.group(3)
        icon_element = match.group(4)
        button_end = match.group(6)

        # Skip if already has variant and size="icon"
        has_variant = "variant=" in attrs
        has_icon_size = 'size="icon"' in attrs or "size='icon'" in attrs
        has_any_size = re.search(r'\bsize=["\']', attrs) is not None

        if has_variant and has_icon_size:
            return match.group(0)

        new_attrs = attrs
        changes = []

        if not has_variant:
            new_attrs = ' variant="ghost"' + new_attrs
            changes.append('variant="ghost"')

        # Only add size="icon" if there's no existing size prop
        # If there's a different size (like size="sm"), replace it instead of adding
        if not has_icon_size:
            if has_any_size:
                # Replace existing size with size="icon"
                new_attrs = re.sub(r'\bsize=["\'][^"\']*["\']', 'size="icon"', new_attrs)
                changes.append('size="icon" (replaced)')
            else:
                new_attrs = ' size="icon"' + new_attrs
                changes.append('size="icon"')

        if changes:
            line_num = find_line_number(content, match.start())
            original = match.group(0).replace("\n", " ")[:60]
            fixes.append(Fix(line_num, original, f"<Button {' '.join(changes)}...>", "icon-button-missing-variant-size"))

        return f"{button_start}{new_attrs}{close_bracket}{icon_element}{button_end}"

    new_content = pattern.sub(replacer, content)
    return new_content, fixes


def fix_file(filepath: Path, dry_run: bool = True) -> list[Fix]:
    """Fix all Button variant issues in a file."""
    content = filepath.read_text()
    all_fixes = []

    # Apply fixes in sequence
    content, fixes = fix_icon_buttons(content)
    all_fixes.extend(fixes)

    content, fixes = fix_cancel_buttons(content)
    all_fixes.extend(fixes)

    content, fixes = fix_destructive_buttons(content)
    all_fixes.extend(fixes)

    if all_fixes and not dry_run:
        filepath.write_text(content)

    return all_fixes


def find_tsx_files(src_dir: Path) -> list[Path]:
    """Find all TSX files excluding tests, stories, and UI components."""
    files = []
    for filepath in src_dir.rglob("*.tsx"):
        # Skip test files, stories, and UI component definitions
        if ".test." in filepath.name:
            continue
        if ".stories." in filepath.name:
            continue
        if "/components/UI/" in str(filepath):
            continue
        files.append(filepath)
    return sorted(files)


def main() -> None:
    parser = argparse.ArgumentParser(description="Fix Button variant violations")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without applying")
    parser.add_argument("--file", type=str, help="Fix a single file")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show detailed output")
    args = parser.parse_args()

    script_dir = Path(__file__).parent
    src_dir = script_dir.parent / "src"

    if args.file:
        files = [Path(args.file)]
    else:
        files = find_tsx_files(src_dir)

    total_fixes = 0
    files_fixed = 0

    for filepath in files:
        if not filepath.exists():
            print(f"File not found: {filepath}", file=sys.stderr)
            continue

        fixes = fix_file(filepath, dry_run=args.dry_run)

        if fixes:
            files_fixed += 1
            total_fixes += len(fixes)

            rel_path = filepath.relative_to(src_dir.parent) if src_dir.parent in filepath.parents else filepath
            print(f"\n{rel_path}: {len(fixes)} fix(es)")

            if args.verbose or args.dry_run:
                for fix in fixes:
                    print(f"  Line {fix.line_num} [{fix.rule}]:")
                    print(f"    - {fix.original[:80]}{'...' if len(fix.original) > 80 else ''}")
                    print(f"    + {fix.fixed[:80]}{'...' if len(fix.fixed) > 80 else ''}")

    print(f"\n{'[DRY RUN] ' if args.dry_run else ''}Summary: {total_fixes} fixes in {files_fixed} files")

    if args.dry_run and total_fixes > 0:
        print("\nRun without --dry-run to apply fixes.")


if __name__ == "__main__":
    main()
