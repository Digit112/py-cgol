from PyQt5 import QtGui
from PyQt5.QtCore import QSize, Qt, QUrl, QTimer, QPoint
from PyQt5.QtWidgets import QApplication, QWidget, QMainWindow, QPushButton, QVBoxLayout, QHBoxLayout, QMenu, QMenuBar, QLabel, QAction, QFileDialog, QDialog, QLineEdit

import threading
import math
import os
import random
import sys
import time

# Defines a label widget with overloaded event handlers
class click_labal(QLabel):
	def __init__(self, parent):
		super().__init__(parent)
		
		# Timer for detecting mouse clicks.
		self.click_timer = time.time()
		
		# Used to control whether, while dragging, you're turning pixels on or off.
		self.lock = None
		
		# The previous mouse position, used for panning.
		self.last_x = None
		self.last_y = None
	
	# Gets the tile at the position passed in local coordinates
	def get_tile(self, x, y):
		parent = self.parentWidget()
		
		rect = self.rect()
		w2 = rect.width() / 2 / parent.cam.s
		h2 = rect.height() / 2 / parent.cam.s
		
		x = min(max(math.floor(x / parent.cam.s + cam.x - w2), 0), cgol.width-1)
		y = min(max(math.floor(y / parent.cam.s + cam.y - h2), 0), cgol.height-1)
		
		return x, y
	
	# If necessary, safely halts the simulation.
	def halt(self):
		parent = self.parentWidget()
		
		if parent.is_playing == True:
			parent.toggle_play()
		
			# If a thread is currently performing a simulation, wait for it to halt.
			# This thread will halt after it finishes the next column, while checking the is_playing flag.
			if parent.simulation_thread.is_alive():
				parent.is_halting = True
				parent.simulation_thread.join()
	
	def mousePressEvent(self, e):
		e.accept()
		
		# If left button clicked, set the click timer. If a release event occurs within 400ms, toggle this pixel.
		if e.button() == Qt.LeftButton:
			self.click_timer = time.time()
	
	def mouseReleaseEvent(self, e):
		e.accept()
		
		self.last_x = None
		self.last_y = None
		
		# If released after dragging, don't do anything
		if self.lock != None:
			self.lock = None
			return
		
		# If the user has released the left mouse button after holding it down for 
		if e.button() == Qt.LeftButton and time.time() - self.click_timer < 0.4:
			parent = self.parentWidget()
			
			self.halt()
			
			# Get the relevant pixel
			x, y = self.get_tile(e.pos().x(), e.pos().y())
			
			parent.cgol.flip(x, y)
			parent.render_queued = True
		
	# If the user drags the mouse while holding the left mouse button, set all pixels they move over to either one or off.
	def mouseMoveEvent(self, e):
		e.accept()
		
		parent = self.parentWidget()
		
		# If dragging the left mouse, paint
		if e.buttons() == Qt.LeftButton:
			self.halt()
			
			# Get the relevant pixel
			x, y = self.get_tile(e.pos().x(), e.pos().y())
			
			# Set the lock
			if self.lock == None:
				if parent.cgol.get(x, y):
					self.lock = False
				else:
					self.lock = True
			
			if self.lock:
				parent.cgol.set(x, y)
			else:
				parent.cgol.reset(x, y)
		
			parent.render_queued = True
		
		# If dragging the middle mouse, pan
		if e.buttons() == Qt.MiddleButton:
			x = e.pos().x()
			y = e.pos().y()
			
			if self.last_x is not None:
				parent.proxy_cam.x += (self.last_x - x) / parent.cam.s
				parent.proxy_cam.y += (self.last_y - y) / parent.cam.s
				
				parent.render_queued = True
			
			self.last_x = x
			self.last_y = y
	
	def wheelEvent(self, e):
		e.accept()
		
		parent = self.parentWidget()
		
		if e.angleDelta().y() < 0:
			parent.proxy_cam.s *= 0.9
		else:
			parent.proxy_cam.s *= 1 / 0.9
		
		parent.proxy_cam.s = min(max(parent.proxy_cam.s, 5), 30)
		
		parent.render_queued = True

