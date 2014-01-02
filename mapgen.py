#PONYHACK: A pony roguelike.
#Copyright (C) 2013 Anonymous
#
#This is the map generation module for Ponyhack. It is responsible for
#generating maps and populating them with objects.
#
#This program is free software: you can redistribute it and/or modify
#it under the terms of the GNU General Public License as published by
#the Free Software Foundation, either version 3 of the License, or
#(at your option) any later version.
#
#This program is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with this program.  If not, see <http://www.gnu.org/licenses/>.

import libtcodpy as libtcod
import math
import data
import objectgen

MAP_WIDTH = data.MAP_WIDTH
MAP_HEIGHT = data.MAP_HEIGHT

MAX_ROOMS = 10
ROOM_MIN_SIZE = 5
ROOM_MAX_SIZE = 10

###COLOR FUNCTIONS###

def grass(lit):
	if lit:
		return libtcod.dark_green
	else:
		return libtcod.darker_green

def pink(lit):
	if lit:
		return libtcod.pink
	else:
		return libtcod.dark_pink

def blue(lit):
	if lit:
		return libtcod.dark_blue
	else:
		return libtcod.darker_blue

def window(lit):
	if lit:
		return libtcod.light_sky
	else:
		return libtcod.sky

def door(lit):
	if lit:
		return libtcod.Color(200,180,50)
	else:
		return libtcod.Color(130, 110, 50)


class Tile:
	#Objects that are tiles on the map.
	def __init__(self, blocked, color=None, block_sight=None):
		self.blocked = blocked
		self.base_color = color
		self.explored = False

		#Blocked tiles also block sight by default.
		if block_sight == None:
			self.block_sight = self.blocked

	def color(self, lit):
		return self.base_color(lit)

class Rect:
	#A rectangle, used for map generation.
	def __init__(self, x, y, w, h):
		self.x1 = x
		self.y1 = y
		self.x2 = x + w
		self.y2 = y + h

	def center(self):
		#Finds the center of a rectangle.
		center_x = (self.x1 + self.x2) / 2
		center_y = (self.y1 + self.y2) / 2
		return (center_x, center_y)

	def intersect(self, other):
		#Returns true if this rectangle intersects with another one.
		return (self.x1 <= other.x2 and self.x2 >= other.x1 and self.y1 <= other.y2 and self.y2 >= other.y1)

class Area:
	#Class for area objects.
	def __init__(self, map, name, dark=False):
		self.name = name
		self.map = map
		self.objects = []
		self.dark = dark

	def gen_block(self, block, color):
		#Generating an impassable block on the map.
		for x in range(block.x1, block.x2):
			for y in range(block.y1, block.y2):
				self.map[x][y].blocked = True
				self.map[x][y].block_sight = True
				self.map[x][y].color = color

	def gen_room(self, room, color):
		#Generating an open space on the map.
		for x in range(room.x1, room.x2):
			for y in range(room.y1, room.y2):
				self.map[x][y].blocked = False
				self.map[x][y].block_sight = False
				self.map[x][y].color = color

	def gen_window(self, x, y):
		#Generates a tile that can be seen through but not passed through.
		#Might be replaced with a breakable object in the future.
		self.map[x][y].blocked = True
		self.map[x][y].block_sight = False
		self.map[x][y].color = window

	def gen_door(self, x, y):
		#Generates a tile that can be passd through but not seen through.
		#Might be replaced with an object in the future.
		self.map[x][y].blocked = False
		self.map[x][y].block_sight = True
		self.map[x][y].color = door

	def gen_building(self, rect, wall_color, floor_color):
		#Generates a square building with impassable walls.
		floor = Rect(rect.x1 + 1, rect.y1 + 1, rect.x2 - rect.x1 - 2, rect.y2 - rect.y1 - 2)
		self.gen_block(rect, wall_color)
		self.gen_room(floor, floor_color)

###AREA GENERATION FUNCTIONS###

def ponyville():
	#Fill map with open tiles.
	map = [[Tile(False, color=grass)
		for y in range(MAP_HEIGHT)]
			for x in range(MAP_WIDTH)]
	area = Area(map, 'Central Ponyville')

	#Generate the building.
	block = Rect(5, 5, 5, 3)
	area.gen_block(block, pink)
	
	#Generate objects.
	data.player = objectgen.gen_player()
	practice_dummy = objectgen.gen_dummy()
	sword = objectgen.gen_sword()
	shield = objectgen.gen_shield()
	area.objects.append(sword)
	area.objects.append(shield)
	area.objects.append(data.player)
	area.objects.append(practice_dummy)
	return area

def ponyville_north():
	#Fill map with open tiles
	map = [[Tile(False, color=grass)
		for y in range(MAP_HEIGHT)]
			for x in range(MAP_WIDTH)]
	area = Area(map, 'Ponyville North')

	#Generate the building.
	block = Rect(8, 8, 20, 20)
	area.gen_building(block, blue, pink)
	area.gen_window(8, 15)
	area.gen_door(15, 8)

	#Generate objects
	stairs = objectgen.gen_down_stairs()
	area.objects.append(stairs)
	return area

def dungeon():

	#Fill map with blocked tiles.
	map = [[Tile(True, color=blue)
		for y in range(MAP_HEIGHT)]
			for x in range(MAP_WIDTH)]
	area = Area(map, 'Dungeon level 1')

	room = Rect(23, 23, 5, 5)
	area.gen_room(room, color=pink)
	stairs = objectgen.gen_up_stairs()
	area.objects.append(stairs)
	return area

#	rooms = []
#	num_rooms = 0

#	for r in range(MAX_ROOMS):
#	#Random width and height.
#		w = libtcod.random_get_int(0, ROOM_MIN_SIZE, ROOM_MAX_SIZE)
#		h = libtcod.random_get_int(0, ROOM_MIN_SIZE, ROOM_MAX_SIZE)
#		#Random position without going out of the boundaries of the map.
#		x = libtcod.random_get_int(0, 0, MAP_WIDTH - w - 1)
#		y = libtcod.random_get_int(0, 0, MAP_HEIGHT - h - 1)

#		room = Rect(x, y, w, h)
		
