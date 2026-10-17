const { test, expect } = require(process.env.HOUSE_S3_PLAYWRIGHT_TEST);

test('synthetic reviewer works with outside requests blocked', async ({ page }) => {
  let blocked = 0;
  await page.context().route('**/*', route => {
    if (new URL(route.request().url()).hostname === '127.0.0.1') return route.continue();
    blocked++;
    return route.abort('internetdisconnected');
  });
  await page.goto(process.env.HOUSE_S3_REVIEWER_URL);
  await expect(page.getByRole('heading', { name: 'Synthetic plan reviewer' })).toBeVisible();
  await page.getByRole('button', { name: 'Measure area' }).click();
  await expect(page.locator('output')).toHaveText('Total: 60 m²');
  expect(await page.evaluate(() => fetch('https://example.invalid/probe').then(() => true, () => false))).toBe(false);
  expect(blocked).toBe(1);
  await page.screenshot({ path: process.env.HOUSE_S3_TEST_SCREENSHOT });
});
