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

#Constants for defining various parts of the main screen
MAP_WIDTH = mapgen.MAP_WIDTH
MAP_HEIGHT = mapgen.MAP_HEIGHT
MAP_WINDOW_WIDTH = 50
MAP_WINDOW_HEIGHT = 50
PANEL_WIDTH = SCREEN_WIDTH - MAP_WINDOW_WIDTH
PANEL_HEIGHT = SCREEN_HEIGHT
MSG_WIDTH = PANEL_WIDTH
MSG_HEIGHT = 20

#Constants for the FOV calculations
FOV_ALGO = 0
TORCH_RADIUS = 50
FOV_LIGHT_WALLS = True

MENU_HILIGHT = libtcod.Color(120, 153, 34)

#Setting custom font. Later this might be changed to allow custom tilesets.
libtcod.console_set_custom_font('arial10x10.png', libtcod.FONT_TYPE_GREYSCALE | libtcod.FONT_LAYOUT_TCOD)

#Initialising the root console
libtcod.console_init_root(SCREEN_WIDTH, SCREEN_HEIGHT, 'Ponyhack', False)

#The virtual console the map will be drawn on before blitting to root
mapcon = libtcod.console_new(MAP_WIDTH, MAP_HEIGHT)

#The panel with various game information
panel = libtcod.console_new(PANEL_WIDTH, PANEL_HEIGHT)

class Area:
	#Class for area objects
	def __init__(self, X, Y, map, name, objects, dark=False):
		global areas		
		self.X = X
		self.Y = Y
		self.name = name
		self.map = map
		self.objects = objects
		self.dark = dark
		#Append the new area to the areas dictionary
		if not self.X in areas:
			areas[X] = {}
		areas[X][Y] = self

class Object:
	#Generic class for all map objects
	def __init__(self, x, y, X, Y, name, char, color, blocks=False, inventory=None, light_emittance=0, creature=None, item=None, equipment=None, ai=None):
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
		#Tell any components what owns them
		self.creature = creature
		if self.creature:
			self.creature.owner = self
			if not self.inventory:
				self.inventory = []
		self.item = item
		if self.item:
			self.item.owner = self
		self.equipment = equipment
		if self.equipment:
			self.equipment.owner = self
			#Equipment objects must be items and equippable.
			self.item = Item(use_function=self.equipment.toggle_equip)
			self.item.owner = self
		self.ai = ai
		if self.ai:
			self.ai.owner = self

	def move(self, dx, dy):
		x = self.x + dx
		y = self.y + dy
		#Change the map area if going off screen
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
    #Otherwise check whether the tile is blocked and if not, move to it.
		elif not current_area.map[x][y].blocked:
			self.x = x
			self.y = y

	def change_area(self, dX, dY):
		#Changing the area that an object exists in.
		global current_area
		X = self.X + dX
		Y = self.Y + dY
		if X in areas:
			if Y in areas[X]:
				areas[X][Y].objects.append(self)
				areas[self.X][self.Y].objects.remove(self)
				self.X = X
				self.Y = Y
				current_area = areas[X][Y]
				initialise_fov()
				return True
		return False

	def distance(self, x, y):
		#return the distance to some coordinates
		return math.sqrt((x - self.x) ** 2 + (y - self.y) ** 2)

	def distance_to(self, other):
		#return the distance to an object
		dx = other.x - self.x
		dy = other.y - self.y
		return math.sqrt(dx ** 2 + dy ** 2)

	def draw(self):
		#Drawing the object to the map.
		if is_visible(self.x, self.y):
			libtcod.console_set_default_foreground(mapcon, self.color)
			libtcod.console_put_char(mapcon, self.x, self.y, self.char, libtcod.BKGND_NONE)

	def clear(self):
		#Clearing the object from the map.
		libtcod.console_put_char(mapcon, self.x, self.y, ' ', libtcod.BKGND_NONE)

