// Import from the TestRelic fixture (not '@playwright/test') so page navigation
// is tracked automatically and reported to TestRelic analytics.
import { test, expect } from '@testrelic/playwright-analytics/fixture'

test.describe('ForgeFlow console — smoke', () => {
  test('landing page loads', async ({ page }) => {
    await page.goto('/')
    await expect(page).toHaveTitle(/ForgeFlow/i)
    await expect(page.getByText('ForgeFlow').first()).toBeVisible()
  })

  test('navigates to the architecture page', async ({ page }) => {
    await page.goto('/')
    await page.goto('/architecture')
    await expect(page).toHaveURL(/\/architecture/)
  })
})
