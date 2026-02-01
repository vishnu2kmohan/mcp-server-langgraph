/**
 * AudioArtifact Component
 *
 * Renders audio content with playback controls.
 * Supports URLs and base64 data URLs.
 */

import type { AudioConfig } from "../../types/artifacts";

export interface AudioArtifactProps {
  data: string;
  title?: string;
  mimeType?: string;
  config?: AudioConfig;
}

export function AudioArtifact({
  data,
  title,
  mimeType,
  config,
}: AudioArtifactProps) {
  if (!data || data.trim() === "") {
    return (
      <div
        className="p-4 bg-error-1 dark:bg-error-a3 border border-error-4 dark:border-error-11 rounded-lg"
        role="alert"
      >
        <p className="text-sm text-error-10 dark:text-error-7">
          No audio source provided
        </p>
      </div>
    );
  }

  const showControls = config?.controls !== false;
  const autoplay = config?.autoplay ?? false;
  const loop = config?.loop ?? false;
  const muted = config?.muted ?? false;
  const preload = config?.preload ?? "metadata";

  return (
    <div className="bg-neutral-1 rounded-lg overflow-hidden">
      {title && (
        <div className="px-4 py-2 border-b border-neutral-5">
          <h4 className="text-sm font-medium text-neutral-11">{title}</h4>
        </div>
      )}
      <div className="p-4">
        {mimeType ? (
          <audio
            data-testid="audio-player"
            controls={showControls}
            autoPlay={autoplay}
            loop={loop}
            muted={muted}
            preload={preload}
            className="w-full"
          >
            <source src={data} type={mimeType} />
            Your browser does not support the audio element.
          </audio>
        ) : (
          <audio
            data-testid="audio-player"
            src={data}
            controls={showControls}
            autoPlay={autoplay}
            loop={loop}
            muted={muted}
            preload={preload}
            className="w-full"
          >
            Your browser does not support the audio element.
          </audio>
        )}
      </div>
    </div>
  );
}
