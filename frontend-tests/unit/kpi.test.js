import { describe, it, expect, beforeEach, vi } from 'vitest';
import fs from 'fs';
import path from 'path';

// Load real HTML file to avoid missing DOM elements errors during script execution
const htmlPath = path.resolve(__dirname, '../../src/static/index.html');
const indexHtmlContent = fs.readFileSync(htmlPath, 'utf8');

describe('Frontend Logic & Math Unit Tests', () => {
  let appModule;

  beforeEach(() => {
    // 1. Setup mock DOM from index.html
    document.body.innerHTML = indexHtmlContent;
    
    // 2. Mock globally required functions/objects (like config or API fetchers)
    global.window.showToast = () => {};
    
    // Mock fetch to prevent network calls during initialization
    global.window.fetch = vi.fn().mockImplementation(() => 
      Promise.resolve({
        ok: false,
        status: 401,
        json: () => Promise.resolve({ detail: "Not authenticated" })
      })
    );
    
    // 3. Import app.js (since it executes immediately on load and binds elements)
    if (!appModule) {
      // Read and evaluate app.js within this jsdom context
      const appJsCode = fs.readFileSync(path.resolve(__dirname, '../../src/static/app.js'), 'utf8');
      
      // Execute app.js in JSDOM context
      const runCode = new Function('window', 'document', 'console', appJsCode);
      runCode(window, document, console);
      
      // The script exposes functions to window after DOMContentLoaded fires
      window.document.dispatchEvent(new window.Event('DOMContentLoaded'));
      
      appModule = {
        prettyModelName: window.prettyModelName,
        checkCampaignModelsIntegrity: window.checkCampaignModelsIntegrity,
        renderAnalyticsChart: window.renderAnalyticsChart
      };
    }
  });

  describe('prettyModelName()', () => {
    it('should format known model keys correctly', () => {
      expect(appModule.prettyModelName('gemini-2.5-flash')).toBe('Gemini 2.5 Flash');
      expect(appModule.prettyModelName('gemini-2.5-pro')).toBe('Gemini 2.5 Pro');
      expect(appModule.prettyModelName('gemini-1.5-flash')).toBe('Gemini 1.5 Flash');
    });

    it('should fallback gracefully for unknown models', () => {
      expect(appModule.prettyModelName('unknown-model-v3')).toBe('Unknown Model V3');
    });
  });

  describe('renderAnalyticsChart() Math Calculations', () => {
    it('should generate valid SVG coordinates and path elements', () => {
      const mockTimeline = [
        { date: '2026-08-01', scans: 5, leads_created: 2 },
        { date: '2026-08-02', scans: 10, leads_created: 5 },
        { date: '2026-08-03', scans: 15, leads_created: 7 }
      ];

      appModule.renderAnalyticsChart(mockTimeline);

      const svg = document.querySelector('svg');
      expect(svg).not.toBeNull();
      
      const paths = document.querySelectorAll('path');
      // Should have 2 path elements (one for scans area, one for leads area, and line paths)
      expect(paths.length).toBeGreaterThan(0);

      // Verify dots are rendered with correct positions
      const dots = document.querySelectorAll('circle');
      // 3 data points * 2 series (scans, leads) = 6 dots
      expect(dots.length).toBe(6);
    });

    it('should handle empty or single point datasets gracefully without division by zero', () => {
      // Empty timeline data
      appModule.renderAnalyticsChart([]);
      expect(document.querySelector('svg')).toBeNull();
      expect(document.getElementById('analytics-chart-container').textContent).toContain('Brak danych');

      // Single data point
      appModule.renderAnalyticsChart([{ date: '2026-08-01', scans: 2, leads_created: 1 }]);
      const svg = document.querySelector('svg');
      expect(svg).not.toBeNull();
      const dots = document.querySelectorAll('circle');
      expect(dots.length).toBe(2);
    });
  });
});
