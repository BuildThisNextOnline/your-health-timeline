// Encrypt each person's payload with their own passphrase, using WebCrypto so
// the output decrypts in the browser with crypto.subtle (identical primitives).
//
// Output per person: site/data/<id>.enc  (JSON: salt, iv, ct, kdf params)
// Public manifest:    site/data/manifest.json (names only, NO health data)
// Passphrases:        data/passphrases.json (LOCAL ONLY, git-ignored) for you
//                     to hand to each person. Never committed.
//
// The public repo therefore contains only ciphertext + names. Without a
// person's passphrase, their data cannot be read.

import { webcrypto as crypto } from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.join(__dirname, "..");
const PAYLOAD = path.join(ROOT, "data", "payload");
const SITE_DATA = path.join(ROOT, "site", "data");
const PASS_FILE = path.join(ROOT, "data", "passphrases.json");
const ITER = 600000;

fs.mkdirSync(SITE_DATA, { recursive: true });

const WORDS = ("amber harbor willow cobalt meadow cedar ember lunar pepper quartz "
  + "ribbon saffron timber velvet walnut cactus falcon garnet hazel indigo jasper "
  + "kettle lagoon marble nectar orchid pelican russet summit tundra violet zephyr "
  + "basil copper dapple fennel ginger hollow ivory jungle kelp lantern maple").split(/\s+/);

function makePassphrase() {
  const pick = () => WORDS[crypto.getRandomValues(new Uint32Array(1))[0] % WORDS.length];
  const num = 100 + (crypto.getRandomValues(new Uint32Array(1))[0] % 900);
  // 6 words + a 3-digit number: much harder to brute-force than 3 words.
  return `${pick()}-${pick()}-${pick()}-${pick()}-${pick()}-${pick()}-${num}`;
}

function b64(buf) { return Buffer.from(buf).toString("base64"); }

async function deriveKey(passphrase, salt) {
  const base = await crypto.subtle.importKey(
    "raw", new TextEncoder().encode(passphrase), "PBKDF2", false, ["deriveKey"]);
  return crypto.subtle.deriveKey(
    { name: "PBKDF2", salt, iterations: ITER, hash: "SHA-256" },
    base, { name: "AES-GCM", length: 256 }, false, ["encrypt", "decrypt"]);
}

async function encryptPayload(passphrase, plaintext) {
  const salt = crypto.getRandomValues(new Uint8Array(16));
  const iv = crypto.getRandomValues(new Uint8Array(12));
  const key = await deriveKey(passphrase, salt);
  const ct = await crypto.subtle.encrypt(
    { name: "AES-GCM", iv }, key, new TextEncoder().encode(plaintext));
  return { v: 1, kdf: "PBKDF2-SHA256", iter: ITER, salt: b64(salt), iv: b64(iv), ct: b64(ct) };
}

// round-trip self-check
async function decryptCheck(passphrase, blob, expectName) {
  const salt = Buffer.from(blob.salt, "base64");
  const iv = Buffer.from(blob.iv, "base64");
  const key = await deriveKey(passphrase, salt);
  const pt = await crypto.subtle.decrypt(
    { name: "AES-GCM", iv }, key, Buffer.from(blob.ct, "base64"));
  const obj = JSON.parse(new TextDecoder().decode(pt));
  if (obj.name !== expectName) throw new Error("round-trip name mismatch");
  return true;
}

const existing = fs.existsSync(PASS_FILE)
  ? JSON.parse(fs.readFileSync(PASS_FILE, "utf8")) : {};

const files = fs.readdirSync(PAYLOAD).filter(f => f.endsWith(".json"));
const manifest = { generated: new Date().toISOString().slice(0, 10), people: [] };

for (const f of files) {
  const id = f.replace(/\.json$/, "");
  const payload = JSON.parse(fs.readFileSync(path.join(PAYLOAD, f), "utf8"));
  const passphrase = existing[id] || makePassphrase();
  existing[id] = passphrase;
  const blob = await encryptPayload(passphrase, JSON.stringify(payload));
  await decryptCheck(passphrase, blob, payload.name);     // verify before writing
  fs.writeFileSync(path.join(SITE_DATA, `${id}.enc`), JSON.stringify(blob));
  // PUBLIC manifest shows FIRST NAME ONLY (no surnames in the published repo).
  // The full name stays inside the encrypted payload, visible only after unlock.
  const first = payload.name.trim().split(/\s+/)[0];
  const initials = first.slice(0, 1).toUpperCase();
  manifest.people.push({ id, name: first, initials });
  console.log(`encrypted ${id}  (${(blob.ct.length/1365).toFixed(1)} KB)  round-trip OK`);
}

manifest.people.sort((a, b) => a.name.localeCompare(b.name));
fs.writeFileSync(path.join(SITE_DATA, "manifest.json"), JSON.stringify(manifest, null, 1));
fs.writeFileSync(PASS_FILE, JSON.stringify(existing, null, 2));
console.log("\nmanifest:", manifest.people.map(p => p.name).join(", "));
console.log("passphrases (LOCAL, git-ignored):", path.relative(ROOT, PASS_FILE));
