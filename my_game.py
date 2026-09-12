import math
from pyray import *

EYE_HEIGHT = 2.0
BOX_SIZE = 4.0
PLAYER_R = 0.4
EXIT_RADIUS = 1.2

# --- New Horror Settings ---
MONSTER_SPEED = 2.5
MONSTER_R = 0.6
FLASHLIGHT_RANGE = 16.0 

init_window(1500, 1000, "3D Maze - Horror")
set_target_fps(60)
disable_cursor()

# '1' = Wall, '0' = Path, 'P' = Player Start, 'E' = Exit Goal, 'M' = Monster Start
LEVEL_MAP = [
    "1111111111111111111",
    "10110010000010010E1",   
    "101110101110101M011",
    "1010000100001111001",   # <--- 'M' is where the monster wakes up
    "1010111110101000101",
    "110000P000100010001",   
    "1111111111111111111"
]

boxes = []
rows = len(LEVEL_MAP)
cols = len(LEVEL_MAP[0])

spawn_x, spawn_z = 0.0, 0.0
exit_x, exit_z = 0.0, 0.0
monster_x, monster_z = 0.0, 0.0

game_won = False
game_over = False
elapsed = 0.0

# Scan the blueprint
for row in range(rows):
    for col in range(cols):
        tile = LEVEL_MAP[row][col]
        wx = (col - cols / 2.0 + 0.5) * BOX_SIZE
        wz = (row - rows / 2.0 + 0.5) * BOX_SIZE
        
        if tile == "1":
            boxes.append((wx, wz))
        elif tile == "P":
            spawn_x, spawn_z = wx, wz
        elif tile == "E":
            exit_x, exit_z = wx, wz
        elif tile == "M":
            monster_x, monster_z = wx, wz

camera = Camera3D(
    Vector3(spawn_x, EYE_HEIGHT, spawn_z),
    Vector3(spawn_x, EYE_HEIGHT, spawn_z - 1.0),
    Vector3(0, 1, 0),
    60.0,
    CAMERA_PERSPECTIVE
)

def hits_box(px, pz):
    half = BOX_SIZE / 2.0 + PLAYER_R
    for bx, bz in boxes:
        if abs(px - bx) < half and abs(pz - bz) < half:
            return True
    return False

while not window_should_close():
    dt = get_frame_time()
    elapsed += dt
    
    old_x = camera.position.x 
    old_z = camera.position.z

    # Only move and update logic if you haven't won or died
    if not game_won and not game_over:
        update_camera(camera, CAMERA_FIRST_PERSON)
        px, pz = camera.position.x, camera.position.z

        # Player Wall Collision
        if hits_box(px, pz):
            dx = old_x - camera.position.x
            dz = old_z - camera.position.z
            camera.position.x += dx
            camera.position.z += dz
            camera.target.x += dx        
            camera.target.z += dz
            
        # --- Monster Hunting Logic ---
        # The monster always knows where you are and floats toward you
        dir_x = camera.position.x - monster_x
        dir_z = camera.position.z - monster_z
        dist_to_player = math.hypot(dir_x, dir_z)
        
        if dist_to_player > 0:
            monster_x += (dir_x / dist_to_player) * MONSTER_SPEED * dt
            monster_z += (dir_z / dist_to_player) * MONSTER_SPEED * dt

        # Check if monster caught you
        if dist_to_player < PLAYER_R + MONSTER_R:
            game_over = True

        # Check if you reached the exit
        dist_to_exit = math.hypot(camera.position.x - exit_x, camera.position.z - exit_z)
        if dist_to_exit < EXIT_RADIUS:
            game_won = True
      
    begin_drawing()
    clear_background(BLACK) # Total darkness
    
    begin_mode_3d(camera)
    
    # Draw floor (Made darker for horror atmosphere)
    floor_w = cols * BOX_SIZE + 4
    floor_l = rows * BOX_SIZE + 4
    draw_cube(Vector3(0, -5, 0), floor_w, 10, floor_l, Color(20, 20, 20, 255))
    
    # --- Flashlight Effect ---
    # Only draw walls that are close to the player
    for bx, bz in boxes:
        dist_to_wall = math.hypot(camera.position.x - bx, camera.position.z - bz)
        if dist_to_wall < FLASHLIGHT_RANGE:
            draw_cube(Vector3(bx, BOX_SIZE / 2.0, bz), BOX_SIZE, BOX_SIZE, BOX_SIZE, BROWN)
            draw_cube_wires(Vector3(bx, BOX_SIZE / 2.0, bz), BOX_SIZE, BOX_SIZE, BOX_SIZE, BLACK)
      
    # Draw Monster (Only if it's inside your flashlight range)
    if math.hypot(camera.position.x - monster_x, camera.position.z - monster_z) < FLASHLIGHT_RANGE:
        float_anim = math.sin(elapsed * 4.0) * 0.3
        # Dark, tall shadowy body
        draw_cylinder(Vector3(monster_x, 0.0, monster_z), MONSTER_R, MONSTER_R, 3.0, 10, Color(15, 0, 0, 255))
        # Floating head
        draw_sphere(Vector3(monster_x, 3.2 + float_anim, monster_z), 0.5, BLACK)
        # Red glowing eyes pointing at the player
        if m_dist > 0.1: # prevent math crash
            look_x = (camera.position.x - monster_x) / m_dist * 0.4
            look_z = (camera.position.z - monster_z) / m_dist * 0.4
            draw_sphere(Vector3(monster_x + look_x, 3.2 + float_anim, monster_z + look_z), 0.15, RED)
        
    # Draw Exit Goal
    pulse = 1.0 + math.sin(elapsed * 4.0) * 0.2
    draw_cylinder(Vector3(exit_x, 0.0, exit_z), 0.6, 0.6, 2.5, 16, MAROON)
    draw_sphere(Vector3(exit_x, 2.5 + pulse * 0.3, exit_z), 0.35, RED)
    
    end_mode_3d()

    # Crosshair
    draw_text("+", 444, 290, 20, DARKGRAY)

    # UI Screens
    if game_won:
        draw_rectangle(0, 0, 1200, 1000, Color(0, 0, 0, 220))
        draw_text("YOU ESCAPED", 280, 250, 50, GRAY)
        
    elif game_over:
        draw_rectangle(0, 0, 1200, 1000, Color(150, 0, 0, 220)) # Blood red screen
        draw_text("YOU DIED", 320, 250, 60, BLACK)

    end_drawing()

close_window()