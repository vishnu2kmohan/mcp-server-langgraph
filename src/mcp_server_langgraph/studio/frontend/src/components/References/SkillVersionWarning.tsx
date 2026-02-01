/**
 * SkillVersionWarning Component
 *
 * Shows warnings when a skill reference uses a version that
 * differs from the currently installed version.
 *
 * WCAG 2.2 AA compliant with proper alert semantics.
 */

import {
  AlertTriangle,
  AlertCircle,
  Info,
  ArrowUp,
  ArrowDown,
} from "lucide-react";
import { cn } from "@/utils/cn";

export interface SkillVersionWarningProps {
  /** Version referenced in the markdown */
  referencedVersion: string | undefined;
  /** Currently installed version */
  installedVersion: string | undefined;
  /** Name of the skill */
  skillName: string;
  /** Compact mode for inline display */
  compact?: boolean;
  /** Additional CSS classes */
  className?: string;
}

type VersionDiff = "major" | "minor" | "patch" | "none" | "unknown";

/**
 * Parse semver version string into components.
 * Handles prerelease and build metadata.
 */
function parseVersion(
  version: string,
): { major: number; minor: number; patch: number } | null {
  // Remove build metadata (after +)
  const withoutBuild = version.split("+")[0];
  // Remove prerelease suffix (after -)
  const withoutPrerelease = withoutBuild.split("-")[0];

  const match = withoutPrerelease.match(/^(\d+)\.(\d+)\.(\d+)$/);
  if (!match) {
    return null;
  }

  return {
    major: parseInt(match[1], 10),
    minor: parseInt(match[2], 10),
    patch: parseInt(match[3], 10),
  };
}

/**
 * Check if version has prerelease suffix.
 */
function hasPrerelease(version: string): boolean {
  const withoutBuild = version.split("+")[0];
  return withoutBuild.includes("-");
}

/**
 * Compare two versions and determine difference level.
 */
function compareVersions(
  referenced: string,
  installed: string,
): { diff: VersionDiff; isUpgrade: boolean } {
  const refParsed = parseVersion(referenced);
  const instParsed = parseVersion(installed);

  if (!refParsed || !instParsed) {
    return { diff: "unknown", isUpgrade: false };
  }

  // Check if major/minor/patch are equal
  const coreEqual =
    refParsed.major === instParsed.major &&
    refParsed.minor === instParsed.minor &&
    refParsed.patch === instParsed.patch;

  if (coreEqual) {
    // Check for prerelease differences (ignore build metadata)
    const refWithoutBuild = referenced.split("+")[0];
    const instWithoutBuild = installed.split("+")[0];
    const refHasPrerelease = hasPrerelease(referenced);
    const instHasPrerelease = hasPrerelease(installed);

    if (
      refHasPrerelease !== instHasPrerelease ||
      refWithoutBuild !== instWithoutBuild
    ) {
      // Prerelease difference - treat as patch-level
      // Stable (no prerelease) is considered "newer" than prerelease
      const isUpgrade = refHasPrerelease && !instHasPrerelease;
      return { diff: "patch", isUpgrade };
    }

    return { diff: "none", isUpgrade: false };
  }

  // Determine if installed is newer (upgrade) or older (downgrade)
  const isUpgrade =
    instParsed.major > refParsed.major ||
    (instParsed.major === refParsed.major &&
      instParsed.minor > refParsed.minor) ||
    (instParsed.major === refParsed.major &&
      instParsed.minor === refParsed.minor &&
      instParsed.patch > refParsed.patch);

  // Determine level of difference
  if (refParsed.major !== instParsed.major) {
    return { diff: "major", isUpgrade };
  }
  if (refParsed.minor !== instParsed.minor) {
    return { diff: "minor", isUpgrade };
  }
  return { diff: "patch", isUpgrade };
}

/**
 * Check if version is a special value like "latest".
 */
function isSpecialVersion(version: string): boolean {
  return ["latest", "stable", "next", "dev"].includes(version.toLowerCase());
}

/**
 * SkillVersionWarning displays version mismatch warnings.
 */
