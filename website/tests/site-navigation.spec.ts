import { expect, test } from "@playwright/test";

const site = "http://127.0.0.1:3034";

test("Help opens the support page and Security deep-links to the reporting instructions", async ({ page }) => {
  await page.goto(site);
  const header = page.getByRole("banner");
  await header.getByRole("link", { name: "Help", exact: true }).click();
  await expect(page).toHaveURL(`${site}/support/`);
  await expect(page.getByRole("heading", { name: "Help and support", exact: true })).toBeVisible();
  await expect(header.getByRole("link", { name: "Help", exact: true })).toHaveAttribute("aria-current", "page");

  await page.goto(`${site}/local/`);
  await page.getByRole("contentinfo").getByRole("link", { name: "Security", exact: true }).click();
  await expect(page).toHaveURL(`${site}/support/#security`);
  const security = page.locator("#security");
  await expect(security.getByRole("heading", { name: "Report a security issue" })).toBeInViewport();
});

test("email actions expose the address and subject before opening an email app", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 850 });
  for (const [path, label, subject] of [
    ["/support/", "Email support", "Ninai support"],
    ["/support/", "Email feedback", "Ninai feedback"],
    ["/support/#security", "Email a security report", "Ninai security report"],
    ["/install/", "Ask about Windows testing", "Ninai for Windows"],
    ["/research/", "Discuss the research", "PACT research"],
    ["/privacy/", "Email a privacy request", "Ninai privacy request"],
    ["/terms/", "Email a question or legal notice", "Ninai terms"],
  ]) {
    await page.goto(`${site}${path}`);
    const toggle = page.locator(".email-contact > summary").filter({ hasText: label });
    const panel = toggle.locator("..").locator(".email-contact__panel");
    await expect(panel).toBeHidden();
    await toggle.click();
    await expect(page).toHaveURL(`${site}${path}`);
    await expect(panel.getByText("hello@ninai.io", { exact: true })).toBeVisible();
    await expect(panel.getByText(subject, { exact: true })).toBeVisible();
    await expect(panel.getByRole("link", { name: "Open email app" })).toHaveAttribute(
      "href", `mailto:hello@ninai.io?subject=${encodeURIComponent(subject)}`,
    );
    await toggle.press("Enter");
    await expect(panel).toBeHidden();
  }
});

test("support email can be copied and shows a manual fallback if clipboard access fails", async ({ context, page }) => {
  await context.grantPermissions(["clipboard-read", "clipboard-write"], { origin: site });
  await page.goto(`${site}/support/`);
  await page.locator("summary").filter({ hasText: "Email support" }).press("Enter");
  const panel = page.locator(".email-contact[open] .email-contact__panel");
  const copy = panel.getByRole("button", { name: "Copy email address" });
  await copy.click();
  await expect(panel.getByRole("status")).toHaveText("Email address copied.");
  expect(await page.evaluate(() => navigator.clipboard.readText())).toBe("hello@ninai.io");

  await page.evaluate(() => {
    Object.defineProperty(navigator, "clipboard", {
      configurable: true,
      value: { writeText: () => Promise.reject(new Error("Clipboard unavailable")) },
    });
  });
  await copy.click();
  await expect(panel.getByRole("status")).toHaveText("Select and copy the email address above.");
  await expect(panel.getByText("hello@ninai.io", { exact: true })).toBeVisible();
});

test("skip links move keyboard focus to the main content on every page", async ({ page }) => {
  for (const path of ["/", "/local/", "/governance/", "/install/", "/compatibility/", "/start/", "/support/", "/privacy/", "/terms/", "/research/", "/404.html"]) {
    await page.goto(`${site}${path}`);
    await page.keyboard.press("Tab");
    const skipLink = page.getByRole("link", { name: "Skip to content" });
    await expect(skipLink).toBeFocused();
    await skipLink.press("Enter");
    await expect(page.getByRole("main")).toBeFocused();
  }
});

test("primary navigation remains visible on tablets", async ({ page }) => {
  await page.setViewportSize({ width: 768, height: 900 });
  await page.goto(site);
  const navigation = page.getByRole("navigation", { name: "Primary navigation" });
  for (const name of ["How it works", "Why local", "Governance", "Help"]) {
    await expect(navigation.getByRole("link", { name, exact: true })).toBeVisible();
  }
});

test("the phone menu supports keyboard dismissal and keeps install and help reachable", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 850 });
  await page.goto(site);
  const menu = page.locator(".mobile-nav");
  const toggle = menu.locator("summary");
  await toggle.focus();
  await toggle.press("Enter");
  await expect(menu).toHaveAttribute("open", "");
  await expect(menu.getByRole("link", { name: "Get Ninai", exact: true })).toHaveAttribute("href", "/install/");
  const help = menu.getByRole("link", { name: "Help", exact: true });
  await help.focus();
  await help.press("Escape");
  await expect(menu).not.toHaveAttribute("open", "");
  await expect(toggle).toBeFocused();

  await toggle.press("Enter");
  await help.click();
  await expect(page).toHaveURL(`${site}/support/`);
  await expect(menu).not.toHaveAttribute("open", "");
});

