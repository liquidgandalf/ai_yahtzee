"""
AI Yahtzee Game Display
Pygame-based server display for the Yahtzee game
"""

import pygame
import sys
from app.server import shared_data, socketio

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
    for i, (sid, player) in enumerate(shared_data.players.items()):
        # Player color indicator
        pygame.draw.rect(screen, player['color'], (20, y_offset, 20, 20))

        # Player name and status
        status = "Ready" if player['ready'] else "Waiting"
        name_surf = font.render(f"{player['name']} ({status})", True, TEXT_COLOR)
        screen.blit(name_surf, (50, y_offset))

        y_offset += 30

    # Game status
    status_y = y_offset + 20
    phase_text = f"Phase: {shared_data.game_state['phase'].title()}"
    phase_surf = font.render(phase_text, True, TEXT_COLOR)
    screen.blit(phase_surf, (20, status_y))

    if shared_data.game_state['current_player']:
        current_player = shared_data.players.get(shared_data.game_state['current_player'])
        if current_player:
            current_text = f"Current: {current_player['name']}"
            current_surf = font.render(current_text, True, TEXT_COLOR)
            screen.blit(current_surf, (20, status_y + 30))

def draw_dice(screen, font):
    """Draw the current dice"""
    dice_y = 320  # Moved down to avoid QR code overlap (QR is at y=80-280)
    dice_text = font.render("Dice:", True, TEXT_COLOR)
    screen.blit(dice_text, (20, dice_y))

    dice_values = shared_data.game_state['dice']
    dice_kept = shared_data.game_state['dice_kept']

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
    roll_text = f"Roll: {shared_data.game_state['roll_count']}/{shared_data.game_state['max_rolls']}"
    roll_surf = font.render(roll_text, True, TEXT_COLOR)
    screen.blit(roll_surf, (20, dice_y + 80))

def draw_scoreboards(screen, font):
    """Draw player scoreboards in grid format: players as columns, categories as rows"""
    start_x = GAME_AREA_X + 20
    start_y = 20
    cell_width = 100
    cell_height = 30
    header_height = 40

    # Get player list (sorted by join order)
    player_list = []
    for sid, player_data in shared_data.players.items():
        player_data_copy = player_data.copy()
        player_data_copy['sid'] = sid  # Add sid to player data
        player_list.append(player_data_copy)

    if not player_list:
        return

    # Categories (rows)
    categories = [
        "Ones", "Twos", "Threes", "Fours", "Fives", "Sixes",
        "3-of-Kind", "4-of-Kind", "Full House", "Sm Straight",
        "Lg Straight", "Yahtzee", "Chance"
    ]

    # Draw player names as column headers
    for i, player in enumerate(player_list):
        player_x = start_x + (i + 1) * cell_width  # +1 to skip category column

        # Player name (truncated if too long)
        name = player['name'][:8] if len(player['name']) > 8 else player['name']
        name_surf = font.render(name, True, player['color'])
        screen.blit(name_surf, (player_x + 5, start_y + 10))

    # Draw category names and scores
    for row, category in enumerate(categories):
        row_y = start_y + header_height + (row * cell_height)

        # Category name in first column
        cat_name = category[:10]  # Truncate if too long
        cat_surf = font.render(cat_name, True, TEXT_COLOR)
        screen.blit(cat_surf, (start_x + 5, row_y + 5))

        # Draw scores for each player
        for col, player in enumerate(player_list):
            player_x = start_x + (col + 1) * cell_width
            player_scores = shared_data.game_state['scores'].get(player['sid'], {})

            # Get score for this category
            score_key = category.lower().replace(' ', '_').replace('-', '_')
            score = player_scores.get(score_key, '')

            # Draw cell background
            pygame.draw.rect(screen, (30, 30, 30), (player_x, row_y, cell_width-2, cell_height-2))

            # Draw score or dash
            score_text = str(score) if score != '' else '-'
            score_surf = font.render(score_text, True, TEXT_COLOR)
            screen.blit(score_surf, (player_x + cell_width//2 - 5, row_y + 5))

    # Draw total row
    total_row_y = start_y + header_height + (len(categories) * cell_height)

    # Total label
    total_surf = font.render("TOTAL", True, TEXT_COLOR)
    screen.blit(total_surf, (start_x + 5, total_row_y + 5))

    # Draw totals for each player
    for col, player in enumerate(player_list):
        player_x = start_x + (col + 1) * cell_width
        player_scores = shared_data.game_state['scores'].get(player['sid'], {})

        # Calculate total score
        total = 0
        for category in categories:
            score_key = category.lower().replace(' ', '_').replace('-', '_')
            score = player_scores.get(score_key, 0)
            if isinstance(score, int):
                total += score

        # Draw total cell background
        pygame.draw.rect(screen, (40, 40, 40), (player_x, total_row_y, cell_width-2, cell_height-2))

        # Draw total
        total_surf = font.render(str(total), True, (255, 255, 0))  # Yellow for totals
        screen.blit(total_surf, (player_x + cell_width//2 - 10, total_row_y + 5))

def run_game(screen, qr_surface):
    """Main game display loop"""
    clock = pygame.time.Clock()
    font = pygame.font.SysFont(None, 24)
    running = True
    frame_count = 0

    print("🎮 Starting Pygame display loop...")
    print(f"📺 Screen size: {SCREEN_WIDTH}x{SCREEN_HEIGHT}")
    print(f"👥 Players: {len(shared_data.players)}")
    print(f"🎲 Game phase: {shared_data.game_state['phase']}")

    while running:
        frame_count += 1
        screen.fill(BG_COLOR)

        # Draw borders
        pygame.draw.rect(screen, BORDER_COLOR, (GAME_AREA_X, 0, GAME_AREA_WIDTH, SCREEN_HEIGHT), BORDER_WIDTH)
        pygame.draw.line(screen, BORDER_COLOR, (SIDEBAR_WIDTH, 0), (SIDEBAR_WIDTH, SCREEN_HEIGHT), BORDER_WIDTH)

        # Draw game elements
        draw_sidebar(screen, font)

        # Draw QR code (after sidebar so it appears on top)
        if qr_surface:
            screen.blit(qr_surface, (20, 80))
        else:
            # Draw QR placeholder if no surface
            pygame.draw.rect(screen, (100, 100, 100), (20, 80, 200, 200))
            qr_text = font.render("QR Code", True, TEXT_COLOR)
            screen.blit(qr_text, (70, 170))

        draw_dice(screen, font)
        draw_scoreboards(screen, font)

        # Debug info with periodic logging
        debug_text = f"Players: {len(shared_data.players)} | Phase: {shared_data.game_state['phase']}"
        if shared_data.players:
            player_names = [p['name'] for p in shared_data.players.values()]
            debug_text += f" | Names: {', '.join(player_names)}"

            # Log player changes every 30 frames (1 second at 30fps)
            if frame_count % 30 == 0:
                print(f"📊 Display Update - Players: {len(shared_data.players)}, Names: {player_names}, Phase: {shared_data.game_state['phase']}")
                print(f"📊 Players dict keys: {list(shared_data.players.keys())}")
                print(f"📊 Players dict values: {list(shared_data.players.values())}")
        elif frame_count % 30 == 0:
            print(f"📊 Display Update - Players: {len(shared_data.players)}, Phase: {shared_data.game_state['phase']}")

        debug_surf = font.render(debug_text, True, (255, 255, 0))
        screen.blit(debug_surf, (GAME_AREA_X + 20, SCREEN_HEIGHT - 30))

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