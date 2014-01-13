#PONYHACK: A pony roguelike.
#Copyright (C) 2013 Anonymous
#
#This is the rendering module for Ponyhack. It is usually imported
#with "import rendering as render", for readability. It handles all
#of the rendering functions.
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
import textwrap
import data

SCREEN_WIDTH = data.SCREEN_WIDTH
SCREEN_HEIGHT = data.SCREEN_HEIGHT
MAP_WIDTH = data.MAP_WIDTH
MAP_HEIGHT = data.MAP_HEIGHT
MAP_WINDOW_WIDTH = 50
MAP_WINDOW_HEIGHT = 50
PANEL_WIDTH = SCREEN_WIDTH - MAP_WINDOW_WIDTH
PANEL_HEIGHT = SCREEN_HEIGHT
MSG_WIDTH = PANEL_WIDTH
MSG_HEIGHT = 20

#Constants for the FOV calculations
FOV_ALGO = libtcod.FOV_SHADOW
TORCH_RADIUS = 71
FOV_LIGHT_WALLS = True

#Colors for the menus.
MENU_HILIGHT = libtcod.Color(120, 153, 34)
MENU_SELECTED = libtcod.yellow

#The panel with various game information
panel = libtcod.console_new(PANEL_WIDTH, PANEL_HEIGHT)

#The virtual console the map will be drawn on before blitting to root
mapcon = libtcod.console_new(MAP_WIDTH, MAP_HEIGHT)

global key, mouse
key = libtcod.Key()
mouse = libtcod.Mouse()

def initialise_fov():
	global fov_recompute
	fov_recompute = True

	#Create the FOV map
	data.fov_map = libtcod.map_new(MAP_WIDTH, MAP_HEIGHT)
	for y in range(MAP_HEIGHT):
		for x in range(MAP_WIDTH):
			libtcod.map_set_properties(data.fov_map, x, y, not data.current_area.map[x][y].block_sight, not data.current_area.map[x][y].blocked)

	#Initialise the light maps for the objects
	for object in data.current_area.objects:
		if object.light_emittance != 0:
			object.light_map = libtcod.map_new(MAP_WIDTH, MAP_HEIGHT)
			for y in range(MAP_HEIGHT):
				for x in range(MAP_WIDTH):
					libtcod.map_set_properties(object.light_map, x, y, not data.current_area.map[x][y].block_sight, not data.current_area.map[x][y].blocked)

def render_all():
	global fov_recompute
	map = data.current_area.map

	#Define the upper left corner of the visable map
	start_x = data.player.x - MAP_WINDOW_WIDTH/2
	if start_x < 0:
		start_x = 0
	elif start_x > MAP_WIDTH - MAP_WINDOW_WIDTH:
		start_x = MAP_WIDTH - MAP_WINDOW_WIDTH
	start_y = data.player.y - MAP_WINDOW_HEIGHT/2
	if start_y < 0:
		start_y = 0
	elif start_y > MAP_HEIGHT - MAP_WINDOW_HEIGHT:
		start_y = MAP_HEIGHT - MAP_WINDOW_HEIGHT
	if fov_recompute:
		#Compute the FOV
		fov_recompute = False
		libtcod.map_compute_fov(data.fov_map, data.player.x, data.player.y, TORCH_RADIUS, FOV_LIGHT_WALLS, FOV_ALGO)

		#Recompute the light maps for each object
		for object in data.current_area.objects:
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
	for object in data.current_area.objects:
		object.draw()
	#Blit the map to the screen
	libtcod.console_blit(mapcon, start_x, start_y, MAP_WINDOW_WIDTH, MAP_WINDOW_HEIGHT, 0, 0, 0)
	render_panel()

def is_visible(x, y):
	#Determines whether a map tile is visible or not.
	#First checking whether the tile is in FOV.
	if libtcod.map_is_in_fov(data.fov_map, x, y):
		#If it is, check that it's lit.
		for object in data.current_area.objects:
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
	render_bar(1, 1, PANEL_WIDTH - 2, 'HP', data.player.creature.hp, data.player.creature.max_hp, libtcod.red, libtcod.dark_red)

	#Render the stamina bar
	render_bar(1, 3, PANEL_WIDTH - 2, 'STA', data.player.creature.stamina, data.player.creature.max_stamina, libtcod.blue, libtcod.dark_blue)

	#Show the player stats
	libtcod.console_set_default_foreground(panel, libtcod.white)
	stats = ['STR: ' + str(data.player.creature.strength), 'TOU: ' + str(data.player.creature.toughness), 'DEX: ' + str(data.player.creature.dexterity)]
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

def info(msg):
	#Function to display temporary information.
	msg_lines = textwrap.wrap(msg, MSG_WIDTH)
	height = len(msg_lines)
	window = libtcod.console_new(MSG_WIDTH, height)
	libtcod.console_set_default_foreground(window, libtcod.white)

	for i, line in enumerate(msg_lines):
		libtcod.console_print_ex(window, 0, i, libtcod.BKGND_NONE, libtcod.LEFT, line)

	libtcod.console_blit(window, 0, 0, MSG_WIDTH, height, 0, MAP_WINDOW_WIDTH, SCREEN_HEIGHT - MSG_HEIGHT - height - 1)
	libtcod.console_flush()

def menu(header, options, width=30, talk=False):
	#The player is presented with some options and makes a choice based on graphics
	choice = 0
	new_choice = 0

	#Calculate total height for header (after auto-wrap) and one line per option
	header_height = libtcod.console_get_height_rect(mapcon, 0, 0, width, SCREEN_HEIGHT, header)
	height = len(options) + header_height

	if talk:
		width = 50
		x = 0
		y = SCREEN_HEIGHT - height

	else:
		x = SCREEN_WIDTH/2 - width/2
		y = SCREEN_HEIGHT/2 - height/2

	#Create the virtual console to write the menu on
	window = libtcod.console_new(width, height)

	while not libtcod.console_is_window_closed():
		#Clear the console ready to draw
		libtcod.console_clear(window)

		#Draw the header
		libtcod.console_set_default_foreground(window, libtcod.white)
		libtcod.console_print_rect_ex(window, 0, 0, width, height, libtcod.BKGND_NONE, libtcod.LEFT, header)

		#Iterate through and print the options, highlighting the current selection.
		i = header_height
		for index, option in enumerate(options):
			libtcod.console_set_default_foreground(window, libtcod.white)

			if index == choice:
				#Draw an arrow and hilight the option.
				libtcod.console_set_default_foreground(window, MENU_HILIGHT)
				libtcod.console_print_ex(window, 0, i, libtcod.BKGND_NONE, libtcod.LEFT, '>')

			libtcod.console_print_ex(window, 1, i, libtcod.BKGND_NONE, libtcod.LEFT, option)
			i += 1

		#Blit the window to the root and flush to render everything.
		libtcod.console_blit(window, 0, 0, width, height, 0, x, y)
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

def image(file_string):
	#Create the image console.
	imagecon = libtcod.console_new(MAP_WINDOW_WIDTH, MAP_WINDOW_HEIGHT)

	img = libtcod.image_load('resources/' + file_string)

	#Set green as the transparent colour.
	#libtcod.console_set_key_color(imagecon, libtcod.Color(0, 255, 0))

	#Render the image and blit it to the root console.
	libtcod.image_blit_rect(img, imagecon, 0, 0, -1, -1, libtcod.BKGND_SET)
	libtcod.console_blit(imagecon, 0, 0, 50, 50, 0, 0, 0)