class Creature:
	#Component for all creature objects.
	def __init__(self, hp, stamina, strength, dexterity, toughness, death_function=None):
		self.base_max_hp = hp
		self.hp = hp
		self.base_max_stamina = stamina
		self.stamina = stamina
		self.base_strength = strength
		self.base_dexterity = dexterity
		self.base_toughness = toughness
		self.death_function = death_function

	@property
	def max_hp(self):
		bonus = sum(equipment.max_hp_bonus for equipment in get_all_equipped(self.owner))
		return self.base_max_hp + bonus

	@property
	def max_stamina(self):
		bonus = sum(equipment.max_stamina_bonus for equipment in get_all_equipped(self.owner))
		return self.base_max_stamina + bonus

	@property
	def strength(self):
		bonus = sum(equipment.strength_bonus for equipment in get_all_equipped(self.owner))
		return self.base_strength + bonus

	@property
	def dexterity(self):
		bonus = sum(equipment.dexterity_bonus for equipment in get_all_equipped(self.owner))
		return self.base_dexterity + bonus

	@property
	def toughness(self):
		bonus = sum(equipment.toughness_bonus for equipment in get_all_equipped(self.owner))
		return self.base_toughness + bonus

	def attack(self, target):
		damage = self.strength - target.creature.toughness

		if damage > 0:
			message('The ' + self.owner.name + ' attacks the ' + target.name + ' for ' + str(damage) + ' damage.')
			target.creature.take_damage(damage)
		else:
			message('The ' + self.owner.name + ' attacks the ' + target.name + ' but the blow glances away!')

	def take_damage(self, damage):
		if damage > 0:
			self.hp -= damage
			if self.hp <= 0 and self.death_function != None:
				self.death_function(self.owner)

	def heal(self, amount):
		self.hp += amount
		if self.hp > self.max_hp:
			self.hp = self.max_hp

class Item:
	#Component for all item objects.
	def __init__(self, use_function=None):
		self.use_function = use_function

	def pick_up(self, target):
		#Picking up the object. Currently only the player can do this, but eventually NPCs will be able to too.
#		inv.append(self.owner)
#		current_area.objects.remove(self.owner)
		target.inventory.append(self.owner)
		current_area.objects.remove(self.owner)
		message(player.name + ' picked up a ' + self.owner.name + '.', color=libtcod.desaturated_green)

	def drop(self, target):
		self.owner.x = target.x
		self.owner.y = target.y
		self.owner.X = target.X
		self.owner.Y = target.Y
		if self.owner.equipment:
			self.owner.equipment.dequip()
		current_area.objects.append(self.owner)
		target.inventory.remove(self.owner)
		message('You dropped a ' + self.owner.name + '.', color=libtcod.desaturated_red)

class Equipment:
	#Component for equippable items.
	def __init__(self, max_hp_bonus=0, max_stamina_bonus=0 , strength_bonus=0, toughness_bonus=0, dexterity_bonus=0, is_equipped = False):
		self.max_hp_bonus = max_hp_bonus
		self.max_stamina_bonus = max_stamina_bonus
		self.strength_bonus = strength_bonus
		self.toughness_bonus = toughness_bonus
		self.dexterity_bonus = dexterity_bonus
		self.is_equipped = is_equipped

	def equip(self):
		self.is_equipped = True
		message('You equipped the ' + self.owner.name)

	def dequip(self):
		self.is_equipped = False
		message('You dequipped the ' + self.owner.name)

	def toggle_equip(self):
		if self.is_equipped:
			self.dequip()
		else:
			self.equip()

##AI classes##

