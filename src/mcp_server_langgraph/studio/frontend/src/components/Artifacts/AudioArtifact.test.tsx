/**
 * AudioArtifact Tests
 *
 * TDD tests for audio artifact rendering component.
 */

import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { AudioArtifact } from "./AudioArtifact";

describe("AudioArtifact", () => {
  const testAudioUrl = "https://example.com/audio.mp3";
  const testBase64Audio = "data:audio/mpeg;base64,SGVsbG8gV29ybGQ=";

  describe("rendering", () => {
    it("should render audio element with controls by default", () => {
      render(<AudioArtifact data={testAudioUrl} />);
      const audio = screen.getByTestId("audio-player");
      expect(audio).toBeInTheDocument();
      expect(audio).toHaveAttribute("controls");
    });

    it("should set src attribute from data prop", () => {
      render(<AudioArtifact data={testAudioUrl} />);
      const audio = screen.getByTestId("audio-player");
      expect(audio).toHaveAttribute("src", testAudioUrl);
    });

    it("should render title if provided", () => {
      render(<AudioArtifact data={testAudioUrl} title="My Audio Track" />);
      expect(screen.getByText("My Audio Track")).toBeInTheDocument();
    });

    it("should handle base64 data URLs", () => {
      render(<AudioArtifact data={testBase64Audio} />);
      const audio = screen.getByTestId("audio-player");
      expect(audio).toHaveAttribute("src", testBase64Audio);
    });
  });

  describe("config options", () => {
    it("should not autoplay by default", () => {
      render(<AudioArtifact data={testAudioUrl} />);
      const audio = screen.getByTestId("audio-player");
      expect(audio).not.toHaveAttribute("autoplay");
    });

    it("should enable autoplay when configured", () => {
      render(<AudioArtifact data={testAudioUrl} config={{ autoplay: true }} />);
      const audio = screen.getByTestId("audio-player");
      expect(audio).toHaveAttribute("autoplay");
    });

    it("should enable loop when configured", () => {
      render(<AudioArtifact data={testAudioUrl} config={{ loop: true }} />);
      const audio = screen.getByTestId("audio-player");
      expect(audio).toHaveAttribute("loop");
    });

    it("should enable muted when configured", () => {
      render(<AudioArtifact data={testAudioUrl} config={{ muted: true }} />);
      const audio = screen.getByTestId("audio-player") as HTMLAudioElement;
      expect(audio.muted).toBe(true);
    });

    it("should hide controls when configured", () => {
      render(
        <AudioArtifact data={testAudioUrl} config={{ controls: false }} />,
      );
      const audio = screen.getByTestId("audio-player");
      expect(audio).not.toHaveAttribute("controls");
    });

    it("should set preload attribute when configured", () => {
      render(
        <AudioArtifact data={testAudioUrl} config={{ preload: "metadata" }} />,
      );
      const audio = screen.getByTestId("audio-player");
      expect(audio).toHaveAttribute("preload", "metadata");
    });
  });

  describe("mime type", () => {
    it("should include source element with mime type when provided", () => {
      render(<AudioArtifact data={testAudioUrl} mimeType="audio/mpeg" />);
      const source = document.querySelector("source");
      expect(source).toBeInTheDocument();
      expect(source).toHaveAttribute("type", "audio/mpeg");
    });
  });

  describe("error handling", () => {
    it("should show error for empty data", () => {
      render(<AudioArtifact data="" />);
      expect(screen.getByText(/no audio source/i)).toBeInTheDocument();
    });
  });
});
