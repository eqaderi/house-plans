import { test, expect } from "@playwright/test";

test.describe("House AI Plan Reviewer - Local 2D Reviewer E2E", () => {
  test("Gate Banner renders human commands and strictly no approval button (S4-23)", async ({
    page,
  }) => {
    await page.goto("/");
    const gateBanner = page.locator('[data-testid="gate-banner"]');
    await expect(gateBanner).toBeVisible();

    // Verify approval command is shown for human CLI execution
    await expect(gateBanner).toContainText("house-ai workflow approve");

    // Strictly verify NO approve buttons exist anywhere on the page
    const buttons = await page.locator("button").allInnerTexts();
    for (const btnText of buttons) {
      expect(btnText.toLowerCase()).not.toContain("approve gate");
      expect(btnText.toLowerCase()).not.toBe("approve");
    }
  });

  test("Semantic SVG renders elements with stable data-id and data-kind (S4-07, S4-08)", async ({
    page,
  }) => {
    await page.goto("/");
    const canvas = page.locator('[data-testid="plan-canvas"]');
    await expect(canvas).toBeVisible();

    const svg = page.locator('[data-testid="plan-svg"]');
    await expect(svg).toBeVisible();

    // Check spaces have data-id and data-kind="space"
    const spaces = page.locator('svg polygon[data-kind="space"]');
    const spaceCount = await spaces.count();
    expect(spaceCount).toBeGreaterThan(0);

    // Check first space has data-id attribute
    const firstSpaceId = await spaces.first().getAttribute("data-id");
    expect(firstSpaceId).toBeTruthy();

    // Check walls have data-kind="wall"
    const walls = page.locator('svg line[data-kind="wall"]');
    const wallCount = await walls.count();
    expect(wallCount).toBeGreaterThan(0);
  });

  test("Element selection inspects canonical attributes in PropertyPanel (S4-09)", async ({
    page,
  }) => {
    await page.goto("/");
    const firstSpace = page.locator('svg polygon[data-kind="space"]').first();
    const spaceId = await firstSpace.getAttribute("data-id");

    // Click the space polygon
    await firstSpace.click();

    // Property panel should display the selected element ID
    const propertyPanel = page.locator('[data-testid="property-panel"]');
    await expect(propertyPanel).toBeVisible();
    if (spaceId) {
      await expect(propertyPanel).toContainText(spaceId);
    }
  });

  test("Tabs navigation: Schedule, Findings, Metrics, Comparison, Feedback (S4-11..S4-22)", async ({
    page,
  }) => {
    await page.goto("/");

    // 1. Room Schedule Tab (S4-11)
    await page.locator('[data-testid="tab-schedule"]').click();
    const schedule = page.locator('[data-testid="room-schedule"]');
    await expect(schedule).toBeVisible();
    await expect(schedule).toContainText("Program Target");
    await expect(schedule).toContainText("Gross Area");

    // 2. Findings Tab (S4-13)
    await page.locator('[data-testid="tab-findings"]').click();
    const findings = page.locator('[data-testid="findings-panel"]');
    await expect(findings).toBeVisible();
    await expect(findings).toContainText("Evaluator Findings");

    // 3. Epistemic Metric Matrix Tab (S4-14)
    await page.locator('[data-testid="tab-metrics"]').click();
    const metrics = page.locator('[data-testid="metric-matrix"]');
    await expect(metrics).toBeVisible();
    await expect(metrics).toContainText("Evaluation Metrics (Epistemic Status)");
    await expect(metrics).toContainText("gross_internal_area_m2");
    await expect(metrics).toContainText("measured");

    // 4. Comparison Tab (S4-17, S4-18)
    await page.locator('[data-testid="tab-comparison"]').click();
    const comparison = page.locator('[data-testid="comparison-view"]');
    await expect(comparison).toBeVisible();
    await expect(comparison).toContainText("Concept Comparison");

    // Switch to table mode in comparison
    await page.locator('button:has-text("Metrics Table")').click();
    await expect(page.locator("table")).toBeVisible();

    // 5. Feedback Tab & Revision Ops Export (S4-21, S4-22)
    await page.locator('[data-testid="tab-feedback"]').click();
    const feedback = page.locator('[data-testid="feedback-panel"]');
    await expect(feedback).toBeVisible();

    // Fill in author and verbatim feedback
    await page.locator('[data-testid="author-input"]').fill("homeowner:alice");
    await page
      .locator('[data-testid="verbatim-request-input"]')
      .fill("Make the kitchen larger and add pantry");

    // Add structured revision op
    await page.locator('[data-testid="op-target-input"]').fill("pi-kitchen");
    await page.locator('[data-testid="op-value-input"]').fill("20.0");
    await page.locator('[data-testid="add-op-btn"]').click();

    // Verify op appears in operations list
    await expect(feedback).toContainText("area:pi-kitchen=20");

    // Verify JSON export button is enabled
    const exportBtn = page.locator('button:has-text("Export revision_ops.json")');
    await expect(exportBtn).toBeVisible();
  });

  test("Loading synthetic demonstration bundles from static URL (S4-05, S4-06)", async ({
    page,
  }) => {
    // 1. Synthetic bungalow
    await page.goto("/?bundle=/bundles/synthetic-bungalow/bundle.json");
    await expect(page.locator("header")).toContainText("synthetic-bungalow");
    await expect(page.locator('[data-testid="plan-canvas"]')).toBeVisible();

    // 2. Synthetic hillside
    await page.goto("/?bundle=/bundles/synthetic-hillside/bundle.json");
    await expect(page.locator("header")).toContainText("synthetic-hillside");
    await expect(page.locator('[data-testid="plan-canvas"]')).toBeVisible();
  });
});
