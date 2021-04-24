import numpy
import pandas
import argparse
import sys

from mesa.batchrunner import FixedBatchRunner
from BorderModel import BorderModel

# Define possibilities
parser = argparse.ArgumentParser(description='BorderThink automates the different parameters for the BorderModel simulation')
parser.add_argument('theory', type=str, help="Which theory do you want to test?\
					contact - target - ethnocentrism - scaled_ethnocentrism - media")
parser.add_argument('iterations', type=int, help='How many times should each variable parameter be tested?')
parser.add_argument('max_steps', type=int, help='What is the step ceiling for this model?')

args = parser.parse_args()

fixed_params = {
	"width": 100,
	"height": 240,
	"return_chance": 0.05,
	"home_chance": 0.005,
	"decay_limit": 140,
	"sound_mean_interval": 0.1,
	"border_heights": [ 124, 104 ]
}

if args.theory == "contact":
	fixed_params = { **fixed_params,
					 "domestic_travel_chance_nl": 0.005,
					 "domestic_travel_chance_be": 0.005,
					 "ethnocentrism_nl": 0,
					 "ethnocentrism_be": 0,
					 "scaled_ethnocentrism": False,
					 "media_receptiveness": False }

	parameters_list = [ { "abroad_travel_chance_nl": probability,
						   "abroad_travel_chance_be": probability } \
						   for probability in numpy.arange(0.0000, 0.0101, 0.0001) ]
elif args.theory == "target":
	fixed_params = { **fixed_params,
					 "abroad_travel_chance_be": 0.001,
					 "abroad_travel_chance_nl": 0.001,
					 "domestic_travel_chance_be": 0.005,
					 "ethnocentrism_nl": 0,
					 "ethnocentrism_be": 0,
					 "scaled_ethnocentrism": False,
					 "media_receptiveness": False }

	parameters_list = [ { "domestic_travel_chance_nl": probability } \
						   for probability in numpy.arange(0.000, 0.051, 0.001) ]
elif args.theory == "ethnocentrism":
	fixed_params = { **fixed_params,
					 "abroad_travel_chance_be": 0.001,
					 "abroad_travel_chance_nl": 0.001,
					 "domestic_travel_chance_be": 0.005,
					 "domestic_travel_chance_nl": 0.005,
					 "scaled_ethnocentrism": False,
					 "media_receptiveness": False }

	parameters_list = [ { "ethnocentrism_nl": 0.85,
						  "ethnocentrism_be": probability } \
						   for probability in numpy.arange(0, 1.1, 0.1) ]
elif args.theory == "scaled_ethnocentrism":
	fixed_params = { **fixed_params,
					 "abroad_travel_chance_be": 0.001,
					 "abroad_travel_chance_nl": 0.001,
					 "domestic_travel_chance_be": 0.005,
					 "domestic_travel_chance_nl": 0.005,
					 "media_receptiveness": False,
					 "ethnocentrism_nl": 0,
					 "ethnocentrism_be": 0, }

	parameters_list = [ { "scaled_ethnocentrism": True } ]
elif args.theory == "media":
	fixed_params = { **fixed_params,
					 "abroad_travel_chance_be": 0.001,
					 "abroad_travel_chance_nl": 0.001,
					 "domestic_travel_chance_be": 0.005,
					 "domestic_travel_chance_nl": 0.005,
					 "scaled_ethnocentrism": False,
					 "ethnocentrism_nl": 0,
					 "ethnocentrism_be": 0, }

	parameters_list = [ { "media_receptiveness": probability } \
						   for probability in numpy.arange(0, 1.05, 0.05) ]
else:
	print("Argument not recognised")
	sys.exit(0)

print("Launching simulations for the '{}' theory".format(args.theory))
print("Fixed parameters: {}".format(len(fixed_params)))
print("Variable parameters: {}".format(len(parameters_list[0])))
print("Iterations for each parameter combination: {}".format(args.iterations))
print("Max steps: {}".format(args.max_steps))

print("Launching simulations NOW")

batch_run = FixedBatchRunner(
    BorderModel,
    parameters_list,
    fixed_params,
    iterations=args.iterations,
    max_steps=args.max_steps,
    model_reporters={"data": lambda model: model.datacollector }
)

batch_run.run_all()

print("Simulations finished. Generating report...")

pandas_runs = []

run_data = batch_run.get_model_vars_dataframe()
for run in run_data.iloc:
	panda = run.data.get_model_vars_dataframe()
	panda.index.name = "step"

	for column in run_data.columns.values:
		if column in ["data", "border_heights"]:
			continue

		panda[column.lower()] = run[column]

	pandas_runs.append(panda)

mother_panda = pandas.concat(pandas_runs)
mother_panda.to_csv("{}.csv".format(args.theory), sep=";")

print("Succesfully written report. Exiting...")