class StaticMonster:
	
	def take_turn(self):
		if self.owner.distance_to(player) < 2:
			self.owner.creature.attack(player)
		
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
			player_move_or_attack(0, -1)
		elif key.vk == libtcod.KEY_DOWN or key.vk == libtcod.KEY_KP2:
			player_move_or_attack(0, 1)
		elif key.vk == libtcod.KEY_LEFT or key.vk == libtcod.KEY_KP4:
			player_move_or_attack(-1, 0)
		elif key.vk == libtcod.KEY_RIGHT or key.vk == libtcod.KEY_KP6:
			player_move_or_attack(1, 0)
		elif key.vk == libtcod.KEY_KP7:
			player_move_or_attack(-1, -1)
		elif key.vk == libtcod.KEY_KP9:
			player_move_or_attack(1, -1)
		elif key.vk == libtcod.KEY_KP1:
			player_move_or_attack(-1, 1)
		elif key.vk == libtcod.KEY_KP3:
			player_move_or_attack(1, 1)
		elif key.vk == libtcod.KEY_KP5:
			pass #wait a turn
		else:
			#test for other keys
			key_char = chr(key.c)

			if key_char == 't':
				#[t]est key, currently testing the menu function.
#				option = menu('pony choice', ['Rarity', 'Applejack', 'Rainbow Dash'], 30)
#				if option == 0:
#					print 'Generosity'
#				elif option == 1:
#					print 'Honesty'
#				elif option == 2:
#					print 'Loyalty'
#				else: print 'menu error'
				for object in current_area.objects:
					print object.name + ':'
					if object.inventory and len(object.inventory) > 0:
						for item in object.inventory:
							equipped = ''
							if item.equipment and item.equipment.is_equipped:
								equipped = ' E'
							print item.name + equipped
					else:
						print object.inventory
					print ''

			if key_char == 'g':
				#Picking up / [g]rabbing items.
				for object in current_area.objects:
					if object.x == player.x and object.y == player.y and object != player:
						object.item.pick_up(player)

			if key_char == 'i':
				#Showing the inventory and using an item.
				if len (inv) > 0:
					list = []
					for object in inv:
						equipped = ''
						if object.equipment:
							if object.equipment.is_equipped:
								equipped = ' (Equipped)'
						list.append(object.name + equipped)
					to_use = menu('Inventory', list, 30)
					if to_use != None:
						inv[to_use].item.use_function()
				else:
					message('You have nothing in your inventory.')

			if key_char == 'd':
				#[d]rop an item.
				if len(inv) > 0:
					list = []
					for object in inv:
						list.append(object.name)
					to_drop = menu('Drop Item',list, 30,)
					if to_drop != None:
						inv[to_drop].item.drop(player)
				else:
					message('You have nothing to drop.')

			return 'didnt-take-turn'

def player_move_or_attack(dx, dy):
	global fov_recompute
	
	x = player.x + dx
	y = player.y + dy

	#try to find a target to attack
	target = None
	for object in current_area.objects:
		if object.creature and object.x == x and object.y == y:
			target = object
			break

	if target is not None:
		player.creature.attack(target)

	else:
		player.move(dx, dy)
		fov_recompute = True

def get_all_equipped(obj): #Returns a list of equipped items
	equipped_list = []
	if len(obj.inventory) > 0:
		for item in obj.inventory:
			if item.equipment and item.equipment.is_equipped:
				equipped_list.append(item.equipment)
		return equipped_list
	else:
		return []

def menu(header, options, width,):
	#The player is presented with some options and makes a choice based on graphics
	choice = 0
	new_choice = 0

	#Calculate total height for header (after auto-wrap) and one line per option
	header_height = libtcod.console_get_height_rect(mapcon, 0, 0, width, SCREEN_HEIGHT, header)
	height = len(options) + header_height

	#Create the virtual console to write the menu on
	window = libtcod.console_new(width, height)

	while True:
		#Clear the console ready to draw
		libtcod.console_clear(window)

		#Craw the header
		libtcod.console_set_default_foreground(window, libtcod.white)
		libtcod.console_print_rect_ex(window, 0, 0, width, height, libtcod.BKGND_NONE, libtcod.LEFT, header)

		#Iterate through and print the options, highlighting the current selection.
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

		#Blit the window to the root and flush to render everything.
		libtcod.console_blit(window, 0, 0, width, height, 0, SCREEN_WIDTH/2 - width/2, SCREEN_HEIGHT/2 - height/2)
		libtcod.console_flush()

		
		libtcod.sys_wait_for_event(libtcod.EVENT_KEY_PRESS, key, mouse, True)
		if key.vk == libtcod.KEY_ENTER:
			return choice
		if key.vk == libtcod.KEY_ESCAPE:
			return None
		#Up and down arrows change selection
		elif key.vk == libtcod.KEY_UP or key.vk == libtcod.KEY_KP8:
			new_choice = choice - 1
		elif key.vk == libtcod.KEY_DOWN or key.vk == libtcod.KEY_KP2:
			new_choice = choice + 1
		#Check that we're not selecting outside the boundary
		if 0 <= new_choice < len(options):
			choice = new_choice

