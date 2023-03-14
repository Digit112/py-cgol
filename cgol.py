from PyQt5 import QtGui

import math
import os
import random
import sys

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
		
		# If True, the mainloop should step the simulation once.
		self.step_queued = False
		
		# If true, the mainloop will resize the grid at the next opportunity
		self.resize_queued = None
		
		# If true, the mainloop will place the currently loaded pattern at the next opportunity.
		self.place_queued = None
		
		# If true, the user has opened a pattern file and is placing the pattern currently.
		self.is_placing = False
		
		# If set to true, a new frame has been generated and the GUI should advance one step.
		self.frame_ready = False
		
		# Stores patterns that are opened for writing to the grid.
		self.pattern = None
		
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
			self.step_queued = True
		
		# Otherwise, show the next frame.
		else:
			self.current = (self.current + 1) % (len(self.grids) * self.BIT_WIDTH)
			self.render_queued = True
		
			if record:
				self.append_event(("ADVANCE",))
	
	# Show the previous grid.
	def dec_current(self, record=True):
		prev = (self.current - 1) % (len(self.grids) * self.BIT_WIDTH)
		
		# If showing the previous grid would loop back around to showing the latest grid, don't do anything.
		if (prev == self.latest):
			return False
		
		self.current = prev
		self.render_queued = True
		
		if record:
			self.append_event(("REWIND",))
		
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
		
		self.render_queued = True
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
		
		self.render_queued = True
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
		
		if self.width + left + right > 512 or self.height + top + bottom > 512:
			print("Aborting resize; resulting grid too big! (The limit is 512x512)")
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
		
#		print("Cleared %d (%d, %d)" % (self.latest, *self.get_latest()))
	
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
								
								if neighbors > 3:
									break
					
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
					window.is_halting = False
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
								
								if neighbors > 3:
									break
								
						if neighbors > 3:
							break
					
					# Apply CGoL rules
					if neighbors < 2 or neighbors > 3 or (neighbors == 2 and not self.grids[s_ind][x][y] & s_mask):
						self.grids[d_ind][x][y] &= d_mask_inv
						
					else:
						self.grids[d_ind][x][y] |= d_mask
		
		# Ready to render next frame
		self.set_next_to_latest()
		self.frame_ready = True
		
		print("Next ready at %d (%d, %d), generated from %d (%d, %d)" % (self.latest, d_ind, d_bit, self.current, s_ind, s_bit))
		
	# Renders using the passed camera, to the passed QPixmap
	def render(self, window, cam, elem):
		ind, bit = self.get_current()
		
		pix = elem.pixmap()
		
		print("Rendering frame %d... (%d, %d)" % (self.current, ind, bit))
		
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
		painter.fillRect(grid_l, grid_t, int(self.width * cam.s), int(self.height * cam.s), QtGui.QColor.fromRgb(25, 25, 25))
		
		# Iterate over all the squares in this range
		mask = 1 << bit
		for x in range(max(math.floor(left), 0), min(math.ceil(right), self.width)):
			for y in range(max(math.floor(top), 0), min(math.ceil(bottom), self.height)):
				if self.grids[ind][x][y] & mask:
					painter.fillRect(int((x - left) * cam.s), int((y - top) * cam.s), int(cam.s), int(cam.s), QtGui.QColor.fromRgb(230, 230, 230))
		
		# Render the preview
		if self.is_placing:
			pat_width = len(self.pattern)
			pat_height = len(self.pattern[0])
			
			x = max(math.floor(left + window.label.mouse_x / int(cam.s)), 0)
			y = max(math.floor(top + (window.label.mouse_y + 10) / int(cam.s)), 0)
			print(x, y)
			
			for a in range(max(-x, 0), min(min(pat_width, self.width-x), math.ceil(right)-x)):
				for b in range(max(-y, 0), min(min(pat_height, self.height-y), math.ceil(bottom))):
					if self.pattern[a][b]:
						painter.fillRect(int((x + a - left) * cam.s), int((y + b - top) * cam.s), int(cam.s), int(cam.s), QtGui.QColor.fromRgb(210, 230, 210))
		
		elem.update()
		painter.end()
		
#		elem.setPixmap(pix)
	
	# Copy this frame into the next frame
	def clone(self):
		s_ind, s_bit = self.get_current()
		d_ind, d_bit = self.get_target()
		
		s_mask = 1 << s_bit
		d_mask = 1 << d_bit
		
		for x in range(self.width):
			for y in range(self.height):
				if self.get(x, y):
					self.grids[d_ind][x][y] |= d_mask
				else:
					self.grids[d_ind][x][y] &= ~d_mask
	
	# Crops the pattern currently being displayed and saves it to a file.
	def save(self, fn):
		if os.name == "nt" and fn[0] == "/":
			fn = fn[1:]
		
		# Find the bounding box of the current pattern
		left = 0
		for x in range(self.width):
			has_bits = False
			for y in range(self.height):
				if self.get(x, y):
					has_bits = True
					left = x
					break
			
			if has_bits:
				break
		
		right = 0
		for x in range(self.width-1, -1, -1):
			has_bits = False
			for y in range(self.height):
				if self.get(x, y):
					has_bits = True
					right = x
					break
			
			if has_bits:
				break
		
		top = 0
		for y in range(self.height):
			has_bits = False
			for x in range(self.width):
				if self.get(x, y):
					has_bits = True
					top = y
					break
			
			if has_bits:
				break
		
		bottom = 0
		for y in range(self.height-1, -1, -1):
			has_bits = False
			for x in range(self.width):
				if self.get(x, y):
					has_bits = True
					bottom = y
					break
			
			if has_bits:
				break
		
		print("Saving (%d, %d) - (%d, %d)" % (left, top, right, bottom))
		
		with open(fn, "w") as fout:
			fout.write(str(right - left + 1) + " ")
			fout.write(str(bottom - top + 1) + " ")
			
			for y in range(top, bottom+1):
				for x in range(left, right+1):
					fout.write("1" if self.get(x, y) else "0")
	
	# Opens a file and stores the pattern in this program's
	def open(self, fn):
		if os.name == "nt" and fn[0] == "/":
			fn = fn[1:]
		
		self.pattern = []
		
		with open(fn, "r") as fin:
			# Get width and height
			dat = fin.read().split(" ")
			
			try:
				pat_width = int(dat[0])
				pat_height = int(dat[1])
				
			except ValueError:
				print("Aborting Open: Invalid File.")
			
			try:
				for x in range(pat_width):
					self.pattern.append([])
					
					for y in range(pat_height):
						ind = y*pat_width + x
						
						self.pattern[x].append(1 if dat[2][ind] == "1"  else 0)
				
			except IndexError:
				print("Aborting Open: Invalid File.")
		
		self.is_placing = True

	# Place the opened pattern onto the next grid at the given position.
	# If do_erase, this will overwrite live pixels in the grid with dead pixels in the pattern
	def place(self, x, y, do_erase):
		ind, bit = self.get_target()
		mask = 1 << bit
		
		pat_width = len(self.pattern)
		pat_height = len(self.pattern[0])
		
		self.clone()
		
		for a in range(max(-x, 0), min(pat_width, self.width-x)):
			for b in range(max(-y, 0), min(pat_height, self.height-y)):
				if self.pattern[a][b]:
					self.grids[ind][x+a][y+b] |= mask
				elif do_erase:
					self.grids[ind][x+a][y+b] &= ~mask
		
		self.set_next_to_latest()
		self.frame_ready = True