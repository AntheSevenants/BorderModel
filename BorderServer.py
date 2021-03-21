import json

from BorderCanvasGrid import CanvasGrid
from BorderChartVisualization import ChartModule
from mesa.visualization.ModularVisualization import ModularServer
from BorderModel import BorderModel

def agent_portrayal(agent):
    portrayal = {"Shape": "circle",
                 "Color": "red",
                 "Filled": "true",
                 "Layer": 1,
                 "r": 0.5}

    if agent.travel_sphere:
        portrayal["Color"] = "green"
        if agent.travel_arrived:
            portrayal["Color"] = "orange"

    return portrayal

def influence_sphere_portrayal(influence_sphere):
    portrayal = {"Shape": "rect",
                 "Color": "rgba(208,194,232, 0.5)",
                 "Filled": "true",
                 "Layer": 0,
                 "w": 0.9,
                 "h": 0.9}
    return portrayal

width = 100
height = 100

grid = CanvasGrid(agent_portrayal, influence_sphere_portrayal, width, height, 1000, 1000)
chart = ChartModule([{"Label": "home",
                      "Color": "red"},
                      {"Label": "travelling",
                      "Color": "green"},
                      {"Label": "visiting",
                      "Color": "orange"},],
                    data_collector_name='datacollector')

colours = [ "red", "green", "orange", "blue", "purple", "teal", "yellow" ]
sound_mean_data_groups = []
with open("spheres.json") as spheres_file:
  spheres = json.load(spheres_file)

  i = 0
  for sphere in spheres:
    sound_mean_data_groups.append({"Label": "sphere_" + sphere["name"], "Color": colours[i]})
    i += 1

sound_chart = ChartModule(sound_mean_data_groups, data_collector_name='datacollector')

sound_repo_size_chart = ChartModule([{"Label": "sound_repo_size", "Color": "black"}],
                                    data_collector_name='datacollector')

server = ModularServer(BorderModel,
                       [grid, chart, sound_chart, sound_repo_size_chart],
                       "Border Model",
                       {"num_agents":100, "width": width, "height": height})
server.port = 8521 # The default
server.launch()