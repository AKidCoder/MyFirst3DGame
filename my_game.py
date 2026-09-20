import math
import random
import os
from pyray import *

# --- ELO & Rank System ---
ELO_FILE = "player_elo.txt"

def load_saved_elo():
    if os.path.exists(ELO_FILE):
        try:
            with open(ELO_FILE, "r") as f:
                return int(f.read().strip())
        except:
            return 100
    return 100

def save_player_elo(elo):
    with open(ELO_FILE, "w") as f:
        f.write(str(max(0, elo)))

def get_rank_info(elo):
    if elo >= 2500: return "MASTER", YELLOW
    if elo >= 2000: return "LEGENDARY", RED
    if elo >= 1600: return "MYTHIC", PURPLE
    if elo >= 1200: return "DIAMOND", SKYBLUE
    if elo >= 800:  return "GOLD", GOLD
    if elo >= 400:  return "SILVER", LIGHTGRAY
    return "BRONZE", DARKBROWN

# --- Game & Player Constants ---
NORMAL_EYE_HEIGHT = 2.0
CROUCH_EYE_HEIGHT = 1.0
BOX_SIZE = 4.0
PLAYER_R = 0.4
EXIT_RADIUS = 1.2
MAX_FLASHLIGHT_RANGE = 14.0 

# --- Monster Stats ---
STALKER_SPEED = 2.4
STALKER_R = 0.6

DASHER_NORMAL_SPEED = 1.2
DASHER_RUSH_SPEED = 5.2
DASHER_R = 0.5

# --- Environment Colors ---
WALL_COLOR = BROWN   
LINE_COLOR = BLACK    
FLOOR_COLOR = DARKBROWN   
CEIL_COLOR = Color(20, 15, 10, 255)
LOCKER_COLOR = Color(40, 45, 50, 255)
CYAN = Color(0, 255, 255, 255)

# --- Initialization ---
init_window(1500, 1000, "3D Maze - The Backrooms")
init_audio_device()
set_target_fps(60)
disable_cursor()

# --- Procedural Footstep Audio ---
def create_footstep_sound():
    frame_count = 2000
    data_buffer = ffi.new(f"float[{frame_count}]")
    for i in range(frame_count):
        decay = (1.0 - (i / frame_count)) ** 2
        val = (math.sin(i * 0.08) * 0.7 + (random.random() - 0.5) * 0.3) * decay * 0.6
        data_buffer[i] = max(-1.0, min(1.0, val))
    
    wave = Wave()
    wave.frameCount = frame_count
    wave.sampleRate = 44100
    wave.sampleSize = 32
    wave.channels = 1
    wave.data = data_buffer
    
    snd = load_sound_from_wave(wave)
    set_sound_volume(snd, 0.45)
    return snd

step_sound = create_footstep_sound()

# --- Map Blueprint ---
LEVEL_MAP = [
    "111111111111111111111111111",
    "1000000000000000000000000E1",
    "1011111011111110111111100B1",
    "101000101000001010000010001",
    "101010101011101010111011101",
    "101010000010100000101000101",
    "101011111110111111101110101",
    "1000000000S0000000D00000001",
    "101111111011111110111111101",
    "101L0000101000001010000L101",
    "101111101010111010101111101",
    "1P0000000000000000000000001",
    "111111111111111111111111111"
]

# --- Parse Map Data ---
boxes = []
grid_tiles = []
lockers = []
possible_spots = [] 
rows = len(LEVEL_MAP)
cols = len(LEVEL_MAP[0])

spawn_x, spawn_z = 0.0, 0.0
exit_x, exit_z = 0.0, 0.0
breaker_x, breaker_z = 0.0, 0.0
stalker_spawn_x, stalker_spawn_z = 0.0, 0.0
dasher_spawn_x, dasher_spawn_z = 0.0, 0.0

