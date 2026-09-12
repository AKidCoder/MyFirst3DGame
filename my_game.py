import math
import random
from pyray import *

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
    "1111111111111111111",
    "11110D10000010010E1",   
    "1111101011101010011",
    "111S000110001111001", 
    "11101111L0101000101",
    "110000P0001000100L1",   
    "1111111111111111111"
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
stalker_x, stalker_z = 0.0, 0.0
dasher_x, dasher_z = 0.0, 0.0

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
        elif tile == "S":
            stalker_x, stalker_z = wx, wz
        elif tile == "D":
            dasher_x, dasher_z = wx, wz
        elif tile == "L":
            lockers.append((wx, wz))
        elif tile == "0":
            possible_spots.append((wx, wz))

# Filter spots so the key spawns far away from the player's spawn (and not right at the exit)
MIN_KEY_DIST = 16.0  # Must be at least 4-5 corridors away

far_spots = [
    (wx, wz) for (wx, wz) in possible_spots
    if math.hypot(wx - spawn_x, wz - spawn_z) >= MIN_KEY_DIST
    and math.hypot(wx - exit_x, wz - exit_z) >= 8.0
]

# Fallback in case the map is too small
valid_key_spots = far_spots if far_spots else possible_spots

random.shuffle(valid_key_spots)
key_x, key_z = valid_key_spots[0]

# Remove the key's location from possible battery spots so they don't overlap
remaining_spots = [pt for pt in possible_spots if pt != (key_x, key_z)]
random.shuffle(remaining_spots)
batteries = remaining_spots[:2]

camera = Camera3D(
    Vector3(spawn_x, NORMAL_EYE_HEIGHT, spawn_z),
    Vector3(spawn_x, NORMAL_EYE_HEIGHT, spawn_z - 1.0),
    Vector3(0, 1, 0),
    60.0,
    CAMERA_PERSPECTIVE
)

# --- State Variables ---
game_won = False
game_over = False
death_cause = ""
elapsed = 0.0

bob_timer = 0.0
step_timer = 0.0

# Survival Stats
stamina = 100.0
battery_power = 100.0

has_key = False
show_locked_msg_timer = 0.0

dasher_state_timer = 0.0
dasher_is_rushing = False

is_hiding = False
pre_hide_x, pre_hide_z = 0.0, 0.0 

# --- Smooth Sliding Collision Logic ---
def resolve_collision(px, pz, radius):
    """Pushes an object smoothly out of intersecting walls using Circle-AABB math."""
    # Run twice to resolve corner pinches
    for _ in range(2):
        for bx, bz in boxes:
            min_x, max_x = bx - BOX_SIZE / 2.0, bx + BOX_SIZE / 2.0
            min_z, max_z = bz - BOX_SIZE / 2.0, bz + BOX_SIZE / 2.0
            
            # Find closest point on the box to the circle center
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
                # Failsafe if completely inside a block
                px += radius
                pz += radius
    return px, pz

