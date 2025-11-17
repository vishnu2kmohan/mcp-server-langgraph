#!/usr/bin/env python3
"""
Fix all tests that try to create production Settings without required configs.

TDD Approach:
- RED: Tests fail because Settings(environment='production') requires specific configs
- GREEN: Add required configs to make tests pass
- REFACTOR: Tests now correctly set up production settings
"""

import re
from pathlib import Path

# Find all test files with Settings creation in production mode
test_files = list(Path("tests").rglob("test_*.py"))

fixes_applied = 0

for test_file in test_files:
    content = test_file.read_text()
    original_content = content

    # Pattern 1: Settings(environment="production", ...)
    # Add required production configs if missing
    pattern1 = r'Settings\(\s*environment=["\']production["\'](?!.*auth_provider)([^)]*)\)'

    def add_production_configs(match):
        global fixes_applied
        existing_params = match.group(1)
        # Only add if not already present
        if "auth_provider" not in existing_params:
            fixes_applied += 1
            return f"""Settings(
            environment="production",
            auth_provider="keycloak",
            gdpr_storage_backend="postgres",
            jwt_secret_key="test-secret-key-min-32-chars-long-for-security"{existing_params})"""
        return match.group(0)

    content = re.sub(pattern1, add_production_configs, content)

    # Pattern 2: monkeypatch.setenv("ENVIRONMENT", "production") without other required envvars
    # Find these and add required envvars
    lines = content.split("\n")
    new_lines = []
    for i, line in enumerate(lines):
        new_lines.append(line)
        if 'monkeypatch.setenv("ENVIRONMENT", "production")' in line:
            # Check next few lines for required envvars
            next_lines = lines[i + 1 : i + 5] if i + 1 < len(lines) else []
            has_auth_provider = any("AUTH_PROVIDER" in line for line in next_lines)
            has_gdpr = any("GDPR_STORAGE_BACKEND" in line for line in next_lines)
            has_jwt = any("JWT_SECRET_KEY" in line for line in next_lines)

            indent = "        "  # Match typical indentation
            if "monkeypatch.setenv" in line:
                # Extract indentation
                indent = line[: len(line) - len(line.lstrip())]

            if not has_auth_provider:
                new_lines.append(f'{indent}monkeypatch.setenv("AUTH_PROVIDER", "keycloak")')
                fixes_applied += 1
            if not has_gdpr:
                new_lines.append(f'{indent}monkeypatch.setenv("GDPR_STORAGE_BACKEND", "postgres")')
                fixes_applied += 1
            if not has_jwt:
                new_lines.append(
                    f'{indent}monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-min-32-chars-long-for-security")'
                )
                fixes_applied += 1

    if "\n".join(new_lines) != content:
        content = "\n".join(new_lines)

    # Only write if changed
    if content != original_content:
        test_file.write_text(content)
        print(f"✅ Fixed {test_file}")

print(f"\n✅ Applied {fixes_applied} production settings fixes!")
print("📝 Run: pytest tests/unit/ tests/core/ -v to verify")
