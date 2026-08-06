#!/bin/bash
set -e

echo "================================================================================"
echo " RUNNING QUALITY INFRASTRUCTURE TEST SUITE"
echo "================================================================================"

echo ""
echo "1. Running Frontend Unit Tests (Vitest + jsdom)..."
cd frontend-tests
npm run test:unit
cd ..

echo ""
echo "2. Running Backend Unit & Integration Tests (pytest)..."
PYTHONPATH=.:src .venv/bin/pytest tests/

echo ""
echo "3. Running UI E2E Integration Tests (Playwright)..."
cd frontend-tests
npm run test:e2e
cd ..

echo ""
echo "================================================================================"
echo " ✅ ALL TEST SUITES PASSED SUCCESSFULLY!"
echo "================================================================================"
