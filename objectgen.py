#PONYHACK: A pony roguelike.
#Copyright (C) 2013 Anonymous
#
#This is the object generation module for ponyhack. It is responsible
#for generating all the obgects on the map.
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
import rendering as render
import talk

MAP_WIDTH = data.MAP_WIDTH
MAP_HEIGHT = data.MAP_HEIGHT

class Object:
	#Generic class for all map objects
	def __init__(self, x, y, X, Y, Z, name, char, color, blocks=False, inventory=None, light_emittance=0,  talk_function=None, creature=None, item=None, equipment=None, ai=None, stairs=None):
		self.x = x
		self.y = y
		self.X = X
		self.Y = Y
		self.Z = Z
		self.name = name
		self.char = char
		self.color = color
		self.blocks = blocks
		self.inventory = inventory
		self.light_emittance = light_emittance
		self.light_map = None
		self.talk_function = talk_function
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
		self.stairs = stairs
		if self.stairs:
			self.stairs.owner = self

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
		elif not is_blocked(x, y):
			self.x = x
			self.y = y

	def change_area(self, dX, dY, dZ=0):
		#Changing the area that an object exists in.
		X = self.X + dX
		Y = self.Y + dY
		Z = self.Z + dZ
		if (X, Y, Z) in data.areas:
			data.areas[(X, Y, Z)].objects.append(self)
			data.areas[(self.X, self.Y, self.Z)].objects.remove(self)
			self.X = X
			self.Y = Y
			self.Z = Z
			if self == data.player:
				data.current_area = data.areas[(X, Y, Z)]
				render.initialise_fov()
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
		if self.is_visible():
			libtcod.console_set_default_foreground(render.mapcon, self.color)
			libtcod.console_put_char(render.mapcon, self.x, self.y, self.char, libtcod.BKGND_NONE)

	def is_visible(self):
		if libtcod.map_is_in_fov(data.fov_map, self.x, self.y):
			#If it is, check that it's lit.
			for object in data.current_area.objects:
				if object.light_map:
					if libtcod.map_is_in_fov(object.light_map, self.x, self.y):
						return True
		return False

	def clear(self):
		#Clearing the object from the map.
		libtcod.console_put_char(render.mapcon, self.x, self.y, ' ', libtcod.BKGND_NONE)

	def send_to_back(self):
		data.current_area.objects.remove(self)
		data.current_area.objects.insert(0, self)

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

	#The various properties that can be altered by equipment/
	@property
	def max_hp(self):
		bonus = sum(equipment.max_hp_bonus for equipment in self.get_all_equipped())
		return self.base_max_hp + bonus

	@property
	def max_stamina(self):
		bonus = sum(equipment.max_stamina_bonus for equipment in self.get_all_equipped())
		return self.base_max_stamina + bonus

	@property
	def strength(self):
		bonus = sum(equipment.strength_bonus for equipment in self.get_all_equipped())
		return self.base_strength + bonus

	@property
	def dexterity(self):
		bonus = sum(equipment.dexterity_bonus for equipment in self.get_all_equipped())
		return self.base_dexterity + bonus

	@property
	def toughness(self):
		bonus = sum(equipment.toughness_bonus for equipment in self.get_all_equipped())
		return self.base_toughness + bonus

	def get_all_equipped(self): 
		#Returns a list of equipped items.
		equipped_list = []
		if len(self.owner.inventory) > 0:
			for item in self.owner.inventory:
				if item.equipment and item.equipment.is_equipped:
					equipped_list.append(item.equipment)
			return equipped_list
		else:
			return []

	def attack(self, target):
		if self.to_hit(target):
			damage = self.strength - target.creature.toughness - 2 + dice(2, 3)

			if damage > 0:
				#Make the target take damage.
				render.message('The ' + self.owner.name + ' attacks the ' + target.name + ' for ' + str(damage) + ' damage.', libtcod.light_green)
				target.creature.take_damage(damage)
			else:
				#Message to let the player know that no damage was done.
				render.message('The ' + self.owner.name + ' attacks the ' + target.name + ' but the blow glances away!', libtcod.light_red)
		else:
			#Message that the attack missed.
			render.message('The ' + self.owner.name + ' attacks the ' + target.name + ' but the shot is parried', libtcod.red)

	def to_hit(self, target):
		#Determines whether the owner can hit a target, based on the dexterity of both objects.
		x = self.dexterity - target.creature.dexterity - 3 + dice(1, 6)
		if x > 0:
			return True
		else:
			return False

	def take_damage(self, damage):
		if damage > 0:
			self.hp -= damage
			if self.hp <= 0 and self.death_function != None:
				self.death_function(self.owner)
				self.owner.send_to_back()

	def heal(self, amount):
		self.hp += amount
		if self.hp > self.max_hp:
			self.hp = self.max_hp

