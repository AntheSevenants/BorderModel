# Local imports
import math

from mesa import Agent, Model
from mesa.time import RandomActivation
from mesa.space import MultiGrid

class BorderAgent(Agent):
	def __init__(self, unique_id, influence_sphere, model):
		super().__init__(unique_id, model)
		self.influence_sphere = influence_sphere
		
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
		
		self.init_influence_spheres()
		self.init_agents()
		#print(self.influence_spheres[0].coordinates)

	def init_influence_spheres(self):
		self.influence_spheres = []

		# Create influence spheres
		spheres = [ { "x": 50,
					  "y": 50,
					  "radius": 10,
					  "population": 10 },
					{ "x": 20,
					  "y": 20,
					  "radius": 15,
					  "population": 50 },
					{ "x": 70,
					  "y": 80,
					  "radius": 7,
					  "population": 5 } ]

		for sphere in spheres:
			influence_sphere = InfluenceCircle(sphere["x"], sphere["y"], sphere["radius"],
											   sphere["population"])
			self.influence_spheres.append(influence_sphere)

	def init_agents(self):
		# Create agents based on population count in the influence spheres
		agent_no = 0
		for influence_sphere in self.influence_spheres:
			# Create agents
			for i in range(influence_sphere.population):
				agent = BorderAgent(agent_no, influence_sphere, self)
				# Add agent to the scheduler
				self.schedule.add(agent)
				
				# Place the newly created agent on the grid
				location = self.random.choice(influence_sphere.coordinates)
				self.grid.place_agent(agent, (location[0], location[1]))

				agent_no += 1

	def step(self):
		self.schedule.step()

# http://rosettacode.org/wiki/Bitmap/Midpoint_circle_algorithm#Python
class InfluenceCircle():
	def __init__(self, x0, y0, radius, population):
		self.x = x0
		self.y = y0
		self.radius = radius
		self.population = population

		self.coordinates = []

		for j in range(x0 - radius, x0 + radius + 1):
			for k in range(y0 - radius, y0 + radius + 1):
				if self.distance({ "x": j, "y": k }, { "x": x0, "y": y0 }) <= radius:
					self.coordinates.append([ j, k ])

	def distance(self, p1, p2):
		dx = p2["x"] - p1["x"];
		dx *= dx;
		dy = p2["y"] - p1["y"];
		dy *= dy;
		return math.ceil(math.sqrt(dx + dy));

	def add_coords(self, x, y):
		self.coordinates.append([x, y])