def monster_death(monster):
	#Death function for a generic monster.
	monster.char = '%'
	monster.color = libtcod.dark_red
	monster.blocks = False
	monster.creature = None
	monster.item = Item()
	monster.ai = None
	monster.item.owner = monster
	message('The ' + monster.name +' has died!')
	monster.name = 'remains of ' + monster.name

def initialise_fov():
	global fov_recompute, fov_map, light_map
	fov_recompute = True

	#Create the FOV map
	fov_map = libtcod.map_new(MAP_WIDTH, MAP_HEIGHT)
	for y in range(MAP_HEIGHT):
		for x in range(MAP_WIDTH):
			libtcod.map_set_properties(fov_map, x, y, not current_area.map[x][y].block_sight, not current_area.map[x][y].blocked)

	#Initialise the light maps for the objects
	for object in current_area.objects:
		if object.light_emittance != 0:
			object.light_map = libtcod.map_new(MAP_WIDTH, MAP_HEIGHT)
			for y in range(MAP_HEIGHT):
				for x in range(MAP_WIDTH):
					libtcod.map_set_properties(object.light_map, x, y, not current_area.map[x][y].block_sight, not current_area.map[x][y].blocked)

def render_all():
	global fov_map, fov_recompute
	map = current_area.map

	#Define the upper left corner of the visable map
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
		#Compute the FOV
		fov_recompute = False
		libtcod.map_compute_fov(fov_map, player.x, player.y, TORCH_RADIUS, FOV_LIGHT_WALLS, libtcod.FOV_PERMISSIVE(1))

		#Recompute the light maps for each object
		for object in current_area.objects:
			if object.light_emittance > 0:
				libtcod.map_compute_fov(object.light_map, object.x, object.y, object.light_emittance, FOV_LIGHT_WALLS, FOV_ALGO)

		#Clear the map console ready to draw
		libtcod.console_clear(mapcon)

		#Render the map console
		for y in range(start_y, MAP_HEIGHT):
			for x in range(start_x, MAP_WIDTH):
				#Check that each tile is visable and lit
				visible = is_visible(x, y)
				if visible:
					libtcod.console_set_char_background(mapcon, x, y, map[x][y].color(True), libtcod.BKGND_SET)
					map[x][y].explored = True
				#If not, check whether it is explored.
				elif map[x][y].explored:
					libtcod.console_set_char_background(mapcon, x, y, map[x][y].color(False))

	#Draw all the objects in the current area
	for object in current_area.objects:
		object.draw()
	#Blit the map to the screen
	libtcod.console_blit(mapcon, start_x, start_y, MAP_WINDOW_WIDTH, MAP_WINDOW_HEIGHT, 0, 0, 0)
	render_panel()

def is_visible(x, y):
	#Determines whether a map tile is lit or not.
	if libtcod.map_is_in_fov(fov_map, x, y):
		for object in current_area.objects:
			if object.light_map:
				if libtcod.map_is_in_fov(object.light_map, x, y):
					return True
	return False

