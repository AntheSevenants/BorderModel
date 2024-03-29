# Local imports
import math
import statistics
import json
import numpy
import pprint
import sys

from mesa import Agent, Model
from mesa.time import RandomActivation
from mesa.space import MultiGrid
from mesa.datacollection import DataCollector

def build_sound_mean_lambda_new(influence_sphere_name):
	return lambda model: model.average_sounds_spheres[influence_sphere_name]

# https://stackoverflow.com/questions/39840030/distance-between-point-and-a-line-from-two-points
def distance_to_line(line_begin, line_end, point):
	line_begin = numpy.asarray(line_begin)
	line_end = numpy.asarray(line_end)
	point = numpy.asarray(point)

	return numpy.abs(numpy.cross(line_end - line_begin, line_begin - point)) / numpy.linalg.norm(line_end - line_begin)

def distance_between_points(x0, x1, y0, y1):
	return math.hypot(x0 - x1, 
					  y0 - y1)

# Tron path
def tronPath(a, b, minimum_distance):
	path = [];

	x = a["x"]
	y = a["y"];                         # starting cell
	dx = 0 if a["x"] == b["x"] else 1 if b["x"] > a["x"] else -1 # right or left
	dy = 0 if a["y"] == b["y"] else 1 if b["y"] > a["y"] else -1 # up or down

	if dx == 0:
		if b["y"] > a["y"]:
			path = [ ( a["x"], y ) for y in range(a["y"] + 1, b["y"] + 1, 1)]
		else:
			path = [ ( a["x"], y ) for y in range(b["y"] + 1, a["y"] + 1, 1)]
			path.reverse()
	elif dy == 0:
		if b["x"] > a["x"]:
			path = [ ( x, a["y"] ) for x in range(a["x"] + 1, b["x"] + 1, 1)]
		else:
			path = [ ( x, a["y"] ) for x in range(b["x"] + 1, a["x"] + 1, 1)]
			path.reverse()
	elif (abs(b["x"] - a["x"]) > abs(b["y"] - a["y"])):
		# MAINLY HORIZONTAL
		tan = (b["y"] - a["y"]) / (b["x"] - a["x"]);      # tangent
		maxd = (1 - abs(tan)) / 2;        # distance threshold
		while x != b["x"] or y != b["y"]:            # while target not reached
			ideal = a["y"] + (x - a["x"]) * tan;    # y of ideal line at x
			if ((ideal - y) * dy >= maxd):
				y += dy; # move vertically
			else:
				x += dx;                         # move horizontally
			path.append( (x, y) );                # add cell to path
	else:
		# MAINLY VERTICAL
		cotan = (b["x"] - a["x"]) / (b["y"] - a["y"]);    # cotangent
		maxd = (1 - abs(cotan)) / 2;      # distance threshold
		while x != b["x"] or y != b["y"]:           # while target not reached
			ideal = a["x"] + (y - a["y"]) * cotan;  # x of ideal line at y
			if ((ideal - x) * dx >= maxd):
				x += dx; # move horizontally
			else:
				y += dy;                         # move vertically
			path.append( (x, y) );                # add cell to path

	# Make sure the agent arrives once he reaches the minimum distance from the centre
	n = len(path)
	for point in reversed(path):
		point_distance = distance_between_points(point[0], b["x"], point[1], b["y"])
		if point_distance >= minimum_distance:
			break

		n -= 1

	return path[:n];

