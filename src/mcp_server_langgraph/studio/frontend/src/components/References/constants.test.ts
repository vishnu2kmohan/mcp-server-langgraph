/**
 * Tests for Reference Constants and Utilities
 */

import { describe, it, expect } from 'vitest';
import {
  REFERENCE_ICONS,
  REFERENCE_ICON_COLORS,
  REFERENCE_BG_COLORS,
  REFERENCE_TEXT_COLORS as _REFERENCE_TEXT_COLORS,
  REFERENCE_TYPE_LABELS,
  getReferenceIcon,
  getReferenceIconColor,
  getReferenceBgColor,
  getReferenceTextColor,
  toMarkdownReference,
  parseMarkdownReference,
  isValidReferenceType,
  isSupportedReferenceType,
  SUPPORTED_REFERENCE_TYPES,
} from './constants';

describe('Reference Constants', () => {
  describe('REFERENCE_ICONS', () => {
    it('should have icons for all main types', () => {
      expect(REFERENCE_ICONS.tool).toBeDefined();
      expect(REFERENCE_ICONS.skill).toBeDefined();
      expect(REFERENCE_ICONS.artifact).toBeDefined();
    });

    it('should have icon for type suggestions', () => {
      expect(REFERENCE_ICONS.type).toBeDefined();
    });
  });

  describe('REFERENCE_ICON_COLORS', () => {
    it('should have colors for all types', () => {
      expect(REFERENCE_ICON_COLORS.tool).toBe('text-primary-9');
      expect(REFERENCE_ICON_COLORS.skill).toBe('text-success-9');
      expect(REFERENCE_ICON_COLORS.artifact).toBe('text-neutral-9');
    });
  });

  describe('REFERENCE_BG_COLORS', () => {
    it('should have background colors for all types', () => {
      expect(REFERENCE_BG_COLORS.tool).toBe('bg-primary-3');
      expect(REFERENCE_BG_COLORS.skill).toBe('bg-success-3');
      expect(REFERENCE_BG_COLORS.artifact).toBe('bg-neutral-3');
    });
  });

  describe('REFERENCE_TYPE_LABELS', () => {
    it('should have labels for all types', () => {
      expect(REFERENCE_TYPE_LABELS.tool).toBe('Tool');
      expect(REFERENCE_TYPE_LABELS.skill).toBe('Skill');
      expect(REFERENCE_TYPE_LABELS.artifact).toBe('Artifact');
    });
  });
});

describe('Utility Functions', () => {
  describe('getReferenceIcon', () => {
    it('should return correct icon for known types', () => {
      expect(getReferenceIcon('tool')).toBe(REFERENCE_ICONS.tool);
      expect(getReferenceIcon('skill')).toBe(REFERENCE_ICONS.skill);
    });

    it('should return fallback icon for type suggestions', () => {
      expect(getReferenceIcon('type')).toBe(REFERENCE_ICONS.type);
    });
  });

  describe('getReferenceIconColor', () => {
    it('should return correct color for known types', () => {
      expect(getReferenceIconColor('tool')).toBe('text-primary-9');
      expect(getReferenceIconColor('skill')).toBe('text-success-9');
    });
  });

  describe('getReferenceBgColor', () => {
    it('should return correct background for known types', () => {
      expect(getReferenceBgColor('tool')).toBe('bg-primary-3');
    });

    it('should return artifact color as fallback', () => {
      // @ts-expect-error Testing invalid type
      expect(getReferenceBgColor('unknown')).toBe('bg-neutral-3');
    });
  });

  describe('getReferenceTextColor', () => {
    it('should return correct text color for known types', () => {
      expect(getReferenceTextColor('tool')).toBe('text-primary-11');
      expect(getReferenceTextColor('skill')).toBe('text-success-11');
    });
  });
});

