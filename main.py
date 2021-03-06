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
import talk

SCREEN_WIDTH = data.SCREEN_WIDTH
SCREEN_HEIGHT = data.SCREEN_HEIGHT
LIMIT_FPS = 20

#Constants for defining various parts of the main screen
MAP_WIDTH = data.MAP_WIDTH
MAP_HEIGHT = data.MAP_HEIGHT

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
#				options = multi_objects_menu('pony choice', ['Rarity', 'Applejack', 'Rainbow Dash'], 30)
#				print options
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

				coords = ask_direction('talk')

				for object in data.current_area.objects:
					if object.x == coords[0] and object.y == coords[1] and object.talk_function:
						object.talk_function()

#				print 'Nothing to see here!'
	
			if key_char == 'g':
				#Picking up / [g]rabbing items.
				for object in data.current_areas.objects:
					if object.x == data.player.x and object.y == data.player.y and object.item and object != data.player:
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
					to_use = render.menu('Inventory', list)
					if to_use != None:
						if data.inv[to_use].item.use_function:
							data.inv[to_use].item.use_function()
						else:
							render.message('You can\'t use that item.')
				else:
					render.message('You have nothing in your inventory.')

			if key_char == 'd':
				#[d]rop an item.
				if len(data.inv) > 0:
					list = []
					for object in data.inv:
						equipped = ''
						if object.equipment:
							if object.equipment.is_equipped:
								equipped = ' (Equipped)'
						list.append(object.name + equipped)
					to_drop = render.menu('Drop Item', list)
					if to_drop != None:
						data.inv[to_drop].item.drop(data.player)
				else:
					render.message('You have nothing to drop.')

			#Multiple-item dropping is disabled until I find a consise and robust way of handling it.
#			if key_char == 'D':
#				#[D]rop multiple items.
#				if len(data.inv) > 0:
#					to_drop = multi_objects_menu('Drop Item', data.inv , 30)
#					if to_drop != None:
#						for object in to_drop:
#							object.item.drop(data.player)
#				else:
#					render.message('You have nothing to drop.')

			if key_char == '<':
				#Go up stairs.
				for object in data.current_areas.objects:
					if object.stairs and object.x == data.player.x and object.y == data.player.y:
						object.stairs.go_up(data.player)

			if key_char == '>':
				#Go up stairs.
				for object in data.current_areas.objects:
					if object.stairs and object.x == data.player.x and object.y == data.player.y:
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

def ask_direction(action):
	#Ask the player in which direction they want to perform an action.
	render.info('Which direction do you want to ' + action + '?')

	x = data.player.x
	y = data.player.y

	choice_made = False

	while not libtcod.console_is_window_closed() and x == data.player.x and y == data.player.y :
		libtcod.sys_wait_for_event(libtcod.EVENT_KEY_PRESS, key, mouse, True)
		if key.vk == libtcod.KEY_UP or key.vk == libtcod.KEY_KP8:
			y -= 1
		elif key.vk == libtcod.KEY_DOWN or key.vk == libtcod.KEY_KP2:
			y += 1
		elif key.vk == libtcod.KEY_LEFT or key.vk == libtcod.KEY_KP4:
			x -= 1
		elif key.vk == libtcod.KEY_RIGHT or key.vk == libtcod.KEY_KP6:
			x += 1
		elif key.vk == libtcod.KEY_KP7:
			x -= 1
			y -= 1
		elif key.vk == libtcod.KEY_KP9:
			x += 1
			y -= 1
		elif key.vk == libtcod.KEY_KP1:
			x -= 1
			y += 1
		elif key.vk == libtcod.KEY_KP3:
			x += 1
			y += 1
		elif key.vk == libtcod.KEY_ESCAPE:
			render.message('No direction selected')
			break
	return (x, y)

def multi_objects_menu(header, options, width):
#The player is presented with some options and makes a choice based on graphics
	choice = 0
	new_choice = 0
	selection = []

	#Calculate total height for header (after auto-wrap) and one line per option
	header_height = libtcod.console_get_height_rect(render.mapcon, 0, 0, width, SCREEN_HEIGHT, header)
	height = len(options) + header_height

	#Create the virtual console to write the menu on
	window = libtcod.console_new(width, height)

	while True:
		#Clear the console ready to draw
		libtcod.console_clear(window)

		#Draw the header
		libtcod.console_set_default_foreground(window, libtcod.white)
		libtcod.console_print_rect_ex(window, 0, 0, width, height, libtcod.BKGND_NONE, libtcod.LEFT, header)

		#Iterate through and print the options, highlighting the current selection.
		y = header_height
		for index, option in enumerate(options):
			libtcod.console_set_default_foreground(window, libtcod.white)
			if index == choice:
				libtcod.console_set_default_foreground(window, MENU_HILIGHT)
				libtcod.console_print_ex(window, 0, y, libtcod.BKGND_NONE, libtcod.LEFT, '>')
			if option in selection:
				libtcod.console_set_default_foreground(window, MENU_SELECTED)
			libtcod.console_print_ex(window, 1, y, libtcod.BKGND_NONE, libtcod.LEFT, option.name)
			y += 1

		#Blit the window to the root and flush to render everything.
		libtcod.console_blit(window, 0, 0, width, height, 0, SCREEN_WIDTH/2 - width/2, SCREEN_HEIGHT/2 - height/2)
		libtcod.console_flush()

		
		libtcod.sys_wait_for_event(libtcod.EVENT_KEY_PRESS, key, mouse, True)
		if key.vk == libtcod.KEY_ENTER:
			return selection
		if key.vk == libtcod.KEY_SPACE:
			if options[choice] in selection:
				selection.remove(options[choice])
			else:
				selection.append(options[choice])
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
		global key, mouse
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
	#Load background image.
	img = libtcod.image_load('mmbg.png')

	while not libtcod.console_is_window_closed():
		#Show the bg image.
		libtcod.image_blit_2x(img, 0, 0, 0)
		global key, mouse
		mouse = libtcod.Mouse()
		key = libtcod.Key()
		choice = render.menu('', ['New Game', 'Continue', 'Exit'], width=20)
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
