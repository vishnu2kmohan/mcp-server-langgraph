/**
 * VideoArtifact Component
 *
 * Renders video content with playback controls.
 * Supports URLs and base64 data URLs.
 */

import type { VideoConfig } from "../../types/artifacts";

export interface VideoArtifactProps {
  data: string;
  title?: string;
  mimeType?: string;
  config?: VideoConfig;
}

export function VideoArtifact({
  data,
  title,
  mimeType,
  config,
}: VideoArtifactProps) {
  if (!data || data.trim() === "") {
    return (
      <div
        className="p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg"
        role="alert"
      >
        <p className="text-sm text-red-600 dark:text-red-400">
          No video source provided
        </p>
      </div>
    );
  }

  const showControls = config?.controls !== false;
  const autoplay = config?.autoplay ?? false;
  const loop = config?.loop ?? false;
  const muted = config?.muted ?? false;
  const preload = config?.preload ?? "metadata";
  const poster = config?.poster;

  const videoStyle: React.CSSProperties = {
    width: config?.width
      ? typeof config.width === "number"
        ? `${config.width}px`
        : config.width
      : "100%",
    height: config?.height
      ? typeof config.height === "number"
        ? `${config.height}px`
        : config.height
      : undefined,
  };

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
          <video
            data-testid="video-player"
            controls={showControls}
            autoPlay={autoplay}
            loop={loop}
            muted={muted}
            preload={preload}
            poster={poster}
            style={videoStyle}
            className="rounded"
          >
            <source src={data} type={mimeType} />
            Your browser does not support the video element.
          </video>
        ) : (
          <video
            data-testid="video-player"
            src={data}
            controls={showControls}
            autoPlay={autoplay}
            loop={loop}
            muted={muted}
            preload={preload}
            poster={poster}
            style={videoStyle}
            className="rounded"
          >
            Your browser does not support the video element.
          </video>
        )}
      </div>
    </div>
  );
}
