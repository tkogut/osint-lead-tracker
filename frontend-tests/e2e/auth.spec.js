import { test, expect } from '@playwright/test';

test.describe('Autoryzacja i Logowanie E2E', () => {
  test.beforeEach(async ({ page }) => {
    // Wejdź na stronę główną
    await page.goto('/');
  });

  test('powinien wyświetlić formularz logowania na starcie', async ({ page }) => {
    // Sprawdzenie obecności kontenera logowania
    const loginContainer = page.locator('#login-container');
    await expect(loginContainer).toBeVisible();

    const appContainer = page.locator('#app-container');
    await expect(appContainer).toBeHidden();
  });

  test('powinien wyświetlić błąd przy niepoprawnych danych logowania', async ({ page }) => {
    // Wpisz błędne dane
    await page.fill('#username', 'admin');
    await page.fill('#password', 'złehasło');
    
    // Kliknij zaloguj
    await page.click('button[type="submit"]');

    // Sprawdź komunikat błędu
    const errorAlert = page.locator('#login-error');
    await expect(errorAlert).toBeVisible();
    await expect(errorAlert).toContainText(/niepoprawny/i);
  });

  test('powinien pomyślnie zalogować użytkownika admin i pokazać dashboard', async ({ page }) => {
    // Wpisz poprawne dane
    await page.fill('#username', 'admin');
    await page.fill('#password', 'admin');
    
    // Kliknij zaloguj
    await page.click('button[type="submit"]');

    // Po pomyślnym zalogowaniu kontener app-container powinien być widoczny
    const appContainer = page.locator('#app-container');
    await expect(appContainer).toBeVisible();

    // Sprawdzenie, czy status systemu jest widoczny
    const statusDot = page.locator('#system-status-indicator .status-dot');
    await expect(statusDot).toBeVisible();
  });
});
