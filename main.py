#!/usr/bin/env python3
"""
AI Yahtzee - Multiplayer Yahtzee Game
Main entry point for the game server
"""

import os
from threading import Thread
import pygame
from app.game import run_game
from app.server import run_server
from app.utils import get_local_ip, generate_qr_surface

def main():
    """Main entry point"""
    print("🎲 Starting AI Yahtzee Server...")

    # Start Flask server in background thread
    Thread(target=run_server, daemon=True).start()

    # Initialize Pygame
    pygame.init()

    # Set window to be centered and visible
    os.environ['SDL_VIDEO_CENTERED'] = '1'
    screen = pygame.display.set_mode((1920, 1080))
    pygame.display.set_caption("AI Yahtzee")

    print("🖥️  Pygame window created - should be visible now!")
    print("📍 Window size: 1920x1080 (centered on screen)")
    print("🎨 If you don't see it, check if it's minimized or behind other windows")

    # Generate QR code for mobile access
    ip = get_local_ip()
    url = f"http://{ip}:5050/controller"
    qr_surface = generate_qr_surface(url, size=200)

    print(f"📱 QR points to: {url}")
    print(f"🎮 Game server running at: http://{ip}:5050")
    print("Press ESC or SPACE to quit")

    # Start the game display
    run_game(screen, qr_surface)

if __name__ == "__main__":
    main()