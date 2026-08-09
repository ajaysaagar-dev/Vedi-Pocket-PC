/**
 * QR code helpers — thin wrapper around the `qrcode` package.
 *
 * Pulled out of `main.js` so the IPC handler stays small.
 */
const QRCode = require('qrcode');

async function toDataUrl(text) {
  if (!text) return '';
  try {
    return await QRCode.toDataURL(text);
  } catch (e) {
    console.error('Error generating QR code:', e);
    return '';
  }
}

module.exports = { toDataUrl };
