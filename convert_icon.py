import cairosvg

# Convert SVG to PNG
cairosvg.svg2png(url="icon.svg", write_to="generated-icon.png", output_width=256, output_height=256)
print("Icon successfully converted to PNG!")