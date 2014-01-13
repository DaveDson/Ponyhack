import data
import libtcodpy as libtcod
import rendering as render

def talk(header, options, img):

	render.image(img)

	choice = render.menu(header, options, talk=True)
	return choice

def pinkie_pie():
	img = 'pinkie50x50.png'
	i = talk('Hi there! I\'m Pinkie! What\'s your name?', ['Anon', 'Player', 'Why should I tell you?'], img)

	if i == 0:
		talk('Nice to meet you Anon!', [], img)
		render.message('Pinkie skips away, happily.')

	elif i == 1:
		talk('Tee-hee! That\'s a funny name!', [], img)
		render.message('Pinkie skips away, happily.')

	elif i == 2:
		talk('Why are you such a meanie-pants?', [], img)
		render.message('Pinkie walks away.')