export function SkillVersionWarning({
  referencedVersion,
  installedVersion,
  skillName,
  compact = false,
  className,
}: SkillVersionWarningProps) {
  // No warning if either version is missing
  if (!referencedVersion || !installedVersion) {
    return null;
  }

  // Handle special versions like "latest"
  if (isSpecialVersion(installedVersion)) {
    return (
      <div
        role="alert"
        className={cn(
          "flex items-center gap-2 text-sm",
          "bg-info-2 border border-info-6 rounded p-2",
          className,
        )}
      >
        <Info
          size={16}
          className="text-info-9 flex-shrink-0"
          aria-hidden="true"
        />
        <span className="text-info-11">
          Version comparison unavailable:{" "}
          <code className="text-info-12">{skillName}</code> references{" "}
          <code className="text-info-12">{referencedVersion}</code>, installed
          is <code className="text-info-12">{installedVersion}</code>
        </span>
      </div>
    );
  }

  const { diff, isUpgrade } = compareVersions(
    referencedVersion,
    installedVersion,
  );

  // No warning if versions match
  if (diff === "none") {
    return null;
  }

  // Handle unknown/unparseable versions
  if (diff === "unknown") {
    // Check if it's a prerelease difference
    if (referencedVersion !== installedVersion) {
      return (
        <div
          role="alert"
          className={cn(
            "flex items-center gap-2 text-sm",
            "bg-info-2 border border-info-6 rounded p-2",
            className,
          )}
        >
          <Info
            size={16}
            className="text-info-9 flex-shrink-0"
            aria-hidden="true"
          />
          <span className="text-info-11">
            Version difference:{" "}
            <code className="text-info-12">{skillName}</code> references{" "}
            <code className="text-info-12">{referencedVersion}</code>, installed
            is <code className="text-info-12">{installedVersion}</code>
          </span>
        </div>
      );
    }
    return null;
  }

  // Determine styling based on severity
  const severityConfig = {
    major: {
      bg: "bg-danger-2",
      border: "border-danger-6",
      text: "text-danger-11",
      code: "text-danger-12",
      Icon: AlertTriangle,
      iconColor: "text-danger-9",
      label: "Major version",
    },
    minor: {
      bg: "bg-warning-2",
      border: "border-warning-6",
      text: "text-warning-11",
      code: "text-warning-12",
      Icon: AlertCircle,
      iconColor: "text-warning-9",
      label: "Minor version",
    },
    patch: {
      bg: "bg-info-2",
      border: "border-info-6",
      text: "text-info-11",
      code: "text-info-12",
      Icon: Info,
      iconColor: "text-info-9",
      label: "Patch version",
    },
  };

  const config = severityConfig[diff];
  const { Icon } = config;
  const DirectionIcon = isUpgrade ? ArrowUp : ArrowDown;

  if (compact) {
    return (
      <div
        role="alert"
        className={cn(
          "inline-flex items-center gap-1 text-xs",
          config.bg,
          config.border,
          "border rounded px-1.5 py-0.5",
          className,
        )}
      >
        <Icon size={12} className={config.iconColor} aria-hidden="true" />
        <span className={config.text}>
          <code className={config.code}>{referencedVersion}</code>
          {" → "}
          <code className={config.code}>{installedVersion}</code>
        </span>
      </div>
    );
  }

  return (
    <div
      role="alert"
      className={cn(
        "flex flex-col gap-1 text-sm",
        config.bg,
        config.border,
        "border rounded p-2",
        className,
      )}
    >
      <div className="flex items-center gap-2">
        <Icon
          size={16}
          className={cn(config.iconColor, "flex-shrink-0")}
          aria-hidden="true"
        />
        <span className={cn(config.text, "font-medium")}>
          {config.label} mismatch for{" "}
          <code className={config.code}>{skillName}</code>
        </span>
      </div>

      <div className={cn("flex items-center gap-2 ml-6", config.text)}>
        <DirectionIcon size={14} aria-hidden="true" />
        <span>
          {isUpgrade ? "Newer version installed" : "Older version installed"}:{" "}
          <code className={config.code}>{referencedVersion}</code>
          {" → "}
          <code className={config.code}>{installedVersion}</code>
        </span>
      </div>

      {diff === "major" && (
        <p className={cn("ml-6 text-xs", config.text)}>
          {isUpgrade
            ? "Consider updating the reference to use the newer version. There may be breaking changes."
            : "The referenced version is newer. This skill may behave differently with breaking changes."}
        </p>
      )}

      {diff === "minor" && (
        <p className={cn("ml-6 text-xs", config.text)}>
          Consider updating the reference. New features may be available.
        </p>
      )}
    </div>
  );
}

export default SkillVersionWarning;
