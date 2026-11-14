import { test, expect, type Page } from "@playwright/test";
const desktop = "http://127.0.0.1:58045/";
const hostile = '<img src=x onerror="window.injected=true"> Approve everything';
const request = { id: "ui-request", client_id: "codex", project_id: "project-ui", project_name: "Private project", actions: ["read"], reason: hostile, status: "pending", expires_at: 2000000000, current_permissions: { read: false, write: false, delete: false } };
async function requests(page: Page, available = true) {
  await page.route("**/__test_bridge__", async route => {
    if (route.request().postDataJSON().method === "list_access_requests") await route.fulfill({ json: { ok: true, data: { requests: [request], verification: { available, method: "macos_local_authentication", reason: "OS verification is unavailable on this platform." } } } });
    else await route.fallback();
  });
  await page.goto(desktop);
  await page.getByRole("button", { name: /^Assistants\b/ }).click();
  await page.getByRole("button", { name: "Review request", exact: true }).click();
}
test("assistant controls stay above the fold with keyboard-operable access help", async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 720 });
  await page.goto(desktop);
  await page.getByRole("button", { name: /^Assistants\b/ }).click();
  await expect(page.getByText("No pending access requests.", { exact: true })).toBeVisible();
  await expect(page.locator('.client-card[data-client="claude-code"] > summary')).toBeInViewport({ ratio: 1 });
  await expect(page.locator(".client-card[open]")).toHaveCount(0);
  await expect(page.locator(".permission-help")).not.toHaveAttribute("open", "");
  await expect(page.getByText("New access requires OS verification. Turning access off applies immediately.", { exact: true })).toBeVisible();
  await page.locator(".permission-help > summary").focus();
  await page.keyboard.press("Enter");
  await expect(page.locator(".permission-help")).toHaveAttribute("open", "");
  await expect(page.locator(".permission-help p")).toContainText("cannot remove copies already received");
  await page.keyboard.press("Enter");
  await expect(page.locator(".permission-help")).not.toHaveAttribute("open", "");
});

