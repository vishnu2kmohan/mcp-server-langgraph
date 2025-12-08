# Mintlify Broken Links Report

**Date**: 2025-11-17
**Status**: ✅ ACCEPTABLE
**Action Required**: None

## Summary

The `mintlify broken-links` check reports **10 broken links in 4 files**, all of which are in **template files** (`.mintlify/templates/`).

## Findings

### Broken Links by File

#### 1. `.mintlify/templates/adr-template.mdx` (2 links)
- `/architecture/adr-XXXX` - Placeholder for related ADR link
- `/architecture/adr-YYYY` - Placeholder for related ADR link

#### 2. `.mintlify/templates/deployment-template.mdx` (2 links)
- `/path/to/guide` (appears twice) - Placeholder for related guide links

#### 3. `.mintlify/templates/guide-template.mdx` (4 links)
- `/guides/next-guide` - Placeholder for next guide link
- `/reference/topic` - Placeholder for reference link
- `/guides/related-1` - Placeholder for related guide
- `/guides/related-2` - Placeholder for related guide

#### 4. `.mintlify/templates/reference-template.mdx` (2 links)
- `/reference/related-1` - Placeholder for related reference
- `/reference/related-2` - Placeholder for related reference

## Analysis

### Why These Are Acceptable

1. **Template Nature**: All broken links are in `.mintlify/templates/` directory
2. **Placeholder Intent**: These are intentional placeholder links meant to be replaced when templates are used
3. **No Impact**: Template files are not part of the published documentation
4. **Best Practice**: Showing realistic link examples in templates helps users understand proper formatting

### Actual Documentation Status

- **Total documentation files**: 248 MDX files
- **Broken links in actual docs**: 0 ✅
- **Documentation health**: 100%

## Recommendations

### Current Approach (Recommended)
Keep placeholder links as-is in templates. Benefits:
- ✅ Shows users realistic link examples
- ✅ Templates demonstrate proper Mintlify link syntax
- ✅ Easy to identify what needs to be replaced
- ✅ No impact on actual documentation quality

### Alternative Approaches (If desired)
If you want to eliminate these from the report:

1. **Option 1**: Comment out placeholder links
   ```markdown
   <!-- Example links (replace with actual links):
   * [Related Guide](/path/to/guide)
   -->
   ```

2. **Option 2**: Use code blocks instead of actual links
   ```markdown
   Example link format: `[Title](/path/to/page)`
   ```

3. **Option 3**: Create .mintlifyignore file (if supported)
   ```
   .mintlify/templates/
   ```

## Validation

Run the broken links check:
```bash
cd docs
npx mintlify broken-links
```

**Expected Output**:
```
found 10 broken links in 4 files

.mintlify/templates/adr-template.mdx
 ⎿  /architecture/adr-XXXX
 ⎿  /architecture/adr-YYYY

.mintlify/templates/deployment-template.mdx
 ⎿  /path/to/guide
 ⎿  /path/to/guide

.mintlify/templates/guide-template.mdx
 ⎿  /guides/next-guide
 ⎿  /reference/topic
 ⎿  /guides/related-1
 ⎿  /guides/related-2

.mintlify/templates/reference-template.mdx
 ⎿  /reference/related-1
 ⎿  /reference/related-2
```

## Conclusion

✅ **No action required**. All broken links are in template files with placeholder content. The actual documentation (248 MDX files) has **zero broken links**.

---

**Last Updated**: 2025-11-17
**Next Review**: When templates are modified
