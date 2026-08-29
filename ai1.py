import math
import random
from pyray import *

EYE_HEIGHT = 2.0 # Your Height
MAP_SIZE  = 14   # stadium's half radius
BOX_SIZE  = 2.0  # length of the side
BOX_COUNT = 12   # how many boxes
TOTAL_COINS = 10 # how many coins should I eat and generate
PICK_RANGE = 1.5 # The range that the system will let me eat the coins

init_window(900, 600, "First_3D")
set_target_fps(60)
disable_cursor()

# --- 1. AUDIO SETUP ---
# init_audio_device()
# coin_sound = load_sound("coin.wav") # Create or download a coin.wav and uncomment this!

# --- SAFE SPAWN BOUNDARIES ---
SPAWN_BOUND = MAP_SIZE - 2.0 

# The box generator
boxes = []
while len(boxes) < BOX_COUNT:
    x = random.uniform(-SPAWN_BOUND, SPAWN_BOUND)
    z = random.uniform(-SPAWN_BOUND, SPAWN_BOUND)
    if math.hypot(x, z) > 4: # Don't block the player's spawn at (0,0)
        boxes.append((x, z))

# The coin generator
coins = []
while len(coins) < TOTAL_COINS:
    x = random.uniform(-SPAWN_BOUND, SPAWN_BOUND)
    z = random.uniform(-SPAWN_BOUND, SPAWN_BOUND)
    
    # 1. Don't spawn too close to the player
    if math.hypot(x, z) < 3:
        continue
        
    # 2. Don't spawn inside or too close to a box
    inside_box = False
    for bx, bz in boxes:
        if math.hypot(x - bx, z - bz) < 2.0:
            inside_box = True
            break
            
    # Only add the coin if it didn't hit any boxes
    if not inside_box:
        coins.append((x, z))

score = 0
elapsed = 0.0 

# --- 2. WIN STATE VARIABLES ---
game_won = False
win_time = 0.0

camera = Camera3D(
    Vector3(0, EYE_HEIGHT, 0), # where are you
    Vector3(0, EYE_HEIGHT, -1), # where are you looking
    Vector3(0, 1, 0), 
    60.0, # FOV (how far can you see)
    CAMERA_PERSPECTIVE
)

# --- SPRINT VARIABLES ---
last_w_press_time = 0.0
is_sprinting = False
DOUBLE_TAP_WINDOW = 0.3 # 300ms to double tap
NORMAL_FOV = 60.0
SPRINT_FOV = 75.0
SPRINT_SPEED = 4.0 # Extra speed boost

# --- ENDER PEARL VARIABLES ---
pearl_active = False
pearl_pos = Vector3(0, 0, 0)
pearl_vel = Vector3(0, 0, 0)
is_aiming = False

