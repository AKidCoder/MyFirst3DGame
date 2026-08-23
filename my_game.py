import math
import random
from pyray import *


EYE_HEIGHT = 2.0 #Your Height
MAP_SIZE  = 14 #stadiums's half radious
BOX_SIZE  = 2.0#length of the side
BOX_COUNT = 12  #how many boxes

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

camera = Camera3D(
    Vector3(0, EYE_HEIGHT, 0), #where are you
    Vector3(0, EYE_HEIGHT, -1), #where are you looking
    Vector3(0, 1, 0), #
    60.0, #FOV(how far can you see)
    CAMERA_PERSPECTIVE
)
#The main code is the heart of the whole thing
while not window_should_close():
    update_camera(camera, CAMERA_FIRST_PERSON)
    begin_drawing()
    clear_background(SKYBLUE)
    begin_mode_3d(camera)
    draw_cube(Vector3(0, -5, 0), MAP_SIZE*2+10, 10, MAP_SIZE*2+10, DARKGREEN)
    draw_cube(Vector3(0, -51, 0), MAP_SIZE*2+10, 82, MAP_SIZE*2+10, BROWN)
    draw_grid(MAP_SIZE*2 +10, 1)
    for bx, bz in boxes:
        draw_cube(Vector3(bx, BOX_SIZE/2, bz),
                  BOX_SIZE, BOX_SIZE, BOX_SIZE, GRAY)
        
        
    end_mode_3d()

    draw_text("+", 444, 290, 20, WHITE)

    end_drawing()

close_window()