# --- Main Game Loop ---
while not window_should_close():
    dt = get_frame_time()
    elapsed += dt
    
    old_x = camera.position.x 
    old_z = camera.position.z

    s_dir_x = camera.position.x - stalker_x
    s_dir_z = camera.position.z - stalker_z
    s_dist = math.hypot(s_dir_x, s_dir_z)

    d_dir_x = camera.position.x - dasher_x
    d_dir_z = camera.position.z - dasher_z
    d_dist = math.hypot(d_dir_x, d_dir_z)

    if not game_won and not game_over:
        
        # Flashlight Battery Drain
        if not is_hiding:
            battery_power -= 1 * dt
            if battery_power < 0: battery_power = 0.0

        current_vision = max(4.0, MAX_FLASHLIGHT_RANGE * (battery_power / 100.0))
        
        if battery_power < 25.0 and random.random() < 0.08:
            current_vision = 0.0 

        # --- Locker Interaction Logic ---
        near_locker = None
        for lx, lz in lockers:
            if math.hypot(camera.position.x - lx, camera.position.z - lz) < 2.5:
                near_locker = (lx, lz)
                break

        if is_key_pressed(KEY_E):
            if is_hiding:
                is_hiding = False
                camera.position.x = pre_hide_x
                camera.position.z = pre_hide_z
            elif near_locker is not None:
                is_hiding = True
                pre_hide_x = camera.position.x
                pre_hide_z = camera.position.z
                camera.position.x = near_locker[0]
                camera.position.z = near_locker[1]

        # --- Normal Player Logic ---
        if not is_hiding:
            update_camera(camera, CAMERA_FIRST_PERSON)
            
            moved_x = camera.position.x - old_x
            moved_z = camera.position.z - old_z
            moved_dist = math.hypot(moved_x, moved_z)
            is_moving = moved_dist > 0.001

            # Movement Modifiers
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

            # Apply movement multiplier
            camera.position.x += moved_x * (speed_mult - 1.0)
            camera.position.z += moved_z * (speed_mult - 1.0)
            camera.target.x += moved_x * (speed_mult - 1.0)
            camera.target.z += moved_z * (speed_mult - 1.0)

            # Smooth Player Collision
            new_px, new_pz = resolve_collision(camera.position.x, camera.position.z, PLAYER_R)
            shift_x = new_px - camera.position.x
            shift_z = new_pz - camera.position.z
            camera.position.x += shift_x
            camera.position.z += shift_z
            camera.target.x += shift_x 
            camera.target.z += shift_z

            # Head bobbing & Camera Height smoothing
            if is_moving:
                bob_timer += dt * 10.0 * speed_mult
                step_timer += dt * speed_mult
                
                bob_offset = math.sin(bob_timer) * 0.12 * speed_mult
                camera.position.y += (target_eye_height + bob_offset - camera.position.y) * 10.0 * dt
                camera.target.y = camera.position.y

                if step_timer >= 0.35:
                    if not is_key_down(KEY_LEFT_CONTROL):
                        play_sound(step_sound)
                    step_timer = 0.0
            else:
                camera.position.y += (target_eye_height - camera.position.y) * 10.0 * dt
                camera.target.y = camera.position.y
                step_timer = 0.3

            # Objective: Pick up Key
            if not has_key and math.hypot(camera.position.x - key_x, camera.position.z - key_z) < 1.4:
                has_key = True

            # Objective: Pick up Batteries
            for b in batteries[:]:
                if math.hypot(camera.position.x - b[0], camera.position.z - b[1]) < 1.4:
                    batteries.remove(b)
                    battery_power = min(100.0, battery_power + 40.0)

            # Exit Door Check
            dist_to_exit = math.hypot(camera.position.x - exit_x, camera.position.z - exit_z)
            if dist_to_exit < EXIT_RADIUS:
                if has_key:
                    game_won = True
                else:
                    show_locked_msg_timer = 1.5

            # --- Smooth Monster AI ---
            # Stalker AI
            if s_dist > 0:
                stalker_x += (s_dir_x / s_dist) * STALKER_SPEED * dt
                stalker_z += (s_dir_z / s_dist) * STALKER_SPEED * dt
                stalker_x, stalker_z = resolve_collision(stalker_x, stalker_z, STALKER_R)

            # Dasher AI
            dasher_state_timer += dt
            if not dasher_is_rushing and dasher_state_timer > 4.0:
                dasher_is_rushing = True
                dasher_state_timer = 0.0
            elif dasher_is_rushing and dasher_state_timer > 1.5:
                dasher_is_rushing = False
                dasher_state_timer = 0.0

            current_dasher_speed = DASHER_RUSH_SPEED if dasher_is_rushing else DASHER_NORMAL_SPEED

            if d_dist > 0:
                dasher_x += (d_dir_x / d_dist) * current_dasher_speed * dt
                dasher_z += (d_dir_z / d_dist) * current_dasher_speed * dt
                dasher_x, dasher_z = resolve_collision(dasher_x, dasher_z, DASHER_R)

            # Catch conditions
            if s_dist < PLAYER_R + STALKER_R:
                game_over = True
                death_cause = "THE SHADOW STALKER CAUGHT YOU"
            elif d_dist < PLAYER_R + DASHER_R:
                game_over = True
                death_cause = "THE DASHER TORE YOU APART"

        else: 
            # Hiding in Locker
            update_camera(camera, CAMERA_FIRST_PERSON)
            camera.position.x = near_locker[0] 
            camera.position.z = near_locker[1]

    # Camera math for Threat Arrows
    cam_fwd_x = camera.target.x - camera.position.x
    cam_fwd_z = camera.target.z - camera.position.z
    cam_len = math.hypot(cam_fwd_x, cam_fwd_z)
    if cam_len > 0:
        cam_fwd_x /= cam_len
        cam_fwd_z /= cam_len
    cam_right_x = -cam_fwd_z
    cam_right_z = cam_fwd_x
            
    # --- RENDER 3D WORLD ---
    begin_drawing()
    clear_background(BLACK)
    
    begin_mode_3d(camera)
    
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

    # Render Floating Key
    if not has_key and math.hypot(camera.position.x - key_x, camera.position.z - key_z) < current_vision:
        hover = 1.0 + math.sin(elapsed * 4.0) * 0.2
        draw_cube(Vector3(key_x, hover, key_z), 0.4, 0.4, 0.8, GOLD)
        draw_sphere(Vector3(key_x, hover, key_z + 0.4), 0.3, YELLOW)

    # Render Batteries
    for bx, bz in batteries:
        if math.hypot(camera.position.x - bx, camera.position.z - bz) < current_vision:
            draw_cylinder(Vector3(bx, 0.2, bz), 0.2, 0.2, 0.6, 8, LIME)
            draw_cylinder_wires(Vector3(bx, 0.2, bz), 0.2, 0.2, 0.6, 8, GREEN)
      
    # Monsters
    if s_dist < current_vision:
        s_glitch = (15.0 - s_dist) * 0.05 if s_dist < 15.0 else 0.0
        gx = random.uniform(-s_glitch, s_glitch)
        gz = random.uniform(-s_glitch, s_glitch)
        draw_cylinder(Vector3(stalker_x + gx, 0.0, stalker_z + gz), STALKER_R, STALKER_R, 3.5, 8, BLACK)
        draw_sphere(Vector3(stalker_x + gx, 3.5, stalker_z + gz), 0.5, BLACK)

    if d_dist < current_vision:
        d_color = RED if dasher_is_rushing else MAROON
        d_height = 2.2 + (math.sin(elapsed * 18.0) * 0.4 if dasher_is_rushing else 0.0)
        draw_cylinder(Vector3(dasher_x, 0.0, dasher_z), DASHER_R, 0.1, d_height, 6, d_color)
        draw_sphere(Vector3(dasher_x, d_height + 0.3, dasher_z), 0.3, ORANGE if dasher_is_rushing else RED)
        
    # Exit Portal
    exit_color = GREEN if has_key else MAROON
    wire_color = LIME if has_key else RED
    draw_cube(Vector3(exit_x, 2.0, exit_z), 2.0, 4.0, 2.0, exit_color)
    draw_cube_wires(Vector3(exit_x, 2.0, exit_z), 2.0, 4.0, 2.0, wire_color)
    
    end_mode_3d()

    # --- RENDER 2D SCREEN OVERLAYS ---
    if not is_hiding and dasher_is_rushing and d_dist < 20.0 and not game_over and not game_won:
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
        if is_key_down(KEY_LEFT_CONTROL):
            draw_text("CROUCHING", 700, 520, 18, GRAY)

    if near_locker is not None and not is_hiding:
        draw_text("[E] HIDE IN LOCKER", 610, 560, 26, YELLOW)

    if show_locked_msg_timer > 0.0:
        show_locked_msg_timer -= dt
        draw_text("DOOR LOCKED - FIND THE KEY!", 480, 400, 32, RED)

    # UI: Stamina Bar
    draw_rectangle(20, 950, int(stamina * 3), 20, Color(200, 200, 200, 180))
    draw_rectangle_lines(20, 950, 300, 20, DARKGRAY)
    draw_text("STAMINA", 20, 925, 20, LIGHTGRAY)

    # UI: Battery Bar
    bat_color = LIME if battery_power > 30 else RED
    draw_rectangle(20, 880, int(battery_power * 3), 20, bat_color)
    draw_rectangle_lines(20, 880, 300, 20, DARKGRAY)
    draw_text("FLASHLIGHT BATTERY", 20, 855, 20, LIGHTGRAY)

    # UI: Key Objective
    if has_key:
        draw_text("OBJECTIVE: ESCAPE (KEY COLLECTED)", 30, 30, 24, GOLD)
    else:
        draw_text("OBJECTIVE: FIND THE KEY", 30, 30, 24, WHITE)

    if not is_hiding:
        def draw_threat_arrow(mx, mz, dist, base_r, base_g, base_b):
            if dist < 12.0 and not game_over and not game_won:
                to_m_x = (mx - camera.position.x) / dist
                to_m_z = (mz - camera.position.z) / dist
                fwd_dot = to_m_x * cam_fwd_x + to_m_z * cam_fwd_z
                right_dot = to_m_x * cam_right_x + to_m_z * cam_right_z
                pulse = int((1.0 - (dist / 12.0)) * 220)
                c = Color(base_r, base_g, base_b, pulse)
                
                if fwd_dot < 0.2:
                    if right_dot > 0.4:
                        draw_triangle(Vector2(1480, 500), Vector2(1440, 470), Vector2(1440, 530), c)
                    elif right_dot < -0.4:
                        draw_triangle(Vector2(20, 500), Vector2(60, 530), Vector2(60, 470), c)
                    else:
                        draw_triangle(Vector2(750, 980), Vector2(720, 940), Vector2(780, 940), c)

        draw_threat_arrow(stalker_x, stalker_z, s_dist, 100, 100, 100)
        draw_threat_arrow(dasher_x, dasher_z, d_dist, 230, 40, 40)

    if game_won:
        draw_rectangle(0, 0, 1500, 1000, Color(0, 0, 0, 220))
        draw_text("YOU ESCAPED THE BACKROOMS", 390, 450, 46, GOLD)
        
    elif game_over:
        draw_rectangle(0, 0, 1500, 1000, Color(0, 0, 0, 245))
        draw_text(death_cause, 360, 450, 44, RED)

    end_drawing()

# --- Cleanup ---
unload_sound(step_sound)
close_audio_device()
close_window()