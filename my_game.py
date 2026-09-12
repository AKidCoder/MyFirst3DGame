import math
import random
from pyray import *

EYE_HEIGHT = 2.0
BOX_SIZE = 4.0
PLAYER_R = 0.4
EXIT_RADIUS = 1.2

# --- Monster Stats ---
STALKER_SPEED = 2.4
STALKER_R = 0.6

DASHER_NORMAL_SPEED = 1.2
DASHER_RUSH_SPEED = 5.2
DASHER_R = 0.5

FLASHLIGHT_RANGE = 14.0 

# --- Updated Colors ---
WALL_COLOR = BROWN   
LINE_COLOR = BLACK    
FLOOR_COLOR = DARKBROWN   
CEIL_COLOR = Color(20, 15, 10, 255) # Dark ceiling fits the brown aesthetic   

init_window(1500, 1000, "3D Maze - The Backrooms")
init_audio_device()
set_target_fps(60)
disable_cursor()

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

LEVEL_MAP = [
    "1111111111111111111",
    "10110010000010010E1",   
    "101110101110101S011",
    "1010000100001111001", 
    "1010111110101000D01",
    "110000P000100010001",   
    "1111111111111111111"
]

boxes = []
grid_tiles = []
rows = len(LEVEL_MAP)
cols = len(LEVEL_MAP[0])

spawn_x, spawn_z = 0.0, 0.0
exit_x, exit_z = 0.0, 0.0
stalker_x, stalker_z = 0.0, 0.0
dasher_x, dasher_z = 0.0, 0.0

game_won = False
game_over = False
death_cause = ""
elapsed = 0.0

bob_timer = 0.0
step_timer = 0.0
stamina = 100.0 # New Stamina mechanic

dasher_state_timer = 0.0
dasher_is_rushing = False

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

camera = Camera3D(
    Vector3(spawn_x, EYE_HEIGHT, spawn_z),
    Vector3(spawn_x, EYE_HEIGHT, spawn_z - 1.0),
    Vector3(0, 1, 0),
    60.0,
    CAMERA_PERSPECTIVE
)