for row in range(rows):
    for col in range(cols):
        tile = LEVEL_MAP[row][col]
        wx = (col - cols / 2.0 + 0.5) * BOX_SIZE
        wz = (row - rows / 2.0 + 0.5) * BOX_SIZE
        
        grid_tiles.append((wx, wz))
        
        if tile == "1":
            boxes.append((wx, wz))
        elif tile == "P":
            spawn_x, spawn_z = wx, wz
        elif tile == "E":
            exit_x, exit_z = wx, wz
        elif tile == "B":
            breaker_x, breaker_z = wx, wz
        elif tile == "S":
            stalker_spawn_x, stalker_spawn_z = wx, wz
            possible_spots.append((wx, wz))
        elif tile == "D":
            dasher_spawn_x, dasher_spawn_z = wx, wz
            possible_spots.append((wx, wz))
        elif tile == "L":
            lockers.append((wx, wz))
        elif tile == "0":
            possible_spots.append((wx, wz))

# Determine Valid Fuse Spots Once
MIN_FUSE_DIST = 32.0 
fuse_spots = [
    (wx, wz) for (wx, wz) in possible_spots
    if math.hypot(wx - spawn_x, wz - spawn_z) >= MIN_FUSE_DIST
    and math.hypot(wx - exit_x, wz - exit_z) >= 16.0
]
valid_fuse_spots = fuse_spots if fuse_spots else possible_spots

camera = Camera3D(
    Vector3(spawn_x, NORMAL_EYE_HEIGHT, spawn_z),
    Vector3(spawn_x, NORMAL_EYE_HEIGHT, spawn_z - 1.0),
    Vector3(0, 1, 0),
    60.0,
    CAMERA_PERSPECTIVE
)

# --- State Variables ---
in_menu = True  # <--- New Menu State
game_won = False
game_over = False
death_cause = ""
elapsed = 0.0
bob_timer = 0.0
step_timer = 0.0
stamina = 100.0

# Rank Variables
current_elo = load_saved_elo()
elo_change = 0
match_evaluated = False
match_timer = 0.0
locker_used_count = 0

# Game Phase Variables
has_fuse = False
power_on = False
show_locked_msg_timer = 0.0

stalker_active = False
dasher_active = False
stalker_x, stalker_z = stalker_spawn_x, stalker_spawn_z
dasher_x, dasher_z = dasher_spawn_x, dasher_spawn_z

spawn_warning_msg = ""
spawn_warning_timer = 0.0
spawn_warning_color = WHITE
dasher_state_timer = 0.0
dasher_is_rushing = False

is_hiding = False
pre_hide_x, pre_hide_z = 0.0, 0.0 

# Roll First Fuse
fuse_x, fuse_z = random.choice(valid_fuse_spots)

# --- Helpers ---
def resolve_collision(px, pz, radius):
    for _ in range(2):
        for bx, bz in boxes:
            min_x, max_x = bx - BOX_SIZE / 2.0, bx + BOX_SIZE / 2.0
            min_z, max_z = bz - BOX_SIZE / 2.0, bz + BOX_SIZE / 2.0
            
            cx = max(min_x, min(px, max_x))
            cz = max(min_z, min(pz, max_z))
            
            dist_x = px - cx
            dist_z = pz - cz
            dist_sq = dist_x**2 + dist_z**2
            
            if 0 < dist_sq < radius**2:
                dist = math.sqrt(dist_sq)
                overlap = radius - dist
                px += (dist_x / dist) * overlap
                pz += (dist_z / dist) * overlap
            elif dist_sq == 0:
                px += radius
                pz += radius
    return px, pz

def get_relative_direction(target_x, target_z, cam_pos_x, cam_pos_z, fwd_x, fwd_z, right_x, right_z):
    to_tgt_x = target_x - cam_pos_x
    to_tgt_z = target_z - cam_pos_z
    dist = math.hypot(to_tgt_x, to_tgt_z)
    if dist == 0: return "NEARBY"
    
    to_tgt_x /= dist
    to_tgt_z /= dist
    
    fwd_dot = to_tgt_x * fwd_x + to_tgt_z * fwd_z
    right_dot = to_tgt_x * right_x + to_tgt_z * right_z
    
    if fwd_dot > 0.5: return "AHEAD OF YOU"
    elif fwd_dot < -0.5: return "BEHIND YOU"
    elif right_dot > 0.5: return "TO YOUR RIGHT"
    else: return "TO YOUR LEFT"

