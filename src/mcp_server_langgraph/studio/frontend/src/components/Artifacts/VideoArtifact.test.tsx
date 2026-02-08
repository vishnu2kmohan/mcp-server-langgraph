/**
 * VideoArtifact Tests
 *
 * TDD tests for video artifact rendering component.
 */

import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import { VideoArtifact } from "./VideoArtifact";

import { TestProvider } from "@/test-utils";

describe("VideoArtifact", () => {
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  const testVideoUrl = "https://example.com/video.mp4";
  const testBase64Video = "data:video/mp4;base64,SGVsbG8gV29ybGQ=";

  describe("rendering", () => {
    it("should render video element with controls by default", () => {
      render(
        <TestProvider>
          <VideoArtifact data={testVideoUrl} />
        </TestProvider>,
      );
      const video = screen.getByTestId("video-player");
      expect(video).toBeInTheDocument();
      expect(video).toHaveAttribute("controls");
    });

    it("should set src attribute from data prop", () => {
      render(
        <TestProvider>
          <VideoArtifact data={testVideoUrl} />
        </TestProvider>,
      );
      const video = screen.getByTestId("video-player");
      expect(video).toHaveAttribute("src", testVideoUrl);
    });

    it("should render title if provided", () => {
      render(
        <TestProvider>
          <VideoArtifact data={testVideoUrl} title="My Video" />
        </TestProvider>,
      );
      expect(screen.getByText("My Video")).toBeInTheDocument();
    });

    it("should handle base64 data URLs", () => {
      render(
        <TestProvider>
          <VideoArtifact data={testBase64Video} />
        </TestProvider>,
      );
      const video = screen.getByTestId("video-player");
      expect(video).toHaveAttribute("src", testBase64Video);
    });
  });

  describe("config options", () => {
    it("should not autoplay by default", () => {
      render(
        <TestProvider>
          <VideoArtifact data={testVideoUrl} />
        </TestProvider>,
      );
      const video = screen.getByTestId("video-player");
      expect(video).not.toHaveAttribute("autoplay");
    });

    it("should enable autoplay when configured", () => {
      render(
        <TestProvider>
          <VideoArtifact data={testVideoUrl} config={{ autoplay: true }} />
        </TestProvider>,
      );
      const video = screen.getByTestId("video-player");
      expect(video).toHaveAttribute("autoplay");
    });

    it("should enable loop when configured", () => {
      render(
        <TestProvider>
          <VideoArtifact data={testVideoUrl} config={{ loop: true }} />
        </TestProvider>,
      );
      const video = screen.getByTestId("video-player");
      expect(video).toHaveAttribute("loop");
    });

    it("should enable muted when configured", () => {
      render(
        <TestProvider>
          <VideoArtifact data={testVideoUrl} config={{ muted: true }} />
        </TestProvider>,
      );
      const video = screen.getByTestId("video-player") as HTMLVideoElement;
      expect(video.muted).toBe(true);
    });

    it("should hide controls when configured", () => {
      render(
        <TestProvider>
          <VideoArtifact data={testVideoUrl} config={{ controls: false }} />
        </TestProvider>,
      );
      const video = screen.getByTestId("video-player");
      expect(video).not.toHaveAttribute("controls");
    });

    it("should set preload attribute when configured", () => {
      render(
        <TestProvider>
          <VideoArtifact data={testVideoUrl} config={{ preload: "none" }} />
        </TestProvider>,
      );
      const video = screen.getByTestId("video-player");
      expect(video).toHaveAttribute("preload", "none");
    });

    it("should set poster image when configured", () => {
      const posterUrl = "https://example.com/thumbnail.jpg";
      render(
        <TestProvider>
          <VideoArtifact data={testVideoUrl} config={{ poster: posterUrl }} />
        </TestProvider>,
      );
      const video = screen.getByTestId("video-player");
      expect(video).toHaveAttribute("poster", posterUrl);
    });

    it("should apply custom width from config", () => {
      render(
        <TestProvider>
          <VideoArtifact data={testVideoUrl} config={{ width: 640 }} />
        </TestProvider>,
      );
      const video = screen.getByTestId("video-player");
      expect(video).toHaveStyle({ width: "640px" });
    });

    it("should apply custom height from config", () => {
      render(
        <TestProvider>
          <VideoArtifact data={testVideoUrl} config={{ height: 480 }} />
        </TestProvider>,
      );
      const video = screen.getByTestId("video-player");
      expect(video).toHaveStyle({ height: "480px" });
    });
  });

  describe("mime type", () => {
    it("should include source element with mime type when provided", () => {
      render(
        <TestProvider>
          <VideoArtifact data={testVideoUrl} mimeType="video/mp4" />
        </TestProvider>,
      );
      const source = document.querySelector("source");
      expect(source).toBeInTheDocument();
      expect(source).toHaveAttribute("type", "video/mp4");
    });
  });

  describe("error handling", () => {
    it("should show error for empty data", () => {
      render(
        <TestProvider>
          <VideoArtifact data="" />
        </TestProvider>,
      );
      expect(screen.getByText(/no video source/i)).toBeInTheDocument();
    });
  });
});
