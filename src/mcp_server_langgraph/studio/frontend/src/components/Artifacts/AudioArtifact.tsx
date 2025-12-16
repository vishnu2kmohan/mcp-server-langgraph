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
        className="p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg"
        role="alert"
      >
        <p className="text-sm text-red-600 dark:text-red-400">
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
    <div className="bg-gray-50 dark:bg-gray-800 rounded-lg overflow-hidden">
      {title && (
        <div className="px-4 py-2 border-b border-gray-200 dark:border-gray-700">
          <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300">
            {title}
          </h4>
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
