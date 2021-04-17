import json

from BorderCanvasGrid import CanvasGrid
from BorderChartVisualization import ChartModule
from mesa.visualization.ModularVisualization import ModularServer
from mesa.visualization.UserParam import UserSettableParameter
from BorderModel import BorderModel

def agent_portrayal(agent):
    portrayal = {"Shape": "circle",
                 "Color": "red",
                 "Filled": "true",
                 "Layer": 1,
                 "r": 0.5,
                 # Properties,
                 "Home sphere": agent.influence_sphere.name,
                 "Home country": agent.influence_sphere.country,
                 "Travel sphere": agent.travel_sphere.name if agent.travel_sphere else "None",
                 "Media receptiveness": agent.media_receptiveness,
                 "Ethnocentrism": agent.ethnocentrism }

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

def influence_sphere_circle_portrayal(influence_sphere):
    colour_table = { "The Netherlands": { "fillColor": "rgba(243,110,21, 0.2)",
                                          "strokeColor": "#F47D2D",
                                          "textColor": "#F36E15" },
                      "Belgium": { "fillColor": "rgba(254,222,0, 0.2)",
                                   "strokeColor": "#FEDE00",
                                   "textColor": "#cbb100" } }

    portrayal = { "x": influence_sphere.x,
                  "y": influence_sphere.y,
                  "radius": influence_sphere.radius,
                  "fillColor": colour_table[influence_sphere.country]["fillColor"],
                  "strokeColor": colour_table[influence_sphere.country]["strokeColor"],
                  "textColor": colour_table[influence_sphere.country]["textColor"],
                  "name": influence_sphere.name }
    return portrayal

width = 100
height = 240

grid = CanvasGrid(agent_portrayal, influence_sphere_portrayal, influence_sphere_circle_portrayal,
                  width, height, 500, 1200)
chart = ChartModule([{"Label": "home",
                      "Color": "red"},
                      {"Label": "travelling",
                      "Color": "green"},
                      {"Label": "visiting",
                      "Color": "orange"},],
                    data_collector_name='datacollector')

colours = [ "red", "green", "orange", "blue", "purple", "teal", "yellow", "pink", "gold" ]
sound_mean_data_groups = []
with open("spheres.json") as spheres_file:
  spheres = json.load(spheres_file)

  i = 0
  for sphere in spheres:
    sound_mean_data_groups.append({"Label": "sphere_" + sphere["name"], "Color": colours[i]})
    i += 1

sound_chart = ChartModule(sound_mean_data_groups, data_collector_name='datacollector', canvas_height=400)

sound_repo_size_chart = ChartModule([{"Label": "sound_repo_size", "Color": "black"}],
                                    data_collector_name='datacollector')

avg_sound_chart = ChartModule([{"Label": "avg_sound_nl", "Color": "#F47D2D"},
                               {"Label": "avg_sound_be", "Color": "#FEDE00" }])

model_params = {"width": width, "height": height,
                "return_chance": UserSettableParameter('slider', '🧳 Travel return prob.', value=0.05, min_value=0, max_value=0.10, step=0.01),
                "home_chance": UserSettableParameter('slider', '🏠 Homing prob.', value=0.005, min_value=0, max_value=0.010, step=0.001),
                "domestic_travel_chance_nl": UserSettableParameter('slider', '🇳🇱 Domestic travel prob.', value=0.005, min_value=0, max_value=0.010, step=0.001),
                "domestic_travel_chance_be": UserSettableParameter('slider', '🇧🇪 Domestic travel prob.', value=0.005, min_value=0, max_value=0.010, step=0.001),
                "abroad_travel_chance_nl": UserSettableParameter('slider', '🇳🇱 Abroad travel prob.', value=0.001, min_value=0, max_value=0.010, step=0.001),
                "abroad_travel_chance_be": UserSettableParameter('slider', '🇧🇪 Abroad travel prob.', value=0.001, min_value=0, max_value=0.010, step=0.001),
                "ethnocentrism_nl": UserSettableParameter('slider', '🇳🇱 Ethnocentrism', value=0.85, min_value=0, max_value=1, step=0.1),
                "ethnocentrism_be": UserSettableParameter('slider', '🇧🇪 Ethnocentrism', value=0.0, min_value=0, max_value=1, step=0.1),
                "scaled_ethnocentrism": UserSettableParameter('checkbox', '⛰️ Scaled ethnocentrism', value=True),
                "media_receptiveness": UserSettableParameter('slider', '📺 Media receptiveness', value=0.05, min_value=0, max_value=0.10, step=0.01),
                "sound_mean_interval": 0.1,
                "decay_limit": UserSettableParameter('slider', '🧠 Decay limit', value=140, min_value=1, max_value=200, step=1),
                "border_heights": [ 124, 104 ]}

server = ModularServer(BorderModel,
                       [grid, chart, sound_chart, sound_repo_size_chart, avg_sound_chart],
                       "Border Model",
                       model_params)
server.port = 8521 # The default
server.launch()