# Defines the dialog used to resize the grid.
class resize_diag(QDialog):
	def __init__(self, parent):
		super().__init__(parent)
		
		self.setModal(False)
		
		self.setWindowTitle("Resize Grid")
		self.setMinimumSize(QSize(200, 150))
		self.setWhatsThis("Please specify the number of rows or columns to insert or remove from each side of the grid. Rows/columns will be inserted if the number is positive, and removed if it is negative.")
		
		layout = QVBoxLayout()
		
		# Left layout
		left_layout = QHBoxLayout()
		
		left_label = QLabel("Left:")
		left_label.setMinimumSize(QSize(40, 0))
		self.left_text = QLineEdit()
		
		left_layout.addWidget(left_label)
		left_layout.addWidget(self.left_text)
		
		# Top layout
		top_layout = QHBoxLayout()
		
		top_label = QLabel("Top:")
		top_label.setMinimumSize(QSize(40, 0))
		self.top_text = QLineEdit()
		
		top_layout.addWidget(top_label)
		top_layout.addWidget(self.top_text)
		
		# Right layout
		right_layout = QHBoxLayout()
		
		right_label = QLabel("Right:")
		right_label.setMinimumSize(QSize(40, 0))
		self.right_text = QLineEdit()
		
		right_layout.addWidget(right_label)
		right_layout.addWidget(self.right_text)
		
		# Top layout
		bottom_layout = QHBoxLayout()
		
		bottom_label = QLabel("Bottom:")
		bottom_label.setMinimumSize(QSize(40, 0))
		self.bottom_text = QLineEdit()
		
		bottom_layout.addWidget(bottom_label)
		bottom_layout.addWidget(self.bottom_text)
		
		# Return buttons layout
		finish_layout = QHBoxLayout()
		
		okay = QPushButton("Okay")
		okay.clicked.connect(self.okay)
		
		cancel = QPushButton("Cancel")
		cancel.clicked.connect(self.cancel)
		
		finish_layout.addStretch()
		finish_layout.addWidget(okay)
		finish_layout.addWidget(cancel)
		
		layout.addLayout(left_layout)
		layout.addLayout(top_layout)
		layout.addLayout(right_layout)
		layout.addLayout(bottom_layout)
		layout.addStretch()
		layout.addLayout(finish_layout)
		
		self.setLayout(layout)
	
	def okay(self):
		# Get entries
		left = self.left_text.text().strip()
		top = self.top_text.text().strip()
		right = self.right_text.text().strip()
		bottom = self.bottom_text.text().strip()
		
		# Convert to numbers
		try:
			if left != "":
				left = int(left)
			else:
				left = 0
			
			if top != "":
				top = int(top)
			else:
				top = 0
			
			if right != "":
				right = int(right)
			else:
				right = 0
			
			if bottom != "":
				bottom = int(bottom)
			else:
				bottom = 0
		
		except ValueError:
			print("Canceling Resize: Entries must be integers, or blank.")
			self.setParent(None)
			return
		
		parent = self.parentWidget()
		parent.resize_queued = (left, top, right, bottom, True)
		
		self.setParent(None)
	
	def cancel(self):
		print("Canceling Resize.")
		self.setParent(None)

