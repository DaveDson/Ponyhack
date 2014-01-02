#PONYHACK: A pony roguelike.
#Copyright (C) 2013 Anonymous
#
#This is the main program for Ponyhack.
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
import objectgen
import data
import rendering as render

SCREEN_WIDTH = data.SCREEN_WIDTH
SCREEN_HEIGHT = data.SCREEN_HEIGHT
LIMIT_FPS = 20

#Constants for defining various parts of the main screen
MAP_WIDTH = data.MAP_WIDTH
MAP_HEIGHT = data.MAP_HEIGHT


MENU_HILIGHT = libtcod.Color(120, 153, 34)

#Setting custom font. Later this might be changed to allow custom tilesets.
libtcod.console_set_custom_font('arial10x10.png', libtcod.FONT_TYPE_GREYSCALE | libtcod.FONT_LAYOUT_TCOD)

#Initialising the root console
libtcod.console_init_root(SCREEN_WIDTH, SCREEN_HEIGHT, 'Ponyhack', False)




###GLOBAL FUNCTIONS###		

def handle_keys():
	
	global key
#	if key.vk == libtcod.KEY_ENTER and key.lalt:
#		#Alt+Enter: toggle fullscreen
#		libtcod.console_set_fullscreen(not libtcod.console_is_fullscreen())
	if key.vk ==libtcod.KEY_ESCAPE:
		return 'exit' #exit game

	if data.game_state == 'playing':
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

#				for object in data.current_areas.objects:
#					print object.name + ':'
#					if object.inventory and len(object.inventory) > 0:
#						for item in object.inventory:
#							equipped = ''
#							if item.equipment and item.equipment.is_equipped:
#								equipped = ' E'
#							print item.name + equipped
#					else:
#						print object.inventory
#					print ''

				print dice(1, 6)
				print dice(2, 3)
				print dice(3, 6)

			if key_char == 'g':
				#Picking up / [g]rabbing items.
				for object in data.current_areas.objects:
					if object.x == data.player.x and object.y == data.player.y and object != data.player:
						object.item.pick_up(data.player)

			if key_char == 'i':
				#Showing the inventory and using an item.
				if len (data.inv) > 0:
					list = []
					for object in data.inv:
						equipped = ''
						if object.equipment:
							if object.equipment.is_equipped:
								equipped = ' (Equipped)'
						list.append(object.name + equipped)
					to_use = menu('Inventory', list, 30)
					if to_use != None:
						data.inv[to_use].item.use_function()
				else:
					message('You have nothing in your inventory.')

			if key_char == 'd':
				#[d]rop an item.
				if len(data.inv) > 0:
					list = []
					for object in data.inv:
						list.append(object.name)
					to_drop = menu('Drop Item',list, 30,)
					if to_drop != None:
						data.inv[to_drop].item.drop(data.player)
				else:
					message('You have nothing to drop.')

			if key_char == '<':
				#Go up stairs.
				for object in data.current_areas.objects:
					if object.stairs:
						object.stairs.go_up(data.player)

			if key_char == '>':
				#Go up stairs.
				for object in data.current_areas.objects:
					if object.stairs:
						object.stairs.go_down(data.player)

			return 'didnt-take-turn'

def player_move_or_attack(dx, dy):
	
	x = data.player.x + dx
	y = data.player.y + dy

	#try to find a target to attack
	target = None
	for object in data.current_areas.objects:
		if object.creature and object.x == x and object.y == y:
			target = object
			break

	if target is not None:
		data.player.creature.attack(target)

	else:
		data.player.move(dx, dy)
	render.fov_recompute = True

def menu(header, options, width,):
	#The player is presented with some options and makes a choice based on graphics
	choice = 0
	new_choice = 0

	#Calculate total height for header (after auto-wrap) and one line per option
	header_height = libtcod.console_get_height_rect(render.mapcon, 0, 0, width, SCREEN_HEIGHT, header)
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

###Magic Functions###

###Rendering Functions###

		
def new_game():
	render.game_msgs = []
	data.areas = {}
	data.areas[(0, 0, 0)] = mapgen.ponyville()
	data.areas[(0, -1, 0)] = mapgen.ponyville_north()
	data.areas[(0, -1, 1)] = mapgen.dungeon()
	data.current_area = data.areas[(0, 0, 0)]
	data.inv = data.player.inventory
	render.initialise_fov()

	data.game_state = 'playing'

###########
#MAIN LOOP#
###########
def play_game():
	while not libtcod.console_is_window_closed():
		global key
		mouse = libtcod.Mouse()
		key = libtcod.Key()
		libtcod.sys_check_for_event(libtcod.EVENT_KEY_PRESS, key, mouse)
		data.current_areas = data.areas[(data.player.X, data.player.Y, data.player.Z)]
		render.render_all()
		for object in data.current_areas.objects:
			object.clear()
		libtcod.console_flush()
		player_action = handle_keys()
		if player_action == 'exit':
			break #Exit the game
		#Let mobs take thier turn.
		if data.game_state == ('playing') and player_action != 'didnt-take-turn':
			for object in data.current_areas.objects:
				if object.ai:
					object.ai.take_turn()

def main_menu():
	while not libtcod.console_is_window_closed():
		global key, mouse
		mouse = libtcod.Mouse()
		key = libtcod.Key()
		choice = menu('', ['New Game', 'Continue', 'Exit'], 20)
		if choice == 0:
			new_game()
			play_game()
		elif choice == 1:
			try:
				data.areas
			except AttributeError:
				print 'No ongoing game'
			else:
				play_game()
		elif choice == 2:
			break

main_menu()