class Item:
	#Component for all item objects.
	def __init__(self, use_function=None):
		self.use_function = use_function

	def pick_up(self, target):
		#Picking up the object.
		target.inventory.append(self.owner)
		data.current_area.objects.remove(self.owner)
		render.message(target.name + ' picked up a ' + self.owner.name + '.', color=libtcod.desaturated_green)

	def drop(self, target):
		self.owner.x = target.x
		self.owner.y = target.y
		self.owner.X = target.X
		self.owner.Y = target.Y
		if self.owner.equipment and self.owner.equipment.is_equipped:
			self.owner.equipment.dequip()
		data.current_area.objects.append(self.owner)
		target.inventory.remove(self.owner)
		self.owner.send_to_back()
		if self.owner.light_map:
			render.initialise_fov()
		render.message('You dropped a ' + self.owner.name + '.', color=libtcod.desaturated_red)

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
		render.message('You equipped the ' + self.owner.name)

	def dequip(self):
		self.is_equipped = False
		render.message('You dequipped the ' + self.owner.name)

	def toggle_equip(self):
		if self.is_equipped:
			self.dequip()
		else:
			self.equip()

class Stairs:
	def __init__(self, direction):
		self.direction = direction
	
	def go_up(self, target):
		if self.direction == 'up':
			target.change_area(0, 0, dZ=-1)

	def go_down(self, target):
		if self.direction == 'down':
			target.change_area(0, 0, dZ=1)
	

##AI classes##

class StaticMob:
	
	def take_turn(self):
		if self.owner.distance_to(data.player) < 2:
			self.owner.creature.attack(data.player)

##Death Functions##

def mob_death(mob):
	#Death function for a generic mob.
	mob.char = '%'
	mob.color = libtcod.dark_red
	mob.blocks = False
	mob.creature = None
	mob.item = Item()
	mob.ai = None
	mob.item.owner = mob
	render.message('The ' + mob.name +' has died!')
	mob.name = 'Remains of ' + mob.name

def player_death(mob):
	#Death function for the player.
	#This function ends the game.
	mob.char = '%'
	mob.color = libtcod.dark_red
	mob.blocks = False
	render.message('You have died!', libtcod.dark_red)
	mob.name = 'Remains of ' + mob.name
	data.game_state = 'dead'

##Randomising functions##

def dice(num, sides):
	#Roll 'num' dice with 'sides' sides.
	x = 0
	for i in range(num):
		x += libtcod.random_get_int(0, 1, sides)
	return x

def is_blocked(x, y):
	#Function to determine whether a map tile is blocked or not.
	if data.current_area.map[x][y].blocked:
		return True
	for object in data.current_area.objects:
		if object.blocks and object.x == x and object.y == y:
			return True
	return False

###GENERATION FUNCTIONS###

def gen_player():
	creature_component = Creature(20, stamina=20, strength=5, dexterity=5, toughness=3, death_function=player_death)
	return Object(MAP_WIDTH/2, MAP_HEIGHT/2, 0, 0, 0, 'Player', '@', libtcod.white, light_emittance=12, creature=creature_component)

def gen_dummy():
	creature_component = Creature(hp=10, stamina=10, strength=5, dexterity=5, toughness=2, death_function=mob_death)
	ai_component = StaticMob()
	return Object(MAP_WIDTH/2, MAP_HEIGHT/2 + 2, 0, 0, 0, 'Practice Dummy', 'd', libtcod.red, creature=creature_component , ai=ai_component)

def gen_pinkie():
	creature_component = Creature(hp=10, stamina=10, strength=5, dexterity=5, toughness=2, death_function=mob_death)
	return Object(MAP_WIDTH/2, MAP_HEIGHT/2 - 2, 0, 0, 0, 'Pinkie Pie', 'p', libtcod.pink, talk_function=talk.pinkie_pie, creature=creature_component)

def gen_sword():
	equipment_component = Equipment(strength_bonus=2)
	return Object(MAP_WIDTH/2 + 2, MAP_HEIGHT/2, 0, 0, 0, 'Sword', '/', libtcod.darker_red, light_emittance=8, equipment=equipment_component)

def gen_shield():
	equipment_component = Equipment(toughness_bonus=3)
	return Object(MAP_WIDTH/2 - 2, MAP_HEIGHT/2, 0, 0, 0, 'Shield', '[', libtcod.darker_blue, equipment=equipment_component)

def gen_up_stairs():
	return Object(MAP_WIDTH/2, MAP_HEIGHT/2, 0, -1, 1, 'Up stairs', '<', libtcod.white, stairs=Stairs('up'))

def gen_down_stairs():
	return Object(MAP_WIDTH/2, MAP_HEIGHT/2, 0, -1, 0, 'Down stairs', '>', libtcod.white, stairs=Stairs('down'))
