/**
 * AudioArtifact Tests
 *
 * TDD tests for audio artifact rendering component.
 */

import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import { AudioArtifact } from "./AudioArtifact";

import { TestProvider } from "@/test-utils";

describe("AudioArtifact", () => {
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  const testAudioUrl = "https://example.com/audio.mp3";
  const testBase64Audio = "data:audio/mpeg;base64,SGVsbG8gV29ybGQ=";

  describe("rendering", () => {
    it("should render audio element with controls by default", () => {
      render(
        <TestProvider>
          <AudioArtifact data={testAudioUrl} />
        </TestProvider>,
      );
      const audio = screen.getByTestId("audio-player");
      expect(audio).toBeInTheDocument();
      expect(audio).toHaveAttribute("controls");
    });

    it("should set src attribute from data prop", () => {
      render(
        <TestProvider>
          <AudioArtifact data={testAudioUrl} />
        </TestProvider>,
      );
      const audio = screen.getByTestId("audio-player");
      expect(audio).toHaveAttribute("src", testAudioUrl);
    });

    it("should render title if provided", () => {
      render(
        <TestProvider>
          <AudioArtifact data={testAudioUrl} title="My Audio Track" />
        </TestProvider>,
      );
      expect(screen.getByText("My Audio Track")).toBeInTheDocument();
    });

    it("should handle base64 data URLs", () => {
      render(
        <TestProvider>
          <AudioArtifact data={testBase64Audio} />
        </TestProvider>,
      );
      const audio = screen.getByTestId("audio-player");
      expect(audio).toHaveAttribute("src", testBase64Audio);
    });
  });

  describe("config options", () => {
    it("should not autoplay by default", () => {
      render(
        <TestProvider>
          <AudioArtifact data={testAudioUrl} />
        </TestProvider>,
      );
      const audio = screen.getByTestId("audio-player");
      expect(audio).not.toHaveAttribute("autoplay");
    });

    it("should enable autoplay when configured", () => {
      render(
        <TestProvider>
          <AudioArtifact data={testAudioUrl} config={{ autoplay: true }} />
        </TestProvider>,
      );
      const audio = screen.getByTestId("audio-player");
      expect(audio).toHaveAttribute("autoplay");
    });

    it("should enable loop when configured", () => {
      render(
        <TestProvider>
          <AudioArtifact data={testAudioUrl} config={{ loop: true }} />
        </TestProvider>,
      );
      const audio = screen.getByTestId("audio-player");
      expect(audio).toHaveAttribute("loop");
    });

    it("should enable muted when configured", () => {
      render(
        <TestProvider>
          <AudioArtifact data={testAudioUrl} config={{ muted: true }} />
        </TestProvider>,
      );
      const audio = screen.getByTestId("audio-player") as HTMLAudioElement;
      expect(audio.muted).toBe(true);
    });

    it("should hide controls when configured", () => {
      render(
        <TestProvider>
          <AudioArtifact data={testAudioUrl} config={{ controls: false }} />
        </TestProvider>,
      );
      const audio = screen.getByTestId("audio-player");
      expect(audio).not.toHaveAttribute("controls");
    });

    it("should set preload attribute when configured", () => {
      render(
        <TestProvider>
          <AudioArtifact data={testAudioUrl} config={{ preload: "metadata" }} />
        </TestProvider>,
      );
      const audio = screen.getByTestId("audio-player");
      expect(audio).toHaveAttribute("preload", "metadata");
    });
  });

  describe("mime type", () => {
    it("should include source element with mime type when provided", () => {
      render(
        <TestProvider>
          <AudioArtifact data={testAudioUrl} mimeType="audio/mpeg" />
        </TestProvider>,
      );
      const source = document.querySelector("source");
      expect(source).toBeInTheDocument();
      expect(source).toHaveAttribute("type", "audio/mpeg");
    });
  });

  describe("error handling", () => {
    it("should show error for empty data", () => {
      render(
        <TestProvider>
          <AudioArtifact data="" />
        </TestProvider>,
      );
      expect(screen.getByText(/no audio source/i)).toBeInTheDocument();
    });
  });
});
