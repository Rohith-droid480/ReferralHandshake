{
  "name": "referral-handshake-pwa",
  "version": "1.0.0",
  "private": true,
  "description": "ReferralHandshake (RHP-1) React PWA: Clinician Card, Receiving Desk, Dispatcher Console, Guarantee Arena & Pure-JS Browser Verifier",
  "type": "module",
  "scripts": {
    "dev": "vite --host 0.0.0.0 --port 5173",
    "build": "tsc -b && vite build",
    "preview": "vite preview --host 0.0.0.0 --port 5173",
    "test": "vitest run",
    "test:watch": "vitest",
    "lint": "eslint . --ext ts,tsx --report-unused-disable-directives --max-warnings 0",
    "typecheck": "tsc --noEmit"
  },
  "dependencies": {
    "@noble/curves": "^1.6.0",
    "@noble/hashes": "^1.5.0",
    "clsx": "^2.1.1",
    "idb": "^8.0.0",
    "lucide-react": "^0.454.0",
    "maplibre-gl": "^4.7.1",
    "qrcode.react": "^4.1.0",
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "react-map-gl": "^7.1.7",
    "react-router-dom": "^6.27.0",
    "tailwind-merge": "^2.5.4",
    "uuid": "^11.0.2"
  },
  "devDependencies": {
    "@testing-library/jest-dom": "^6.6.3",
    "@testing-library/react": "^16.0.1",
    "@types/node": "^22.8.6",
    "@types/react": "^18.3.12",
    "@types/react-dom": "^18.3.1",
    "@types/uuid": "^10.0.0",
    "@typescript-eslint/eslint-plugin": "^8.12.2",
    "@typescript-eslint/parser": "^8.12.2",
    "@vitejs/plugin-react": "^4.3.3",
    "autoprefixer": "^10.4.20",
    "eslint": "^9.13.0",
    "eslint-plugin-react-hooks": "^5.0.0",
    "eslint-plugin-react-refresh": "^0.4.14",
    "jsdom": "^25.0.1",
    "postcss": "^8.4.47",
    "tailwindcss": "^3.4.14",
    "typescript": "~5.6.3",
    "vite": "^5.4.10",
    "vite-plugin-pwa": "^0.21.0",
    "vitest": "^2.1.4"
  },
  "engines": {
    "node": ">=20.0.0"
  }
}