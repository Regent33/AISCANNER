import { expect, test } from '@playwright/test'

test('select hosted models, add keys and keep the two pools separate', async ({ page, request }) => {
  const initial = await (await request.get('/api/settings')).json()
  await page.goto('/settings')
  for (const [provider, name] of [['openrouter', 'OpenRouter'], ['nvidia', 'NVIDIA NIM']]) {
    await page.getByRole('radio', { name: new RegExp(name) }).check()
    const models = page.getByRole('combobox', { name: 'Saved models' })
    const previous = await models.inputValue()
    const custom = `example/${provider}-model`
    await models.selectOption('')
    await page.getByRole('textbox', { name: new RegExp(name + ' model ID') }).fill(custom)
    await page.getByLabel('Add API keys').fill('test-only-1,test-only-2')
    await page.getByRole('button', { name: 'Save settings', exact: true }).click()
    await expect(page.getByText('Saved.', { exact: true })).toBeVisible()
    await page.reload()
    await expect(page.getByRole('radio', { name: new RegExp(name) })).toBeChecked()
    await expect(models).toHaveValue(custom)
    await expect(page.getByLabel('Add API keys')).toHaveValue('')
    const count = initial.key_counts[provider] + 2
    await expect(page.getByText(new RegExp(`^${count} configured\\. Separate new keys`))).toBeVisible()
    await models.selectOption(previous)
    await page.getByRole('button', { name: 'Save settings', exact: true }).click()
    await expect(page.getByText('Saved.', { exact: true })).toBeVisible()
    await page.reload()
    await expect(models).toHaveValue(previous)
    await expect(models.getByRole('option', { name: custom, exact: true })).toHaveCount(1)
  }
  await page.getByRole('radio', { name: /On this computer/ }).check()
  await page.getByRole('button', { name: 'Save', exact: true }).click()
  await expect(page.getByText('Saved.', { exact: true })).toBeVisible()
})