# Defines the application window and GUI layout
# Interfaces with the CGOL_grid class
class CGOL_Window(QMainWindow):
	def __init__(self, cgol, cam):
		super().__init__()
		
		# The grid being used by this application
		self.cgol = cgol
		
		# The real camera used by this application
		self.cam = cam
		
		# The mainloop copies this into the real camera between renders. So, this can be safely edited at any time.
		self.proxy_cam = cam
		
		# Where the pattern will be saved.
		self.savename = None
		
		# The time that the last resize event occurred at. When this passes a second, it's set to None and the resize is handled.
		self.last_resize = None
		
		# Set by this library if a render is necessary. The mainloop will render at the next opportunity and set this back to False
		# Set whenever the window is resized, the camera is panned or zoomed, a frame is generated, the grid is modified, or the current grid to display is changed.
		self.render_queued = False
		
		# Set whenever a grid resize is queued. The mainloop will resize at the next opportunity and set this back to None.
		# This will be a 4-tuple of ints when it is set by resize_grid()
		self.resize_queued = None
		
		# Whether we're actively generating frames
		self.is_playing = False
		
		# Set to True to halt an ongoing simulation thread. The thread will set it back to False
		self.is_halting = False
		
		# The time of the most recent frame simulation
		self.last_frame_time = time.time()
		
		# The minimum delay between frames in seconds
		self.frame_delay = 0.6
		
		# The time of the most recent render
		self.last_render_time = time.time()
		
		# The minimum delay between renders in seconds
		self.render_delay = 0.05
		
		# Whether the grid is periodic or finite
		self.is_periodic = True
		
		# Set to the thread currently in charge of simulating the next frame.
		# When set to an active thread, no further threads will be launched for simulation.
		self.simulation_thread = dummy_thread()
		
		# Set to the thread currently in charge of rendering.
		# When set to an active thread, no further threads will be launched for rendering.
		self.render_thread = dummy_thread()
		
		# Create Window
		self.setWindowTitle("Conway's Game of Life")
		self.setMinimumSize(QSize(400, 300))
		self.resize(QSize(800, 600))
		
		# Create the canvas
		self.label = click_labal(self)
		self.label.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
		self.setCentralWidget(self.label)
		
		self.create_canvas()
		
		# Create the menu bar.
		self.create_options()
	
	def create_canvas(self):
		rect = self.label.parentWidget().rect()
		
		self.canvas = QtGui.QPixmap(rect.width(), rect.height())
		self.canvas.fill(Qt.white)
		
		self.render_queued = True
		
		self.label.setPixmap(self.canvas)
		
	def create_options(self):
		menu_bar = QMenuBar()
		self.setMenuBar(menu_bar)
		
		# File menu
		file_menu = QMenu("&File", menu_bar);
		file_menu.setToolTipsVisible(True)
		
		save = QAction("&Save", file_menu)
		save.triggered.connect(self.save)
		file_menu.addAction(save)
		
		save_as = QAction("&Save As", file_menu)
		save_as.triggered.connect(self.save_as)
		file_menu.addAction(save_as)
		
		open = QAction("&Open", file_menu)
		open.triggered.connect(self.open)
		file_menu.addAction(open)
		
		# Action menu
		actn_menu = QMenu("&Action", menu_bar);
		actn_menu.setToolTipsVisible(True)
		
		resz = QAction("Resize Grid", actn_menu)
		resz.triggered.connect(self.resize_grid)
		actn_menu.addAction(resz)
		
		rand = QAction("Randomize", actn_menu)
		rand.triggered.connect(self.cgol.randomize)
		actn_menu.addAction(rand)
		
		clear = QAction("Clear", actn_menu)
		clear.triggered.connect(self.cgol.clear)
		actn_menu.addAction(clear)
		
		# Options menu
		optn_menu = QMenu("&Options", menu_bar);
		optn_menu.setToolTipsVisible(True)
		
		# Period option
		self.period = QAction("Finite", optn_menu)
		self.period.triggered.connect(self.toggle_period)
		optn_menu.addAction(self.period)
		
		# Prev button
		self.prev = QAction("Prev", menu_bar)
		self.prev.triggered.connect(self.cgol.undo)
		
		# Play/Pause button
		self.play = QAction("Play", menu_bar)
		self.play.triggered.connect(self.toggle_play)
		
		# Next button
		self.next = QAction("Next", menu_bar)
		self.next.triggered.connect(self.cgol.redo)
		
		menu_bar.addMenu(file_menu)
		menu_bar.addMenu(actn_menu)
		menu_bar.addMenu(optn_menu)
		menu_bar.addAction(self.prev)
		menu_bar.addAction(self.play)
		menu_bar.addAction(self.next)
	
	# Overload the resize event. This sets a timer. If the timer gets to one second (meaning resizing is complete) then we re-create the pixmap that the grid is being drawn to.
	def resizeEvent(self, event):
		self.last_resize = time.time()
		return super().resizeEvent(event)
	
	# Resize the grid
	def resize_grid(self):
		diag = resize_diag(self)
		diag.show()
	
	# File operations
	def save(self):
		# If the savename is not set, call save_as to get one.
		if self.savename is None:
			self.save_as()
		else:
			print("Saving to " + self.savename + "...")
			
			# TODO: Save the grid
	
	def save_as(self):
		# Get the file to save as
		fn, fil = QFileDialog.getSaveFileUrl(filter="Pattern Files (*.pat);;All Files (*)")
		fn = fn.path()
		
		ext = os.path.splitext(fn)[-1].lower()
		
		# If this didn't result in a file being selected, cancel.
		if (fn == ""):
			print("Canceling save operation.")
			return
		
		# If the user didn't select a file extension and the file dialogue added a .pat extension anyway, which it does for some reason, remove it.
		if fil == "All Files (*)" and ext == ".pat":
			fn = fn[:-4]
		
		self.savename = fn
		
		# Save to the new savename
		self.save()
	
	def open(self):
		fn, fil = QFileDialog.getOpenFileUrl(filter="Pattern Files (*.pat);;All Files (*)")
		fn = fn.path()
		
		ext = os.path.splitext(fn)[-1].lower()
		
		# If this didn't result in a file being selected, cancel.
		if (fn == ""):
			print("Canceling open operation.")
			return
		
		print("Opening " + fn + "...")
		
		#TODO: Open a grid
	
	def toggle_play(self):
		if self.play.text() == "Play":
			self.play.setText("Pause")
			self.is_playing = True
		
		elif self.play.text() == "Pause":
			self.play.setText("Play")
			self.is_playing = False
	
	def toggle_period(self):
		if self.period.text() == "Periodic":
			self.period.setText("Finite")
			self.period.setToolTip("The grid will not loop.")
			self.is_periodic = True
		
		elif self.period.text() == "Finite":
			self.period.setText("Periodic")
			self.period.setToolTip("The grid will loop.")
			self.is_periodic = False

