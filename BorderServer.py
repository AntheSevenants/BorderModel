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
server = ModularServer(BorderModel,
                       [grid, chart],
                       "Border Model",
                       {"num_agents":100, "width": width, "height": height})
server.port = 8521 # The default
server.launch()