"""
AI Yahtzee Game Display
Pygame-based server display for the Yahtzee game
"""

import pygame
import sys
from app.server import players, game_state, socketio

# Constants
SCREEN_WIDTH = 1920
SCREEN_HEIGHT = 1080
SIDEBAR_WIDTH = 300
BORDER_WIDTH = 4
GAME_AREA_X = SIDEBAR_WIDTH + BORDER_WIDTH
GAME_AREA_WIDTH = SCREEN_WIDTH - GAME_AREA_X - BORDER_WIDTH
GAME_AREA_HEIGHT = SCREEN_HEIGHT - (BORDER_WIDTH * 2)

# Colors
BORDER_COLOR = (255, 0, 0)
BG_COLOR = (0, 0, 0)
SIDEBAR_BG = (20, 20, 20)
TEXT_COLOR = (200, 200, 200)
DICE_COLOR = (255, 255, 255)
PLAYER_COLOR = (100, 100, 100)

def draw_sidebar(screen, font):
    """Draw the sidebar with player list and game info"""
    pygame.draw.rect(screen, SIDEBAR_BG, (0, 0, SIDEBAR_WIDTH, SCREEN_HEIGHT))
    pygame.draw.line(screen, BORDER_COLOR, (SIDEBAR_WIDTH, 0), (SIDEBAR_WIDTH, SCREEN_HEIGHT), BORDER_WIDTH)

    # Title
    title_surf = font.render("AI Yahtzee", True, TEXT_COLOR)
    screen.blit(title_surf, (20, 20))

    # QR Code placeholder
    qr_text = font.render("QR Code:", True, TEXT_COLOR)
    screen.blit(qr_text, (20, 60))

    # Player list
    y_offset = 120
    for i, (sid, player) in enumerate(players.items()):
        # Player color indicator
        pygame.draw.rect(screen, player['color'], (20, y_offset, 20, 20))

        # Player name and status
        status = "Ready" if player['ready'] else "Waiting"
        name_surf = font.render(f"{player['name']} ({status})", True, TEXT_COLOR)
        screen.blit(name_surf, (50, y_offset))

        y_offset += 30

    # Game status
    status_y = y_offset + 20
    phase_text = f"Phase: {game_state['phase'].title()}"
    phase_surf = font.render(phase_text, True, TEXT_COLOR)
    screen.blit(phase_surf, (20, status_y))

    if game_state['current_player']:
        current_player = players.get(game_state['current_player'])
        if current_player:
            current_text = f"Current: {current_player['name']}"
            current_surf = font.render(current_text, True, TEXT_COLOR)
            screen.blit(current_surf, (20, status_y + 30))

def draw_dice(screen, font):
    """Draw the current dice"""
    dice_y = 320  # Moved down to avoid QR code overlap (QR is at y=80-280)
    dice_text = font.render("Dice:", True, TEXT_COLOR)
    screen.blit(dice_text, (20, dice_y))

    dice_values = game_state['dice']
    dice_kept = game_state['dice_kept']

    for i, (value, kept) in enumerate(zip(dice_values, dice_kept)):
        x = 20 + (i * 60)
        y = dice_y + 30

        # Dice background
        color = (100, 100, 100) if kept else DICE_COLOR
        pygame.draw.rect(screen, color, (x, y, 40, 40))

        # Dice value
        value_surf = font.render(str(value), True, BG_COLOR)
        screen.blit(value_surf, (x + 15, y + 10))

    # Roll info
    roll_text = f"Roll: {game_state['roll_count']}/{game_state['max_rolls']}"
    roll_surf = font.render(roll_text, True, TEXT_COLOR)
    screen.blit(roll_surf, (20, dice_y + 80))

def draw_scoreboards(screen, font):
    """Draw player scoreboards"""
    start_x = GAME_AREA_X + 20
    start_y = 20

    # Headers
    categories = [
        "Ones", "Twos", "Threes", "Fours", "Fives", "Sixes",
        "3-of-Kind", "4-of-Kind", "Full House", "Sm Straight",
        "Lg Straight", "Yahtzee", "Chance"
    ]

    # Draw headers
    for i, category in enumerate(categories):
        x = start_x + (i % 4) * 150
        y = start_y + (i // 4) * 30
        cat_surf = font.render(category[:8], True, TEXT_COLOR)
        screen.blit(cat_surf, (x, y))

    # Draw player scores
    player_y = start_y + 150
    for sid, player in players.items():
        player_scores = game_state['scores'].get(sid, {})

        # Player name
        name_surf = font.render(player['name'], True, player['color'])
        screen.blit(name_surf, (start_x, player_y))

        # Scores
        for i, category in enumerate(categories):
            x = start_x + (i % 4) * 150
            y = player_y + ((i // 4) + 1) * 25

            score = player_scores.get(category.lower().replace(' ', '_'), '')
            score_text = str(score) if score != '' else '-'
            score_surf = font.render(score_text, True, TEXT_COLOR)
            screen.blit(score_surf, (x, y))

        player_y += 200

def run_game(screen, qr_surface):
    """Main game display loop"""
    clock = pygame.time.Clock()
    font = pygame.font.SysFont(None, 24)
    running = True

    while running:
        screen.fill(BG_COLOR)

        # Draw borders
        pygame.draw.rect(screen, BORDER_COLOR, (GAME_AREA_X, 0, GAME_AREA_WIDTH, SCREEN_HEIGHT), BORDER_WIDTH)
        pygame.draw.line(screen, BORDER_COLOR, (SIDEBAR_WIDTH, 0), (SIDEBAR_WIDTH, SCREEN_HEIGHT), BORDER_WIDTH)

        # Draw game elements
        draw_sidebar(screen, font)

        # Draw QR code (after sidebar so it appears on top)
        if qr_surface:
            screen.blit(qr_surface, (20, 80))

        draw_dice(screen, font)
        draw_scoreboards(screen, font)

        # Event handling
        for event in pygame.event.get():
            if (event.type == pygame.QUIT or
                (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE) or
                (event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE)):
                print("Shutting down game display...")
                running = False

        pygame.display.flip()
        clock.tick(30)

    pygame.quit()
    sys.exit(0)