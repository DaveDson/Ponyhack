#PONYHACK: A pony roguelike.
#Copyright (C) 2013 Anonymous
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
import textwrap
import shelve
import mapgen

SCREEN_WIDTH = 80
SCREEN_HEIGHT = 50
LIMIT_FPS = 20

MAP_WIDTH = mapgen.MAP_WIDTH
MAP_HEIGHT = mapgen.MAP_HEIGHT
MAP_WINDOW_WIDTH = 50
MAP_WINDOW_HEIGHT = 50
PANEL_WIDTH = SCREEN_WIDTH - MAP_WINDOW_WIDTH
PANEL_HEIGHT = SCREEN_HEIGHT
MSG_WIDTH = PANEL_WIDTH
MSG_HEIGHT = 20

FOV_ALGO = 0
TORCH_RADIUS = 50
FOV_LIGHT_WALLS = True

MENU_HILIGHT = libtcod.Color(120, 153, 34)

libtcod.console_set_custom_font('arial10x10.png', libtcod.FONT_TYPE_GREYSCALE | libtcod.FONT_LAYOUT_TCOD)

#initialising the root console
libtcod.console_init_root(SCREEN_WIDTH, SCREEN_HEIGHT, 'Ponyhack', False)

#The virtual console the map will be drawn on before blitting to root
mapcon = libtcod.console_new(MAP_WIDTH, MAP_HEIGHT)

#The panel with various game information
panel = libtcod.console_new(PANEL_WIDTH, PANEL_HEIGHT)

class Area:
	#class for area objects
	def __init__(self, X, Y, map, name, objects, dark=False):
		global areas		
		self.X = X
		self.Y = Y
		self.name = name
		self.map = map
		self.objects = objects
		self.dark = dark
		#append the new area to the areas dictionary
		if not self.X in areas:
			areas[X] = {}
		areas[X][Y] = self

class Object:
	#generic class for all map objects
	def __init__(self, x, y, X, Y, name, char, color, blocks=False, inventory=[], light_emittance=0, creature=None, item=None):
		self.x = x
		self.y = y
		self.X = X
		self.Y = Y
		self.name = name
		self.char = char
		self.color = color
		self.blocks = blocks
		self.inventory = inventory
		self.light_emittance = light_emittance
		self.light_map = None
		#tell any components what owns them
		self.creature = creature
		if self.creature:
			self.creature.owner = self
		self.item = item
		if self.item:
			self.item.owner = self

	def move(self, dx, dy):
		x = self.x + dx
		y = self.y + dy
		#change the map area if going off screen
		if x < 0:
			if self.change_area(-1, 0):
				self.x = MAP_WIDTH - 1
		elif x > MAP_WIDTH - 1:
			if self.change_area(1, 0):
				self.x = 0
		elif y < 0:
			if self.change_area( 0, -1):
				self.y = MAP_HEIGHT -1
		elif y > MAP_HEIGHT - 1:
			if self.change_area(0, 1):
				self.y = 0
		elif not current_area.map[x][y].blocked:
			self.x = x
			self.y = y

	def change_area(self, dX, dY):
		global current_area
		new_X = self.X + dX
		new_Y = self.Y + dY
		if new_X in areas:
			if new_Y in areas[new_X]:
				areas[new_X][new_Y].objects.append(self)
				areas[self.X][self.Y].objects.remove(self)
				self.X = new_X
				self.Y = new_Y
				current_area = areas[new_X][new_Y]
				initialise_fov()
				return True
		return False

	def draw(self):
		libtcod.console_set_default_foreground(mapcon, self.color)
		libtcod.console_put_char(mapcon, self.x, self.y, self.char, libtcod.BKGND_NONE)

	def clear(self):
		libtcod.console_put_char(mapcon, self.x, self.y, ' ', libtcod.BKGND_NONE)

class Creature:
	def __init__(self, hp, stamina, strength, dexterity, toughness):
		self.max_hp = hp
		self.hp = hp
		self.max_stamina = stamina
		self.stamina = stamina
		self.strength = strength
		self.dexterity = dexterity
		self.toughness = toughness

	def attack(self, target):
		damage = self.strength - target.toughness

		if damage > 0:
			target.take_damage(damage)

	def take_damage(self, damage):
		if damage > 0:
			self.hp -= damage

	def heal(self, amount):
		self.hp += amount
		if self.hp > self.max_hp:
			self.hp = self.max_hp

