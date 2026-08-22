from pyray import *
init_window(900, 600, "First_3D")
set_target_fps(60)

camera = Camera3D(
    Vector3(8, 6, 8), #where are you
    Vector3(0, 1, 0), #where are you looking
    Vector3(0, 1, 0), #
    60.0, #FOV(how far can you see)
    CAMERA_PERSPECTIVE
)
#The main code is the heart of the whole thing
while not window_should_close():
    begin_drawing()
    clear_background(SKYBLUE)
    begin_mode_3d(camera)
    draw_plane(Vector3(0, 1, 0), Vector2(20, 20), DARKGREEN)
    draw_grid(20, 1)
    draw_cube(Vector3(0,1,0), 2,2,2, GRAY)
    end_mode_3d()
    
    draw_text("Yo!!!", 20, 20, 28, BLACK)
    end_drawing()

close_window()