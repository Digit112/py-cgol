from PyQt5.QtWidgets import QMainWindow, QApplication

from CGOL import *
from CGOL_Gui import *

# PyQt will call this as quickly as it can while the app is running.
def mainloop():
	global window
	global cgol
	global cam
	
	# Check if we should recreate the canvas
	if window.last_resize is not None and time.time() - window.last_resize > 0.05:
		window.last_resize = None
		window.create_canvas()
	
	# Check if a new frame is ready to be displayed.
	if cgol.frame_ready:
		cgol.inc_current()
		
		# Increment the viewed frame and queue a render.
		cgol.frame_ready = False
		window.render_queued = True
	
	# Always render while placing.
	if cgol.is_placing:
		window.render_queued = True
	
	# In between renders, check if a resize is queued
	if (window.resize_queued is not None or cgol.resize_queued is not None) and not window.render_thread.is_alive() and not window.simulation_thread.is_alive():
		resize = None
		if window.resize_queued is not None:
			resize = window.resize_queued
		else:
			resize = cgol.resize_queued
		
		# Adjust the camera's position
		window.proxy_cam.x += resize[0]
		window.proxy_cam.y += resize[1]
		
		cgol.resize(*resize)
		
		window.resize_queued = None
		cgol.resize_queued = None
	
	# While not simulating a frame, check if a place is queued.
	if cgol.place_queued is not None and not window.simulation_thread.is_alive():
		cgol.place(*cgol.place_queued)
		cgol.place_queued = None
	
	# If a new frame isn't ready, check if the application is requesting a render.
	# If changes have been made and enough time has passed since the previous render AND we are not already rendering, launch another render thread.
	if (window.render_queued or cgol.render_queued) and time.time() - window.last_render_time > window.render_delay and not window.render_thread.is_alive():
		# Copy the proxy cam into the real cam
		window.cam.x = window.proxy_cam.x
		window.cam.y = window.proxy_cam.y
		window.cam.s = round(window.proxy_cam.s) # The proxy camera must be able to have non-integer scales, but the real camera must not.
		
		# Start the render thread
		window.render_thread = threading.Thread(target=CGOL_grid.render, args=(cgol, window, cam, window.label))
		window.render_thread.start()
		
		window.render_queued = False
		cgol.render_queued = False
		window.last_render_time = time.time()
	
	# Check if we should start generating a new frame.
	if window.is_playing and time.time() - window.last_frame_time > window.frame_delay:
		cgol.step_queued = True
	
	# launch a thread to render the next frame.
	if cgol.step_queued and not window.simulation_thread.is_alive():
		window.simulation_thread = threading.Thread(target=CGOL_grid.step, args=(cgol, window, window.is_periodic))
		window.simulation_thread.start()
		
		window.last_frame_time = time.time()
		cgol.step_queued = False
		
cgol = CGOL_grid(40, 20, 2)

cam = camera(20, 10, 10)

cgol.randomize()

app = QApplication(sys.argv)

window = CGOL_Window(cgol, cam)
window.show()

cgol_loop = QTimer()
cgol_loop.timeout.connect(mainloop)
cgol_loop.start()

app.exec()

print("Goodbye!")