class BorderAgent(Agent):
	def __init__(self, unique_id, influence_sphere, sound_mean, model, ethnocentrism=1, media_receptiveness=0.05,
					   domestic_travel_chance=0.005, abroad_travel_chance=0.001):
		super().__init__(unique_id, model)
		self.influence_sphere = influence_sphere
		self.model = model

		self.sound = 1
		self.sound_repository = [] # Previously heard sounds
		self.adopt_modifier = 1 # How quickly does this agent want to adapt?
		self.travel_urge = 1 # How much does this agent want to travel?
		self.ethnocentrism = ethnocentrism # How nationalistic is this agent?
		self.media_receptiveness = media_receptiveness # How receptive is this agent to media influences?
		self.has_spoken = False # Has this agent spoken yet this step?

		# Is the agent travelling?
		self.travel_sphere = False # Target sphere when travelling
		self.travel_arrived = False # Has the agent arrived at travel destination?

		# Travel probabilities
		self.domestic_travel_chance = domestic_travel_chance # chance of an agent travelling to another sphere each step
		self.abroad_travel_chance = abroad_travel_chance # chance of an agent travelling abroad each step
	
		self.init_sound(sound_mean)

	def init_sound(self, sound_mean):
		# Generate the initial sound which will be the only sound in the sound repository
		borders = { "left": sound_mean - self.model.sound_mean_interval,
					"right": sound_mean + self.model.sound_mean_interval }

		if borders["left"] < 0:
			borders["left"] = 0
		if borders["right"] > 1:
			borders["right"] = 1

		if sound_mean > 0.1:
			initial_sound = round(self.model.random.uniform(borders["left"], borders["right"]), 9)
		else:
			initial_sound = sound_mean

		if not self.model.init_big_inventory:
			self.sound_repository.append(initial_sound)
		else:
			self.sound_repository += [initial_sound] * 140

	def step(self):
		self.travel_chance_time()
		self.move() # TODO: repeat this a number of times probably -- refer to Stanford & Kenny (p. 127)
		self.speak()

		if self.media_receptiveness:
			self.media_influence()
	
	# Attempt to travel
	def travel_chance_time(self):
		# Don't initiate a new travel target if already travelling
		if self.travel_sphere:
			return

		# Check if travel chance time happens (when number is lower than the model threshold)
		if self.model.random.random() < self.domestic_travel_chance:
			self.set_travel_sphere(abroad=False)
		# Check if ABROAD travel chance time happens
		elif self.model.random.random() < self.abroad_travel_chance:
			self.set_travel_sphere(abroad=True)

	# Set a travel sphere
	def set_travel_sphere(self, abroad=False):
		# Travel chance time is happening
		# TODO: better decision making on which sphere to travel to
		# Current implementation = random influence sphere FROM SAME OR NEIGHBOURING COUNTRY
		# with probabilities based on radiation model (see infra)
		while True:
			travel_sphere = self.random.choice(self.model.influence_spheres)
			# Keep picking a travel sphere until we've found one that isn't our home sphere
			# I don't know whether this is more efficient than removing the home sphere from 
			# a deepcopy of the list of all spheres but I assume this is better
			if travel_sphere != self.influence_sphere:
				# Country check
				if (not abroad and travel_sphere.country == self.influence_sphere.country) or \
					(abroad and travel_sphere.country != self.influence_sphere.country):

					# Travel probabilities check
					if self.model.random.random() < \
						self.model.travel_probabilities[(self.influence_sphere.name, travel_sphere.name)]:
						self.travel_sphere = travel_sphere # set current travel target to target travel sphere
						self.set_travel_path()
						break

	def set_travel_path(self):
		A = (self.influence_sphere.x, self.influence_sphere.y)
		B = (self.travel_sphere.x, self.travel_sphere.y)

		m = slope(A, B)
		b = intercept(A, m)

		coordinates = [];
		for x in range(A[0], B[0] + 1, 1):
			y = m * x + b
			coordinates.append([round(x), round(y)])

		print(coordinates)

	def set_travel_path(self):
		x1 = self.influence_sphere.x
		y1 = self.influence_sphere.y
		x2 = self.travel_sphere.x
		y2 = self.travel_sphere.y

		points = []
		issteep = abs(y2-y1) > abs(x2-x1)
		if issteep:
			x1, y1 = y1, x1
			x2, y2 = y2, x2
		rev = False
		if x1 > x2:
			x1, x2 = x2, x1
			y1, y2 = y2, y1
			rev = True
		deltax = x2 - x1
		deltay = abs(y2-y1)
		error = int(deltax / 2)
		y = y1
		ystep = None
		if y1 < y2:
			ystep = 1
		else:
			ystep = -1
		for x in range(x1, x2 + 1):
			if issteep:
				points.append((y, x))
			else:
				points.append((x, y))
			error -= deltay
			if error < 0:
				y += ystep
				error += deltax
		# Reverse the list if the coordinates were reversed
		if rev:
			points.reverse()
		
		print(points)

		# Interpolate points
		n = 0
		interpolated_points = []
		for point in points:
			interpolated_points.append(point)

			print("Current point")
			print(point)

			if n - 1 >= len(points):
				break

			print("Next point")
			print(points[n+1])

			if point[0] == points[n + 1][0] or point[1] == points[n + 1][1]:
				pass
			else:
				print("Inserting interpolated point")
				chosen_point = self.model.random.choice([ (point[0] + 1, point[1]),
																	  (point[0], point[1] + 1) ])
				print(chosen_point)
				interpolated_points.append(chosen_point)

			n += 1

		print(interpolated_points)
		sys.exit(0)

	def set_travel_path(self):
		a = { "x": self.pos[0], "y": self.pos[1] }
		b = { "x": self.travel_sphere.x, "y": self.travel_sphere.y }

		self.path = tronPath(a, b, self.travel_sphere.radius / 2)

	# All movement related code 
	def move(self):
		# TODO: use Moore or not? (Moore = diagonal -- currently using Von Neumann)
		possible_steps = self.model.grid.get_neighborhood(self.pos, moore=False, include_center=True)
		
		# If not travelling, wander
		if not self.travel_sphere:
			# Every once in a while, an agent should attempt to return home
			if self.model.random.random() < self.model.home_chance:
				new_position = self.home(possible_steps)
			else:
				new_position = self.wander(possible_steps)
		# If travelling, check if we should wander
		else:
			# If we have not yet arrived at the destination sphere
			if not self.travel_arrived:
				# If we are within half the radius of the travel sphere, then...
				#print(len(self.path))
				if len(self.path) == 0:
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
				if self.model.random.random() < self.model.return_chance:
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
			
			if distance_from_center < self.influence_sphere.radius:
				legal_steps.append(possible_step)

	# Code for travelling to another sphere (or travelling home)
	def travel(self, possible_steps):
		# I don't want agents to always take the shortest path, because this causes "trains" which could
		# interfere with language change patterns
		# Instead, agents choose from the two closest steps to their target

		# Dict which will keep track of each step and its distance
		step_dict = {}

		# Check the distance for every possible step
		for possible_step in possible_steps:
			# Find the distance to the centre of the travel sphere from the possible next step
			distance_from_travel_center = distance_between_points(possible_step[0], self.travel_sphere.x, 
																						 possible_step[1], self.travel_sphere.y) 
			
			# Add this possible step to the step dictionary, so we can sort it later
			step_dict[distance_from_travel_center] = possible_step

		# Sort the step dict based on distance, get the two shortest steps
		sorted_step_dict_keys = sorted(step_dict)[:1]
		# Chose a random step based on a random key
		new_position = step_dict[self.model.random.choice(sorted_step_dict_keys)]

		return new_position

	# Code for travelling to another sphere
	def travel(self, possible_steps):
		new_position = self.path[0]
		self.path = self.path[1:]

		return new_position

	# Code for returning home
	def home(self, possible_steps):
		# Set the travel sphere to the home sphere
		self.travel_sphere = self.influence_sphere
		self.set_travel_path()

		# If we are already close enough to home, just wander
		if len(self.path) == 0:
			self.travel_sphere = False
			return self.wander(possible_steps)

		self.travel_arrived = False
		return self.travel(possible_steps)

	# Simulate media influence to the agents
	def media_influence(self):
		# Idea = every agent "receives" a sound randomly based on media receptiveness
		# Sound is based on **average sound** in a country (assumption that media reflect society)
		# Agents do not *return* a sound -> media are one-sided
		# Agents in Belgium get influenced by Dutch media as well
		# (Flemings listened to Dutch radio stations / watched Dutch television extensively in the past)
		if self.model.random.random() < self.media_receptiveness:
			# People in The Netherlands rarely watch Belgian television
			# For Dutch people, we always assign The Netherlands as the source country for media influence
			if self.influence_sphere.country == "The Netherlands":
				chosen_country = "The Netherlands"
			# People in Flanders are avid watchers of Dutch television
			else:
				# For Dutch programmes, the ratio should be 1/4 for Dutch television
				chosen_country = "The Netherlands" if self.model.random.random() <= 0.25 else "Belgium"

			# Add to sound repository
			self.adopt_sound(self.model.get_central_sound(chosen_country), chosen_country)
			
	
	# Speaking-related code
	def speak(self):
		# For the neighbours we *do* want to be using the Moore specification, and also the center (there could be someone we share the space with)
		neighbourhood = self.model.grid.get_neighborhood(self.pos, moore=True, include_center=True)
		neighbours = self.model.grid.get_cell_list_contents(neighbourhood)
		if len(neighbours) > 1:
			# Select one neighbour
			neighbour = self.model.random.choice(neighbours)
			
			# This agent speaks, and the neighbour agent saves the sound
			spoken_sound = self.model.random.choice(self.sound_repository)

			# Add spoken sound to neighbour's sound repository
			neighbour.adopt_sound(spoken_sound, self.influence_sphere.country)

			# Set this agent's spoken state to True
			self.has_spoken = True

	# Adopt a sound
	def adopt_sound(self, sound, sound_origin_country):
		adoption_count = 1

		# If the sound origin country is not the home country, implement the ethnocentrism
		if sound_origin_country != self.influence_sphere.country:
			# The higher the ethnocentrism value, the less likely an agent is to adopt the foreign variant
			if self.model.random.random() < self.ethnocentrism:
				return

		# Make sure the shift *always* happens for the Netherlands
		if self.influence_sphere.country == "The Netherlands" and sound_origin_country == "The Netherlands":
			# If the sound to be received is lower than the current average sound, don't take over this sound
			# I know this is circular, but that's the point -- the shift in the Netherlands is a given, not something I want to test
			if sound < statistics.mean(self.sound_repository):
				return

			# If target acceleration is activated, set the adoption count to the acceleration count defined in the model parameters
			if self.model.target_accel_count:
				adoption_count = self.model.target_accel_count

		# If the sound origin country is the home country, or the ethnocentrism wasn't a big enough influence this time,
		# just adopt the sound as much as required
		for adoption_turn in range(adoption_count):
			self.sound_repository.append(sound)