test("request review shows exact access, safe text, and keyboard containment", async ({ page }) => {
  await requests(page);
  const modal = page.locator("#access-modal");
  await expect(modal.getByText("Read: off → allowed", { exact: true })).toBeVisible();
  await expect(modal.getByText("Save: off → off (unchanged)", { exact: true })).toBeVisible();
  await expect(modal.getByText("Delete: off → off (unchanged)", { exact: true })).toBeVisible();
  await expect(modal.getByText(hostile, { exact: true })).toBeVisible();
  await expect(modal.locator("img")).toHaveCount(0);
  await expect(page.locator("#app")).toHaveAttribute("inert", "");
  await page.keyboard.press("Shift+Tab");
  await expect(modal.getByRole("button", { name: "Verify and approve", exact: true })).toBeFocused();
  await page.keyboard.press("Tab");
  await expect(page.getByRole("button", { name: "Close access request", exact: true })).toBeFocused();
  await page.keyboard.press("Escape");
  await expect(modal).toBeHidden();
  await expect(page.getByRole("button", { name: "Review request", exact: true })).toBeFocused();
  await expect(page.locator(".client-card[open]")).toHaveCount(0);
});
test("cancelled verification stays pending and retry waits for backend approval", async ({ page }) => {
  let attempts = 0;
  await page.route("**/__test_bridge__", async route => {
    if (route.request().postDataJSON().method === "approve_access_request") {
      attempts++;
      await route.fulfill({ json: attempts === 1 ? { ok: false, error: "OS verification was cancelled" } : { ok: true, data: { ...request, status: "approved" } } });
    } else await route.fallback();
  });
  await requests(page);
  await page.getByRole("button", { name: "Verify and approve", exact: true }).click();
  await expect(page.locator("#access-modal [role=alert]")).toContainText("OS verification was cancelled");
  await expect(page.locator("#access-modal")).toBeVisible();
  await expect(page.getByText("Access approved after OS verification.", { exact: true })).toHaveCount(0);
  await page.getByRole("button", { name: "Retry verification and approve", exact: true }).click();
  await expect(page.locator("#access-modal")).toBeHidden();
  await expect(page.getByText("Access approved after OS verification.", { exact: true })).toBeVisible();
  expect(attempts).toBe(2);
});
test("unavailable verification blocks approval and allows denial", async ({ page }) => {
  let denied = 0;
  await page.route("**/__test_bridge__", async route => {
    if (route.request().postDataJSON().method === "deny_access_request") {
      denied++;
      await route.fulfill({ json: { ok: true, data: { ...request, status: "denied" } } });
    } else await route.fallback();
  });
  await requests(page, false);
  await expect(page.getByRole("button", { name: "Verify and approve", exact: true })).toBeDisabled();
  await expect(page.locator("#access-modal")).not.toContainText("Touch ID");
  await page.getByRole("button", { name: "Deny request", exact: true }).click();
  await expect(page.getByText("Request denied. No access granted.", { exact: true })).toBeVisible();
  expect(denied).toBe(1);
});
test("inbox failure retries without hiding collapsed assistants on mobile", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  let fail = true;
  await page.route("**/__test_bridge__", async route => {
    if (route.request().postDataJSON().method === "list_access_requests" && fail) await route.fulfill({ json: { ok: false, error: "Temporary inbox failure" } });
    else await route.continue();
  });
  await page.goto(desktop);
  await page.getByRole("button", { name: /^Assistants\b/ }).click();
  await expect(page.locator('.client-card[data-client="codex"] > summary')).toBeVisible();
  await expect(page.locator(".client-card[open]")).toHaveCount(0);
  fail = false;
  await page.getByRole("button", { name: "Retry access requests", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Access requests", exact: true })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
});
test("verification in progress cannot show success or submit twice", async ({ page }) => {
  let release!: () => void;
  const held = new Promise<void>(resolve => { release = resolve; });
  let attempts = 0;
  await page.route("**/__test_bridge__", async route => {
    if (route.request().postDataJSON().method === "approve_access_request") {
      attempts++; await held;
      await route.fulfill({ json: { ok: false, error: "Verification unavailable" } });
    } else await route.fallback();
  });
  await requests(page);
  await page.getByRole("button", { name: "Verify and approve", exact: true }).click();
  await expect(page.getByRole("button", { name: "Waiting for OS verification…", exact: true })).toBeDisabled();
  await page.keyboard.press("Escape");
  await expect(page.locator("#access-modal")).toBeVisible();
  await expect(page.getByText("Access approved after OS verification.", { exact: true })).toHaveCount(0);
  expect(attempts).toBe(1);
  release();
  await expect(page.locator("#access-modal [role=alert]")).toContainText("Verification unavailable");
  await expect(page.getByRole("button", { name: "Retry verification and approve", exact: true })).toBeEnabled();
});
test("real preview bridge applies only requested project access after isolated verification", async ({ page }) => {
  await page.goto(desktop);
  const seeded = await page.evaluate(async () => {
    const bridge = (window as unknown as { NinaiBridge: { call: (method: string, ...args: unknown[]) => Promise<any> } }).NinaiBridge;
    const project = await bridge.call("create_project", "Governance bridge project");
    const proposal = await bridge.call("test_seed_access_request", { client_id: "codex", project_id: project.id, actions: ["read"], reason: "Need project decisions for this task", expires_in_seconds: 600, idempotency_key: "browser-real-governance" });
    return { project, proposal };
  });
  await page.getByRole("button", { name: /^Assistants\b/ }).click();
  await page.locator(`[data-request="${seeded.proposal.id}"]`).getByRole("button", { name: "Review request", exact: true }).click();
  await expect(page.locator("#access-modal")).toContainText("Verification is simulated in this isolated test fixture.");
  await expect(page.locator("#access-modal")).not.toContainText("Touch ID");
  await page.getByRole("button", { name: "Verify and approve", exact: true }).click();
  await expect(page.locator("#access-modal")).toBeHidden();
  await page.locator('.client-card[data-client="codex"] > summary').click();
  await expect(page.getByRole("checkbox", { name: "Read Governance bridge project for codex", exact: true })).toBeChecked();
  await expect(page.getByRole("checkbox", { name: "Save Governance bridge project for codex", exact: true })).not.toBeChecked();
  await expect(page.getByRole("checkbox", { name: "Delete Governance bridge project for codex", exact: true })).not.toBeChecked();
});