test("the small-tablet menu uses the visible header install action", async ({ page }) => {
  await page.setViewportSize({ width: 600, height: 850 });
  await page.goto(site);
  const header = page.getByRole("banner");
  await expect(header.getByRole("link", { name: "Get Ninai", exact: true })).toBeVisible();
  const menu = page.locator(".mobile-nav");
  await menu.locator("summary").click();
  await expect(menu).toHaveAttribute("open", "");
  await expect(menu.locator(".mobile-nav__install")).toBeHidden();
});

test("the homepage links to the local governance guide and Mac setup", async ({ page }) => {
  await page.goto(site);
  await page.getByRole("link", { name: "See how it works", exact: true }).click();
  await expect(page).toHaveURL(`${site}/#how-it-works`);
  await expect(page.getByRole("heading", { name: "Pick up a decision in a new session." })).toBeInViewport();
  await page.getByRole("link", { name: "Explore governance", exact: true }).click();
  await expect(page).toHaveURL(`${site}/governance/`);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Give each assistant the access it needs.");
  await page.getByRole("link", { name: "Install on Mac", exact: true }).click();
  await expect(page).toHaveURL(`${site}/install/`);
  await expect(page.getByRole("link", { name: "Create account for Mac setup" })).toHaveAttribute(
    "href", "https://app.ninai.io/control/login?screen_hint=signup",
  );
  await expect(page.getByRole("link", { name: "Sign in for Mac setup" })).toHaveAttribute(
    "href", "https://app.ninai.io/control/login",
  );
});

test("install walkthrough waits for chapters before enabling automatic pause", async ({ page }) => {
  let releaseChapters!: () => void;
  const chaptersReady = new Promise<void>((resolve) => { releaseChapters = resolve; });
  await page.route("**/assets/ninai-install-chapters.json", async (route) => {
    await chaptersReady;
    await route.continue();
  });
  await page.goto(`${site}/install/`);
  const pause = page.getByRole("checkbox", { name: "Pause after each step so I can try it" });
  try {
    await expect(pause).toBeDisabled();
  } finally {
    releaseChapters();
  }
  await expect(pause).toBeEnabled();
  await pause.check();
  await expect(pause).toBeChecked();
});

test("install walkthrough points to the text guide when the video fails", async ({ page }) => {
  let releaseScripts!: () => void;
  const scriptsReady = new Promise<void>((resolve) => { releaseScripts = resolve; });
  await page.route("**/_next/static/chunks/*.js", async (route) => {
    await scriptsReady;
    await route.continue();
  });
  await page.route("**/assets/ninai-install-guide.mp4", (route) => route.abort());
  try {
    await page.goto(`${site}/install/`, { waitUntil: "commit" });
    await page.waitForFunction(() => Boolean(document.querySelector("video")?.error));
  } finally {
    releaseScripts();
  }
  await expect(page.getByRole("status")).toContainText("The video could not load. Use the text guide below");
  const guide = page.locator("details").filter({ hasText: "Read the step-by-step text guide" });
  await guide.locator("summary").click();
  await expect(guide.getByRole("heading").first()).toBeVisible();
});

test("install walkthrough chapters, checklist, and text guide work", async ({ page }) => {
  await page.goto(`${site}/install/`);
  const chapters = page.getByRole("navigation", { name: "Video chapters" });
  const secondStep = chapters.locator("ol").getByRole("button").nth(1);
  await secondStep.click();
  await expect(secondStep).toHaveAttribute("aria-current", "step");
  await expect(page.getByRole("status")).toContainText("Step 2 selected");
  const pause = page.getByRole("checkbox", { name: "Pause after each step so I can try it" });
  await pause.check();
  await expect(pause).toBeChecked();
  await page.getByRole("button", { name: /mark complete/i }).click();
  await expect(chapters).toContainText(/1 of \d+ steps tried/);
  await page.reload();
  await expect(chapters).toContainText(/1 of \d+ steps tried/);
  await page.getByRole("button", { name: "Reset checklist" }).click();
  await expect(chapters).toContainText(/0 of \d+ steps tried/);
  const guide = page.locator("details").filter({ hasText: "Read the step-by-step text guide" });
  await guide.locator("summary").click();
  await expect(guide).toHaveAttribute("open", "");
  await expect(guide.getByRole("heading").first()).toBeVisible();
});
