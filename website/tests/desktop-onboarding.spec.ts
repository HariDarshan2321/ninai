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
  await expect(page.locator("#drawer-body").getByText("Project: Browser drawer", { exact: true })).toBeVisible();
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
  await page.locator('.client-card[data-client="codex"] > summary').click();
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

test("assistant cards collapse controls while retaining a live grant summary", async ({ page }) => {
  await startDecision(page, "Browser collapsed access");
  await page.getByRole("button", { name: "Save memory", exact: true }).click();
  await expect(page.locator("#add-modal")).toBeHidden();
  await page.getByRole("button", { name: /^Assistants\b/ }).click();
  const card = page.locator('.client-card[data-client="codex"]');
  await expect(card).not.toHaveAttribute("open", "");
  const read = card.getByRole("checkbox", { name: "Read Browser collapsed access for codex", exact: true });
  await expect(read).toBeHidden();
  await card.locator(":scope > summary").focus();
  await page.keyboard.press("Enter");
  await expect(read).toBeVisible();
  await expect(read).not.toBeChecked();
  await read.check();
  await expect(read).toBeEnabled();
  await expect(card.locator(".client-card__granted")).toContainText(/Access grants: [1-9]\d* read/);
  await card.locator(":scope > summary").click();
  await expect(read).toBeHidden();
  await expect(card.locator(".client-card__granted")).toBeVisible();
  await card.locator(":scope > summary").click();
  await expect(read).toBeChecked();
  await page.getByRole("button", { name: "Check connections again", exact: true }).click();
  await expect(read).toBeVisible();
  await expect(read).toBeChecked();
  await expect(card.getByText("Read other memory areas", { exact: true }).locator("..")).not.toHaveAttribute("open", "");
});

