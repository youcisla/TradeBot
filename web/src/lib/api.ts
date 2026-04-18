/**
 * Shared API helpers — fire-and-forget commands and typed fetch utilities.
 * No WebSocket logic here; WS stays in AppShellProvider only.
 */

/** Fire-and-forget POST to the commands API. */
export async function sendCommand(
  action: string,
  params?: Record<string, unknown>
): Promise<void> {
  await fetch("/api/commands", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ action, ...params }),
  }).catch(() => {
    // Command failures are logged by the bot; don't surface to UI
  });
}