class Item:
	def __init__(self, use_function=None):
		self.use_function = use_function

	def pick_up(self):
		inv.append(self.owner)
		current_area.objects.remove(self.owner)
		message('You picked up a ' + self.owner.name + '.', color=libtcod.desaturated_green)

	def drop(self):
		self.owner.x = player.x
		self.owner.y = player.y
		self.owner.X = player.X
		self.owner.Y = player.Y
		current_area.objects.append(self.owner)
		inv.remove(self.owner)
		message('You dropped a ' + self.owner.name + '.', color=libtcod.desaturated_red)


###GLOBAL FUNCTIONS###		

def handle_keys():
	
	global key
#	if key.vk == libtcod.KEY_ENTER and key.lalt:
#		#Alt+Enter: toggle fullscreen
#		libtcod.console_set_fullscreen(not libtcod.console_is_fullscreen())
	if key.vk ==libtcod.KEY_ESCAPE:
		return 'exit' #exit game

	if game_state == 'playing':
		#movement keys
		if key.vk == libtcod.KEY_UP or key.vk == libtcod.KEY_KP8:
			player_move(0, -1)
		elif key.vk == libtcod.KEY_DOWN or key.vk == libtcod.KEY_KP2:
			player_move(0, 1)
		elif key.vk == libtcod.KEY_LEFT or key.vk == libtcod.KEY_KP4:
			player_move(-1, 0)
		elif key.vk == libtcod.KEY_RIGHT or key.vk == libtcod.KEY_KP6:
			player_move(1, 0)
		elif key.vk == libtcod.KEY_KP7:
			player_move(-1, -1)
		elif key.vk == libtcod.KEY_KP9:
			player_move(1, -1)
		elif key.vk == libtcod.KEY_KP1:
			player_move(-1, 1)
		elif key.vk == libtcod.KEY_KP3:
			player_move(1, 1)
		elif key.vk == libtcod.KEY_KP5:
			pass #wait a turn
		else:
			#test for other keys
			key_char = chr(key.c)

			if key_char == 't':
				option = menu('pony choice', ['Rarity', 'Applejack', 'Rainbow Dash'], 30)
				if option == 0:
					print 'Generosity'
				elif option == 1:
					print 'Honesty'
				elif option == 2:
					print 'Loyalty'
				else: print 'menu error'

			if key_char == 'g':
				for object in current_area.objects:
					if object.x == player.x and object.y == player.y and object != player:
						object.item.pick_up()

			if key_char == 'd':
				if len(inv) > 0:
					list = []
					for object in inv:
						list.append(object.name)
					to_drop = menu('Drop Item',list, 30,)
					inv[to_drop].item.drop()
				else:
					message('You have nothing to drop.')

			return 'didnt-take-turn'

def player_move(x, y):
	global fov_recompute
	player.move(x, y)
	fov_recompute = True

def menu(header, options, width,):
	#the player is presented with some options and makes a choice based on graphics
	choice = 0
	new_choice = 0

	#calculate total height for header (after auto-wrap) and one line per option
	header_height = libtcod.console_get_height_rect(mapcon, 0, 0, width, SCREEN_HEIGHT, header)
	height = len(options) + header_height

	#create the virtual console to write the menu on
	window = libtcod.console_new(width, height)

	while True:
		#clear the console ready to draw
		libtcod.console_clear(window)

		#draw the header
		libtcod.console_set_default_foreground(window, libtcod.white)
		libtcod.console_print_rect_ex(window, 0, 0, width, height, libtcod.BKGND_NONE, libtcod.LEFT, header)

		#iterate through and print the options, highlighting the current selection.
		y = header_height
		for index, option in enumerate(options):
			if index == choice:
				text = '>' + option
				libtcod.console_set_default_foreground(window, MENU_HILIGHT)
				libtcod.console_print_ex(window, 0, y, libtcod.BKGND_NONE, libtcod.LEFT, text)
			else:
				text = option
				libtcod.console_set_default_foreground(window, libtcod.white)
				libtcod.console_print_ex(window, 1, y, libtcod.BKGND_NONE, libtcod.LEFT, text)
			y += 1

		#blit the window to the root and flush to render everything.
		libtcod.console_blit(window, 0, 0, width, height, 0, SCREEN_WIDTH/2 - width/2, SCREEN_HEIGHT/2 - height/2)
		libtcod.console_flush()

		
		#up and down arrows change selection
		libtcod.sys_wait_for_event(libtcod.EVENT_KEY_PRESS, key, mouse, True)	
		if key.vk == libtcod.KEY_ENTER:
			return choice
		elif key.vk == libtcod.KEY_UP or key.vk == libtcod.KEY_KP8:
			new_choice = choice - 1
		elif key.vk == libtcod.KEY_DOWN or key.vk == libtcod.KEY_KP2:
			new_choice = choice + 1
		#check that we're not selecting outside the boundary
		if 0 <= new_choice < len(options):
			choice = new_choice

