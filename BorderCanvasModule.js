var CanvasModule = function(canvas_width, canvas_height, grid_width, grid_height) {
	// Create the element
	// ------------------

	// Create the tag with absolute positioning :
	var canvas_tag = `<canvas width="${canvas_width}" height="${canvas_height}" class="world-grid"/>`

	var parent_div_tag = '<div style="height:' + canvas_height + 'px; width:' + canvas_width + 'px; \
									  display: inline-block;" class="world-grid-parent"></div>'

	// Append it to body:
	var canvas = $(canvas_tag)[0];
	var interaction_canvas = $(canvas_tag)[0];
	var parent = $(parent_div_tag)[0];

	//$("body").append(canvas);
	$("#elements").append(parent);
	parent.append(canvas);
	parent.append(interaction_canvas);

	// Create the context for the agents and interactions and the drawing controller:
	var context = canvas.getContext("2d");

	// Create an interaction handler using the
	var interactionHandler = new InteractionHandler(canvas_width, canvas_height, grid_width, grid_height, interaction_canvas.getContext("2d"));
	var canvasDraw = new GridVisualization(canvas_width, canvas_height, grid_width, grid_height, context, interactionHandler);

	this.render = function(data) {
		canvasDraw.resetCanvas();
		canvasDraw.drawSpheres(data["spheres"]);
		for (var layer in data["cells"])
			canvasDraw.drawLayer(data["cells"][layer]);
		canvasDraw.drawGridLines("#eee");
		canvasDraw.drawBorder(data["border"]);
		canvasDraw.drawSphereNames(data["spheres"]);
	};

	this.reset = function() {
		canvasDraw.resetCanvas();
	};

};
