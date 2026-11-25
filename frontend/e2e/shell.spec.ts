import { expect, test } from '@playwright/test'

test('UI shell loads and reaches the server', async ({ page }) => {
  const errors: string[] = []
  page.on('pageerror', (e) => errors.push(e.message))
  page.on('console', (m) => m.type() === 'error' && errors.push(m.text()))
  await page.goto('/')
  const nav = page.getByRole('navigation', { name: 'Main' })
  await expect(nav).toBeVisible()
  for (const item of ['Tests', 'Scan', 'Review', 'Report', 'Settings'])
    await expect(nav.getByRole('link', { name: item, exact: true })).toBeVisible()
  await expect(page.getByTestId('health')).toHaveText('Server connected')
  expect(errors).toEqual([])
})
