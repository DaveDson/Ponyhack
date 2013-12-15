import libtcodpy as libtcod

MAP_WIDTH = 120
MAP_HEIGHT = 80

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

class Tile:
	#Objects that are tiles on the map
	def __init__(self, blocked, color=None, block_sight=None):
		self.blocked = blocked
		self.base_color = color
		self.explored = False

		#Blocked tiles also block sight by default
		if block_sight == None:
			self.block_sight = self.blocked

	def color(self, lit):
		return self.base_color(lit)

def gen_building(map, posx, posy, width, height, color):
	for x in range(posx, posx+width):
		for y in range(posy, posy+height):
			map[x][y].blocked = True
			map[x][y].block_sight = True
			map[x][y].color = color
	return map

def ponyville():
	map = [[Tile(False, color=grass)
		for y in range(MAP_HEIGHT)]
			for x in range(MAP_WIDTH)]
	map = gen_building(map, 5, 10, 5, 3, color=pink)
	return map

def ponyville_north():
	map = [[Tile(False, color=grass)
		for y in range(MAP_HEIGHT)]
			for x in range(MAP_WIDTH)]
	map = gen_building(map, 8, 8, 20, 20, color=blue)
	return map
