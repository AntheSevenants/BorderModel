# Local imports
from mesa import Agent, Model
from mesa.time import RandomActivation
from mesa.space import MultiGrid

class BorderAgent(Agent):
	def __init__(self, unique_id, model):
		super().__init__(unique_id, model)
		self.sound = 1
		self.sound_repository = []
		self.adopt_modifier = 1
		self.travel_urge = 1
		self.ethnocentrism = 1
		self.media_receptiveness = 1
				
	def step(self):
		self.move() # TODO: repeat this a number of times probably -- refer to Stanford & Kenny (p. 127)
		self.speak()
		
	def move(self):
		# TODO: use Moore or not? (Moore = diagonal -- currently using Von Neumann)
		possible_steps = self.model.grid.get_neighborhood(self.pos, moore=False, include_center=True)
		new_position = self.random.choice(possible_steps)
		self.model.grid.move_agent(self, new_position)
	
	def speak(self):
		# For the neighbours we *do* want to be using the Moore specification, and also the center (there could be someone we share the space with)
		neighbourhood = self.model.grid.get_neighborhood(self.pos, moore=True, include_center=True)
		neighbours = self.model.grid.get_cell_list_contents(neighbourhood)
		if len(neighbours) > 1:
			for neighbour in neighbours:
				# TODO: speak!
				pass

class BorderModel(Model):
	def __init__(self, num_agents, width, height):
		self.num_agents = num_agents
		self.grid = MultiGrid(width, height, False)
		self.schedule = RandomActivation(self)
		self.running = True
		
		# Create agents
		for i in range(self.num_agents):
			agent = BorderAgent(i, self)
			# Add agent to the scheduler
			self.schedule.add(agent)
			
			# Place the newly created agent on the grid
			x = self.random.randrange(self.grid.width)
			y = self.random.randrange(self.grid.height)
			self.grid.place_agent(agent, (x, y))

		self.init_influence_spheres()
		print(self.influence_spheres[0].coordinates)

	def init_influence_spheres(self):
		self.influence_spheres = []

		# Create influence spheres
		spheres = [ { "x": 50,
					  "y": 50,
					  "radius": 10 } ]
		for sphere in spheres:
			influence_sphere = InfluenceCircle(sphere["x"], sphere["y"], sphere["radius"])
			self.influence_spheres.append(influence_sphere)

	def step(self):
		self.schedule.step()

# http://rosettacode.org/wiki/Bitmap/Midpoint_circle_algorithm#Python
class InfluenceCircle():
	def __init__(self, x0, y0, radius):
		self.coordinates = []

		f = 1 - radius
		ddf_x = 1
		ddf_y = -2 * radius
		x = 0
		y = radius
		self.add_coords(x0, y0 + radius)
		self.add_coords(x0, y0 - radius)
		self.add_coords(x0 + radius, y0)
		self.add_coords(x0 - radius, y0)
	
		while x < y:
			if f >= 0: 
				y -= 1
				ddf_y += 2
				f += ddf_y
			x += 1
			ddf_x += 2
			f += ddf_x    
			self.add_coords(x0 + x, y0 + y)
			self.add_coords(x0 - x, y0 + y)
			self.add_coords(x0 + x, y0 - y)
			self.add_coords(x0 - x, y0 - y)
			self.add_coords(x0 + y, y0 + x)
			self.add_coords(x0 - y, y0 + x)
			self.add_coords(x0 + y, y0 - x)
			self.add_coords(x0 - y, y0 - x)

	def add_coords(self, x, y):
		self.coordinates.append([x, y])