import { test, expect, type Page } from "@playwright/test";

const desktop = "http://127.0.0.1:58045/";
const decision = "Browser regression: keep every migration reversible.";

async function startDecision(page: Page, projectName: string) {
  await page.goto(desktop);
  await page.getByRole("button", { name: "Add a project decision", exact: true }).click();
  await page.locator("#add-content").fill(decision);
  if (await page.locator("#new-project-details").getAttribute("open") === null) {
    await page.getByText("Create a project", { exact: true }).click();
  }
  await page.getByLabel("Project name", { exact: true }).fill(projectName);
  await page.getByRole("button", { name: "Create project", exact: true }).click();
  await expect(page.locator("#add-project option:checked")).toHaveText(projectName);
}

test("guide rejects an unassigned save, contains keyboard focus, and saves once under a named project", async ({ page }) => {
  await page.goto(desktop);
  await page.getByRole("button", { name: "Add a project decision", exact: true }).click();
  await page.locator("#add-content").fill(decision);
  await page.getByRole("button", { name: "Save memory", exact: true }).click();
  await expect(page.getByRole("alert")).toContainText("Choose or create a named project");
  await expect(page.locator("#add-content")).toHaveValue(decision);
  await expect(page.locator("#app")).toHaveAttribute("inert", "");
  await page.locator("#add-submit").focus();
  await page.keyboard.press("Tab");
  await expect(page.locator("#add-close")).toBeFocused();
  await page.keyboard.press("Shift+Tab");
  await expect(page.locator("#add-submit")).toBeFocused();
  await page.getByLabel("Project name", { exact: true }).fill("Browser first success");
  await page.getByRole("button", { name: "Create project", exact: true }).click();
  await page.getByRole("button", { name: "Save memory", exact: true }).click();
  await expect(page.locator("#add-modal")).toBeHidden();
  await expect(page.getByRole("button", { name: "✓ Save a decision", exact: true })).toBeVisible();
  await expect(page.locator("#app")).not.toHaveAttribute("inert", "");
});

test("recall and revocation instructions do not paste the saved answer into the assistant", async ({ page }) => {
  await startDecision(page, "Browser private prompt");
  await page.getByRole("button", { name: "Save memory", exact: true }).click();
  await page.getByLabel("Assistant to test", { exact: true }).selectOption("codex");
  await page.getByRole("button", { name: "3. Test recall", exact: true }).click();
  await expect(page.locator("#setup-request")).toHaveValue(/query ""/);
  await expect(page.locator("#setup-request")).not.toHaveValue(new RegExp("keep every migration"));
  await page.getByRole("button", { name: "4. Test revocation", exact: true }).click();
  await expect(page.locator("#setup-request")).toHaveValue(/Make a fresh tool call/);
  await expect(page.locator("#setup-request")).not.toHaveValue(new RegExp("keep every migration"));
});

test("a failed save retains the draft and retry creates only one decision", async ({ page }) => {
  await startDecision(page, "Browser retry");
  const retryDecision = "Unique retry decision: use reversible changes.";
  await page.locator("#add-content").fill(retryDecision);
  let failed = false;
  await page.route("**/__test_bridge__", async route => {
    if (route.request().postDataJSON().method === "add_memory" && !failed) {
      failed = true;
      await route.fulfill({ json: { ok: false, error: "Synthetic write failure" } });
    } else await route.continue();
  });
  await page.getByRole("button", { name: "Save memory", exact: true }).click();
  await expect(page.getByRole("alert")).toContainText("Synthetic write failure");
  await expect(page.locator("#add-content")).toHaveValue(retryDecision);
  await expect(page.getByRole("button", { name: "Save memory", exact: true })).toBeEnabled();
  await page.getByRole("button", { name: "Save memory", exact: true }).click();
  await expect(page.locator("#add-modal")).toBeHidden();
  await expect(page.locator("#setup-project option:checked")).toHaveText("Browser retry");
  await page.getByRole("button", { name: /^Memories\b/ }).click();
  await page.getByRole("searchbox", { name: "Search memories" }).fill(retryDecision);
  await expect(page.getByRole("button", { name: `Open memory: ${retryDecision}`, exact: true })).toHaveCount(1);
});

