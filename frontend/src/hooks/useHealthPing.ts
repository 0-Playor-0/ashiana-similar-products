import { useEffect, useState } from "react";
import { getHealth } from "../api/client";

// §10.3 cold start: ping /health on load. If there's no response within 3s,
// show a non-blocking banner and keep retrying with backoff until it
// succeeds. A free-tier API that's been asleep can take up to about a
// minute to wake, so retries aren't capped — they just back off.
const BANNER_DELAY_MS = 3000;
const REQUEST_TIMEOUT_MS = 8000;
const RETRY_BASE_MS = 1000;
const RETRY_MAX_MS = 15000;

export function useHealthPing(): { ready: boolean; showBanner: boolean } {
  const [ready, setReady] = useState(false);
  const [showBanner, setShowBanner] = useState(false);

  useEffect(() => {
    let cancelled = false;
    let retryTimer: ReturnType<typeof setTimeout> | undefined;
    const bannerTimer = setTimeout(() => {
      if (!cancelled) setShowBanner(true);
    }, BANNER_DELAY_MS);

    let attempt = 0;

    async function ping() {
      const controller = new AbortController();
      const abortTimer = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
      try {
        await getHealth(controller.signal);
        if (cancelled) return;
        setReady(true);
        setShowBanner(false);
        clearTimeout(bannerTimer);
      } catch {
        if (cancelled) return;
        attempt += 1;
        const delay = Math.min(RETRY_BASE_MS * 2 ** (attempt - 1), RETRY_MAX_MS);
        retryTimer = setTimeout(ping, delay);
      } finally {
        clearTimeout(abortTimer);
      }
    }

    ping();

    return () => {
      cancelled = true;
      clearTimeout(bannerTimer);
      if (retryTimer) clearTimeout(retryTimer);
    };
  }, []);

  return { ready, showBanner: showBanner && !ready };
}
