#!/usr/bin/env node
/* Build-time safe-route attestation check.
 * Fails the build if the bundled safe route is missing, lacks a version or
 * attestation, or contains any network/storage access.
 */
import { readFileSync, writeFileSync, mkdirSync, existsSync } from 'node:fs'
import { createHash } from 'node:crypto'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const here = dirname(fileURLToPath(import.meta.url))
const candidates = [
  resolve('public/safe-route.html'),
  resolve('frontend/public/safe-route.html'),
  join(here, '..', 'frontend', 'public', 'safe-route.html'),
]
const path = candidates.find((p) => existsSync(p)) || candidates[0]
const outputDir = resolve(dirname(path), '..', '..', 'artifacts')

let html
try {
  html = readFileSync(path, 'utf8')
} catch {
  console.error(`FAIL: ${path} is missing`)
  process.exit(1)
}

const failures = []
const version = html.match(/name="wzdm-safe-route-version"\s+content="([^"]+)"/)
const attestation = html.match(/name="wzdm-safe-route-attestation"\s+content="([^"]+)"/)
if (!version) failures.push('missing version meta')
if (!attestation) failures.push('missing attestation meta')
if (!html.includes('(555) 010-2200')) failures.push('missing practice phone')
if (!html.includes('(555) 010-2211')) failures.push('missing emergency text')
for (const pattern of ['fetch(', 'XMLHttpRequest', 'localStorage', 'sessionStorage', 'import(']) {
  if (html.includes(pattern)) failures.push(`forbidden construct: ${pattern}`)
}

if (failures.length) {
  console.error('FAIL: safe-route attestation checks failed:')
  for (const f of failures) console.error(`  - ${f}`)
  process.exit(1)
}

const manifest = {
  asset: 'safe-route.html',
  version: version[1],
  attestation: attestation[1],
  sha256: createHash('sha256').update(html).digest('hex'),
  generated_at: new Date().toISOString(),
  offline_capable: true,
  phi_free: true,
}
mkdirSync(outputDir, { recursive: true })
writeFileSync(join(outputDir, 'safe-route-manifest.json'), JSON.stringify(manifest, null, 2) + '\n')
console.log(`OK: safe route ${manifest.version} ${manifest.sha256.slice(0, 16)}…`)