while not window_should_close():
    dt = get_frame_time()
    
    # Only increase time if the game hasn't been won
    if not game_won:
        elapsed += dt
        
    for coin in list(coins): 
        cx, cz = coin
        dist = math.hypot(camera.position.x - cx, camera.position.z - cz)
        if dist < PICK_RANGE:
            coins.remove(coin)
            score += 1
            # play_sound(coin_sound) # Uncomment when you have a sound file!
            
    # Check for win condition
    if score >= TOTAL_COINS and not game_won:
        game_won = True
        win_time = elapsed

    # --- SPRINT LOGIC ---
    if is_key_pressed(KEY_W):
        if elapsed - last_w_press_time < DOUBLE_TAP_WINDOW:
            is_sprinting = True
        last_w_press_time = elapsed
        
    if is_key_released(KEY_W):
        is_sprinting = False

    # Apply FOV changes and speed boost
    if is_sprinting and not game_won:
        camera.fovy += (SPRINT_FOV - camera.fovy) * 10.0 * dt
        dx = camera.target.x - camera.position.x
        dz = camera.target.z - camera.position.z
        length = math.hypot(dx, dz)
        
        if length != 0:
            dx /= length
            dz /= length
            move_x = dx * SPRINT_SPEED * dt
            move_z = dz * SPRINT_SPEED * dt
            camera.position.x += move_x
            camera.position.z += move_z
            camera.target.x += move_x
            camera.target.z += move_z
    else:
        camera.fovy += (NORMAL_FOV - camera.fovy) * 10.0 * dt

    # --- ENDER PEARL LOGIC ---
    is_aiming = False
    
    # 1. Aiming (Holding Right Click)
    if is_mouse_button_down(MOUSE_BUTTON_RIGHT) and not pearl_active and not game_won:
        is_aiming = True
        
    # 2. Throwing (Releasing Right Click)
    if is_mouse_button_released(MOUSE_BUTTON_RIGHT) and not pearl_active and not game_won:
        pearl_active = True
        pearl_pos = Vector3(camera.position.x, camera.position.y, camera.position.z)
        
        dx = camera.target.x - camera.position.x
        dy = camera.target.y - camera.position.y
        dz = camera.target.z - camera.position.z
        length = math.sqrt(dx*dx + dy*dy + dz*dz)
        
        THROW_SPEED = 30.0
        pearl_vel = Vector3((dx/length)*THROW_SPEED, (dy/length)*THROW_SPEED + 5.0, (dz/length)*THROW_SPEED)

    # Moving the pearl and checking collisions
    if pearl_active:
        pearl_vel.y -= 25.0 * dt
        pearl_pos.x += pearl_vel.x * dt
        pearl_pos.y += pearl_vel.y * dt
        pearl_pos.z += pearl_vel.z * dt
        
        hit = False
        
        if pearl_pos.y <= 0:
            hit = True
            
        max_bound = MAP_SIZE - 0.5
        if abs(pearl_pos.x) > max_bound or abs(pearl_pos.z) > max_bound:
            hit = True
            
        for bx, bz in boxes:
            if abs(pearl_pos.x - bx) < BOX_SIZE/2.0 and abs(pearl_pos.z - bz) < BOX_SIZE/2.0:
                if pearl_pos.y < BOX_SIZE:
                    hit = True
                    break
                    
        if hit:
            move_x = pearl_pos.x - camera.position.x
            move_z = pearl_pos.z - camera.position.z
            
            final_x = max(-max_bound, min(max_bound, pearl_pos.x))
            final_z = max(-max_bound, min(max_bound, pearl_pos.z))
            
            camera.position.x = final_x
            camera.position.y = EYE_HEIGHT 
            camera.position.z = final_z
            
            camera.target.x += (final_x - (pearl_pos.x - move_x))
            camera.target.z += (final_z - (pearl_pos.z - move_z))
            
            pearl_active = False
            
    update_camera(camera, CAMERA_FIRST_PERSON)
    
    # --- 3. COLLISION DETECTION ---
    max_bound = MAP_SIZE - 0.5
    camera.position.x = max(-max_bound, min(max_bound, camera.position.x))
    camera.position.z = max(-max_bound, min(max_bound, camera.position.z))

    player_radius = 0.4
    half_box = BOX_SIZE / 2.0
    for bx, bz in boxes:
        if abs(camera.position.x - bx) < (half_box + player_radius) and \
           abs(camera.position.z - bz) < (half_box + player_radius):
            dx = camera.position.x - bx
            dz = camera.position.z - bz
            if abs(dx) > abs(dz):
                camera.position.x = bx + math.copysign(half_box + player_radius, dx)
            else:
                camera.position.z = bz + math.copysign(half_box + player_radius, dz)

    begin_drawing()
    clear_background(SKYBLUE)
    begin_mode_3d(camera)
    
    draw_cube(Vector3(0, -5, 0), MAP_SIZE*2+10, 10, MAP_SIZE*2+10, DARKGREEN)
    draw_cube(Vector3(0, -51, 0), MAP_SIZE*2+10, 82, MAP_SIZE*2+10, BROWN)
    draw_grid(MAP_SIZE*2, 1) 
    
    wall_length = MAP_SIZE * 2
    draw_cube(Vector3(0, 2, MAP_SIZE), wall_length, 4, 1, DARKBLUE) 
    draw_cube(Vector3(0, 2, -MAP_SIZE), wall_length, 4, 1, DARKBLUE) 
    draw_cube(Vector3(MAP_SIZE, 2, 0), 1, 4, wall_length, DARKBLUE) 
    draw_cube(Vector3(-MAP_SIZE, 2, 0), 1, 4, wall_length, DARKBLUE) 
    
    for bx, bz in boxes:
        draw_cube(Vector3(bx, BOX_SIZE/2, bz), BOX_SIZE, BOX_SIZE, BOX_SIZE, GRAY)
        draw_cube_wires(Vector3(bx, BOX_SIZE/2, bz), BOX_SIZE, BOX_SIZE, BOX_SIZE, BLACK)
        
    for cx, cz in coins:
        bob =  1.0 + math.sin(elapsed * 3 + cx) * 0.2
        draw_sphere(Vector3(cx, bob, cz), 0.4 , GOLD)
    
    # --- DRAW ENDER PEARL IN 3D ---
    if pearl_active:
        draw_sphere(pearl_pos, 0.2, DARKPURPLE)

    if is_aiming:
        dx = camera.target.x - camera.position.x
        dy = camera.target.y - camera.position.y
        dz = camera.target.z - camera.position.z
        length = math.sqrt(dx*dx + dy*dy + dz*dz)
        
        THROW_SPEED = 30.0
        sim_vel_x = (dx/length)*THROW_SPEED
        sim_vel_y = (dy/length)*THROW_SPEED + 5.0
        sim_vel_z = (dz/length)*THROW_SPEED
        
        sim_pos_x = camera.position.x
        sim_pos_y = camera.position.y
        sim_pos_z = camera.position.z
        sim_dt = 0.05 
        
        for i in range(50):
            prev_x = sim_pos_x
            prev_y = sim_pos_y
            prev_z = sim_pos_z
            
            sim_vel_y -= 25.0 * sim_dt 
            sim_pos_x += sim_vel_x * sim_dt
            sim_pos_y += sim_vel_y * sim_dt
            sim_pos_z += sim_vel_z * sim_dt
            
            draw_line_3d(Vector3(prev_x, prev_y, prev_z), Vector3(sim_pos_x, sim_pos_y, sim_pos_z), MAGENTA)
            draw_sphere(Vector3(sim_pos_x, sim_pos_y, sim_pos_z), 0.15, MAGENTA)
            
            # FIXED INDENTATION: This is now correctly inside the loop!
            if sim_pos_y <= 0:
                landing_pos = Vector3(sim_pos_x, 0.2, sim_pos_z) 
                draw_sphere(landing_pos, 0.2, DARKPURPLE)
                break

    end_mode_3d()

    # UI Layer
    if not is_aiming:
        draw_text("+", 444, 290, 20, WHITE)
        
    draw_text(f"Coins: {score} / {TOTAL_COINS}", 20, 20 , 28, BLACK)
    
    if game_won:
        draw_text("YOU WIN!", 320, 240, 50, GOLD)
        draw_text(f"Time: {win_time:.2f}s", 370, 310, 24, WHITE)
    else:
        draw_text(f"Time: {elapsed:.1f}s", 720, 20, 24, BLACK)

    # --- BACKPACK / HOTBAR UI ---
    slot_size = 50
    slot_x = 450 - (slot_size / 2) 
    slot_y = 530 
    
    draw_rectangle(int(slot_x), int(slot_y), slot_size, slot_size, Color(30, 30, 30, 200))
    draw_rectangle_lines(int(slot_x), int(slot_y), slot_size, slot_size, LIGHTGRAY)
    draw_circle(int(slot_x + 25), int(slot_y + 25), 14, DARKPURPLE)
    draw_circle_lines(int(slot_x + 25), int(slot_y + 25), 14, PURPLE)
    draw_text("inf", int(slot_x + 24), int(slot_y + 32), 16, WHITE)
    draw_text("Right Click", int(slot_x - 12), int(slot_y - 20), 16, BLACK)
    
    end_drawing()
    
close_window()