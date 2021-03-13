from mesa.visualization.modules import CanvasGrid
from mesa.visualization.ModularVisualization import ModularServer
from BorderModel import BorderModel

def agent_portrayal(agent):
    portrayal = {"Shape": "circle",
                 "Color": "red",
                 "Filled": "true",
                 "Layer": 0,
                 "r": 0.5}
    return portrayal

grid = CanvasGrid(agent_portrayal, 10, 10, 500, 500)
server = ModularServer(BorderModel,
                       [grid],
                       "Border Model",
                       {"num_agents":100, "width":10, "height":10})
server.port = 8521 # The default
server.launch()