import { ApiError } from "../api/client";

// §10.3: "say what happened and what to do... Never a generic 'Something
// went wrong.'" Every message names the view and a concrete reason.
export function describeError(view: string, error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 404) return `Couldn't load ${view}. It isn't in the catalog.`;
    if (error.status >= 500) return `Couldn't load ${view}. The server hit an error.`;
    return `Couldn't load ${view}. ${error.detail}.`;
  }
  if (error instanceof DOMException && error.name === "AbortError") {
    return `Couldn't load ${view}. The request timed out.`;
  }
  return `Couldn't load ${view}. The server didn't respond. Retry.`;
}
