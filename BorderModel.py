# Local imports
import math
import statistics
import json

from mesa import Agent, Model
from mesa.time import RandomActivation
from mesa.space import MultiGrid
from mesa.datacollection import DataCollector

# Data collection function
# This is really slow, but I can't think of an alternative
# ...and it works, so...
def compute_population(model, group):
	count = 0
	if group == "home":
		for agent in model.schedule.agents:
			# If the agent is not travelling, or they are travelling homewards, count them
			# as being "home"
			if not agent.travel_sphere or agent.travel_sphere == agent.influence_sphere:
				count += 1
				continue
	elif group == "travelling":
		for agent in model.schedule.agents:
			# If the agent is travelling and the travel target is not the home sphere,
			# count the agent as "travelling"
			if agent.travel_sphere and agent.travel_sphere != agent.influence_sphere and not agent.travel_arrived:
				count += 1
				continue
	elif group == "visiting":
		for agent in model.schedule.agents:
			# If the agent is travelling and has arrived, count the agent as "visiting"
			if agent.travel_sphere and agent.travel_arrived:
				count += 1
				continue

	return count

# Get the sound mean for a population / influence sphere
def compute_sound_means(model, influence_sphere_name):
	population_sound_repository = []
	for agent in model.schedule.agents:
		if agent.influence_sphere.name == influence_sphere_name:
			population_sound_repository += agent.sound_repository

	return statistics.mean(population_sound_repository)

def distance_between_points(x0, x1, y0, y1):
	return math.hypot(x0 - x1, 
					  y0 - y1)

class BorderAgent(Agent):
	def __init__(self, unique_id, influence_sphere, sound_mean, model):
		super().__init__(unique_id, model)
		self.influence_sphere = influence_sphere
		self.model = model

		self.sound = 1
		self.sound_repository = [] # Previously heard sounds
		self.adopt_modifier = 1 # How quickly does this agent want to adapt?
		self.travel_urge = 1 # How much does this agent want to travel?
		self.ethnocentrism = 1 # How nationalistic is this agent?
		self.media_receptiveness = 1 # How receptive is this agent to media influences?

		# Is the agent travelling?
		self.travel_sphere = False # Target sphere when travelling
		self.travel_arrived = False # Has the agent arrived at travel destination?
	
		self.init_sound(sound_mean)

	def init_sound(self, sound_mean):
		# Generate the initial sound which will be the only sound in the sound repository
		borders = { "left": sound_mean - self.model.sound_mean_interval,
					"right": sound_mean + self.model.sound_mean_interval }

		if borders["left"] < 0:
			borders["left"] = 0
		if borders["right"] > 1:
			borders["right"] = 1

		initial_sound = self.model.random.uniform(borders["left"], borders["right"])
		self.sound_repository.append(initial_sound)

	def step(self):
		self.travel_chance_time()
		self.move() # TODO: repeat this a number of times probably -- refer to Stanford & Kenny (p. 127)
		self.speak()
	
	# Attempt to travel
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

	# All movement related code 
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

	# Code for strolling around casually
	def wander(self, possible_steps):
		return self.random.choice(possible_steps)

		# This code can be used to prevent agents from leaving their influence sphere
		# It is disabled through the return statement above, because it is no longer needed
		# However, it could be interesting to use for other experiments, so I'm leaving it in
		legal_steps = []
		for possible_step in possible_steps:
			distance_from_center = distance_between_points(possible_step[0], self.influence_sphere.x, 
										  	  			   possible_step[1], self.influence_sphere.y)
			
			if distance_from_center <= self.influence_sphere.radius:
				legal_steps.append(possible_step)

	# Code for travelling to another sphere (or travelling home)
	def travel(self, possible_steps):
		# This is a bit of a hack, but I'm keeping track of the step with the lowest distance
		# to the target. To make sure the first step distance will be used as a reference,
		# I set the default lowest distance to infinity, so any step will always be lower
		current_lowest_distance = float('inf')
		
		new_position = False
		# Check the distance for every possible step
		for possible_step in possible_steps:
			# Find the distance to the centre of the travel sphere from the possible next step
			distance_from_travel_center = distance_between_points(possible_step[0], self.travel_sphere.x, 
										  	  			   								 possible_step[1], self.travel_sphere.y) 
			
			# If the distance found is shorter than the current lowest distance, prefer this possible
			# step to the one already stored, and update the current lowest distance
			if distance_from_travel_center < current_lowest_distance:
				current_lowest_distance = distance_from_travel_center
				new_position = possible_step

		return new_position

	# Code for returning home
	def home(self, possible_steps):
		# Set the travel sphere to the home sphere
		self.travel_sphere = self.influence_sphere
		self.travel_arrived = False
		return self.travel(possible_steps)
	
	# Speaking-related code
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
		self.sound_mean_interval = 0.1 # distance of one side of sound interval around sound mean

		self.init_influence_spheres()
		self.init_agents()
		self.init_data_collect()

	def init_influence_spheres(self):
		self.influence_spheres = []

		# Create influence spheres
		with open("spheres.json") as spheres_file:
			spheres = json.load(spheres_file)

		# Create the influence spheres based on the info in the dict above
		for sphere in spheres:
			influence_sphere = InfluenceSphere(**sphere)
			self.influence_spheres.append(influence_sphere)

	def init_agents(self):
		# Create agents based on population count in the influence spheres
		agent_no = 0
		for influence_sphere in self.influence_spheres:
			# Create agents
			for i in range(influence_sphere.population):
				agent = BorderAgent(agent_no, influence_sphere,
									influence_sphere.sound_mean, self)
				# Add agent to the scheduler
				self.schedule.add(agent)
				
				# Place the newly created agent on the grid
				location = self.random.choice(influence_sphere.coordinates)
				self.grid.place_agent(agent, (location[0], location[1]))

				agent_no += 1

	def init_data_collect(self):
		# Initialise the data collector which will be used for graphing and stats
		model_reporters = { "home": lambda model: compute_population(model, "home"),
							"travelling": lambda model: compute_population(model, "travelling"),
							"visiting": lambda model: compute_population(model, "visiting") }

		for influence_sphere in self.influence_spheres:
			model_reporters["sphere_" + influence_sphere.name] = \
				lambda model: compute_sound_means(model, influence_sphere.name)

		self.datacollector = DataCollector(
			model_reporters=model_reporters)

	def step(self):
		self.datacollector.collect(self)
		self.schedule.step()

class InfluenceSphere():
	# This code generates a list of all coordinates which will be inside the influence sphere
	def __init__(self, x, y, radius, population, sound_mean, name):
		self.name = name

		self.x = x
		self.y = y
		self.radius = radius
		self.population = population
		self.sound_mean = sound_mean # the mean around which population values are initialised

		self.coordinates = []

		for j in range(x - radius, x + radius + 1):
			for k in range(y - radius, y + radius + 1):
				if self.distance({ "x": j, "y": k }, { "x": x, "y": y }) <= radius:
					self.coordinates.append([ j, k ])

	def distance(self, p1, p2):
		dx = p2["x"] - p1["x"];
		dx *= dx;
		dy = p2["y"] - p1["y"];
		dy *= dy;
		return math.ceil(math.sqrt(dx + dy));

	def add_coords(self, x, y):
		self.coordinates.append([x, y])