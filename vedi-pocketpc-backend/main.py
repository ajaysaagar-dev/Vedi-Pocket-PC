import os
import sys
import threading
import socket
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import qrcode

# Import local modules
from state import state
from discovery import ServiceAdvertiser, get_local_ip, get_all_local_ips
from routes import pairing, system, media
import ws_handler

# Create FastAPI app
app = FastAPI(title="PC Remote Agent", version="1.0.0")

# Setup CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(pairing.router)
app.include_router(system.router, prefix="/system")
app.include_router(media.router, prefix="/media")
app.include_router(ws_handler.router)

# Discovery advertiser instance
advertiser = None

def print_banner(local_ip: str, port: int):
    """
    Prints a beautiful banner in the console with connection instructions
    and prints a text-based QR code for scanning.
    """
    all_ips = get_all_local_ips()
    print("=" * 60)
    print("                 PC REMOTE SERVER ACTIVE                ")
    print("=" * 60)
    print(f" Hostname:    {socket.gethostname()}")
    print(f" Primary IP:  {local_ip}")
    if len(all_ips) > 1:
        print(f" All IPs:     {', '.join(all_ips)}")
    print(f" Port:        {port}")
    print(f" Pairing PIN: {state.pairing_pin}")
    print("-" * 60)
    print(" Scan the QR Code below from your PC Remote Mobile App:")
    print("-" * 60)
    
    try:
        # Generate QR code containing connection payload: ip:port:pin
        qr_data = f"{local_ip}:{port}:{state.pairing_pin}"
        qr = qrcode.QRCode(version=1, box_size=1, border=2)
        qr.add_data(qr_data)
        qr.make(fit=True)
        # Print QR Code directly into the terminal
        qr.print_ascii(out=sys.stdout, invert=True)
    except Exception as e:
        print(f"Could not print QR Code: {e}")
        
    print("=" * 60)
    print(" Keep this window open or check the system tray icon.")
    print("=" * 60)

def show_pairing_info_dialog(icon=None, item=None):
    """
    Opens a small system message box displaying pairing details.
    """
    try:
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw() # Hide the main tk window
        # Put on top of other windows
        root.attributes("-topmost", True)
        messagebox.showinfo(
            "PC Remote Connection",
            f"Connect your mobile app using:\n\n"
            f"IP Address: {state.local_ip}\n"
            f"Port: {state.port}\n"
            f"Pairing PIN: {state.pairing_pin}"
        )
        root.destroy()
    except Exception as e:
        print(f"Error displaying dialog: {e}")

def run_tray():
    """
    Initializes and runs the Windows System Tray icon using pystray.
    """
    try:
        import pystray
        from PIL import Image, ImageDraw

        def create_image():
            # Create a 64x64 icon image with a rounded circle and white "R"
            image = Image.new('RGBA', (64, 64), color=(0, 0, 0, 0))
            draw = ImageDraw.Draw(image)
            # Draw a nice blue circle
            draw.ellipse([4, 4, 60, 60], fill=(33, 150, 243, 255))
            # Draw a white outline
            draw.ellipse([4, 4, 60, 60], outline=(255, 255, 255, 255), width=2)
            # Draw a crosshair or Remote icon representation
            draw.rectangle([28, 16, 36, 48], fill=(255, 255, 255, 255))
            draw.rectangle([16, 28, 48, 36], fill=(255, 255, 255, 255))
            return image

        def on_quit(icon, item):
            print("[SERVER] Shutting down agent...")
            if advertiser:
                advertiser.stop()
            icon.stop()
            # Clean process exit
            os._exit(0)

        # Build context menu for tray icon
        menu = pystray.Menu(
            pystray.MenuItem("Show Connection Info", show_pairing_info_dialog),
            pystray.MenuItem("Quit", on_quit)
        )
        
        icon = pystray.Icon(
            "pcremote",
            create_image(),
            title=f"PC Remote Server (PIN: {state.pairing_pin})",
            menu=menu
        )
        icon.run()
    except Exception as e:
        print(f"[TRAY] System tray could not start: {e}. Running in headless/terminal mode.")
        # If tray fails (e.g. no GUI environment), block main thread indefinitely
        import time
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            if advertiser:
                advertiser.stop()
            os._exit(0)

def main():
    global advertiser
    port = 8000
    local_ip = get_local_ip()

    # Save IP, hostname and port
    state.local_ip = local_ip
    state.port = port
    state.hostname = socket.gethostname()

    # Start Zeroconf mDNS advertisement
    advertiser = ServiceAdvertiser(port=port)
    advertiser.start()

    # Print pairing banner in console
    print_banner(local_ip, port)

    # Log detected monitors so the user can confirm pyautogui is targeting
    # the right display.
    import input_control
    input_control._log_monitor_info_once()

    # Start FastAPI server in a background thread
    def start_fastapi():
        # bind to all interfaces (0.0.0.0) so it's accessible over local network
        uvicorn.run(app, host="0.0.0.0", port=port, log_level="warning")

    server_thread = threading.Thread(target=start_fastapi, daemon=True)
    server_thread.start()

    # Automatically show connection info popup dialog after startup (2s delay)
    # This ensures users immediately see their pairing PIN when launching the .exe
    startup_timer = threading.Timer(2.0, show_pairing_info_dialog)
    startup_timer.daemon = True
    startup_timer.start()

    # Run system tray blockingly on the main thread (needed on Windows/Mac)
    run_tray()

if __name__ == "__main__":
    main()