class camera:
	def __init__(self, x, y, s):
		self.x = x
		self.y = y
		self.s = s

# Dummy thread for initializing variables for which is_alive() will be called.
class dummy_thread():
	def is_alive(self):
		return False

class CGOL_grid:
	def __init__(self, width, height, history):
		# This hard-coded constant gives the number of cgols frames that can be stored in each grid.
		# It can be adjusted and the program benchmarked for speed and memory usage.
		# For memory usage, it should pretty much always be a multiple of 30 because of how Python integers work.
		self.BIT_WIDTH = 30
		
		self.width = width
		self.height = height
		
		# If True, the mainloop should step the simulation once.
		self.step_queued = False
		
		# If true, the mainloop will resize the grid at the next opportunity
		self.resize_queued = None
		
		# If set to true, a new frame has been generated and the GUI should advance one step.
		self.frame_ready = False
		
		# The history of this grid
		self.history = []
		self.history_cur = 0
		
		# Holds all of the grids currently in use.
		self.grids = []
		for h in range(history):
			self.grids.append([])
			
			for x in range(width):
				self.grids[h].append([])
				
				for y in range(height):
					self.grids[h][x].append(0)
		
		# Points to the grid that should be used to generate the next step.
		# THIS DOES NOT SIMPLY INDEX THE GRIDS ARRAY.
		# self.latest % len(grids) is the grid that should be used. self.latest // len(grids) is how many times the indexed grid should be rshifted before use.
		self.latest = 0
		
		# Points to the grid that is currently being rendered. This is used the same way as self.latest.
		self.current = 0
	
	# Appends an event to the history
	def append_event(self, e):
		if self.history_cur == len(self.history):
			self.history.append(e)
			self.history_cur+=1
		else:
			self.history[self.history_cur] = e
			self.history_cur+=1
			self.history = self.history[:self.history_cur]
	
	# Get the pixel at these coordinates for the current frame
	def get(self, x, y):
		ind, bit = self.get_current()
		mask = 1 << bit
		
		return self.grids[ind][x][y] & mask
	
	# Set the pixel at these coordinates for the current frame
	def set(self, x, y, record=True):
		ind, bit = self.get_current()
		mask = 1 << bit
		
		if record:
			val = self.get(x, y)
			if not val:
				self.append_event(("PIX", x, y, False, True))
		
		self.grids[ind][x][y] |= mask
	
	# Reset the pixel at these coordinates for the current frame
	def reset(self, x, y, record=True):
		ind, bit = self.get_current()
		mask = 1 << bit
		
		if record:
			val = self.get(x, y)
			if val:
				self.append_event(("PIX", x, y, True, False))
		
		self.grids[ind][x][y] &= ~mask
	
	# Flip the pixel at these coordinates for the current frame
	def flip(self, x, y, record=True):
		ind, bit = self.get_current()
		mask = 1 << bit
		
		if self.grids[ind][x][y] & mask:
			self.grids[ind][x][y] &= ~mask
			
			if record:
				self.append_event(("PIX", x, y, True, False))
		else:
			self.grids[ind][x][y] |= mask
			
			if record:
				self.append_event(("PIX", x, y, False, True))
	
	# Get the latest indexes
	def get_latest(self):
		return self.latest % len(self.grids), self.latest // len(self.grids)
	
	# Get the currently rendered indexes
	def get_current(self):
		return self.current % len(self.grids), self.current // len(self.grids)
	
	# Get the indexes of the grid we should render to.
	def get_target(self):
		next = (self.current + 1) % (len(self.grids) * self.BIT_WIDTH)
		return next % len(self.grids), next // len(self.grids)
	
	# Show the next grid
	def inc_current(self, record=True):
		# If we're already showing the latest frame, step the simulation.
		if (self.current == self.latest):
			cgol.step_queued = True
		
		# Otherwise, show the next frame.
		else:
			self.current = (self.current + 1) % (len(self.grids) * self.BIT_WIDTH)
			cgol.render_queued = True
		
			if record:
				cgol.append_event(("ADVANCE",))
	
	# Show the previous grid.
	def dec_current(self, record=True):
		prev = (self.current - 1) % (len(self.grids) * self.BIT_WIDTH)
		
		# If showing the previous grid would loop back around to showing the latest grid, don't do anything.
		if (prev == self.latest):
			return False
		
		self.current = prev
		cgol.render_queued = True
		
		if record:
			cgol.append_event(("REWIND",))
		
		return True
	
	# Undo
	def undo(self):
		print("Undo")
		if self.history_cur == 0:
			return
		
		e = self.history[self.history_cur-1]
		
		if e[0] == "PIX":
			ind, bit = self.get_current()
			mask = 1 << bit
			
			if e[3]:
				self.grids[ind][e[1]][e[2]] |= mask
			else:
				self.grids[ind][e[1]][e[2]] &= ~mask
		
		elif e[0] == "ADVANCE":
			if not self.dec_current(False):
				return
		
		elif e[0] == "REWIND":
			print("This should never be printed (1)")
			self.inc_current(False)
		
		elif e[0] == "RESIZE":
			self.resize_queued = (-e[1], -e[2], -e[3], -e[4], False)
		
		cgol.render_queued = True
		self.history_cur-=1
	
	def redo(self):
		print("Redo")
		if self.history_cur == len(self.history):
			self.latest = self.current
			self.inc_current()
			return
		
		e = self.history[self.history_cur]
		
		if e[0] == "PIX":
			ind, bit = self.get_current()
			mask = 1 << bit
			
			if e[4]:
				self.grids[ind][e[1]][e[2]] |= mask
			else:
				self.grids[ind][e[1]][e[2]] &= ~mask
		
		elif e[0] == "ADVANCE":
			self.inc_current(False)
		
		elif e[0] == "REWIND":
			print("This should never be printed (2)")
			if not self.dec_current(False):
				return
		
		elif e[0] == "RESIZE":
			self.resize_queued = (*e[1:], False)
		
		cgol.render_queued = True
		self.history_cur+=1
	
	# Set the grid that follows the currently rendered one as the latest.
	def set_next_to_latest(self):
		self.latest = (self.current + 1) % (len(self.grids) * self.BIT_WIDTH)
	
	# Add or remove rows and columns to the sides of the grid.
	# Also adjusts the position of the passed camera accordingly.
	def resize(self, left, top, right, bottom, record=True):
		# Error checking
		if self.width + left + right < 4 or self.height + top + bottom < 4:
			print("Aborting resize; resulting grid too small! (The limit is 4x4)")
			return
		
		if self.width + left + right > 1024 or self.height + top + bottom > 1024:
			print("Aborting resize; resulting grid too big! (The limit is 1024x1024)")
			return
		
		# Modify columns
		if left < 0:
			for g in range(len(self.grids)):
				self.grids[g] = self.grids[g][-left:]
		
		elif left > 0:
			for g in range(len(self.grids)):
				for i in range(left):
					self.grids[g].insert(0, [])
					
					for y in range(self.height):
						self.grids[g][0].append(0)
		
		if right < 0:
			for g in range(len(self.grids)):
				self.grids[g] = self.grids[g][:right+1]
		
		elif right > 0:
			for g in range(len(self.grids)):
				for i in range(right):
					self.grids[g].append([])
					
					for y in range(self.height):
						self.grids[g][-1].append(0)
		
		self.width += left + right
		
		# Modify rows
		if top < 0:
			for g in range(len(self.grids)):
				for x in range(self.width):
					self.grids[g][x] = self.grids[g][x][-top:]
		
		elif top > 0:
			for g in range(len(self.grids)):
				for x in range(self.width):
					for i in range(top):
						self.grids[g][x].insert(0, 0)
		if bottom < 0:
			for g in range(len(self.grids)):
				for x in range(self.width):
					self.grids[g][x] = self.grids[g][x][:bottom+1]
		
		elif bottom > 0:
			for g in range(len(self.grids)):
				for x in range(self.width):
					for i in range(bottom):
						self.grids[g][x].append(0)
		
		# Modify stored width and height
		self.height += top + bottom
		
		if record:
			self.append_event(("RESIZE", left, top, right, bottom))
		
		# Queue render
		self.render_queued = True
	
	# Fill the next grid with random data.
	def randomize(self):
		ind, bit = self.get_target()
		mask = 1 << bit
		
		for x in range(self.width):
			for y in range(self.height):
				if random.randint(0, 2) == 0:
					self.grids[ind][x][y] |= mask
		
		self.set_next_to_latest()
		self.frame_ready = True
		
