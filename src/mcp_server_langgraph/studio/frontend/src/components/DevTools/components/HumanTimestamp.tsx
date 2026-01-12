import * as React from "react";
import { cn } from "../../../utils/cn";

export type HumanTimestampFormat = "time" | "datetime";

export interface HumanTimestampProps {
  timestamp: number | string;
  format?: HumanTimestampFormat;
  showUtcOnHover?: boolean;
  className?: string;
}

function toDate(value: number | string): Date | null {
  if (typeof value === "number") return new Date(value);
  const parsed = Date.parse(value);
  return Number.isNaN(parsed) ? null : new Date(parsed);
}

export function HumanTimestamp({
  timestamp,
  format = "time",
  showUtcOnHover = true,
  className,
}: HumanTimestampProps): React.ReactElement | null {
  const date = React.useMemo(() => toDate(timestamp), [timestamp]);
  if (!date) return null;

  const text =
    format === "datetime"
      ? date.toLocaleString(undefined, {
          hour12: false,
          timeZoneName: "short",
        })
      : date.toLocaleTimeString(undefined, {
          hour12: false,
          hour: "2-digit",
          minute: "2-digit",
          second: "2-digit",
          fractionalSecondDigits: 3,
        });

  const title = showUtcOnHover ? `${date.toISOString()}` : undefined;

  return (
    <span
      className={cn(
        "font-mono text-xs text-neutral-500 dark:text-neutral-400",
        className,
      )}
      title={title}
      data-testid="human-timestamp"
    >
      {text}
    </span>
  );
}

export default HumanTimestamp;
