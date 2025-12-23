/**
 * VideoArtifact Tests
 *
 * TDD tests for video artifact rendering component.
 */

import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import { VideoArtifact } from "./VideoArtifact";

describe("VideoArtifact", () => {
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  const testVideoUrl = "https://example.com/video.mp4";
  const testBase64Video = "data:video/mp4;base64,SGVsbG8gV29ybGQ=";

  describe("rendering", () => {
    it("should render video element with controls by default", () => {
      render(<VideoArtifact data={testVideoUrl} />);
      const video = screen.getByTestId("video-player");
      expect(video).toBeInTheDocument();
      expect(video).toHaveAttribute("controls");
    });

    it("should set src attribute from data prop", () => {
      render(<VideoArtifact data={testVideoUrl} />);
      const video = screen.getByTestId("video-player");
      expect(video).toHaveAttribute("src", testVideoUrl);
    });

    it("should render title if provided", () => {
      render(<VideoArtifact data={testVideoUrl} title="My Video" />);
      expect(screen.getByText("My Video")).toBeInTheDocument();
    });

    it("should handle base64 data URLs", () => {
      render(<VideoArtifact data={testBase64Video} />);
      const video = screen.getByTestId("video-player");
      expect(video).toHaveAttribute("src", testBase64Video);
    });
  });

  describe("config options", () => {
    it("should not autoplay by default", () => {
      render(<VideoArtifact data={testVideoUrl} />);
      const video = screen.getByTestId("video-player");
      expect(video).not.toHaveAttribute("autoplay");
    });

    it("should enable autoplay when configured", () => {
      render(<VideoArtifact data={testVideoUrl} config={{ autoplay: true }} />);
      const video = screen.getByTestId("video-player");
      expect(video).toHaveAttribute("autoplay");
    });

    it("should enable loop when configured", () => {
      render(<VideoArtifact data={testVideoUrl} config={{ loop: true }} />);
      const video = screen.getByTestId("video-player");
      expect(video).toHaveAttribute("loop");
    });

    it("should enable muted when configured", () => {
      render(<VideoArtifact data={testVideoUrl} config={{ muted: true }} />);
      const video = screen.getByTestId("video-player") as HTMLVideoElement;
      expect(video.muted).toBe(true);
    });

    it("should hide controls when configured", () => {
      render(
        <VideoArtifact data={testVideoUrl} config={{ controls: false }} />,
      );
      const video = screen.getByTestId("video-player");
      expect(video).not.toHaveAttribute("controls");
    });

    it("should set preload attribute when configured", () => {
      render(
        <VideoArtifact data={testVideoUrl} config={{ preload: "none" }} />,
      );
      const video = screen.getByTestId("video-player");
      expect(video).toHaveAttribute("preload", "none");
    });

    it("should set poster image when configured", () => {
      const posterUrl = "https://example.com/thumbnail.jpg";
      render(
        <VideoArtifact data={testVideoUrl} config={{ poster: posterUrl }} />,
      );
      const video = screen.getByTestId("video-player");
      expect(video).toHaveAttribute("poster", posterUrl);
    });

    it("should apply custom width from config", () => {
      render(<VideoArtifact data={testVideoUrl} config={{ width: 640 }} />);
      const video = screen.getByTestId("video-player");
      expect(video).toHaveStyle({ width: "640px" });
    });

    it("should apply custom height from config", () => {
      render(<VideoArtifact data={testVideoUrl} config={{ height: 480 }} />);
      const video = screen.getByTestId("video-player");
      expect(video).toHaveStyle({ height: "480px" });
    });
  });

  describe("mime type", () => {
    it("should include source element with mime type when provided", () => {
      render(<VideoArtifact data={testVideoUrl} mimeType="video/mp4" />);
      const source = document.querySelector("source");
      expect(source).toBeInTheDocument();
      expect(source).toHaveAttribute("type", "video/mp4");
    });
  });

  describe("error handling", () => {
    it("should show error for empty data", () => {
      render(<VideoArtifact data="" />);
      expect(screen.getByText(/no video source/i)).toBeInTheDocument();
    });
  });
});
