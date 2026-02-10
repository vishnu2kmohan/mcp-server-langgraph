import { vi } from "vitest";

export const mockDispatch = vi.fn();
export const mockNavigate = vi.fn();

// Helper to create a mock ReadableStream that yields SSE chunks
export function createMockSSEStream(
  chunks: string[],
): ReadableStream<Uint8Array> {
  const encoder = new TextEncoder();
  let index = 0;

  return new ReadableStream({
    pull(controller) {
      if (index < chunks.length) {
        controller.enqueue(encoder.encode(chunks[index]));
        index++;
      } else {
        controller.close();
      }
    },
  });
}

// Helper to create a mock Response with SSE stream
export function createMockSSEResponse(
  chunks: string[],
  _ok = true,
  status = 200,
): Response {
  const stream = createMockSSEStream(chunks);
  return new Response(stream, {
    status,
    headers: { "Content-Type": "text/event-stream" },
  });
}
