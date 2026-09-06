import math
import random
from pyray import *
from time import *

EYE_HEIGHT = 2.0 #Your Height
MAP_SIZE  = 14 #stadiums's half radious
BOX_SIZE  = 2.0#length of the side
BOX_COUNT = 9  #how many boxes
TOTAL_COINS = 10 #how many coins should I eat and generate
PICK_RANGE = 1.5#The range that the system will let me eat the coins
PLAYER_R = 0.4
init_window(900, 600, "First_3D")
set_target_fps(60)
disable_cursor()

#The box generater's code
boxes = []
while len(boxes) < BOX_COUNT:
    x = random.uniform(-MAP_SIZE, MAP_SIZE)
    z = random.uniform(-MAP_SIZE, MAP_SIZE)
    if math.hypot(x, z) > 4: #don't block the spawn
        boxes.append((x, z))

coins = []
while len(coins) < TOTAL_COINS:
    x = random.uniform(-MAP_SIZE, MAP_SIZE)
    z = random.uniform(-MAP_SIZE, MAP_SIZE)
    if math.hypot(x, z) > 3:
        coins.append((x, z))  

score = 0
elapsed = 0.0 

camera = Camera3D(
    Vector3(0, EYE_HEIGHT, 0), #where are you
    Vector3(0, EYE_HEIGHT, -1), #where are you looking
    Vector3(0, 1, 0), #
    60.0, #FOV(how far can you see)
    CAMERA_PERSPECTIVE
)

#This is where I wrote the hitbox

def hits_box(px, pz):
    half = BOX_SIZE/2 + PLAYER_R
    for bx, bz in boxes:
        if abs(px - bx) < half and abs(pz - bz) < half:
            return True
    return False
#The main code is the heart of the whole thing
while not window_should_close():
    old_x = camera.position.x #remember the old position of x and z
    old_z = camera.position.z
    dt = get_frame_time()
    elapsed += dt
    for coin in list(coins) : #don't forget the list(), very important
        cx, cz = coin
        dist = math.hypot(camera.position.x - cx,
                        camera.position.z - cz)
        if dist < PICK_RANGE:
            coins.remove(coin)
            score += 1
        
    update_camera(camera, CAMERA_FIRST_PERSON)
    px, pz = camera.position.x, camera.position.z
    begin_drawing()
    clear_background(SKYBLUE)
    begin_mode_3d(camera)
    draw_cube(Vector3(0, -5, 0), MAP_SIZE*2+10, 10, MAP_SIZE*2+10, DARKGREEN)
    draw_cube(Vector3(0, -51, 0), MAP_SIZE*2+10, 82, MAP_SIZE*2+10, BROWN)
    draw_grid(MAP_SIZE*2 +10, 1)
    for bx, bz in boxes:
        draw_cube(Vector3(bx, BOX_SIZE/2, bz),
            BOX_SIZE, BOX_SIZE, BOX_SIZE, GRAY)
    for cx, cz in coins:
        bob =  1.0 + math.sin(elapsed * 3 + cx) * 0.2
        draw_sphere(Vector3(cx, bob, cz), 0.4 , GOLD)
    if hits_box(px, pz) or abs(px) > MAP_SIZE + 2 or abs(pz) > MAP_SIZE + 2:
        dx = old_x - camera.position.x
        dz = old_z - camera.position.z
        camera.position.x += dx
        camera.position.z += dz
        camera.target.x += dx        
        camera.target.z += dz
      
    end_mode_3d()

    draw_text("+", 444, 290, 20, WHITE)
    draw_text(f"Coins: {score} / {TOTAL_COINS}", 20, 20 , 28, BLACK)
    if score == TOTAL_COINS:
        draw_text("YOU WIN", 340, 260, 50, MAROON)
    draw_fps(20, 60)
    end_drawing()

close_window()