describe('toMarkdownReference', () => {
  it('should generate tool reference', () => {
    expect(toMarkdownReference('tool', 'filesystem', 'read_file')).toBe(
      '[[tool:filesystem:read_file]]'
    );
  });

  it('should generate skill reference', () => {
    expect(toMarkdownReference('skill', 'code-review')).toBe(
      '[[skill:code-review]]'
    );
  });

  it('should generate artifact reference', () => {
    expect(toMarkdownReference('artifact', 'chart-123')).toBe(
      '[[artifact:chart-123]]'
    );
  });

  it('should include label when provided', () => {
    expect(toMarkdownReference('tool', 'filesystem', 'read_file', 'Read File')).toBe(
      '[[tool:filesystem:read_file|Read File]]'
    );
  });

  it('should include label for non-tool types', () => {
    expect(toMarkdownReference('skill', 'code-review', undefined, 'Code Review')).toBe(
      '[[skill:code-review|Code Review]]'
    );
  });
});

describe('parseMarkdownReference', () => {
  it('should parse tool reference', () => {
    const result = parseMarkdownReference('[[tool:filesystem:read_file]]');
    expect(result).toEqual({
      type: 'tool',
      qualifier: 'filesystem',
      id: 'read_file',
      label: undefined,
    });
  });

  it('should parse skill reference', () => {
    const result = parseMarkdownReference('[[skill:code-review]]');
    expect(result).toEqual({
      type: 'skill',
      qualifier: 'code-review',
      id: 'code-review',
      label: undefined,
    });
  });

  it('should parse artifact reference', () => {
    const result = parseMarkdownReference('[[artifact:chart-123]]');
    expect(result).toEqual({
      type: 'artifact',
      qualifier: 'chart-123',
      id: 'chart-123',
      label: undefined,
    });
  });

  it('should parse reference with label', () => {
    const result = parseMarkdownReference('[[tool:filesystem:read_file|Read File]]');
    expect(result).toEqual({
      type: 'tool',
      qualifier: 'filesystem',
      id: 'read_file',
      label: 'Read File',
    });
  });

  it('should return null for invalid reference', () => {
    expect(parseMarkdownReference('not a reference')).toBeNull();
    expect(parseMarkdownReference('[[invalid]]')).toBeNull();
    expect(parseMarkdownReference('[tool:fs:read]')).toBeNull();
  });

  it('should handle tool with multiple colons in id', () => {
    const result = parseMarkdownReference('[[tool:server:tool:subpart]]');
    expect(result).toEqual({
      type: 'tool',
      qualifier: 'server',
      id: 'tool:subpart',
      label: undefined,
    });
  });
});

describe('isValidReferenceType', () => {
  it('should return true for supported types', () => {
    expect(isValidReferenceType('tool')).toBe(true);
    expect(isValidReferenceType('skill')).toBe(true);
    expect(isValidReferenceType('artifact')).toBe(true);
  });

  it('should return true for future types', () => {
    expect(isValidReferenceType('memory')).toBe(true);
    expect(isValidReferenceType('plan')).toBe(true);
  });

  it('should return false for invalid types', () => {
    expect(isValidReferenceType('unknown')).toBe(false);
    expect(isValidReferenceType('')).toBe(false);
  });
});

describe('isSupportedReferenceType', () => {
  it('should return true for all supported types', () => {
    expect(isSupportedReferenceType('tool')).toBe(true);
    expect(isSupportedReferenceType('skill')).toBe(true);
    expect(isSupportedReferenceType('artifact')).toBe(true);
    expect(isSupportedReferenceType('memory')).toBe(true);
    expect(isSupportedReferenceType('plan')).toBe(true);
  });
});

describe('SUPPORTED_REFERENCE_TYPES', () => {
  it('should include all reference types', () => {
    expect(SUPPORTED_REFERENCE_TYPES).toContain('tool');
    expect(SUPPORTED_REFERENCE_TYPES).toContain('skill');
    expect(SUPPORTED_REFERENCE_TYPES).toContain('artifact');
    expect(SUPPORTED_REFERENCE_TYPES).toContain('memory');
    expect(SUPPORTED_REFERENCE_TYPES).toContain('plan');
  });

  it('should have 5 supported types', () => {
    expect(SUPPORTED_REFERENCE_TYPES).toHaveLength(5);
  });
});
