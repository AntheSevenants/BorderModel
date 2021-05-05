from BorderModel import BorderModel
from BorderModel import distance_between_points

class CsvWriter:
	def __init__(self, filename):
		self.filename = filename
		self.file = open(filename, "w")

		self.file.write("name;distance;sound_mean_zero\n")

	def write_line(self, name, distance, sound_mean_zero):
		self.file.write("{};{};{}\n".format(name, distance, sound_mean_zero))

	def close(self):
		self.file.close()

# Instantiate a model
model = BorderModel(width=100, height=240, border_heights=[ 124, 104 ])

csv_writer = CsvWriter("nl_towns.csv")

# Go over every influence sphere...
for influence_sphere in model.influence_spheres:
	if influence_sphere.country == "The Netherlands":
		distance = distance_between_points(47, influence_sphere.x, 32, influence_sphere.y)
		sound_mean_zero = "1" if influence_sphere.sound_mean == 0 else "0"

		csv_writer.write_line(influence_sphere.name, distance, sound_mean_zero)

csv_writer.close()