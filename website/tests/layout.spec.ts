import { test, expect } from "@playwright/test";

for (const width of [320, 390, 768, 1440]) {
  test(`public pages stay aligned at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    for (const path of ["/", "/install/", "/local/", "/privacy/", "/compatibility/", "/terms/", "/start/", "/research/"]) {
      const response = await page.goto(`http://127.0.0.1:3034${path}`);
      expect(response?.ok(), path).toBeTruthy();
      await expect(page.locator("h1"), path).toHaveCount(1);
      if (path === "/install/") {
        const actionsBottom = await page.locator(".page-hero__aside .hero-actions").evaluate(node => node.getBoundingClientRect().bottom);
        const noteTop = await page.locator(".page-hero__aside .install-note").evaluate(node => node.getBoundingClientRect().top);
        expect(noteTop - actionsBottom, "Install prerequisite note overlaps the buttons").toBeGreaterThanOrEqual(20);
      }
      await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), { message: `${path} overflows at ${width}px` }).toBeTruthy();
      const broken = await page.locator("img").evaluateAll(images => images.filter(image => !(image as HTMLImageElement).complete || !(image as HTMLImageElement).naturalWidth).map(image => (image as HTMLImageElement).src));
      expect(broken, `${path} broken images`).toEqual([]);
    }
  });
}
