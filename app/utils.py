"""
Utility functions for AI Yahtzee
"""

import socket
import qrcode
from PIL import Image
import pygame

def get_local_ip():
    """Get the local IP address of the machine"""
    try:
        # Create a socket to get local IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

def generate_qr_surface(url, size=200):
    """Generate a QR code surface for Pygame display"""
    # Generate QR code
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(url)
    qr.make(fit=True)

    # Create PIL image
    img = qr.make_image(fill_color="black", back_color="white")

    # Convert to Pygame surface
    mode = img.mode
    size_pil = img.size
    data = img.tobytes()

    # Create Pygame surface
    surface = pygame.image.fromstring(data, size_pil, mode)

    # Scale to desired size
    surface = pygame.transform.scale(surface, (size, size))

    return surface