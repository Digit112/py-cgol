from PyQt5.QtCore import QSize, Qt, QUrl
from PyQt5.QtWidgets import QApplication, QWidget, QMainWindow, QPushButton, QVBoxLayout, QMenu, QMenuBar, QLabel, QAction, QFileDialog

import os
import sys

class CGOL_Window(QMainWindow):
	def __init__(self):
		super().__init__()
		
		# Where the pattern will be saved.
		self.savename = None
		
		# Create Window
		self.setWindowTitle("Conway's Game of Life")
		self.setMinimumSize(QSize(400, 300))
		self.resize(QSize(800, 600))
		
		# Create the central widget
		self.central_w = QLabel("Hello Menu.")
		self.central_w.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
		self.setCentralWidget(self.central_w)
		
		# Create the menu bar.
		self.create_options()
		
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
		self.play.triggered.connect(self.play_pause)
		
		menu_bar.addMenu(file_menu)
		menu_bar.addMenu(optn_menu)
		menu_bar.addAction(self.play)
	
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
	
	def play_pause(self):
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
			

app = QApplication(sys.argv)

window = CGOL_Window()
window.show()

app.exec()

print("Goodbye!")