def initialise_fov():
	global fov_recompute, fov_map, light_map
	fov_recompute = True

	#create the FOV map
	fov_map = libtcod.map_new(MAP_WIDTH, MAP_HEIGHT)
	for y in range(MAP_HEIGHT):
		for x in range(MAP_WIDTH):
			libtcod.map_set_properties(fov_map, x, y, not current_area.map[x][y].block_sight, not current_area.map[x][y].blocked)

	#initialise the light maps for the objects
	for object in current_area.objects:
		if object.light_emittance != 0:
			object.light_map = libtcod.map_new(MAP_WIDTH, MAP_HEIGHT)
			for y in range(MAP_HEIGHT):
				for x in range(MAP_WIDTH):
					libtcod.map_set_properties(object.light_map, x, y, not current_area.map[x][y].block_sight, not current_area.map[x][y].blocked)

def render_all():
	global fov_map, fov_recompute
	map = current_area.map

	#define the upper left corner of the visable map
	start_x = player.x - MAP_WINDOW_WIDTH/2
	if start_x < 0:
		start_x = 0
	elif start_x > MAP_WIDTH - MAP_WINDOW_WIDTH:
		start_x = MAP_WIDTH - MAP_WINDOW_WIDTH
	start_y = player.y - MAP_WINDOW_HEIGHT/2
	if start_y < 0:
		start_y = 0
	elif start_y > MAP_HEIGHT - MAP_WINDOW_HEIGHT:
		start_y = MAP_HEIGHT - MAP_WINDOW_HEIGHT
	if fov_recompute:
		#compute the FOV
		fov_recompute = False
		libtcod.map_compute_fov(fov_map, player.x, player.y, TORCH_RADIUS, FOV_LIGHT_WALLS, libtcod.FOV_PERMISSIVE(1))

		#recompute the light maps for each object
		for object in current_area.objects:
			if object.light_emittance > 0:
				libtcod.map_compute_fov(object.light_map, object.x, object.y, object.light_emittance, FOV_LIGHT_WALLS, FOV_ALGO)

		#clear the map console ready to draw
		libtcod.console_clear(mapcon)

		#render the map console
		for y in range(start_y, MAP_HEIGHT):
			for x in range(start_x, MAP_WIDTH):
				#check that each tile is visable and lit
				visible = libtcod.map_is_in_fov(fov_map, x, y)
				lit = is_lit(x, y)
				if visible and lit:
					libtcod.console_set_char_background(mapcon, x, y, map[x][y].color(True), libtcod.BKGND_SET)
					map[x][y].explored = True
				#if not, check whether it is explored.
				elif map[x][y].explored:
					libtcod.console_set_char_background(mapcon, x, y, map[x][y].color(False))

	#draw all the objects in the current area
	for object in current_area.objects:
		object.draw()
	#blit the map to the screen
	libtcod.console_blit(mapcon, start_x, start_y, MAP_WINDOW_WIDTH, MAP_WINDOW_HEIGHT, 0, 0, 0)
	render_panel()

def is_lit(x, y):
	#determines whether a map tile is lit or not.
	for object in current_area.objects:
		if object.light_map:
			if libtcod.map_is_in_fov(object.light_map, x, y):
				return True
	return False