test("a delayed earlier save cannot erase a newer draft", async ({ page }) => {
  await startDecision(page, "Browser delayed write");
  let release!: () => void;
  let entered!: () => void;
  const held = new Promise<void>(resolve => { release = resolve; });
  const arrived = new Promise<void>(resolve => { entered = resolve; });
  let intercepted = false;
  await page.route("**/__test_bridge__", async route => {
    if (route.request().postDataJSON().method === "add_memory" && !intercepted) {
      intercepted = true; entered(); await held;
    }
    await route.continue();
  });
  const saved = page.waitForResponse(response => response.url().endsWith("/__test_bridge__") && response.request().postDataJSON().method === "add_memory");
  await page.getByRole("button", { name: "Save memory", exact: true }).click();
  await arrived;
  await page.keyboard.press("Escape");
  await expect(page.locator("#add-modal")).toBeHidden();
  await page.getByRole("button", { name: "Add a project decision", exact: true }).click();
  await page.locator("#add-content").fill("Newer unsaved draft must survive.");
  release(); await saved;
  await expect(page.getByText("Memory saved.", { exact: true })).toBeVisible();
  await expect(page.locator("#add-modal")).toBeVisible();
  await expect(page.locator("#add-content")).toHaveValue("Newer unsaved draft must survive.");
  await expect(page.getByRole("button", { name: "Save memory", exact: true })).toBeEnabled();
});

test("a setup-status failure keeps memories available and can be retried", async ({ page }) => {
  await startDecision(page, "Browser status recovery");
  await page.getByRole("button", { name: "Save memory", exact: true }).click();
  await expect(page.locator("#add-modal")).toBeHidden();
  let fail = true;
  await page.route("**/__test_bridge__", async route => {
    if (route.request().postDataJSON().method === "setup_status" && fail) await route.fulfill({ json: { ok: false, error: "Synthetic status failure" } });
    else await route.continue();
  });
  await page.goto(desktop);
  await expect(page.getByRole("button", { name: "Retry setup guide", exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Recent memories", exact: true })).toBeVisible();
  fail = false;
  await page.getByRole("button", { name: "Retry setup guide", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Your first private handoff", exact: true })).toBeVisible();
});

test("memory drawer contains keyboard focus and returns it on Escape", async ({ page }) => {
  await startDecision(page, "Browser drawer");
  const content = "Unique drawer sample: keep updates reversible.";
  await page.locator("#add-content").fill(content);
  await page.getByRole("button", { name: "Save memory", exact: true }).click();
  await expect(page.locator("#add-modal")).toBeHidden();
  await page.getByRole("button", { name: /^Memories\b/ }).click();
  const memory = page.getByRole("button", { name: `Open memory: ${content}`, exact: true });
  await memory.click();
  await expect(page.locator("#drawer-close")).toBeFocused();
  await expect(page.locator("#drawer-actions").getByRole("button", { name: "Delete", exact: true })).toBeVisible();
  await page.keyboard.press("Shift+Tab");
  await expect(page.locator("#drawer-actions").getByRole("button", { name: "Delete", exact: true })).toBeFocused();
  await page.keyboard.press("Tab");
  await expect(page.locator("#drawer-close")).toBeFocused();
  await page.keyboard.press("Escape");
  await expect(page.locator("#drawer")).toBeHidden();
  await expect(memory).toBeFocused();
});

test("failed permission update rolls back its switch and can be retried", async ({ page }) => {
  await startDecision(page, "Browser permission retry");
  await page.getByRole("button", { name: "Save memory", exact: true }).click();
  await expect(page.locator("#add-modal")).toBeHidden();
  await page.getByRole("button", { name: /^Assistants\b/ }).click();
  const read = page.getByRole("checkbox", { name: "Read Browser permission retry for codex", exact: true });
  await expect(read).not.toBeChecked();
  let failed = false;
  await page.route("**/__test_bridge__", async route => {
    if (route.request().postDataJSON().method === "set_project_permission" && !failed) {
      failed = true;
      await route.fulfill({ json: { ok: false, error: "Synthetic permission failure" } });
    } else await route.continue();
  });
  await read.click();
  await expect(page.getByText("Synthetic permission failure", { exact: true })).toBeVisible();
  await expect(read).not.toBeChecked();
  await expect(read).toBeEnabled();
  await read.click();
  await expect(read).toBeChecked();
  await expect(page.getByText("Permission updated. Applies to future requests.", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Setup guide", exact: true }).click();
  await page.getByLabel("Assistant to test", { exact: true }).selectOption("codex");
  await expect(page.getByRole("button", { name: "✓ Choose access", exact: true })).toBeVisible();
});