# --- Main Game Loop ---
while not window_should_close():
    dt = get_frame_time()
    elapsed += dt
    
    # --- 1. MAIN MENU LOGIC ---
    if in_menu:
        if is_key_pressed(KEY_ENTER):
            in_menu = False
            match_timer = 0.0  # Reset timer on fresh start

        begin_drawing()
        clear_background(Color(10, 10, 12, 255))
        
        # Title
        draw_text("THE BACKROOMS", 450, 200, 75, MAROON)
        draw_text("ISOLATION PROTOCOL", 610, 290, 24, GRAY)
        
        # Rank Display
        rank_title, rank_col = get_rank_info(current_elo)
        draw_text(f"CURRENT RANK: {rank_title} ({current_elo} ELO)", 520, 390, 32, rank_col)
        
        # Controls Box
        draw_rectangle_lines(580, 480, 340, 180, DARKGRAY)
        draw_text("CONTROLS:", 600, 495, 22, LIGHTGRAY)
        draw_text("[W A S D] - Move", 600, 535, 20, GRAY)
        draw_text("[SHIFT] - Sprint", 600, 565, 20, GRAY)
        draw_text("[CTRL] - Crouch / Sneak", 600, 595, 20, GRAY)
        draw_text("[E] - Interact", 600, 625, 20, GRAY)
        
        # Pulsing Start Prompt
        pulse_alpha = int((math.sin(elapsed * 5.0) + 1.0) / 2.0 * 200 + 55)
        draw_text("PRESS [ENTER] TO DESCEND", 530, 750, 32, Color(255, 255, 255, pulse_alpha))
        
        end_drawing()
        continue  # Skips the rest of the game loop while in the menu

    # --- 2. GAMEPLAY LOGIC ---
    old_x = camera.position.x 
    old_z = camera.position.z

    # --- Match Restart (SPACE) or Return to Menu (M) ---
    if game_won or game_over:
        if is_key_pressed(KEY_SPACE) or is_key_pressed(KEY_M):
            
            # Go back to menu if M is pressed
            if is_key_pressed(KEY_M):
                in_menu = True

            # Reset all states for the next round
            game_won = False
            game_over = False
            match_evaluated = False
            match_timer = 0.0
            locker_used_count = 0
            has_fuse = False
            power_on = False
            stalker_active = False
            dasher_active = False
            stamina = 100.0
            spawn_warning_timer = 0.0
            is_hiding = False
            
            camera.position = Vector3(spawn_x, NORMAL_EYE_HEIGHT, spawn_z)
            camera.target = Vector3(spawn_x, NORMAL_EYE_HEIGHT, spawn_z - 1.0)
            
            stalker_x, stalker_z = stalker_spawn_x, stalker_spawn_z
            dasher_x, dasher_z = dasher_spawn_x, dasher_spawn_z
            fuse_x, fuse_z = random.choice(valid_fuse_spots)

    if not game_won and not game_over:
        match_timer += dt
        
        cam_fwd_x = camera.target.x - camera.position.x
        cam_fwd_z = camera.target.z - camera.position.z
        cam_len = math.hypot(cam_fwd_x, cam_fwd_z)
        if cam_len > 0:
            cam_fwd_x /= cam_len
            cam_fwd_z /= cam_len
        cam_right_x = -cam_fwd_z
        cam_right_z = cam_fwd_x

        if not is_hiding:
            if not stalker_active and math.hypot(camera.position.x - stalker_spawn_x, camera.position.z - stalker_spawn_z) < 32.0:
                stalker_active = True
                direction = get_relative_direction(stalker_x, stalker_z, camera.position.x, camera.position.z, cam_fwd_x, cam_fwd_z, cam_right_x, cam_right_z)
                spawn_warning_msg = f"SHADOW STALKER APPEARED {direction}!"
                spawn_warning_timer = 4.0
                spawn_warning_color = GRAY
                
            if not dasher_active and math.hypot(camera.position.x - dasher_spawn_x, camera.position.z - dasher_spawn_z) < 32.0:
                if spawn_warning_timer <= 0.0: 
                    dasher_active = True
                    direction = get_relative_direction(dasher_x, dasher_z, camera.position.x, camera.position.z, cam_fwd_x, cam_fwd_z, cam_right_x, cam_right_z)
                    spawn_warning_msg = f"THE DASHER SPAWNED {direction}!"
                    spawn_warning_timer = 4.0
                    spawn_warning_color = RED

        s_dist = math.hypot(camera.position.x - stalker_x, camera.position.z - stalker_z) if stalker_active else 999.0
        d_dist = math.hypot(camera.position.x - dasher_x, camera.position.z - dasher_z) if dasher_active else 999.0

        near_locker = None
        for lx, lz in lockers:
            if math.hypot(camera.position.x - lx, camera.position.z - lz) < 2.5:
                near_locker = (lx, lz)
                break

        near_breaker = math.hypot(camera.position.x - breaker_x, camera.position.z - breaker_z) < 3.0

        if is_key_pressed(KEY_E):
            if is_hiding:
                is_hiding = False
                camera.position.x = pre_hide_x
                camera.position.z = pre_hide_z
            elif near_locker is not None:
                is_hiding = True
                locker_used_count += 1
                pre_hide_x = camera.position.x
                pre_hide_z = camera.position.z
                camera.position.x = near_locker[0]
                camera.position.z = near_locker[1]
            elif near_breaker and has_fuse and not power_on:
                power_on = True
                play_sound(step_sound) 

        if not is_hiding:
            update_camera(camera, CAMERA_FIRST_PERSON)
            
            moved_x = camera.position.x - old_x
            moved_z = camera.position.z - old_z
            moved_dist = math.hypot(moved_x, moved_z)
            is_moving = moved_dist > 0.001

            speed_mult = 1.0
            target_eye_height = NORMAL_EYE_HEIGHT
            
            if is_key_down(KEY_LEFT_CONTROL):
                speed_mult = 0.4
                target_eye_height = CROUCH_EYE_HEIGHT
                stamina = min(100.0, stamina + 20.0 * dt) 
            elif is_key_down(KEY_LEFT_SHIFT) and stamina > 0 and is_moving:
                speed_mult = 1.4
                stamina -= 35.0 * dt
            else:
                stamina = min(100.0, stamina + 15.0 * dt)

            camera.position.x += moved_x * (speed_mult - 1.0)
            camera.position.z += moved_z * (speed_mult - 1.0)
            camera.target.x += moved_x * (speed_mult - 1.0)
            camera.target.z += moved_z * (speed_mult - 1.0)

            new_px, new_pz = resolve_collision(camera.position.x, camera.position.z, PLAYER_R)
            shift_x = new_px - camera.position.x
            shift_z = new_pz - camera.position.z
            camera.position.x += shift_x
            camera.position.z += shift_z
            camera.target.x += shift_x 
            camera.target.z += shift_z

            if is_moving:
                bob_timer += dt * 10.0 * speed_mult
                step_timer += dt * speed_mult
                
                bob_offset = math.sin(bob_timer) * 0.12 * speed_mult
                camera.position.y += (target_eye_height + bob_offset - camera.position.y) * 10.0 * dt
                camera.target.y = camera.position.y

                if step_timer >= 0.35:
                    if not is_key_down(KEY_LEFT_CONTROL): play_sound(step_sound)
                    step_timer = 0.0
            else:
                camera.position.y += (target_eye_height - camera.position.y) * 10.0 * dt
                camera.target.y = camera.position.y
                step_timer = 0.3

            if not has_fuse and math.hypot(camera.position.x - fuse_x, camera.position.z - fuse_z) < 1.4:
                has_fuse = True

            dist_to_exit = math.hypot(camera.position.x - exit_x, camera.position.z - exit_z)
            if dist_to_exit < EXIT_RADIUS:
                if power_on: game_won = True
                else: show_locked_msg_timer = 1.5

            if stalker_active and s_dist > 0:
                s_dir_x = camera.position.x - stalker_x
                s_dir_z = camera.position.z - stalker_z
                stalker_x += (s_dir_x / s_dist) * STALKER_SPEED * dt
                stalker_z += (s_dir_z / s_dist) * STALKER_SPEED * dt
                stalker_x, stalker_z = resolve_collision(stalker_x, stalker_z, STALKER_R)

            if dasher_active:
                dasher_state_timer += dt
                if not dasher_is_rushing and dasher_state_timer > 4.0:
                    dasher_is_rushing = True
                    dasher_state_timer = 0.0
                elif dasher_is_rushing and dasher_state_timer > 1.5:
                    dasher_is_rushing = False
                    dasher_state_timer = 0.0

                current_dasher_speed = DASHER_RUSH_SPEED if dasher_is_rushing else DASHER_NORMAL_SPEED

                if d_dist > 0:
                    d_dir_x = camera.position.x - dasher_x
                    d_dir_z = camera.position.z - dasher_z
                    dasher_x += (d_dir_x / d_dist) * current_dasher_speed * dt
                    dasher_z += (d_dir_z / d_dist) * current_dasher_speed * dt
                    dasher_x, dasher_z = resolve_collision(dasher_x, dasher_z, DASHER_R)

            if stalker_active and s_dist < PLAYER_R + STALKER_R:
                game_over = True
                death_cause = "THE SHADOW STALKER CAUGHT YOU"
            elif dasher_active and d_dist < PLAYER_R + DASHER_R:
                game_over = True
                death_cause = "THE DASHER TORE YOU APART"

        else: 
            update_camera(camera, CAMERA_FIRST_PERSON)
            camera.position.x = near_locker[0] 
            camera.position.z = near_locker[1]
            cam_fwd_x = camera.target.x - camera.position.x
            cam_fwd_z = camera.target.z - camera.position.z
            cam_len = math.hypot(cam_fwd_x, cam_fwd_z)
            if cam_len > 0:
                cam_fwd_x /= cam_len
                cam_fwd_z /= cam_len
            cam_right_x = -cam_fwd_z
            cam_right_z = cam_fwd_x

    # --- Match Evaluation (ELO Processing) ---
    if (game_won or game_over) and not match_evaluated:
        match_evaluated = True
        if game_won:
            gained = 60
            if match_timer < 60.0: gained += 30
            elif match_timer < 90.0: gained += 15
            if locker_used_count == 0: gained += 25
            elo_change = gained
            current_elo += gained
        else:
            lost = 35
            if match_timer < 20.0: lost += 15
            elo_change = -lost
            current_elo = max(0, current_elo - lost)
        save_player_elo(current_elo)

    # --- 3. RENDER 3D WORLD ---
    begin_drawing()
    clear_background(BLACK)
    
    begin_mode_3d(camera)
    current_vision = MAX_FLASHLIGHT_RANGE
    
    for tx, tz in grid_tiles:
        if math.hypot(camera.position.x - tx, camera.position.z - tz) < current_vision:
            draw_cube(Vector3(tx, -0.5, tz), BOX_SIZE, 1.0, BOX_SIZE, FLOOR_COLOR)
            draw_cube(Vector3(tx, 4.5, tz), BOX_SIZE, 1.0, BOX_SIZE, CEIL_COLOR)

    for bx, bz in boxes:
        if math.hypot(camera.position.x - bx, camera.position.z - bz) < current_vision:
            draw_cube(Vector3(bx, BOX_SIZE / 2.0, bz), BOX_SIZE, BOX_SIZE, BOX_SIZE, WALL_COLOR)
            draw_cube_wires(Vector3(bx, BOX_SIZE / 2.0, bz), BOX_SIZE, BOX_SIZE, BOX_SIZE, LINE_COLOR)

    for lx, lz in lockers:
        if math.hypot(camera.position.x - lx, camera.position.z - lz) < current_vision:
            draw_cube(Vector3(lx, 1.8, lz), 1.6, 3.6, 1.6, LOCKER_COLOR)
            draw_cube_wires(Vector3(lx, 1.8, lz), 1.6, 3.6, 1.6, BLACK)

    if math.hypot(camera.position.x - breaker_x, camera.position.z - breaker_z) < current_vision:
        draw_cube(Vector3(breaker_x, 2.0, breaker_z), 1.5, 2.0, 1.5, GRAY)
        light_color = GREEN if power_on else RED
        draw_cube(Vector3(breaker_x, 2.5, breaker_z + 0.8), 0.2, 0.2, 0.2, light_color)

    if not has_fuse and math.hypot(camera.position.x - fuse_x, camera.position.z - fuse_z) < current_vision:
        hover = 1.0 + math.sin(elapsed * 4.0) * 0.2
        draw_cube(Vector3(fuse_x, hover, fuse_z), 0.3, 0.6, 0.3, CYAN)
        draw_cube_wires(Vector3(fuse_x, hover, fuse_z), 0.3, 0.6, 0.3, BLUE)
      
    if stalker_active and s_dist < current_vision:
        s_glitch = (15.0 - s_dist) * 0.05 if s_dist < 15.0 else 0.0
        gx = random.uniform(-s_glitch, s_glitch)
        gz = random.uniform(-s_glitch, s_glitch)
        draw_cylinder(Vector3(stalker_x + gx, 0.0, stalker_z + gz), STALKER_R, STALKER_R, 3.5, 8, BLACK)
        draw_sphere(Vector3(stalker_x + gx, 3.5, stalker_z + gz), 0.5, BLACK)

    if dasher_active and d_dist < current_vision:
        d_color = RED if dasher_is_rushing else MAROON
        d_height = 2.2 + (math.sin(elapsed * 18.0) * 0.4 if dasher_is_rushing else 0.0)
        draw_cylinder(Vector3(dasher_x, 0.0, dasher_z), DASHER_R, 0.1, d_height, 6, d_color)
        draw_sphere(Vector3(dasher_x, d_height + 0.3, dasher_z), 0.3, ORANGE if dasher_is_rushing else RED)
        
    exit_color = GREEN if power_on else MAROON
    wire_color = LIME if power_on else RED
    draw_cube(Vector3(exit_x, 2.0, exit_z), 2.0, 4.0, 2.0, exit_color)
    draw_cube_wires(Vector3(exit_x, 2.0, exit_z), 2.0, 4.0, 2.0, wire_color)
    
    end_mode_3d()

    # --- 4. RENDER 2D SCREEN OVERLAYS ---
    if not is_hiding and dasher_active and dasher_is_rushing and d_dist < 20.0 and not game_over and not game_won:
        blood_pulse = (math.sin(elapsed * 20.0) + 1.0) / 2.0
        blood_alpha = int((1.0 - (d_dist / 20.0)) * 120 * blood_pulse + 40)
        draw_rectangle(0, 0, 1500, 1000, Color(200, 0, 0, blood_alpha))

    if is_hiding:
        draw_rectangle(0, 0, 1500, 260, Color(0, 0, 0, 230))
        draw_rectangle(0, 740, 1500, 260, Color(0, 0, 0, 230))
        draw_rectangle(0, 260, 300, 480, Color(0, 0, 0, 230))
        draw_rectangle(1200, 260, 300, 480, Color(0, 0, 0, 230))
        draw_text("[E] EXIT LOCKER", 630, 800, 28, LIGHTGRAY)
    else:
        draw_text("+", 744, 490, 20, DARKGRAY) 
        if is_key_down(KEY_LEFT_CONTROL): draw_text("CROUCHING", 700, 520, 18, GRAY)

    if not is_hiding and not game_over and not game_won:
        if near_locker is not None:
            draw_text("[E] HIDE IN LOCKER", 610, 560, 26, YELLOW)
        elif near_breaker and has_fuse and not power_on:
            draw_text("[E] FLIP POWER BREAKER", 580, 560, 26, GREEN)

        if spawn_warning_timer > 0.0:
            spawn_warning_timer -= dt
            text_width = measure_text(spawn_warning_msg, 38)
            draw_text(spawn_warning_msg, 750 - (text_width // 2), 150, 38, spawn_warning_color)

        if show_locked_msg_timer > 0.0:
            show_locked_msg_timer -= dt
            draw_text("NO POWER - FLIP THE BREAKER!", 470, 400, 32, RED)

        # UI: Stamina Bar
        draw_rectangle(20, 950, int(stamina * 3), 20, Color(200, 200, 200, 180))
        draw_rectangle_lines(20, 950, 300, 20, DARKGRAY)
        draw_text("STAMINA", 20, 925, 20, LIGHTGRAY)

        # UI: Live Rank & ELO
        rank_title, rank_col = get_rank_info(current_elo)
        draw_text(f"RANK: {rank_title} ({current_elo} ELO)", 1150, 30, 20, rank_col)

        # UI: Objectives
        if power_on: draw_text("OBJECTIVE: POWER ON - ESCAPE!", 30, 30, 24, GOLD)
        elif has_fuse: draw_text("OBJECTIVE: FIND BREAKER NEAR EXIT", 30, 30, 24, ORANGE)
        else: draw_text("OBJECTIVE: FIND THE FUSE", 30, 30, 24, CYAN)

        # UI: Threat Arrows
        def draw_threat_arrow(mx, mz, dist, base_r, base_g, base_b):
            if dist < 12.0:
                to_m_x = (mx - camera.position.x) / dist
                to_m_z = (mz - camera.position.z) / dist
                fwd_dot = to_m_x * cam_fwd_x + to_m_z * cam_fwd_z
                right_dot = to_m_x * cam_right_x + to_m_z * cam_right_z
                pulse = int((1.0 - (dist / 12.0)) * 220)
                c = Color(base_r, base_g, base_b, pulse)
                
                if fwd_dot < 0.2:
                    if right_dot > 0.4: draw_triangle(Vector2(1480, 500), Vector2(1440, 470), Vector2(1440, 530), c)
                    elif right_dot < -0.4: draw_triangle(Vector2(20, 500), Vector2(60, 530), Vector2(60, 470), c)
                    else: draw_triangle(Vector2(750, 980), Vector2(720, 940), Vector2(780, 940), c)

        if stalker_active: draw_threat_arrow(stalker_x, stalker_z, s_dist, 100, 100, 100)
        if dasher_active: draw_threat_arrow(dasher_x, dasher_z, d_dist, 230, 40, 40)

    # --- Match End Evaluation Screen ---
    if game_won or game_over:
        draw_rectangle(0, 0, 1500, 1000, Color(0, 0, 0, 235))
        
        if game_won: draw_text("VICTORY - ESCAPED", 520, 220, 48, GOLD)
        else: draw_text(death_cause, 380, 220, 40, RED)

        rank_title, rank_col = get_rank_info(current_elo)
        draw_text(f"TIER: {rank_title}", 620, 340, 44, rank_col)
        
        change_text = f"+{elo_change} ELO" if elo_change >= 0 else f"{elo_change} ELO"
        change_col = GREEN if elo_change >= 0 else RED
        draw_text(f"RATING: {current_elo}  ({change_text})", 530, 410, 32, change_col)

        mins = int(match_timer) // 60
        secs = int(match_timer) % 60
        draw_text(f"SURVIVAL TIME: {mins:02d}:{secs:02d}", 580, 480, 24, LIGHTGRAY)
        draw_text(f"LOCKER HIDES: {locker_used_count}", 580, 515, 24, LIGHTGRAY)

        draw_text("PRESS [SPACE] TO PLAY AGAIN  |  PRESS [M] FOR MAIN MENU", 360, 620, 24, DARKGRAY)

    end_drawing()

# --- Cleanup ---
unload_sound(step_sound)
close_audio_device()
close_window()