def render_panel():
	global game_msgs
	#render the information panel on the right side of the screen

	#clear the panel ready to render
	libtcod.console_set_default_background(panel, libtcod.black)
	libtcod.console_clear(panel)

	#render the HP bar
	render_bar(1, 1, PANEL_WIDTH - 2, 'HP', player.creature.hp, player.creature.max_hp, libtcod.red, libtcod.dark_red)

	#render the stamina bar
	render_bar(1, 3, PANEL_WIDTH - 2, 'STA', player.creature.stamina, player.creature.max_stamina, libtcod.blue, libtcod.dark_blue)

	#write the game messages
	y = 0
	for line, color in game_msgs:
		libtcod.console_set_default_foreground(panel, color)
		libtcod.console_print_ex(panel, 0, PANEL_HEIGHT - MSG_HEIGHT + y, libtcod.BKGND_NONE, libtcod.LEFT, line)
		y +=1

	libtcod.console_blit(panel, 0, 0, PANEL_WIDTH, PANEL_HEIGHT, 0, MAP_WINDOW_WIDTH, 0)

def render_bar(x,y,total_width, name, value, maximum, bar_color, back_color):
	#render a bar (HP, EXP etc.). First, calculate the width of the bar.
	bar_width = int(float(value) / maximum * total_width)

	#render the background first
	libtcod.console_set_default_background(panel, back_color)
	libtcod.console_rect(panel, x, y, total_width, 1, False, libtcod.BKGND_SCREEN)

	#now render the bar on top
	libtcod.console_set_default_background(panel, bar_color)
	if bar_width > 0:
		libtcod.console_rect(panel, x, y, bar_width, 1, False, libtcod.BKGND_SCREEN)

	#Finally, some text with the values
	libtcod.console_set_default_foreground(panel, libtcod.white)
	libtcod.console_print_ex(panel, x + total_width / 2, y, libtcod.BKGND_NONE, libtcod.CENTER, name + ': ' + str(value) + '/' + str(maximum))

def message(new_msg, color=libtcod.white):
	global game_msgs, panel
	#split the message amongst multiple lines
	new_msg_lines = textwrap.wrap(new_msg, MSG_WIDTH)

	for line in new_msg_lines:
		#if the message log is too long, delete the earliest line
		if len(game_msgs) == MSG_HEIGHT:
			del game_msgs[0]

		game_msgs.append( (line, color) )
		
def new_game():
	global game_msgs, areas, current_area, player, inv, game_state
	game_msgs = []
	areas = {}
	north = Area(0, -1, mapgen.ponyville_north(), 'ponyville north', [])
	current_area = Area(0, 0, mapgen.ponyville(), 'Central Ponyville', [])
	#creature_component = Creature(hp=20, stamina=20, strength=5, dexterity=5, toughness=5)
	player = Object(MAP_WIDTH/2, MAP_HEIGHT/2, 0, 0, 'Player', '@', libtcod.white, light_emittance=12, creature=Creature(20, stamina=20, strength=5, dexterity=5, toughness=5))
	inv = player.inventory
	sword = Object(MAP_WIDTH/2 + 2, MAP_HEIGHT/2, 0, 0, 'Sword', '/', libtcod.darker_red, light_emittance=8, item=Item())
	shield = Object(MAP_WIDTH/2 - 2, MAP_HEIGHT/2, 0, 0, 'Shield', '[', libtcod.darker_blue, item=Item())
	current_area.objects.append(sword)
	current_area.objects.append(shield)
	current_area.objects.append(player)
	initialise_fov()

	game_state = 'playing'

###########
#MAIN LOOP#
###########
def play_game():
	while not libtcod.console_is_window_closed():
		global key, current_area
		mouse = libtcod.Mouse()
		key = libtcod.Key()
		libtcod.sys_check_for_event(libtcod.EVENT_KEY_PRESS, key, mouse)
		current_area = areas[player.X][player.Y]
		render_all()
		for object in current_area.objects:
			object.clear()
		libtcod.console_flush()
		player_action = handle_keys()
		if player_action == 'exit':
			break

def main_menu():
	while not libtcod.console_is_window_closed():
		global key, mouse
		mouse = libtcod.Mouse()
		key = libtcod.Key()
		choice = menu('', ['Play', 'Exit'], 20)
		if choice == 0:
			play_game()
		elif choice == 1:
			break

new_game()
main_menu()