def hits_box(px, pz, radius):
    half = BOX_SIZE / 2.0 + radius
    for bx, bz in boxes:
        if abs(px - bx) < half and abs(pz - bz) < half:
            return True
    return False

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
        update_camera(camera, CAMERA_FIRST_PERSON)
        
        # --- Sprint Logic ---
        moved_x = camera.position.x - old_x
        moved_z = camera.position.z - old_z
        moved_dist = math.hypot(moved_x, moved_z)
        is_moving = moved_dist > 0.001

        # Hold SHIFT to sprint if you have stamina
        if is_key_down(KEY_LEFT_SHIFT) and stamina > 0 and is_moving:
            stamina -= 35.0 * dt
            boost = 1.2 # Adds 120% extra speed
            camera.position.x += moved_x * boost
            camera.position.z += moved_z * boost
            camera.target.x += moved_x * boost
            camera.target.z += moved_z * boost
            bob_timer += dt * 8.0 # Bob head faster while running
        else:
            stamina = min(100.0, stamina + 15.0 * dt)

        # Player Wall Collision (Calculated AFTER sprint is applied)
        px, pz = camera.position.x, camera.position.z
        if hits_box(px, pz, PLAYER_R):
            dx = old_x - camera.position.x
            dz = old_z - camera.position.z
            camera.position.x += dx
            camera.position.z += dz
            camera.target.x += dx        
            camera.target.z += dz

        # Head bobbing & footsteps
        if is_moving:
            bob_timer += dt * 10.0
            step_timer += dt
            
            bob_offset = math.sin(bob_timer) * 0.12
            camera.position.y = EYE_HEIGHT + bob_offset
            camera.target.y = EYE_HEIGHT + bob_offset

            if step_timer >= (0.25 if is_key_down(KEY_LEFT_SHIFT) else 0.35):
                play_sound(step_sound)
                step_timer = 0.0
        else:
            camera.position.y += (EYE_HEIGHT - camera.position.y) * 8.0 * dt
            camera.target.y = camera.position.y
            step_timer = 0.3

        # Stalker AI
        if s_dist > 0:
            step_x = (s_dir_x / s_dist) * STALKER_SPEED * dt
            step_z = (s_dir_z / s_dist) * STALKER_SPEED * dt
            
            stalker_x += step_x
            if hits_box(stalker_x, stalker_z, STALKER_R):
                stalker_x -= step_x
                
            stalker_z += step_z
            if hits_box(stalker_x, stalker_z, STALKER_R):
                stalker_z -= step_z

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
            d_step_x = (d_dir_x / d_dist) * current_dasher_speed * dt
            d_step_z = (d_dir_z / d_dist) * current_dasher_speed * dt
            
            dasher_x += d_step_x
            if hits_box(dasher_x, dasher_z, DASHER_R):
                dasher_x -= d_step_x
                
            dasher_z += d_step_z
            if hits_box(dasher_x, dasher_z, DASHER_R):
                dasher_z -= d_step_z

        if s_dist < PLAYER_R + STALKER_R:
            game_over = True
            death_cause = "THE SHADOW STALKER CAUGHT YOU"
        elif d_dist < PLAYER_R + DASHER_R:
            game_over = True
            death_cause = "THE DASHER TORE YOU APART"

        dist_to_exit = math.hypot(camera.position.x - exit_x, camera.position.z - exit_z)
        if dist_to_exit < EXIT_RADIUS:
            game_won = True

    cam_fwd_x = camera.target.x - camera.position.x
    cam_fwd_z = camera.target.z - camera.position.z
    cam_len = math.hypot(cam_fwd_x, cam_fwd_z)
    if cam_len > 0:
        cam_fwd_x /= cam_len
        cam_fwd_z /= cam_len
    cam_right_x = -cam_fwd_z
    cam_right_z = cam_fwd_x
            
    begin_drawing()
    clear_background(BLACK)
    
    begin_mode_3d(camera)
    
    for tx, tz in grid_tiles:
        tile_dist = math.hypot(camera.position.x - tx, camera.position.z - tz)
        if tile_dist < FLASHLIGHT_RANGE:
            draw_cube(Vector3(tx, -0.5, tz), BOX_SIZE, 1.0, BOX_SIZE, FLOOR_COLOR)
            draw_cube(Vector3(tx, 4.5, tz), BOX_SIZE, 1.0, BOX_SIZE, CEIL_COLOR)

    for bx, bz in boxes:
        wall_dist = math.hypot(camera.position.x - bx, camera.position.z - bz)
        if wall_dist < FLASHLIGHT_RANGE:
            draw_cube(Vector3(bx, BOX_SIZE / 2.0, bz), BOX_SIZE, BOX_SIZE, BOX_SIZE, WALL_COLOR)
            draw_cube_wires(Vector3(bx, BOX_SIZE / 2.0, bz), BOX_SIZE, BOX_SIZE, BOX_SIZE, LINE_COLOR)
      
    if s_dist < FLASHLIGHT_RANGE:
        s_glitch = (15.0 - s_dist) * 0.05 if s_dist < 15.0 else 0.0
        gx = random.uniform(-s_glitch, s_glitch)
        gz = random.uniform(-s_glitch, s_glitch)
        draw_cylinder(Vector3(stalker_x + gx, 0.0, stalker_z + gz), STALKER_R, STALKER_R, 3.5, 8, BLACK)
        draw_sphere(Vector3(stalker_x + gx, 3.5, stalker_z + gz), 0.5, BLACK)

    if d_dist < FLASHLIGHT_RANGE:
        d_color = RED if dasher_is_rushing else MAROON
        d_height = 2.2 + (math.sin(elapsed * 18.0) * 0.4 if dasher_is_rushing else 0.0)
        draw_cylinder(Vector3(dasher_x, 0.0, dasher_z), DASHER_R, 0.1, d_height, 6, d_color)
        draw_sphere(Vector3(dasher_x, d_height + 0.3, dasher_z), 0.3, ORANGE if dasher_is_rushing else RED)
        
    draw_cube(Vector3(exit_x, 2.0, exit_z), 2.0, 4.0, 2.0, MAROON)
    draw_cube_wires(Vector3(exit_x, 2.0, exit_z), 2.0, 4.0, 2.0, RED)
    
    end_mode_3d()

    # --- Dasher Blood Effect Screen Overlay ---
    # Fades in intensely when the Dasher is rushing toward you and is close
    if dasher_is_rushing and d_dist < 20.0 and not game_over and not game_won:
        blood_pulse = (math.sin(elapsed * 20.0) + 1.0) / 2.0
        blood_alpha = int((1.0 - (d_dist / 20.0)) * 120 * blood_pulse + 40)
        draw_rectangle(0, 0, 1500, 1000, Color(200, 0, 0, blood_alpha))

    draw_text("+", 744, 490, 20, DARKGRAY) 

    # --- UI: Stamina Bar ---
    draw_rectangle(20, 950, int(stamina * 3), 20, Color(200, 200, 200, 180))
    draw_rectangle_lines(20, 950, 300, 20, DARKGRAY)
    draw_text("STAMINA", 20, 925, 20, LIGHTGRAY)

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
        draw_text("YOU ESCAPED THE BACKROOMS", 390, 450, 46, GRAY)
        
    elif game_over:
        draw_rectangle(0, 0, 1500, 1000, Color(0, 0, 0, 245))
        draw_text(death_cause, 360, 450, 44, RED)

    end_drawing()

unload_sound(step_sound)
close_audio_device()
close_window()