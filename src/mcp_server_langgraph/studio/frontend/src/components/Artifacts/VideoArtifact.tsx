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
        className="p-4 bg-error-1 dark:bg-error-a3 border border-error-4 dark:border-error-11 rounded-lg"
        role="alert"
      >
        <p className="text-sm text-error-10 dark:text-error-7">
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
    <div className="bg-neutral-1 rounded-lg overflow-hidden">
      {title && (
        <div className="px-4 py-2 border-b border-neutral-5">
          <h4 className="text-sm font-medium text-neutral-11">{title}</h4>
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