#		print("Randomized %d (%d, %d)" % (self.latest, *self.get_latest()))
	
	# Fill the next grid with dead cells.
	def clear(self):
		ind, bit = self.get_target()
		mask = 1 << bit
		
		for x in range(len(self.grids[ind])):
			for y in range(len(self.grids[ind][0])):
				self.grids[ind][x][y] &= ~mask
		
		self.set_next_to_latest()
		self.frame_ready = True
		
#		print("Randomized %d (%d, %d)" % (self.latest, *self.get_latest()))
	
	# Simulates one step into the next grid. Gets a copy of is_periodic so we can change it from another thread without affecting the render.
	def step(self, window, is_periodic):
		s_ind, s_bit = self.get_current()
		d_ind, d_bit = self.get_target()
		
		s_mask = 1 << s_bit
		d_mask = 1 << d_bit
		
		d_mask_inv = ~d_mask
		
		# Separate loops for periodic vs finite grids helps performance
		# This is the only part of the code where performance is a serious concern.
		if is_periodic:
			# For each tile...
			for x in range(self.width):
				
				# In between columns, check if we should abort
				if window.is_halting:
					print("Halting simulation thread.")
					window.is_halting = False
					return
				
				for y in range(self.height):
					neighbors = 0
					
					# For each neighbor of this tile...
					for a in range(x-1, x+2):
						for b in range(y-1, y+2):
							# Don't count this cell as its own neighbor.
							if (a == x and b == y):
								continue
							
							# Count the neighbors
							if self.grids[s_ind][a % self.width][b % self.height] & s_mask:
								neighbors+=1
					
					# Apply CGoL rules
					if neighbors < 2 or neighbors > 3 or (neighbors == 2 and not self.grids[s_ind][x][y] & s_mask):
						self.grids[d_ind][x][y] &= d_mask_inv
						
					else:
						self.grids[d_ind][x][y] |= d_mask
			
		else:
			# For each tile...
			for x in range(self.width):
				
				# In between columns, check if we should abort
				if not window.is_halting:
					print("Halting simulation thread.")
					return
				
				for y in range(self.height):
					neighbors = 0
					
					# For each neighbor of this tile...
					for a in range(max(x-1, 0), min(x+2, self.width)):
						for b in range(max(y-1, 0), min(y+2, self.height-1)):
							# Don't count this cell as its own neighbor.
							if (a == x and b == y):
								continue
							
							# Count the neighbors
							if self.grids[s_ind][a % self.width][b % self.height] & s_mask:
								neighbors+=1
					
					# Apply CGoL rules
					if neighbors < 2 or neighbors > 3 or (neighbors == 2 and not self.grids[s_ind][x][y] & s_mask):
						self.grids[d_ind][x][y] &= d_mask_inv
						
					else:
						self.grids[d_ind][x][y] |= d_mask
		
		# Ready to render next frame
		self.set_next_to_latest()
		self.frame_ready = True
		
