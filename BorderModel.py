# Local imports
import math

from mesa import Agent, Model
from mesa.time import RandomActivation
from mesa.space import MultiGrid
from mesa.datacollection import DataCollector

def compute_population(model, group):
	count = 0
	if group == "home":
		for agent in model.schedule.agents:
			if not agent.travel_sphere or agent.travel_sphere == agent.influence_sphere:
				count += 1
				continue
	elif group == "travelling":
		for agent in model.schedule.agents:
			if agent.travel_sphere and agent.travel_sphere != agent.influence_sphere:
				count += 1
				continue
	elif group == "visiting":
		for agent in model.schedule.agents:
			if agent.travel_sphere and agent.travel_arrived:
				count += 1
				continue

	return count

def distance_between_points(x0, x1, y0, y1):
	return math.hypot(x0 - x1, 
					  y0 - y1)

class BorderAgent(Agent):
	def __init__(self, unique_id, influence_sphere, model):
		super().__init__(unique_id, model)
		self.influence_sphere = influence_sphere
		self.model = model

		self.sound = 1
		self.sound_repository = []
		self.adopt_modifier = 1
		self.travel_urge = 1
		self.ethnocentrism = 1
		self.media_receptiveness = 1

		# Is the agent travelling?
		self.travel_sphere = False
		self.travel_arrived = False
				
	def step(self):
		self.travel_chance_time()
		self.move() # TODO: repeat this a number of times probably -- refer to Stanford & Kenny (p. 127)
		self.speak()
		
	def travel_chance_time(self):
		# Don't initiate a new travel target if already travelling
		if self.travel_sphere:
			return

		# Check if travel chance time happens (when number is lower than the model threshold)
		if self.model.random.random() <= self.model.travel_chance:
			# Travel chance time is happening
			# TODO: better decision making on which sphere to travel to
			# Current implementation = random influence sphere
			while True:
				travel_sphere = self.random.choice(self.model.influence_spheres)
				# Keep picking a travel sphere until we've found one that isn't our home sphere
				# I don't know whether this is more efficient than removing the home sphere from 
				# a deepcopy of the list of all spheres but I assume this is better
				if travel_sphere != self.influence_sphere:
					self.travel_sphere = travel_sphere # set current travel target to target travel sphere
					break

	def move(self):
		# TODO: use Moore or not? (Moore = diagonal -- currently using Von Neumann)
		possible_steps = self.model.grid.get_neighborhood(self.pos, moore=False, include_center=True)
		
		# If not travelling, wander
		if not self.travel_sphere:
			# Every once in a while, an agent should attempt to return home
			if self.model.random.random() <= self.model.home_chance:
				new_position = self.home(possible_steps)
			else:
				new_position = self.wander(possible_steps)
		# If travelling, check if we should wander
		else:
			# If we have not yet arrived at the destination sphere
			if not self.travel_arrived:
				distance_from_travel_center = distance_between_points(self.pos[0], self.travel_sphere.x, 
												  	  			   	  self.pos[1], self.travel_sphere.y) 

				# If we are within half the radius of the travel sphere, then...
				if distance_from_travel_center <= self.travel_sphere.radius / 2:
					# 1. set travel status to arrived
					self.travel_arrived = True

					# If we have returned home, reset everything
					if self.travel_sphere == self.influence_sphere:
						self.travel_sphere = False
						self.travel_arrived = False

					# 2. start wandering
					new_position = self.wander(possible_steps)
				# Else, keep travelling
				else:
					new_position = self.travel(possible_steps)
			else:
				# Check if we ought to return home (when number is lower than the model threshold)
				if self.model.random.random() <= self.model.return_chance:
					# We just initiate a new travel, but this time with the home sphere as the target
					new_position = self.home(possible_steps)
				else:
					new_position = self.wander(possible_steps)

		self.model.grid.move_agent(self, new_position)		

	def wander(self, possible_steps):
		return self.random.choice(possible_steps)

		# temporarily disable this section
		legal_steps = []
		for possible_step in possible_steps:
			distance_from_center = distance_between_points(possible_step[0], self.influence_sphere.x, 
										  	  			   possible_step[1], self.influence_sphere.y)
			
			if distance_from_center <= self.influence_sphere.radius:
				legal_steps.append(possible_step)

	def travel(self, possible_steps):
		current_lowest_distance = float('inf')
		
		new_position = False
		for possible_step in possible_steps:
			distance_from_travel_center = distance_between_points(possible_step[0], self.travel_sphere.x, 
										  	  			   								 possible_step[1], self.travel_sphere.y) 
			if distance_from_travel_center < current_lowest_distance:
				current_lowest_distance = distance_from_travel_center
				new_position = possible_step

		return new_position

	def home(self, possible_steps):
		# Return home
		self.travel_sphere = self.influence_sphere
		self.travel_arrived = False
		return self.travel(possible_steps)
	
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
		self.travel_chance = 0.005 # chance of an agent travelling to another sphere each step
		self.return_chance = 0.05 # chance of an agent returning home each step after having arrived
		self.home_chance = 0.005 # chance of an agent returning home each step after having arrived
		
		self.init_influence_spheres()
		self.init_agents()
		#print(self.influence_spheres[0].coordinates)

	def init_influence_spheres(self):
		self.influence_spheres = []

		# Create influence spheres
		spheres = [ { "x": 30,
					  "y": 60,
					  "radius": 10,
					  "population": 10 },
					{ "x": 60,
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

		self.datacollector = DataCollector(
			model_reporters={ "home": lambda model: compute_population(model, "home"),
							  "travelling": lambda model: compute_population(model, "travelling"),
							  "visiting": lambda model: compute_population(model, "visiting")})

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
		self.datacollector.collect(self)
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