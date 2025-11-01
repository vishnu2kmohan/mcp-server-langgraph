# MDX Syntax Best Practices and Error Prevention

This guide documents common MDX parsing errors in Mintlify documentation and how to prevent them.

## Common Errors and Solutions

### 1. Unescaped Angle Brackets Before/After Numbers

**Error**: `Unexpected character '1' (U+0031) before name`

**Cause**: Using `<` or `>` directly before numbers (e.g., `<100K`, `>1M`)

**Solution**: Use HTML entities

❌ **Wrong:**
```
- Low volume (<100K requests/mo)
- High volume (>1M requests/mo)
```

✅ **Correct:**
```
- Low volume (&lt;100K requests/mo)
- High volume (&gt;1M requests/mo)
```

**Automated Fix**: Run `python scripts/fix_mdx_angle_brackets.py`

### 2. Missing Blank Lines Around Component Tags

**Error**: `Expected a closing tag for <CodeGroup>`

**Cause**: Missing blank lines after opening or before closing component tags

**Solution**: Always add blank lines

❌ **Wrong:**
```
<CodeGroup>
  ```bash
  code here
  ```
</CodeGroup>
```

✅ **Correct:**
```
<CodeGroup>

  ```bash
  code here
  ```

</CodeGroup>
```

**Components requiring blank lines**:
- `<CodeGroup>`
- `<Accordion>`
- `<AccordionGroup>`
- `<Tabs>` / `<Tab>`
- `<Card>` / `<CardGroup>`
- `<Steps>` / `<Step>`

### 3. Stray Language Tags After Code Blocks

**Error**: Various parsing errors

**Cause**: Accidental `xml` or other language tags after closing triple backticks

**Solution**: Remove stray language tags
```
❌ Wrong:
```bash
command here
```xml

✅ Correct:
```bash
command here
```
```

**Automated Fix**: `find . -name "*.mdx" -exec sed -i 's/```xml$/```/g' {} \;`

### 4. Heredoc Syntax in Code Blocks

**Error**: `Unexpected closing slash '/' in tag`

**Cause**: Using heredoc syntax with quotes that confuse the MDX parser

**Solution**: Use separate code blocks or avoid heredoc quotes
```
❌ Problematic:
```bash
kubectl patch deployment grafana --patch '
spec:
  template:
    ...
'
```

✅ Better:
```bash
kubectl patch deployment grafana --patch-file=patch.yaml
```

Then show the patch file separately:

```yaml
spec:
  template:
    ...
```
```

### 5. Unclosed or Mismatched Tags

**Error**: `Expected a closing tag for <Accordion>`

**Cause**: Missing closing tags or tags closed in wrong order

**Solution**: Ensure all tags are properly matched

❌ **Wrong** (missing closing tag):
```
<AccordionGroup>
  <Accordion title="First">
    Content
  </Accordion>
  <Accordion title="Second">
    Content
  {/* Missing </Accordion> */}
</AccordionGroup>
```

✅ **Correct:**
```
<AccordionGroup>
  <Accordion title="First">
    Content
  </Accordion>
  <Accordion title="Second">
    Content
  </Accordion>
</AccordionGroup>
```

**Validation**: Run `python scripts/validate_mdx_syntax.py`

## Preventive Scripts

### 1. Fix Angle Brackets
```bash
python scripts/fix_mdx_angle_brackets.py --dry-run  # Preview changes
python scripts/fix_mdx_angle_brackets.py            # Apply fixes
```

### 2. Validate MDX Syntax
```bash
python scripts/validate_mdx_syntax.py                     # Validate all files
python scripts/validate_mdx_syntax.py --file path.mdx     # Validate one file
python scripts/validate_mdx_syntax.py --fix               # Fix spacing issues
```

### 3. Remove Stray XML Tags
```bash
find . -name "*.mdx" -exec sed -i 's/```xml$/```/g' {} \;
```

### 4. Run Mintlify Link Checker
```bash
mintlify broken-links
```

## Pre-Commit Checklist

Before committing MDX files:

- [ ] Run `python scripts/fix_mdx_angle_brackets.py`
- [ ] Run `python scripts/validate_mdx_syntax.py --fix`
- [ ] Run `mintlify broken-links` to verify no parsing errors
- [ ] Check for stray ```xml tags: `grep -r '```xml' docs/ --include="*.mdx"`
- [ ] Verify blank lines around all component tags

## Common Patterns to Avoid

### Shell Commands with Quotes
Instead of using heredoc syntax with quotes in code blocks, use separate blocks:

**Instead of this:**
```bash
kubectl patch --patch '
spec:
  key: value
'
```

**Do this:**
First create `patch.yaml`:

```yaml
spec:
  key: value
```

Then apply:

```bash
kubectl patch --patch-file=patch.yaml
```

### Comparison Operators
Always escape comparison operators when followed by numbers:

```
✅ Use: &lt; and &gt;
❌ Avoid: < and >
```

### Component Nesting
Keep component nesting clean and well-spaced:

```
<OuterComponent>

  <InnerComponent>
    Content here
  </InnerComponent>

  <InnerComponent>
    More content
  </InnerComponent>

</OuterComponent>
```

## Automated CI/CD Integration

Add to `.github/workflows/docs-validation.yml`:

```yaml
name: Validate Documentation

on: [push, pull_request]

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Fix angle brackets
        run: python scripts/fix_mdx_angle_brackets.py

      - name: Validate MDX syntax
        run: python scripts/validate_mdx_syntax.py

      - name: Check for stray XML tags
        run: |
          if grep -r '```xml' docs/ --include="*.mdx"; then
            echo "Error: Found stray XML tags"
            exit 1
          fi

      - name: Run Mintlify link checker
        run: mintlify broken-links
```

## Emergency Fixes

If `mintlify broken-links` fails:

1. Note the file and line number from the error
2. Run validation on that specific file:
   ```bash
   python scripts/validate_mdx_syntax.py --file docs/path/to/file.mdx
   ```
3. Check for common issues in order:
   - Unescaped `<` or `>` before numbers
   - Missing blank lines around components
   - Stray ````xml` tags
   - Heredoc syntax with quotes
   - Unclosed/mismatched tags
4. Fix and re-run `mintlify broken-links`

## Additional Resources

- [Mintlify MDX Documentation](https://mintlify.com/docs/content/text)
- [MDX Specification](https://mdxjs.com/)
- Project scripts:
  - `/scripts/fix_mdx_angle_brackets.py`
  - `/scripts/validate_mdx_syntax.py`
  - `/scripts/add_code_block_lang_tags.py`
