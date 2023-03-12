from PyQt5 import QtGui
from PyQt5.QtCore import QSize, Qt, QUrl, QTimer
from PyQt5.QtWidgets import QApplication, QWidget, QMainWindow, QPushButton, QVBoxLayout, QMenu, QMenuBar, QLabel, QAction, QFileDialog

import asyncio
import math
import os
import random
import sys
import time

# Defines the 

# Defines the application window and GUI layout
# Interfaces with the CGOL_grid class
class CGOL_Window(QMainWindow):
	def __init__(self):
		super().__init__()
		
		# Where the pattern will be saved.
		self.savename = None
		
		# The time that the last resize event occurred at. When this passes a second, it's set to None and the resize is handled.
		self.last_resize = None
		
		# Set by this library if a render is necessary (caused by a resize)
		self.render_queued = False
		
		# Create Window
		self.setWindowTitle("Conway's Game of Life")
		self.setMinimumSize(QSize(400, 300))
		self.resize(QSize(800, 600))
		
		# Create the canvas
		self.label = QLabel(self)
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
		
		# Options menu
		optn_menu = QMenu("&Options", menu_bar);
		optn_menu.setToolTipsVisible(True)
		
		# Period option
		self.period = QAction("Periodic", optn_menu)
		self.period.triggered.connect(self.toggle_period)
		optn_menu.addAction(self.period)
		
		# Play/Pause button
		self.play = QAction("Play", optn_menu)
		self.play.triggered.connect(self.toggle_play)
		
		menu_bar.addMenu(file_menu)
		menu_bar.addMenu(optn_menu)
		menu_bar.addAction(self.play)
	
	# Overload the resize event. This sets a timer. If the timer gets to one second (meaning resizing is complete) then we re-create the pixmap that the grid is being drawn to.
	def resizeEvent(self, event):
		self.last_resize = time.time()
		return super().resizeEvent(event)
	
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
		
		elif self.play.text() == "Pause":
			self.play.setText("Play")
	
	def toggle_period(self):
		if self.period.text() == "Periodic":
			self.period.setText("Finite")
			self.period.setToolTip("The grid will not loop.")
		
		elif self.period.text() == "Finite":
			self.period.setText("Periodic")
			self.period.setToolTip("The grid will loop.")

class camera:
	def __init__(self, x, y, s):
		self.x = x
		self.y = y
		self.s = s

class CGOL_grid:
	def __init__(self, width, height, history):
		# This hard-coded constant gives the number of cgols frames that can be stored in each grid.
		# It can be adjusted and the program benchmarked for speed and memory usage.
		# For memory usage, it should pretty much always be a multiple of 30 because of how Python integers work.
		self.BIT_WIDTH = 30
		
		self.width = width
		self.height = height
		
		# If set to true, a new frame has been generated and the GUI should advance one step.
		self.frame_ready = False
		
		# Holds all of the grids currently in use.
		self.grids = []
		for h in range(history):
			self.grids.append([])
			
			for x in range(width):
				self.grids[h].append([])
				
				for y in range(height):
					self.grids[h][x].append(0)
		
		# Points to the grid that should be used to generate the next step.
		# THIS DOES NOT SIMPLY INDEX THE grids ARRAY.
		# self.latest % len(grids) is the grid that should be used. self.latest // len(grids) is how many times the indexed grid should be rshifted before use.
		self.latest = 0
		
		# Points to the grid that is currently being rendered. This is used the same way as self.latest.
		self.current = 0
	
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
	def inc_current(self):
		self.current = (self.current + 1) % (len(self.grids) * self.BIT_WIDTH)
	
	# Show the previous grid
	def dec_current(self):
		prev = (self.current + 1 + (len(self.grids) * self.BIT_WIDTH)) % (len(self.grids) * self.BIT_WIDTH)
		
		# If showing the previous grid would loop back around to showing the latest grid, don't do anything.
		if (prev == self.latest):
			return
		
		self.current = prev
	
	# Set the grid that follows the currently rendered one as the latest.
	def set_next_to_latest(self):
		self.latest = (self.current + 1) % (len(self.grids) * self.BIT_WIDTH)
	
	# Fill the next grid with random data.
	def randomize(self):
		ind, bit = self.get_target()
		mask = 1 << bit
		
		for x in range(len(self.grids[ind])):
			for y in range(len(self.grids[ind][0])):
				if random.randint(0, 1):
					self.grids[ind][x][y] |= mask
		
		self.set_next_to_latest()
		self.frame_ready = True
	
	def render(self, cam, pix):
		ind, bit = self.get_current()
		
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
		painter.fillRect(0, 0, rect.width(), rect.height(), QtGui.QColor.fromRgb(25, 25, 25))
		
		# Iterate over all the squares in this range
		mask = 1 << bit
		for x in range(max(math.floor(left), 0), min(math.ceil(right), self.width)):
			for y in range(max(math.floor(top), 0), min(math.ceil(bottom), self.height)):
				if self.grids[ind][x][y] & mask:
					painter.fillRect(int((x - left) * cam.s), int((y - top) * cam.s), cam.s, cam.s, QtGui.QColor.fromRgb(230, 230, 230))
		
		painter.end()

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
		print("Next frame...")
		cgol.inc_current()
		cgol.render(cam, window.label.pixmap())
		cgol.frame_ready = False
	
	# If a new frame isn't ready, check if the application is requesting a render
	elif window.render_queued:
		cgol.render(cam, window.label.pixmap())
		window.render_queued = False

cgol = CGOL_grid(200, 150, 1)
cam = camera(100, 75, 10)

cgol.randomize()

app = QApplication(sys.argv)

window = CGOL_Window()
window.show()

cgol_loop = QTimer()
cgol_loop.timeout.connect(mainloop)
cgol_loop.start()

app.exec()

print("Goodbye!")