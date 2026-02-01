/**
 * Table Component
 *
 * A compound component for rendering accessible data tables with
 * consistent design system styling.
 *
 * Features:
 * - Compound component pattern (Table, TableHead, TableBody, TableRow, etc.)
 * - CVA-based variants (compact, striped, hoverable, bordered)
 * - Full accessibility support (scope, aria attributes)
 * - Dark mode support
 * - Cell alignment options
 *
 * @example
 * ```tsx
 * <Table striped hoverable>
 *   <TableHead>
 *     <TableRow>
 *       <TableHeaderCell>Name</TableHeaderCell>
 *       <TableHeaderCell align="right">Amount</TableHeaderCell>
 *     </TableRow>
 *   </TableHead>
 *   <TableBody>
 *     <TableRow>
 *       <TableCell>Item 1</TableCell>
 *       <TableCell align="right">$100.00</TableCell>
 *     </TableRow>
 *   </TableBody>
 * </Table>
 * ```
 */

import { createContext, useContext, forwardRef } from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/utils/cn";

// =============================================================================
// Context
// =============================================================================

interface TableContextValue {
  size: "default" | "compact";
  hoverable: boolean;
  bordered: boolean;
}

const TableContext = createContext<TableContextValue>({
  size: "default",
  hoverable: false,
  bordered: false,
});

// =============================================================================
// Table Variants
// =============================================================================

const tableVariants = cva("w-full text-sm", {
  variants: {
    size: {
      default: "",
      compact: "",
    },
  },
  defaultVariants: {
    size: "default",
  },
});

// =============================================================================
// Table Component
// =============================================================================

export interface TableProps
  extends
    React.TableHTMLAttributes<HTMLTableElement>,
    VariantProps<typeof tableVariants> {
  striped?: boolean;
  hoverable?: boolean;
  bordered?: boolean;
}

const Table = forwardRef<HTMLTableElement, TableProps>(
  (
    {
      className,
      size = "default",
      striped = false,
      hoverable = false,
      bordered = false,
      children,
      ...props
    },
    ref,
  ) => {
    return (
      <TableContext.Provider
        value={{ size: size ?? "default", hoverable, bordered }}
      >
        <table
          ref={ref}
          className={cn(tableVariants({ size, className }))}
          data-striped={striped || undefined}
          {...props}
        >
          {children}
        </table>
      </TableContext.Provider>
    );
  },
);
Table.displayName = "Table";

// =============================================================================
// TableHead Component
// =============================================================================

export type TableHeadProps = React.HTMLAttributes<HTMLTableSectionElement>;

const TableHead = forwardRef<HTMLTableSectionElement, TableHeadProps>(
  ({ className, ...props }, ref) => {
    return (
      <thead
        ref={ref}
        className={cn(
          "bg-neutral-1 border-b border-neutral-5 dark:border-neutral-6",
          className,
        )}
        {...props}
      />
    );
  },
);
TableHead.displayName = "TableHead";

// =============================================================================
// TableBody Component
// =============================================================================

export interface TableBodyProps extends React.HTMLAttributes<HTMLTableSectionElement> {
  striped?: boolean;
}

const TableBody = forwardRef<HTMLTableSectionElement, TableBodyProps>(
  ({ className, ...props }, ref) => {
    return (
      <tbody
        ref={ref}
        className={cn(
          "divide-y divide-neutral-5 dark:divide-neutral-6",
          // Apply striped styling if table has striped prop
          "[table[data-striped]>&]:even:[&>tr]:bg-neutral-2",
          className,
        )}
        {...props}
      />
    );
  },
);
TableBody.displayName = "TableBody";

// =============================================================================
// TableRow Component
// =============================================================================

export interface TableRowProps extends React.HTMLAttributes<HTMLTableRowElement> {
  selected?: boolean;
}

const TableRow = forwardRef<HTMLTableRowElement, TableRowProps>(
  ({ className, selected, onClick, ...props }, ref) => {
    const { hoverable } = useContext(TableContext);

    return (
      <tr
        ref={ref}
        className={cn(
          // Base styles
          "",
          // Hoverable variant (from context or explicit onClick)
          (hoverable || onClick) && "hover:bg-neutral-a6",
          // Clickable cursor when onClick is provided
          onClick && "cursor-pointer",
          // Selected state
          selected && "bg-primary-1",
          className,
        )}
        onClick={onClick}
        {...props}
      />
    );
  },
);
TableRow.displayName = "TableRow";

// =============================================================================
// TableHeaderCell Component
// =============================================================================

const headerCellVariants = cva(
  "font-medium text-neutral-11 dark:text-neutral-11",
  {
    variants: {
      size: {
        default: "px-4 py-3",
        compact: "px-2 py-1.5",
      },
      align: {
        left: "text-left",
        center: "text-center",
        right: "text-right",
      },
    },
    defaultVariants: {
      size: "default",
      align: "left",
    },
  },
);

export interface TableHeaderCellProps
  extends
    React.ThHTMLAttributes<HTMLTableCellElement>,
    Omit<VariantProps<typeof headerCellVariants>, "size"> {
  align?: "left" | "center" | "right";
}

const TableHeaderCell = forwardRef<HTMLTableCellElement, TableHeaderCellProps>(
  ({ className, align = "left", ...props }, ref) => {
    const { size } = useContext(TableContext);

    return (
      <th
        ref={ref}
        scope="col"
        className={cn(headerCellVariants({ size, align, className }))}
        {...props}
      />
    );
  },
);
TableHeaderCell.displayName = "TableHeaderCell";

// =============================================================================
// TableCell Component
// =============================================================================

const cellVariants = cva("text-neutral-12", {
  variants: {
    size: {
      default: "px-4 py-3",
      compact: "px-2 py-1.5",
    },
    align: {
      left: "text-left",
      center: "text-center",
      right: "text-right",
    },
  },
  defaultVariants: {
    size: "default",
    align: "left",
  },
});

export interface TableCellProps
  extends
    React.TdHTMLAttributes<HTMLTableCellElement>,
    Omit<VariantProps<typeof cellVariants>, "size"> {
  align?: "left" | "center" | "right";
}

const TableCell = forwardRef<HTMLTableCellElement, TableCellProps>(
  ({ className, align = "left", ...props }, ref) => {
    const { size, bordered } = useContext(TableContext);

    return (
      <td
        ref={ref}
        className={cn(
          cellVariants({ size, align }),
          bordered && "border border-neutral-5",
          className,
        )}
        {...props}
      />
    );
  },
);
TableCell.displayName = "TableCell";

// =============================================================================
// Exports
// =============================================================================

export { Table, TableHead, TableBody, TableRow, TableHeaderCell, TableCell };
