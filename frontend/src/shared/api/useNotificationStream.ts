import { useEffect } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { API_BASE } from "./client";

export function useNotificationStream(enabled: boolean) {
  const queryClient = useQueryClient();

  useEffect(() => {
    if (!enabled) {
      return;
    }
    const controller = new AbortController();
    let stopped = false;

    async function read() {
      while (!stopped) {
        try {
          const token = localStorage.getItem("access_token");
          const response = await fetch(`${API_BASE}/notifications/stream/`, {
            headers: {
              Authorization: `Bearer ${token}`,
              Accept: "text/event-stream",
            },
            signal: controller.signal,
          });
          if (!response.ok || !response.body) {
            await wait(2000);
            continue;
          }
          const reader = response.body.getReader();
          const decoder = new TextDecoder();
          let buffer = "";
          while (!stopped) {
            const { value, done } = await reader.read();
            if (done) {
              await wait(2000);
              break;
            }
            buffer += decoder.decode(value, { stream: true });
            const frames = buffer.split("\n\n");
            buffer = frames.pop() ?? "";
            if (frames.some((frame) => frame.includes("event: notification"))) {
              await queryClient.invalidateQueries({ queryKey: ["notifications"] });
            }
          }
        } catch {
          if (stopped) {
            return;
          }
          await wait(2000);
        }
      }
    }

    void read();
    return () => {
      stopped = true;
      controller.abort();
    };
  }, [enabled, queryClient]);
}

function wait(ms: number) {
  return new Promise((resolve) => {
    setTimeout(resolve, ms);
  });
}
