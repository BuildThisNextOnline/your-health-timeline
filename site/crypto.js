// Browser-side decryption. Mirrors scripts/encrypt.mjs exactly:
// PBKDF2-SHA256 -> AES-GCM-256. Decryption happens entirely in this browser;
// nothing is sent anywhere. Without the correct passphrase the ciphertext
// cannot be read.
export async function decryptBlob(blob, passphrase) {
  const dec = (b64) => Uint8Array.from(atob(b64), c => c.charCodeAt(0));
  const salt = dec(blob.salt), iv = dec(blob.iv), ct = dec(blob.ct);
  const base = await crypto.subtle.importKey(
    "raw", new TextEncoder().encode(passphrase), "PBKDF2", false, ["deriveKey"]);
  const key = await crypto.subtle.deriveKey(
    { name: "PBKDF2", salt, iterations: blob.iter || 600000, hash: "SHA-256" },
    base, { name: "AES-GCM", length: 256 }, false, ["decrypt"]);
  const pt = await crypto.subtle.decrypt({ name: "AES-GCM", iv }, key, ct);
  return JSON.parse(new TextDecoder().decode(pt));
}
