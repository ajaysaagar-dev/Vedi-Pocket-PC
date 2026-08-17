"""QR code generator returning base64 data URLs."""

from __future__ import annotations

import base64
import io
from typing import Optional


def to_data_url(text: str) -> str:
    """Generate a PNG QR code and return it as a data:image/png;base64,... URL."""
    if not text:
        return ""
    try:
        import qrcode

        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=8,
            border=2,
        )
        qr.add_data(text)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        b64 = base64.b64encode(buf.getvalue()).decode("ascii")
        return f"data:image/png;base64,{b64}"
    except Exception as e:
        print(f"[QR] Error generating QR code: {e}")
        return ""
