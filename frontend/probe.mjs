import { chromium } from 'playwright'
const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1400, height: 900 } })
const errors = []
page.on('pageerror', (e) => errors.push(`[pageerror] ${e.message}`))
await page.goto('http://localhost:5173/', { waitUntil: 'networkidle' })
await page.waitForTimeout(4000)

// Far view (default altitude 2).
await page.screenshot({ path: 'probe-far.png' })

// Zoom in: wheel up over the globe center a few times, let onZoom raise resolution.
await page.mouse.move(700, 480)
for (let i = 0; i < 8; i++) {
  await page.mouse.wheel(0, -400)
  await page.waitForTimeout(150)
}
await page.waitForTimeout(3000)
await page.screenshot({ path: 'probe-near.png' })

console.log('errors:', errors.length ? errors.join('\n') : '(none)')
// Intentionally NOT closing the browser.