test("every desktop page and Help remain usable at a narrow viewport", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(desktop);
  const pages = [
    [/^Memories\b/, "Memories"], [/^Origins\b/, "Where memories came from"],
    [/^Agent sessions\b/, "Agent sessions"], [/^Assistants\b/, "Connected assistants"],
    [/^Sharing history\b/, "Sharing history"], [/^Help & feedback$/, "Help & feedback"],
  ] as const;
  for (const [button, title] of pages) {
    await page.getByRole("button", { name: button }).click();
    await expect(page.getByRole("heading", { name: title, exact: true, level: 1 })).toBeVisible();
    await page.locator(".screen.is-active .spinner").waitFor({ state: "hidden" });
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBeTruthy();
  }
  await page.getByText("What is on each page?", { exact: true }).click();
  await expect(page.getByText("Search, add, edit, and delete saved facts and decisions. Each memory keeps its origin.", { exact: true })).toBeVisible();
  await expect(page.getByRole("link", { name: "Email help & feedback", exact: true })).toHaveAttribute("href", /^mailto:hello@ninai.io/);
  await page.getByRole("button", { name: "Open setup guide", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Home", exact: true, level: 1 })).toBeVisible();
});

test("archive failures are visible and the action can be retried", async ({ page }) => {
  await page.goto(desktop);
  await page.getByRole("button", { name: /^Agent sessions\b/ }).click();
  const toggle = page.getByRole("button", { name: /^(Enable|Disable) archive$/ });
  const before = await toggle.textContent();
  let failed = false;
  await page.route("**/__test_bridge__", async route => {
    if (route.request().postDataJSON().method === "set_capture_enabled" && !failed) {
      failed = true;
      await route.fulfill({ json: { ok: false, error: "Synthetic archive failure" } });
    } else await route.continue();
  });
  await toggle.click();
  await expect(page.getByText("Synthetic archive failure", { exact: true })).toBeVisible();
  await expect(toggle).toBeEnabled();
  await expect(toggle).toHaveText(before!);
  await toggle.click();
  await expect(toggle).not.toHaveText(before!);
});

test("update checks require an explicit action and recover after a failure", async ({ page }) => {
  let checks = 0;
  await page.route("**/__test_bridge__", async route => {
    if (route.request().postDataJSON().method === "check_for_updates") {
      checks++;
      if (checks === 1) await route.fulfill({ json: { ok: false, error: "Synthetic offline check" } });
      else await route.fulfill({ json: { ok: true, data: { status: "update_available", message: "Version 99.0.0 is available.", release_url: "https://github.com/HariDarshan2321/ninai/releases/tag/v99.0.0" } } });
    } else await route.continue();
  });
  await page.goto(desktop);
  await page.getByRole("button", { name: "Help & feedback", exact: true }).click();
  await page.getByText("Updating Ninai and recovering data", { exact: true }).click();
  await expect(page.getByText(/^Installed version:/)).toBeVisible();
  expect(checks).toBe(0);
  const check = page.getByRole("button", { name: "Check for updates", exact: true });
  await check.click();
  await expect(page.getByRole("status").filter({ hasText: "Could not check for updates" })).toBeVisible();
  await expect(check).toBeEnabled();
  await check.click();
  await expect(page.getByRole("link", { name: "Read release notes", exact: true })).toHaveAttribute("href", /v99.0.0$/);
  expect(checks).toBe(2);
});

test("an older search response cannot replace the latest search results", async ({ page }) => {
  await startDecision(page, "Browser search race");
  await page.getByRole("button", { name: "Save memory", exact: true }).click();
  await expect(page.locator("#add-modal")).toBeHidden();
  await page.getByRole("button", { name: /^Memories\b/ }).click();
  let release!: () => void;
  let entered!: () => void;
  const held = new Promise<void>(resolve => { release = resolve; });
  const arrived = new Promise<void>(resolve => { entered = resolve; });
  await page.route("**/__test_bridge__", async route => {
    const payload = route.request().postDataJSON();
    if (payload.method === "search" && payload.args[0] === "reversible") {
      const response = await route.fetch();
      entered(); await held;
      await route.fulfill({ response });
    } else await route.continue();
  });
  const search = page.getByRole("searchbox", { name: "Search memories", exact: true });
  await search.fill("reversible"); await arrived;
  await search.fill("unmatchable-search-race");
  await expect(page.getByText("No memories match", { exact: true })).toBeVisible();
  const stale = page.waitForResponse(response => response.url().endsWith("/__test_bridge__") && response.request().postDataJSON().args?.[0] === "reversible");
  release(); await stale;
  await expect(page.getByText("No memories match", { exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: `Open memory: ${decision}`, exact: true })).toHaveCount(0);
});

test("page load failures offer a working retry", async ({ page }) => {
  let failed = false;
  await page.goto(desktop);
  await page.route("**/__test_bridge__", async route => {
    if (route.request().postDataJSON().method === "sources" && !failed) {
      failed = true;
      await route.fulfill({ json: { ok: false, error: "Synthetic origins failure" } });
    } else await route.continue();
  });
  await page.getByRole("button", { name: /^Origins\b/ }).click();
  await expect(page.getByText("Synthetic origins failure", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Try again", exact: true }).click();
  await expect(page.getByText("This page groups memories by where Ninai received them. Only sources already present on this computer appear here.", { exact: true })).toBeVisible();
});

test("a full search page discloses its result limit", async ({ page }) => {
  await startDecision(page, "Browser result limit");
  await page.getByRole("button", { name: "Save memory", exact: true }).click();
  await expect(page.locator("#add-modal")).toBeHidden();
  await page.route("**/__test_bridge__", async route => {
    if (route.request().postDataJSON().method === "search") {
      const response = await route.fetch();
      const data = await response.json();
      const memory = data.data[0];
      await route.fulfill({ json: { ok: true, data: Array.from({ length: 200 }, (_, i) => ({ ...memory, id: `limit-${i}` })) } });
    } else await route.continue();
  });
  await page.getByRole("button", { name: /^Memories\b/ }).click();
  await expect(page.getByText("Showing the latest 200 memories matching your search and selected filters.", { exact: false })).toBeVisible();
  await expect(page.locator(".mem-row")).toHaveCount(200);
});

test("memory filters are sent to the backend before results are limited", async ({ page }) => {
  await startDecision(page, "Browser server filters");
  const content = "Server filter decision: keep search complete before limiting results.";
  await page.locator("#add-content").fill(content);
  await page.getByRole("button", { name: "Save memory", exact: true }).click();
  await expect(page.locator("#add-modal")).toBeHidden();
  await page.getByRole("button", { name: /^Memories\b/ }).click();
  const result = page.getByRole("button", { name: `Open memory: ${content}`, exact: true });
  await expect(result).toBeVisible();
  const filterRequest = page.waitForRequest(request => {
    if (!request.url().endsWith("/__test_bridge__") || request.method() !== "POST") return false;
    const payload = request.postDataJSON();
    return payload.method === "search" && payload.args[1] === "project";
  });
  await page.getByLabel("Filter by memory area", { exact: true }).selectOption("project");
  await filterRequest;
  await expect(result).toBeVisible();
  const typeRequest = page.waitForRequest(request => {
    if (!request.url().endsWith("/__test_bridge__") || request.method() !== "POST") return false;
    const payload = request.postDataJSON();
    return payload.method === "search" && payload.args[1] === "project" && payload.args[2] === "decision";
  });
  await page.getByLabel("Filter by type", { exact: true }).selectOption("decision");
  await typeRequest;
  await expect(result).toBeVisible();
  await page.getByLabel("Filter by type", { exact: true }).selectOption("preference");
  await expect(page.getByText("No memories match", { exact: true })).toBeVisible();
  await expect(result).toHaveCount(0);
});