class BorderModel(Model):
	def __init__(self, width, height, return_chance=0.05, home_chance=0.005,
					   domestic_travel_chance_nl=0.005,
					   domestic_travel_chance_be=0.005,
					   abroad_travel_chance_nl=0.001,
					   abroad_travel_chance_be=0.001,
					   ethnocentrism_nl=1,
					   ethnocentrism_be=1,
					   scaled_ethnocentrism=False,
					   media_receptiveness=0.05,
					   sound_mean_interval=0.1, decay_limit=140,
					   border_heights=[ 74, 54 ],
					   init_big_inventory=False,
					   target_accel_count=False):

		self.width = width
		self.height = height

		self.num_agents = 0

		# Program the border so it always starts on the horizontal borders (only the y axis is controllable)
		self.border_coords = [ (0, border_heights[0]), (width, border_heights[1]) ]
		self.set_border_longest_distance()

		self.grid = MultiGrid(width, height, False)
		self.schedule = RandomActivation(self)
		self.running = True
		self.return_chance = return_chance # chance of an agent returning home each step after having arrived
		self.home_chance = home_chance # chance of an agent returning home each step after having arrived
		self.sound_mean_interval = sound_mean_interval # distance of one side of sound interval around sound mean
		self.decay_limit = decay_limit # amount of sounds an agent can remember

		self.domestic_travel_chances = { "The Netherlands": domestic_travel_chance_nl,
										 "Belgium": domestic_travel_chance_be }
		self.abroad_travel_chances = { "The Netherlands": abroad_travel_chance_nl,
										 "Belgium": abroad_travel_chance_be }
		self.ethnocentrism = { "The Netherlands": ethnocentrism_nl,
							   "Belgium": ethnocentrism_be }
		self.scaled_ethnocentrism = scaled_ethnocentrism
		self.media_receptiveness = media_receptiveness

		self.travel_probabilities = {} # probabilities of one sphere member travelling to another sphere

		self.init_big_inventory = init_big_inventory
		self.target_accel_count = target_accel_count

		self.init_influence_spheres()
		self.init_agents()
		self.compute_radiation_probabilities()
		self.collect_data_bulk()
		self.init_data_collect()

		self.step()

	# We want to get the longest distance from the border to the top or bottom, depending on the country
	def set_border_longest_distance(self):
		self.border_longest_distance = { "The Netherlands": [],
										 "Belgium": [] }

		# Go over each x coordinate to see which distance is the longest
		for x in range(0, self.width + 1, 1):
			nl_point = (x, 0) # Dutch points are calculated from the top
			be_point = (x, self.height) # Belgium points are calculated form the bottom

			self.border_longest_distance["The Netherlands"].append(distance_to_line(self.border_coords[0],
																		  self.border_coords[1], nl_point))
			self.border_longest_distance["Belgium"].append(distance_to_line(self.border_coords[0],
																		  self.border_coords[1], be_point))
		
		self.border_longest_distance = { "The Netherlands": round(max(self.border_longest_distance["The Netherlands"])),
										 "Belgium": round(max(self.border_longest_distance["Belgium"])) }

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
				# Define a location for this agent (we need to know this beforehand to be able to seed ethnocentrism)
				location = self.random.choice(influence_sphere.coordinates)

				# Assign value for ethnocentrism based on whether it is seeded or not
				if self.scaled_ethnocentrism:
					distance_to_border = distance_to_line(self.border_coords[0], self.border_coords[1], location)
					# Ethnocentrism is the proportion of the distance of this agent to the border and the longest distance
					# to the border in the entire country (the closer to the border, the less ethnocentrism)
					ethnocentrism = distance_to_border / self.border_longest_distance[influence_sphere.country]
					ethnocentrism = round(ethnocentrism, 2)
				else:
					ethnocentrism = self.ethnocentrism[influence_sphere.country]

				agent = BorderAgent(unique_id=agent_no, influence_sphere=influence_sphere,
									sound_mean=influence_sphere.sound_mean, model=self,
									ethnocentrism=ethnocentrism,
									media_receptiveness=self.media_receptiveness,
									domestic_travel_chance=self.domestic_travel_chances[influence_sphere.country],
									abroad_travel_chance=self.abroad_travel_chances[influence_sphere.country])
				# Add agent to the scheduler
				self.schedule.add(agent)
				
				# Place the newly created agent on the grid
				self.grid.place_agent(agent, (location[0], location[1]))

				agent_no += 1

		self.num_agents = agent_no

	def init_data_collect(self):
		# Initialise the data collector which will be used for graphing and stats
		model_reporters = { "home": lambda model: model.whereabouts_data["home"],
							"travelling": lambda model: model.whereabouts_data["travelling"],
							"visiting": lambda model: model.whereabouts_data["visiting"],
							"sound_repo_size": lambda model: model.average_population_sound_repository_length,
							"avg_sound_nl": lambda model: model.average_sounds["The Netherlands"],
							"avg_sound_be": lambda model: model.average_sounds["Belgium"] }

		for influence_sphere in self.influence_spheres:
			model_reporters["sphere_" + influence_sphere.name] = \
				build_sound_mean_lambda_new(influence_sphere.name)

		self.datacollector = DataCollector(
			model_reporters=model_reporters)

	# Data collectors are built in a very clumsy way, so this is an attempt to make data collection more efficient
	def collect_data_bulk(self):
		self.whereabouts_data = { "home": 0, "travelling": 0, "visiting": 0 }

		population_sound_repository_lengths = []

		# Create sound repositories for both countries
		average_sound_repository = { "The Netherlands": [],
									 "Belgium": [] }

		average_sound_repository_spheres = { }
		self.average_sounds_spheres = { }
		for influence_sphere in self.influence_spheres:
			average_sound_repository_spheres[influence_sphere.name] = []
			self.average_sounds_spheres[influence_sphere.name] = 0

		for agent in self.schedule.agents:
			# ----
			# Whereabouts
			# ----

			# If the agent is not travelling, or they are travelling homewards, count them
			# as being "home"
			if not agent.travel_sphere or agent.travel_sphere == agent.influence_sphere:
				self.whereabouts_data["home"] += 1
			# If the agent is travelling and the travel target is not the home sphere,
			# count the agent as "travelling"
			elif agent.travel_sphere and agent.travel_sphere != agent.influence_sphere and not agent.travel_arrived:
				self.whereabouts_data["travelling"] += 1
			# If the agent is travelling and has arrived, count the agent as "visiting"
			elif agent.travel_sphere and agent.travel_arrived:
				self.whereabouts_data["visiting"] += 1

			# ----
			# Average sound repository size
			# ----
			population_sound_repository_lengths.append(len(agent.sound_repository))

			# ----
			# Average sounds (real)
			# ----
			average_sound_repository[agent.influence_sphere.country] += agent.sound_repository
			average_sound_repository_spheres[agent.influence_sphere.name] += agent.sound_repository

		self.average_population_sound_repository_length = round(statistics.mean(population_sound_repository_lengths))
		
		self.average_sounds = { "The Netherlands": None,
								"Belgium": None }
		# Compute and set the means
		for country in self.average_sounds:
			self.average_sounds[country] = round(statistics.mean(average_sound_repository[country]), 9)

		for influence_sphere in self.influence_spheres:
			self.average_sounds_spheres[influence_sphere.name] = \
				round(statistics.mean(average_sound_repository_spheres[influence_sphere.name]), 9)

	# Get a sound from a central region to simulate media influence
	def get_central_sound(self, country):
		while True:
			random_agent = self.random.choice(self.schedule.agents)
			# Return a sound if the agent belongs to the country we want and if their region is central
			if random_agent.influence_sphere.country == country and random_agent.influence_sphere.central:
				return self.random.choice(random_agent.sound_repository)

	def compute_radiation_probabilities(self):
		# For each influence sphere, compute the probability of an agent going to another influence sphere
		for influence_sphere_source in self.influence_spheres:
			for influence_sphere_destination in self.influence_spheres:
				# If destination is self, continue
				if influence_sphere_source == influence_sphere_destination:
					continue

				# Find out the distance between the points we are comparing, then round it
				spheres_distance = distance_between_points(influence_sphere_source.x, influence_sphere_destination.x,
														   influence_sphere_source.y, influence_sphere_destination.y)
				spheres_distance = round(spheres_distance)

				# We create a temporary influence sphere in order to be able to assess who lives within the s sphere
				temp_influence_sphere = InfluenceSphere(influence_sphere_source.x, influence_sphere_source.y, spheres_distance)
				# It is possible that the temporary influence sphere goes outside the grid, so we have to check which coordinates
				# are actually legal
				legal_coordinates = [coordinates_pair for coordinates_pair in temp_influence_sphere.coordinates \
									 if coordinates_pair[0] in range(0, self.grid.width) \
									 and coordinates_pair[1] in range(0, self.grid.height)]
				# Get the agents living in the calculated cells
				temp_influence_sphere_population = self.grid.get_cell_list_contents(legal_coordinates)

				# The population is called s-population because it is used for the parameter s in Simini et al. (2012)
				s_population = []
				for agent in temp_influence_sphere_population:
					# If this agent belongs to our comparison population, don't include it
					if agent.influence_sphere.country in [ influence_sphere_source.country,
														   influence_sphere_destination.country ]:
						continue

					s_population.append(agent)

				# Implementation of:
				# p =               m~i~ * m~j~
				#     --------------------------------------
				#     (m~i~ + s~ij~) * (m~i~ + m~j~ + s~ij~)
				# found in RUG paper (TODO attribution)
				# In this model: m~i~ = source influence sphere population
				#                m~j~ = destination influence sphere population
				#                s~ij~ = "total population (not including the populations of *i* and *j*) living within
				#                         a circle radius r~ij~ centered on i" (p. 24)     
				probability = (influence_sphere_source.population * influence_sphere_destination.population) / \
							  ((influence_sphere_source.population + len(s_population)) * \
							  (influence_sphere_source.population + influence_sphere_destination.population + len(s_population)))

				# Save the probability to the dict (key = tuple of the travel direction vector)
				self.travel_probabilities[(influence_sphere_source.name, influence_sphere_destination.name)] = probability
				print("{} -> {}: {}".format(influence_sphere_source.name, influence_sphere_destination.name,
											round(probability, 2)))

	def compute_radiation_probabilities(self):
		# For each influence sphere, compute the probability of an agent going to another influence sphere
		for influence_sphere_destination in self.influence_spheres:
			influence_sources = { "The Netherlands": {},
								  "Belgium": {} }
			total_influence = { "The Netherlands": 0,
								  "Belgium": 0 }

			for influence_sphere_source in self.influence_spheres:
				# If destination is self, continue
				if influence_sphere_source == influence_sphere_destination:
					continue

				# Find out the distance between the points we are comparing, then round it
				spheres_distance = distance_between_points(influence_sphere_source.x, influence_sphere_destination.x,
														   influence_sphere_source.y, influence_sphere_destination.y)
				spheres_distance = round(spheres_distance)

				# Implementation of:
				#       P~i~ * P~j~                P~i~
				# ------------------------- * --------------
				#          d~ij~²              P~i~ + P~j~
				influence = ((influence_sphere_source.population * influence_sphere_destination.population) / \
												(spheres_distance * spheres_distance)) * \
				((influence_sphere_source.population) / (influence_sphere_source.population + influence_sphere_destination.population))

				# Idea: SOURCE OF INFLUENCE -> DESTINATION OF INFLUENCE
				# is the result of DESTINATION visiting SOURCE
				# so: REVERSAL = travel probabilities

				# Save the probability to the a temporary dict
				influence_sources[influence_sphere_source.country][influence_sphere_source.name] = influence
				total_influence[influence_sphere_source.country] += influence
			
			# Compute probabilities depending on total influence on this sphere
			for influence_source_country in influence_sources:
				for influence_source in influence_sources[influence_source_country]:
					self.travel_probabilities[(influence_sphere_destination.name, influence_source)] = \
						round(influence_sources[influence_source_country][influence_source] / total_influence[influence_source_country], 2)

		#pp = pprint.PrettyPrinter(indent=4)
		#pp.pprint(self.travel_probabilities)

	def step(self):
		self.collect_data_bulk()
		self.datacollector.collect(self)
		self.schedule.step()

		for agent in self.schedule.agents:
			# Reset speaking turns for every agent
			agent.has_spoken = False

			# Decay sound memory
			if len(agent.sound_repository) > self.decay_limit:
				agent.sound_repository = agent.sound_repository[-self.decay_limit:]

class InfluenceSphere():
	# This code generates a list of all coordinates which will be inside the influence sphere
	def __init__(self, x, y, radius, population=None, sound_mean=None, name=None, country=None, central=None):
		self.name = name
		self.country = country

		self.x = x
		self.y = y
		self.radius = radius
		self.population = population
		self.sound_mean = sound_mean # the mean around which population values are initialised
		self.central = central

		self.coordinates = []

		for j in range(x - radius, x + radius + 1):
			for k in range(y - radius, y + radius + 1):
				if self.distance({ "x": j, "y": k }, { "x": x, "y": y }) <= radius:
					self.coordinates.append(( j, k ))

	def distance(self, p1, p2):
		dx = p2["x"] - p1["x"];
		dx *= dx;
		dy = p2["y"] - p1["y"];
		dy *= dy;
		return math.ceil(math.sqrt(dx + dy));

	def add_coords(self, x, y):
		self.coordinates.append([x, y])