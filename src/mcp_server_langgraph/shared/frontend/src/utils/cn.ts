/**
 * Tailwind CSS class name utility
 *
 * Combines clsx for conditional class names with tailwind-merge
 * to properly handle Tailwind CSS class conflicts.
 *
 * @example
 * ```tsx
 * // Simple usage
 * cn('text-red-500', 'bg-blue-500')
 *
 * // Conditional classes
 * cn('base-class', isActive && 'active-class')
 *
 * // Override conflicts (tailwind-merge handles this)
 * cn('p-4', 'p-2') // → 'p-2' (later wins)
 *
 * // With CVA variants
 * cn(buttonVariants({ variant: 'primary' }), className)
 * ```
 */

import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

/**
 * Combines class names using clsx and resolves Tailwind conflicts with tailwind-merge.
 *
 * @param inputs - Class values to combine (strings, objects, arrays, conditionals)
 * @returns Merged and deduplicated class string
 */
export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}

export default cn;
