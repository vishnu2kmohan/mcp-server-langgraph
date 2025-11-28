import re
from pathlib import Path


def main():
    with open("mypy_errors_6.txt") as f:
        lines = f.readlines()

    pattern = re.compile(r"^([^:]+):(\d+): error: Unused \"type: ignore.*\" comment\s+\[unused-ignore\]")

    updates = {}

    for line in lines:
        match = pattern.match(line)
        if match:
            file_path = match.group(1)
            line_num = int(match.group(2))
            if file_path not in updates:
                updates[file_path] = []
            updates[file_path].append(line_num)

    for file_path, line_nums in updates.items():
        path = Path(file_path)
        if not path.exists():
            print(f"File not found: {file_path}")
            continue

        with open(path) as f:
            content = f.readlines()

        modified = False
        for ln in line_nums:
            idx = ln - 1
            if idx < len(content):
                original = content[idx]
                # Remove the type: ignore comment part
                new_line = re.sub(r"\s*#\s*type:\s*ignore.*$", "", original, flags=re.IGNORECASE)
                if original.endswith("\n") and not new_line.endswith("\n"):
                    new_line += "\n"

                if content[idx] != new_line:
                    content[idx] = new_line
                    modified = True

        if modified:
            print(f"Fixing {file_path}")
            with open(path, "w") as f:
                f.writelines(content)


if __name__ == "__main__":
    main()