#		print("Next ready at %d (%d, %d), generated from %d (%d, %d)" % (self.latest, d_ind, d_bit, self.current, s_ind, s_bit))
		
	# Renders using the passed camera, to the passed QPixmap
	def render(self, window, cam, elem):
		ind, bit = self.get_current()
		
		pix = elem.pixmap()
		
#		print("Rendering frame %d... (%d, %d)" % (self.current, ind, bit))
		
		rect = pix.rect()
		w2 = rect.width() / 2 / cam.s
		h2 = rect.height() / 2 / cam.s
		
		# Get the range of grid squares that should be rendered
		left = cam.x - w2
		top = cam.y - h2
		right = cam.x + w2 + 1
		bottom = cam.y + h2 + 1
		
		painter = QtGui.QPainter(pix)
		
		# Clear the pixmap
		painter.fillRect(0, 0, rect.width(), rect.height(), QtGui.QColor.fromRgb(10, 10, 10))
		
		# Draw the grid background
		grid_l = int(0 - cam.x * cam.s + rect.width() / 2)
		grid_t = int(0 - cam.y * cam.s + rect.height() / 2)
		painter.fillRect(grid_l, grid_t, cgol.width * cam.s, cgol.height * cam.s, QtGui.QColor.fromRgb(25, 25, 25))
		
		# Iterate over all the squares in this range
		mask = 1 << bit
		for x in range(max(math.floor(left), 0), min(math.ceil(right), self.width)):
			for y in range(max(math.floor(top), 0), min(math.ceil(bottom), self.height)):
				if self.grids[ind][x][y] & mask:
					painter.fillRect(int((x - left) * cam.s), int((y - top) * cam.s), int(cam.s), int(cam.s), QtGui.QColor.fromRgb(230, 230, 230))
		
		elem.update()
		painter.end()
		
#		elem.setPixmap(pix)

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