import { expect, test } from '@playwright/test'
import { execFileSync } from 'node:child_process'
import fs from 'node:fs'
import path from 'node:path'
import { DATA, PY, ROOT } from '../playwright.config'

const FIX = path.join(ROOT, 'fixtures', 'out', 'seed7', 'math8')
const PAPERS = 6 // first 6 papers of the main batch, in scan order

function batchFiles(): string[] {
  const truth = JSON.parse(fs.readFileSync(path.join(FIX, 'main', 'truth.json'), 'utf8'))
  return truth.papers.slice(0, PAPERS).flatMap((p: { pages: { file: string }[] }) =>
    p.pages.map((pg) => path.join(FIX, 'main', 'pages', pg.file)))
}

test('golden path: create test, scan a batch, review, report, PDF', async ({ page }) => {
  test.setTimeout(600_000)
  await page.goto('/')
  await page.getByRole('link', { name: 'New test' }).click()

  await page.getByLabel('Test name').fill('Grade 8 Mathematics Unit Test')
  await page.getByLabel('Subject').fill('Mathematics')
  await page.getByLabel('Pages per paper').fill('2')
  await page.getByRole('button', { name: 'Continue' }).click()

  await page.getByLabel('Answer key file').setInputFiles(path.join(FIX, 'key.txt'))
  await page.getByRole('button', { name: 'Continue' }).click()
  await expect(page.getByText('Found 14 questions.')).toBeVisible()

  await page.getByRole('textbox', { name: 'Syllabus' }).fill(fs.readFileSync(path.join(FIX, 'syllabus.txt'), 'utf8'))
  await page.getByRole('button', { name: 'Continue' }).click()
  await expect(page.getByText('Found 5 topics.')).toBeVisible()

  const [printable] = await Promise.all([page.waitForEvent('download'),
    page.getByRole('link', { name: 'Download printable test' }).click()])
  expect(fs.readFileSync(await printable.path()).subarray(0, 5).toString()).toBe('%PDF-')
  await page.getByRole('button', { name: 'Save and start scanning' }).click()
  await expect(page).toHaveURL(/\/scan\?test=\d+/)

  const files = batchFiles()
  await page.getByLabel('Upload scanned pages').setInputFiles(files)
  await expect(page.getByText(`Added ${files.length} pages.`)).toBeVisible()
  await page.getByRole('button', { name: 'Last page is in' }).click()
  await expect(page.getByTestId('batch-status')).toHaveText('Finished', { timeout: 300_000 })
  await expect(page.getByTestId('stat-graded')).toHaveText(String(PAPERS))

  // Review: the teacher accepts or fixes every flagged item with the keyboard
  await page.getByRole('link', { name: /Review \d+ items/ }).click()
  const remaining = page.getByTestId('review-remaining')
  for (let i = 0; i < 100 && !(await page.getByText('Nothing left to check').isVisible()); i++) {
    if (await page.getByRole('heading', { name: 'Student details' }).isVisible()) {
      await page.getByLabel('Student ID').fill('100000')
      await page.getByRole('button', { name: 'Save' }).click()
    } else {
      await page.keyboard.press('Enter')
    }
  }
  await expect(remaining).toHaveText('0 items to check')

  // Report reached from the sidebar; PDF downloads
  await page.getByRole('link', { name: 'Report', exact: true }).click()
  await expect(page.getByTestId('weak-topics').locator('li')).toHaveCount(5)
  await expect(page.getByTestId('reteach')).toBeVisible()
  await expect(page.getByTestId('question-table').locator('tbody tr')).toHaveCount(14)
  await expect(page.getByTestId('provisional')).toHaveCount(0)
  const [download] = await Promise.all([page.waitForEvent('download'), page.getByRole('link', { name: 'Export PDF' }).click()])
  const pdf = fs.readFileSync(await download.path())
  expect(pdf.subarray(0, 5).toString()).toBe('%PDF-')
})

test('home to report in 3 clicks or fewer', async ({ page }) => {
  await page.goto('/')
  let clicks = 0
  await page.getByRole('link', { name: 'Report', exact: true }).click(); clicks++
  await expect(page.getByRole('heading', { name: /Report/ })).toBeVisible()
  expect(clicks).toBeLessThanOrEqual(3)
})

test('review queue with 500 items stays responsive (< 200 ms per action)', async ({ page }) => {
  const seeded = JSON.parse(execFileSync(PY, [path.join(ROOT, 'gates', 'seed_review.py'), DATA, '500']).toString())
  await page.goto(`/review?test=${seeded.test_id}&batch=${seeded.batch_id}`)
  await expect(page.getByTestId('review-remaining')).toHaveText('500 items to check')
  const heading = page.getByRole('heading', { level: 2 }).first()
  await expect(heading).toBeVisible()
  const times: number[] = []
  for (let i = 0; i < 20; i++) {
    // time from the key press to the next item being on screen, measured inside the page
    await page.evaluate(() => {
      const w = window as unknown as { t0: number; t1: number }
      const h = () => document.querySelector('main section h2')?.textContent + '|' + document.querySelector('[aria-current="true"]')?.textContent
      const before = h()
      w.t0 = 0; w.t1 = 0
      window.addEventListener('keydown', () => { w.t0 = performance.now() }, { once: true, capture: true })
      const obs = new MutationObserver(() => { if (w.t0 && !w.t1 && h() !== before) { w.t1 = performance.now(); obs.disconnect() } })
      obs.observe(document.querySelector('main')!, { subtree: true, childList: true, characterData: true })
    })
    await page.keyboard.press(i % 2 ? 'Enter' : '0')
    await page.waitForFunction(() => (window as unknown as { t1: number }).t1 > 0)
    times.push(await page.evaluate(() => { const w = window as unknown as { t0: number; t1: number }; return w.t1 - w.t0 }))
  }
  times.sort((a, b) => a - b)
  console.log(`review action latency ms: median ${times[10].toFixed(1)}, max ${times[19].toFixed(1)}`)
  fs.writeFileSync(path.join(ROOT, 'data', 'e2e-review-latency.json'), JSON.stringify({ median: times[10], max: times[19] }))
  expect(times[19]).toBeLessThan(200)
  await expect(page.getByTestId('review-remaining')).toHaveText('480 items to check')
})
