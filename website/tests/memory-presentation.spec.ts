import { test, expect, type Page } from "@playwright/test";

const desktop = "http://127.0.0.1:58045/";

async function seed(page: Page, content: string, source: string) {
  await page.goto(desktop);
  await expect(page.getByRole("heading", { name: "Home", exact: true })).toBeVisible();
  return await page.evaluate(async fixture => {
    const api = (window as any).pywebview.api;
    const saved = await api.add_memory(fixture.content, "event", "project", fixture.source, "normal", null);
    if (!saved.ok) throw new Error(saved.error);
    return saved.data.id as string;
  }, { content, source });
}

async function stored(page: Page, id: string) {
  return await page.evaluate(async memoryId => (await (window as any).pywebview.api.get_memory(memoryId)).data, id);
}

test("legacy JSON errors use a readable card while exact original text and provenance remain available", async ({ page }) => {
  const content = 'Tool outcome from mcp__database__run_select_query: {"result":{"status":"error","message":"SELECT synthetic_column failed <img src=x onerror=alert(1)>"}}';
  const source = "claude-hook://synthetic-error/memory-card";
  const id = await seed(page, content, source);
  const before = await stored(page, id);
  await page.reload();
  const card = page.locator(`.today-item[data-id="${id}"]`);
  await expect(card).toHaveAttribute("aria-label", "Open memory: Captured tool error");
  await expect(card).toContainText("Assistant capture");
  await expect(card).not.toContainText("SELECT synthetic_column");
  await expect(card.locator("a,button")).toHaveCount(0);
  await card.focus();
  await page.keyboard.press("Enter");
  const drawer = page.locator("#drawer");
  await expect(drawer).toBeVisible();
  await expect(drawer.getByText(source, { exact: true })).toBeVisible();
  const original = drawer.locator(".memory-original");
  await expect(original).not.toHaveAttribute("open", "");
  await expect(original.locator("pre")).toBeHidden();
  await original.locator("summary").focus();
  await page.keyboard.press("Enter");
  await expect(original.locator("pre")).toHaveText(content);
  await expect(original.locator("img,script")).toHaveCount(0);
  expect(await stored(page, id)).toEqual(before);
});

test("truncated legacy failures stay reviewable in Memories without displaying a raw query preview", async ({ page }) => {
  const content = 'Tool outcome from mcp__database__run_select_query: {"result":{"status":"error","message":"SELECT synthetic_truncated_query';
  const id = await seed(page, content, "claude-hook://synthetic-truncated/card");
  await page.getByRole("button", { name: /^Memories\b/ }).click();
  const row = page.locator(`.mem-row[data-id="${id}"]`);
  await expect(row).toContainText("Captured tool error");
  await expect(row).not.toContainText("synthetic_truncated_query");
  await row.click();
  await page.locator(".memory-original summary").click();
  await expect(page.locator(".memory-original pre")).toHaveText(content);
  expect((await stored(page, id)).content).toBe(content);
});

test("normal notes keep their accessible labels and links open only in details without mobile overflow", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  const content = "Ordinary saved decision: " + "a".repeat(500);
  const source = "https://example.com/synthetic-source";
  const id = await seed(page, content, source);
  await page.reload();
  const home = page.locator(`.today-item[data-id="${id}"]`);
  await expect(home).toHaveAttribute("aria-label", "Open memory: " + content);
  await expect(home.locator("a")).toHaveCount(0);
  await home.click();
  await expect(page.locator("#drawer .drawer__content")).toHaveText(content);
  await expect(page.locator("#drawer a.source-tag")).toHaveAttribute("href", source);
  await expect(page.locator("#drawer .memory-original")).toHaveCount(0);
  await page.keyboard.press("Escape");
  await page.getByRole("button", { name: /^Memories\b/ }).click();
  const row = page.locator(`.mem-row[data-id="${id}"]`);
  await expect(row).toHaveAttribute("aria-label", "Open memory: " + content);
  await expect(row.locator("a")).toHaveCount(0);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
});

test("compact successful captures lose the tool prefix and keep a bounded verbatim outcome preview", async ({ page }) => {
  const content = ("Tool outcome from mcp__github__merge_pull_request: result.status=merged; result.decision=Keep reversible changes. " + "More recorded detail. ".repeat(25)).trim();
  const id = await seed(page, content, "claude-hook://synthetic-success/card");
  await page.reload();
  const card = page.locator(`.today-item[data-id="${id}"]`);
  await expect(card).toContainText("Assistant capture");
  await expect(card).toContainText("Status: merged; Decision: Keep reversible changes.");
  await expect(card).not.toContainText("Tool outcome from");
  expect((await card.locator(".today-item__content").textContent())!.length).toBeLessThanOrEqual(280);
  await card.click();
  await page.locator(".memory-original summary").click();
  await expect(page.locator(".memory-original pre")).toHaveText(content);
  expect((await stored(page, id)).content).toBe(content);
});
