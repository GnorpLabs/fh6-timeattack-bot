import { test, expect, Page } from '@playwright/test';
import { _electron as electron, ElectronApplication } from 'playwright';
import path from 'path';

const MAIN_JS = path.join(__dirname, '../dist/main/index.js');

let app: ElectronApplication;
let page: Page;

test.beforeAll(async () => {
  app = await electron.launch({ args: [MAIN_JS] });
  page = await app.firstWindow();
  await page.waitForLoadState('domcontentloaded');
});

test.afterAll(async () => {
  // The app's tray handler prevents graceful quit, so force-kill by PID.
  try {
    const pid = await app.evaluate(() => process.pid);
    process.kill(pid, 'SIGKILL');
  } catch {
    app?.close().catch(() => {});
  }
});

// ── Tab navigation ──────────────────────────────────────────────────────────

test('all four tab buttons are visible', async () => {
  await expect(page.locator('[data-tab="live"]')).toBeVisible();
  await expect(page.locator('[data-tab="session"]')).toBeVisible();
  await expect(page.locator('[data-tab="replay"]')).toBeVisible();
  await expect(page.locator('[data-tab="settings"]')).toBeVisible();
});

test('Live tab is active by default', async () => {
  await expect(page.locator('[data-tab="live"]')).toHaveClass(/active/);
  await expect(page.locator('#tab-live')).toHaveClass(/active/);
});

test('clicking Session tab activates Session pane', async () => {
  await page.locator('[data-tab="session"]').click();
  await expect(page.locator('#tab-session')).toHaveClass(/active/);
  await expect(page.locator('#tab-live')).not.toHaveClass(/active/);
});

test('clicking Replay tab activates Replay pane', async () => {
  await page.locator('[data-tab="replay"]').click();
  await expect(page.locator('#tab-replay')).toHaveClass(/active/);
});

test('clicking Settings tab activates Settings pane', async () => {
  await page.locator('[data-tab="settings"]').click();
  await expect(page.locator('#tab-settings')).toHaveClass(/active/);
});

test('clicking Live tab returns to Live pane', async () => {
  await page.locator('[data-tab="live"]').click();
  await expect(page.locator('#tab-live')).toHaveClass(/active/);
});

// ── Live tab ─────────────────────────────────────────────────────────────────

test.describe('Live tab', () => {
  test.beforeEach(async () => {
    await page.locator('[data-tab="live"]').click();
  });

  test('shows map canvas', async () => {
    await expect(page.locator('#live-map')).toBeVisible();
  });

  test('shows speed display', async () => {
    await expect(page.locator('#live-speed')).toBeVisible();
  });

  test('shows gear display', async () => {
    await expect(page.locator('#live-gear')).toBeVisible();
  });

  test('shows RPM display', async () => {
    await expect(page.locator('#live-rpm')).toBeVisible();
  });

  test('shows throttle progress bar', async () => {
    await expect(page.locator('#bar-throttle')).toBeVisible();
  });

  test('shows brake progress bar', async () => {
    await expect(page.locator('#bar-brake')).toBeVisible();
  });

  test('shows clutch progress bar', async () => {
    await expect(page.locator('#bar-clutch')).toBeVisible();
  });

  test('shows idle overlay when no session is active', async () => {
    await expect(page.locator('#live-idle')).toBeVisible();
  });
});

// ── Session tab ───────────────────────────────────────────────────────────────

test.describe('Session tab', () => {
  test.beforeEach(async () => {
    await page.locator('[data-tab="session"]').click();
  });

  test('shows track selector', async () => {
    await expect(page.locator('#track-select')).toBeVisible();
  });

  test('shows vehicle selector', async () => {
    await expect(page.locator('#vehicle-select')).toBeVisible();
  });

  test('shows Full Race Replay button', async () => {
    await expect(page.locator('#btn-full-race')).toBeVisible();
  });

  test('Full Race Replay button switches to Replay tab', async () => {
    await page.locator('#btn-full-race').click();
    await expect(page.locator('#tab-replay')).toHaveClass(/active/);
    await page.locator('[data-tab="session"]').click();
  });

  test('shows lap table with correct column headers', async () => {
    const headers = page.locator('table thead th');
    await expect(headers.nth(0)).toContainText('#');
    await expect(headers.nth(1)).toContainText('Lap Time');
    await expect(headers.nth(2)).toContainText('Actions');
  });

  test('status area is present', async () => {
    await expect(page.locator('#session-status')).toBeAttached();
  });
});

// ── Replay tab ────────────────────────────────────────────────────────────────

test.describe('Replay tab', () => {
  test.beforeEach(async () => {
    await page.locator('[data-tab="replay"]').click();
  });

  test('shows lap selector', async () => {
    await expect(page.locator('#replay-lap-select')).toBeVisible();
  });

  test('shows track map canvas', async () => {
    await expect(page.locator('#replay-map')).toBeVisible();
  });

  test('shows play/pause button', async () => {
    await expect(page.locator('#btn-play-pause')).toBeVisible();
  });

  test('play/pause button is clickable without crashing', async () => {
    await page.locator('#btn-play-pause').click();
    await expect(page.locator('#btn-play-pause')).toBeVisible();
  });

  test('shows speed multiplier selector', async () => {
    await expect(page.locator('#speed-select')).toBeVisible();
  });

  test('speed selector has expected options', async () => {
    const options = await page.locator('#speed-select option').allTextContents();
    expect(options).toContain('0.25×');
    expect(options).toContain('1×');
    expect(options).toContain('4×');
  });

  test('shows timeline scrubber', async () => {
    await expect(page.locator('#timeline-scrubber')).toBeVisible();
  });

  test('shows playhead readout', async () => {
    await expect(page.locator('#playhead-readout')).toBeVisible();
  });

  test('shows playhead time', async () => {
    await expect(page.locator('#playhead-time')).toBeVisible();
  });

  test('chart canvases are in the DOM', async () => {
    await expect(page.locator('#chart-speed')).toBeAttached();
    await expect(page.locator('#chart-rpm')).toBeAttached();
    await expect(page.locator('#chart-gear')).toBeAttached();
    await expect(page.locator('#chart-elevation')).toBeAttached();
  });
});

// ── Settings tab ──────────────────────────────────────────────────────────────

test.describe('Settings tab', () => {
  test.beforeEach(async () => {
    await page.locator('[data-tab="settings"]').click();
  });

  test('shows API URL input', async () => {
    await expect(page.locator('#cfg-api-url')).toBeVisible();
  });

  test('shows Discord User ID input', async () => {
    await expect(page.locator('#cfg-discord-id')).toBeVisible();
  });

  test('shows Discord Username input', async () => {
    await expect(page.locator('#cfg-discord-username')).toBeVisible();
  });

  test('shows Token input', async () => {
    await expect(page.locator('#cfg-token')).toBeVisible();
  });

  test('shows UDP Port input', async () => {
    await expect(page.locator('#cfg-udp-port')).toBeVisible();
  });

  test('shows Replay Retention input', async () => {
    await expect(page.locator('#cfg-retention')).toBeVisible();
  });

  test('shows Save button', async () => {
    await expect(page.locator('#cfg-save')).toBeVisible();
  });

  test('inputs are interactive', async () => {
    await page.locator('#cfg-api-url').fill('https://test.example.com');
    await expect(page.locator('#cfg-api-url')).toHaveValue('https://test.example.com');
    await page.locator('#cfg-udp-port').fill('20440');
    await expect(page.locator('#cfg-udp-port')).toHaveValue('20440');
  });

  test('Save button is enabled', async () => {
    await expect(page.locator('#cfg-save')).toBeEnabled();
  });
});