def render_panel():
	global game_msgs
	#Render the information panel on the right side of the screen

	#Clear the panel ready to render
	libtcod.console_set_default_background(panel, libtcod.black)
	libtcod.console_clear(panel)

	#Render the HP bar
	render_bar(1, 1, PANEL_WIDTH - 2, 'HP', player.creature.hp, player.creature.max_hp, libtcod.red, libtcod.dark_red)

	#Render the stamina bar
	render_bar(1, 3, PANEL_WIDTH - 2, 'STA', player.creature.stamina, player.creature.max_stamina, libtcod.blue, libtcod.dark_blue)

	#Show the player stats
	libtcod.console_set_default_foreground(panel, libtcod.white)
	stats = ['STR: ' + str(player.creature.strength), 'TOU: ' + str(player.creature.toughness), 'DEX: ' + str(player.creature.dexterity)]
	y = 5
	for line in stats:
		libtcod.console_print_ex(panel, 0, y, libtcod.BKGND_NONE, libtcod.LEFT, line)
		y += 1

	#Write the game messages
	y = 0
	for line, color in game_msgs:
		libtcod.console_set_default_foreground(panel, color)
		libtcod.console_print_ex(panel, 0, PANEL_HEIGHT - MSG_HEIGHT + y, libtcod.BKGND_NONE, libtcod.LEFT, line)
		y += 1

	libtcod.console_blit(panel, 0, 0, PANEL_WIDTH, PANEL_HEIGHT, 0, MAP_WINDOW_WIDTH, 0)

def render_bar(x,y,total_width, name, value, maximum, bar_color, back_color):
	#Render a bar (HP, EXP etc.). First, calculate the width of the bar.
	bar_width = int(float(value) / maximum * total_width)

	#Render the background first
	libtcod.console_set_default_background(panel, back_color)
	libtcod.console_rect(panel, x, y, total_width, 1, False, libtcod.BKGND_SCREEN)

	#Now render the bar on top
	libtcod.console_set_default_background(panel, bar_color)
	if bar_width > 0:
		libtcod.console_rect(panel, x, y, bar_width, 1, False, libtcod.BKGND_SCREEN)

	#Finally, some text with the values
	libtcod.console_set_default_foreground(panel, libtcod.white)
	libtcod.console_print_ex(panel, x + total_width / 2, y, libtcod.BKGND_NONE, libtcod.CENTER, name + ': ' + str(value) + '/' + str(maximum))

def message(new_msg, color=libtcod.white):
	global game_msgs, panel
	#Split the message amongst multiple lines
	new_msg_lines = textwrap.wrap(new_msg, MSG_WIDTH)

	for line in new_msg_lines:
		#If the message log is too long, delete the earliest line
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
	player = Object(MAP_WIDTH/2, MAP_HEIGHT/2, 0, 0, 'Player', '@', libtcod.white, light_emittance=12, creature=Creature(20, stamina=20, strength=5, dexterity=5, toughness=3))
	practice_dummy = Object(MAP_WIDTH/2, MAP_HEIGHT/2 + 2, 0, 0, 'Practice Dummy', 'd', libtcod.red, creature=Creature(hp=10, stamina=10, strength=5, dexterity=5, toughness=2, death_function=monster_death), ai=StaticMonster())
	inv = player.inventory
	sword = Object(MAP_WIDTH/2 + 2, MAP_HEIGHT/2, 0, 0, 'Sword', '/', libtcod.darker_red, light_emittance=8, equipment=Equipment(strength_bonus=2))
	shield = Object(MAP_WIDTH/2 - 2, MAP_HEIGHT/2, 0, 0, 'Shield', '[', libtcod.darker_blue, equipment=Equipment(toughness_bonus=3))
	current_area.objects.append(sword)
	current_area.objects.append(shield)
	current_area.objects.append(player)
	current_area.objects.append(practice_dummy)
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
			break #Exit the game
		#Let monsters take thier turn.
		if game_state == 'playing' and player_action != 'didnt-take-turn':
			for object in current_area.objects:
				if object.ai:
					object.ai.take_turn()

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
