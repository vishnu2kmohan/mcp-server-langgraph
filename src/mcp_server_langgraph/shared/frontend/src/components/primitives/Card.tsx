/**
 * Card Component (Shared Primitive)
 *
 * Flexible card component with composable subcomponents.
 * Uses CVA for consistent variant styling.
 *
 * @module @mcp-server-langgraph/shared-frontend/primitives
 */

import { forwardRef, type HTMLAttributes } from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '../../utils/cn';

/**
 * Card variants using CVA for type-safe, consistent styling
 */
export const cardVariants = cva(
  // Base styles
  ['rounded-lg'],
  {
    variants: {
      variant: {
        default: [
          'border border-gray-200 bg-white',
          'dark:border-gray-700 dark:bg-gray-900',
        ],
        elevated: [
          'border border-gray-100 bg-white shadow-lg',
          'dark:border-gray-700 dark:bg-gray-900',
        ],
        ghost: ['border border-transparent bg-transparent', 'dark:bg-transparent'],
      },
      padding: {
        none: 'p-0',
        sm: 'p-3',
        md: 'p-4',
        lg: 'p-6',
      },
      interactive: {
        true: [
          'cursor-pointer transition-all duration-150',
          'hover:shadow-md hover:border-gray-300',
          'dark:hover:border-gray-600',
        ],
        false: '',
      },
    },
    defaultVariants: {
      variant: 'default',
      padding: 'md',
      interactive: false,
    },
  }
);

export interface CardProps
  extends HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof cardVariants> {}

/**
 * Card component with consistent styling
 *
 * @example
 * ```tsx
 * <Card variant="elevated" padding="lg">
 *   <CardHeader>
 *     <CardTitle>Card Title</CardTitle>
 *   </CardHeader>
 *   <CardContent>Card content here</CardContent>
 *   <CardFooter>
 *     <Button>Action</Button>
 *   </CardFooter>
 * </Card>
 * ```
 */
export const Card = forwardRef<HTMLDivElement, CardProps>(
  ({ className, variant, padding, interactive, children, ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={cn(cardVariants({ variant, padding, interactive, className }))}
        {...props}
      >
        {children}
      </div>
    );
  }
);

Card.displayName = 'Card';

/**
 * CardHeader - Container for card title and actions
 */
export type CardHeaderProps = HTMLAttributes<HTMLDivElement>;

export function CardHeader({ className, children, ...props }: CardHeaderProps) {
  return (
    <div
      className={cn(
        'flex items-center justify-between gap-4',
        '-m-4 mb-4 p-4 border-b border-gray-100',
        'dark:border-gray-800',
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
}

/**
 * CardTitle - Heading for the card
 */
export type CardTitleProps = HTMLAttributes<HTMLHeadingElement>;

export function CardTitle({ className, children, ...props }: CardTitleProps) {
  return (
    <h3
      className={cn(
        'text-lg font-semibold text-gray-900',
        'dark:text-gray-100',
        className
      )}
      {...props}
    >
      {children}
    </h3>
  );
}

/**
 * CardContent - Main content area of the card
 */
export type CardContentProps = HTMLAttributes<HTMLDivElement>;

export function CardContent({ className, children, ...props }: CardContentProps) {
  return (
    <div
      className={cn('text-gray-600 dark:text-gray-400', className)}
      {...props}
    >
      {children}
    </div>
  );
}

/**
 * CardFooter - Container for card actions
 */
export type CardFooterProps = HTMLAttributes<HTMLDivElement>;

export function CardFooter({ className, children, ...props }: CardFooterProps) {
  return (
    <div
      className={cn(
        'flex items-center justify-end gap-2',
        '-m-4 mt-4 p-4 border-t border-gray-100',
        'dark:border-gray-800',
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
}
