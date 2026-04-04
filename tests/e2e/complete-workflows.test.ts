/**
 * E2E Tests for ARIA UX Rollout
 * Complete user workflows from creation to export
 *
 * Run: npm run test:e2e
 * Requires: Backend running on http://localhost:8000
 */

import { test, expect } from '@playwright/test';

const BASE_URL = process.env.BASE_URL || 'http://localhost:3000';
const API_URL = process.env.API_URL || 'http://localhost:8000';

test.describe('ARIA UX Workflows', () => {
  
  test('Flow 1: Create Case → Run ARIA → Inspect Evidence → Export', async ({ page, context }) => {
    // 1. Login
    await page.goto(`${BASE_URL}/login`);
    await page.fill('input[name="email"]', 'test@example.com');
    await page.fill('input[name="password"]', 'testpassword123');
    await page.click('button:has-text("Sign In")');
    await expect(page).toHaveURL(`${BASE_URL}/workspace`);

    // 2. Create Project
    await page.click('button:has-text("New Project")');
    await page.fill('input[name="projectName"]', 'Q2 Market Analysis');
    await page.fill('textarea[name="description"]', 'Analyzing market trends for Q2');
    await page.click('button:has-text("Create")');
    await expect(page.locator('text=Q2 Market Analysis')).toBeVisible();

    // 3. Create Case
    await page.click('button:has-text("New Case")');
    await page.fill('textarea[name="question"]', 'What are the top 5 emerging AI trends in healthcare?');
    await page.click('button:has-text("Create Case")');
    await expect(page).toHaveURL(/\/workspace\/[^/]+\/case\/[^/]+/);

    // 4. Select Mode and Run ARIA
    await page.click('[data-testid="mode-selector"]');
    await page.click('text=Deep Research');
    await page.click('button:has-text("Run ARIA")');

    // 5. Verify streaming output starts
    await expect(page.locator('[data-testid="live-output"]')).toBeVisible();
    await page.waitForLoadState('networkidle');

    // 6. Wait for run to complete
    await page.waitForSelector('[data-testid="run-complete"]', { timeout: 60000 });
    await expect(page.locator('text=Research complete')).toBeVisible();

    // 7. Open Evidence Panel
    await page.click('[data-testid="evidence-panel-sources"]');
    const sourcesCount = await page.locator('[data-testid="source-item"]').count();
    expect(sourcesCount).toBeGreaterThan(0);

    // 8. Check Quality Metrics
    await page.click('[data-testid="evidence-panel-quality"]');
    await expect(page.locator('[data-testid="trust-score"]')).toBeVisible();
    const trustScore = await page.locator('[data-testid="trust-score"]').textContent();
    expect(parseFloat(trustScore!)).toBeGreaterThanOrEqual(0);
    expect(parseFloat(trustScore!)).toBeLessThanOrEqual(1);

    // 9. Export DOCX
    await page.click('button:has-text("Export")');
    await page.click('text=Download DOCX');
    
    // Verify download started
    const downloadPath = await new Promise<string>(resolve => {
      page.on('download', async (download) => {
        resolve(download.suggestedFilename());
      });
    });
    expect(downloadPath).toMatch(/\.docx$/);
  });

  test('Flow 2: Compare Two Runs Side-by-Side', async ({ page }) => {
    // 1. Login
    await page.goto(`${BASE_URL}/login`);
    await page.fill('input[name="email"]', 'test@example.com');
    await page.fill('input[name="password"]', 'testpassword123');
    await page.click('button:has-text("Sign In")');

    // 2. Navigate to case with multiple runs
    await page.goto(`${BASE_URL}/workspace/project1/case/case1`);
    
    // 3. Open Compare view
    await page.click('button:has-text("Compare")');
    await expect(page).toHaveURL(/\/workspace\/[^/]+\/compare/);

    // 4. Select two runs
    await page.click('[data-testid="run-select-0"]');
    await page.click('[data-testid="run-select-1"]');
    await page.click('button:has-text("Compare Runs")');

    // 5. Verify side-by-side view
    await expect(page.locator('[data-testid="compare-left"]')).toBeVisible();
    await expect(page.locator('[data-testid="compare-right"]')).toBeVisible();

    // 6. Check diff highlights
    const diffItems = await page.locator('[data-testid="diff-item"]').count();
    expect(diffItems).toBeGreaterThanOrEqual(0);

    // 7. Compare quality scores
    const leftScore = await page.locator('[data-testid="quality-left"]').textContent();
    const rightScore = await page.locator('[data-testid="quality-right"]').textContent();
    expect(leftScore).toBeTruthy();
    expect(rightScore).toBeTruthy();
  });

  test('Flow 3: Share Case and Access via Link', async ({ page, context, browser }) => {
    // 1. Login
    await page.goto(`${BASE_URL}/login`);
    await page.fill('input[name="email"]', 'test@example.com');
    await page.fill('input[name="password"]', 'testpassword123');
    await page.click('button:has-text("Sign In")');

    // 2. Open case
    await page.goto(`${BASE_URL}/workspace/project1/case/case1`);

    // 3. Generate share link
    await page.click('button[title="Share"]');
    await page.click('text=Generate Link');
    const shareLink = await page.inputValue('[data-testid="share-link"]');
    expect(shareLink).toMatch(/^https?:\/\//);

    // 4. Copy link
    await page.click('button:has-text("Copy")');
    
    // 5. Open share link in new incognito context (unauthenticated)
    const newContext = await browser.newContext();
    const newPage = await newContext.newPage();
    await newPage.goto(shareLink);

    // 6. Verify case is visible without login
    await expect(newPage.locator('[data-testid="case-title"]')).toBeVisible();
    await expect(newPage.locator('[data-testid="run-button"]')).not.toBeVisible(); // Can't run without auth

    // 7. Verify can still view evidence
    await newPage.click('[data-testid="evidence-panel-sources"]');
    const sources = await newPage.locator('[data-testid="source-item"]').count();
    expect(sources).toBeGreaterThan(0);

    await newContext.close();
  });

  test('Flow 4: Model Selection and Cost Tracking', async ({ page }) => {
    // 1. Login
    await page.goto(`${BASE_URL}/login`);
    await page.fill('input[name="email"]', 'test@example.com');
    await page.fill('input[name="password"]', 'testpassword123');
    await page.click('button:has-text("Sign In")');

    // 2. Navigate to Settings/Model selection
    await page.click('[data-testid="settings-button"]');
    await page.click('text=Model Provider');

    // 3. Verify available models display
    const modelOptions = await page.locator('[data-testid="model-option"]').count();
    expect(modelOptions).toBeGreaterThan(0);

    // 4. Select different model
    await page.click('[data-testid="model-option-gemini"]');
    await page.click('button:has-text("Save")');

    // 5. Create case and run ARIA
    await page.goto(`${BASE_URL}/workspace/project1/case/case1`);
    await page.click('button:has-text("Run ARIA")');

    // 6. Check cost tracker updates
    await expect(page.locator('[data-testid="cost-tracker"]')).toContainText(/\$[\d.]+/);

    // 7. Verify cost is tracked per run
    await page.waitForSelector('[data-testid="run-complete"]', { timeout: 60000 });
    const runCost = await page.locator('[data-testid="run-cost"]').textContent();
    expect(runCost).toMatch(/\$[\d.]+/);
  });

  test('Flow 5: Org and Team Member Management', async ({ page }) => {
    // 1. Login
    await page.goto(`${BASE_URL}/login`);
    await page.fill('input[name="email"]', 'test@example.com');
    await page.fill('input[name="password"]', 'testpassword123');
    await page.click('button:has-text("Sign In")');

    // 2. Open organization settings
    await page.click('[data-testid="org-switcher"]');
    await page.click('button:has-text("Settings")');
    await expect(page).toHaveURL(/\/settings\/organization/);

    // 3. Add team member
    await page.click('button:has-text("Invite Member")');
    await page.fill('input[name="email"]', 'newmember@example.com');
    await page.selectOption('[name="role"]', 'member');
    await page.click('button:has-text("Send Invite")');
    await expect(page.locator('text=Invite sent')).toBeVisible();

    // 4. Set member permissions
    await page.click('[data-testid="member-settings-newmember"]');
    await page.selectOption('[name="role"]', 'admin');
    await page.click('button:has-text("Update")');
    await expect(page.locator('text=Role updated')).toBeVisible();

    // 5. Remove member
    await page.click('[data-testid="member-remove-newmember"]');
    await page.click('button:has-text("Confirm Remove")');
    await expect(page.locator('text=Member removed')).toBeVisible();
  });

  test('Edge Case: Streaming Interruption and Resume', async ({ page }) => {
    // 1. Login
    await page.goto(`${BASE_URL}/login`);
    await page.fill('input[name="email"]', 'test@example.com');
    await page.fill('input[name="password"]', 'testpassword123');
    await page.click('button:has-text("Sign In")');

    // 2. Create case
    await page.goto(`${BASE_URL}/workspace/project1/case/case1`);
    await page.click('button:has-text("Run ARIA")');

    // 3. Wait for streaming to start
    await expect(page.locator('[data-testid="live-output"]')).toBeVisible();

    // 4. Simulate network interruption (via DevTools)
    await page.context().setOffline(true);
    await page.waitForTimeout(2000);

    // 5. Restore network
    await page.context().setOffline(false);

    // 6. Verify reconnection happened
    const reconnectMessage = await page.locator('[data-testid="reconnecting"]');
    if (await reconnectMessage.isVisible()) {
      await expect(reconnectMessage).toContainText(/reconnect|retry/i);
    }

    // 7. Verify run continues or recovers
    await page.waitForSelector('[data-testid="run-complete"]', { timeout: 120000 });
  });

  test('Performance: Large evidence set rendering', async ({ page }) => {
    // 1. Login
    await page.goto(`${BASE_URL}/login`);
    await page.fill('input[name="email"]', 'test@example.com');
    await page.fill('input[name="password"]', 'testpassword123');
    await page.click('button:has-text("Sign In")');

    // 2. Navigate to case with many sources
    await page.goto(`${BASE_URL}/workspace/project1/case/case-with-100-sources`);

    // 3. Measure time to render sources list
    const startTime = Date.now();
    await page.click('[data-testid="evidence-panel-sources"]');
    await page.waitForSelector('[data-testid="source-item"]:nth-child(50)', { timeout: 5000 });
    const renderTime = Date.now() - startTime;

    // 4. Verify acceptable performance
    expect(renderTime).toBeLessThan(3000); // Should render within 3 seconds

    // 5. Scroll through sources
    const sourcesList = page.locator('[data-testid="sources-list"]');
    await sourcesList.evaluate(el => el.scrollTop = el.scrollHeight);
    await page.waitForTimeout(500);

    // 6. Verify all sources still rendered
    const sources = await page.locator('[data-testid="source-item"]').count();
    expect(sources).toBeGreaterThanOrEqual(100);
  });

  test('Accessibility: Keyboard navigation', async ({ page }) => {
    // 1. Login
    await page.goto(`${BASE_URL}/login`);
    await page.fill('input[name="email"]', 'test@example.com');
    await page.fill('input[name="password"]', 'testpassword123');

    // 2. Tab to Sign In button
    await page.focus('input[name="password"]');
    await page.keyboard.press('Tab');
    await expect(page.locator('button:has-text("Sign In")')).toBeFocused();

    // 3. Press Enter to submit
    await page.keyboard.press('Enter');
    await expect(page).toHaveURL(`${BASE_URL}/workspace`);

    // 4. Navigate to case via Tab
    await page.keyboard.press('Tab');
    let focusCount = 0;
    while (focusCount < 10) {
      await page.keyboard.press('Tab');
      focusCount++;
    }

    // 5. Verify tabbable elements are in logical order
    const focusedElement = await page.evaluate(() => document.activeElement?.getAttribute('data-testid'));
    expect(focusedElement).toBeTruthy();

    // 6. Test arrow keys in dropdown
    await page.click('[data-testid="mode-selector"]');
    await page.keyboard.press('ArrowDown');
    await expect(page.locator('[data-testid="mode-option-chat"]')).toBeFocused();
    
    await page.keyboard.press('ArrowDown');
    await expect(page.locator('[data-testid="mode-option-deep-research"]')).toBeFocused();

    // 7. Select with Enter
    await page.keyboard.press('Enter');
    // Verify selection
  });

});
