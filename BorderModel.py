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
            
    def step(self):
        self.schedule.step()