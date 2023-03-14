from PyQt5 import QtGui
from PyQt5.QtCore import QSize, Qt, QUrl, QTimer, QPoint
from PyQt5.QtWidgets import QApplication, QWidget, QMainWindow, QPushButton, QVBoxLayout, QHBoxLayout, QMenu, QMenuBar, QLabel, QAction, QFileDialog, QDialog, QLineEdit

import math
import os
import time
import threading

# Dummy thread for initializing variables for which is_alive() will be called.
class dummy_thread():
	def is_alive(self):
		return False

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
		
		# Mouse position
		self.mouse_x = 0
		self.mouse_y = 0
	
	# Gets the tile at the position passed in local coordinates
	def get_tile(self, x, y):
		parent = self.parentWidget()
		
		rect = self.rect()
		w2 = rect.width() / 2 / parent.cam.s
		h2 = rect.height() / 2 / parent.cam.s
		
		x = min(max(math.floor(x / parent.cam.s + parent.cam.x - w2), 0), parent.cgol.width-1)
		y = min(max(math.floor(y / parent.cam.s + parent.cam.y - h2), 0), parent.cgol.height-1)
		
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
		
		parent = self.parentWidget()
		
		self.last_x = None
		self.last_y = None
		
		# If placing, place the pattern.
		if parent.cgol.is_placing:
			# If left click, place
			if e.button() == Qt.LeftButton:
				x, y = self.get_tile(e.pos().x(), e.pos().y())
				
				parent.cgol.place_queued = (x, y, True)
				parent.cgol.is_placing = False
				
			# If right-click, cancel
			elif e.button() == Qt.RightButton:
				parent.cgol.is_placing = False
		
		else:
			# If released after dragging, don't do anything
			if self.lock != None:
				self.lock = None
				return
			
			# If the user has released the left mouse button after holding it down for 
			if e.button() == Qt.LeftButton and time.time() - self.click_timer < 0.4:
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
		
		# Otherwise, set the saved mouse position
		else:
			self.mouse_x = e.pos().x()
			self.mouse_y = e.pos().y()
	
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
		self.frame_delay = 0.2
		
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
		self.label.setMouseTracking(True)
		
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
			
			self.cgol.save(self.savename)
	
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
		
		self.cgol.open(fn)
	
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
