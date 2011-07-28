#!/usr/bin/python
# -*- coding: utf-8 -*-
from argparse import ArgumentParser
from PIL import Image
from StringIO import StringIO
from urllib import urlopen
import os
import subprocess

def get_args():
	parser = ArgumentParser(description='Convert qr codes to CAD objects')
	parser.add_argument('-x', dest='dxf', action='store_const', const=True, default=False, help='Defaults to .stl by default, this option changes output to .dxf')
	parser.add_argument('-m', dest='make', action='store_const', const=True, default=False, help='Outputs qr2cad.scad by default, this options makes the result into a .dxf or .stl')
	parser.add_argument('-u', dest='url', type=str, default='http://www.thingiverse.com/thing:10408', help='The url you want to create a qr code for.')
	parser.add_argument('-d', dest='maxdim', type=int, default=150, help='The maximum size in mm to make the x or y dimension. Only applies if exporting to .scad and/or .stl.')
	parser.add_argument('-z', dest='zheight', type=int, default=5, help='The max z-height of the text, defaults to 5. Not relevant for .dxf files')
	return parser.parse_args()

def get_image_data(url):
	chart_url = 'http://chart.apis.google.com/chart?chs=150x150&cht=qr&chl=%s&choe=ISO-8859-1' % (url)
	data = urlopen(chart_url).read()
	im = Image.open(StringIO(data))
	return [list(im.getdata()), im.size[0], im.size[1]]

def create_matrix(data, zheight, width):
	white = 255*len(data[0])
	matrix = []
	line = []
	i = width
	while i < len(data):
		mod = i%width
		if mod == 0 and i != width:
			matrix.append(line)
			i += width*3
			line = []
		if mod > 0 and mod < width-1:
			line.append(0 if sum(data[i]) == white else zheight)
			i += 4
		else:
			i += 1

	return matrix

def create_scad(matrix, filename, width, height, maxdim, dxf):
	if width > height:
		scale = [float(maxdim)/width, (maxdim*float(height)/width)/height, 1]
	else:
		scale = [(maxdim*float(width)/height)/width, float(maxdim)/height, 1]
	f = open(filename, 'w')
	f.write('message = %s;' % (repr(matrix)))
	f.write(display_matrix_core(len(matrix[0]), len(matrix), dxf))
	f.close()
	print 'SCAD file is '+filename

def make_scad(dxf, scadfilename):
	openscadexec = 'openscad'
	windows = 'C:\Program Files\OpenSCAD\openscad.exe'
	mac = '/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD'
	if os.path.exists(windows):
		openscadexec = windows
	elif os.path.exists(mac):
		openscadexec = mac
	outfilename = 'qr2cad.%s' % ('dxf' if dxf else 'stl')
	command = [openscadexec, '-m', 'make', '-x' if dxf else '-s', outfilename, scadfilename]
	print 'Exporting to %s' % ('DXF' if dxf else 'STL')
	subprocess.call(command)
	print '%s file is %s' % ('DXF' if dxf else 'STL', outfilename)

def display_matrix_core(width, height, dxf):
	return """
message_cols = %s;
message_rows = %s;
fudge = 0.01;
block_width = 2;
block_z = 1;

xy = block_width;
xy1 = block_width-fudge;
xy2 = block_width-fudge*2;

translate([-block_width*message_cols/2, block_width*message_rows/2, 0]) {
	%s
	translate([0, 0, 1]) {
		for(i = [1 : message_rows-2]) {
			for(j = [1 : message_cols-2]) {
				if(message[i][j] != 0) {
					// If connected only by a corner to the block to the lower-left
					if(message[i][j-1] == 0 && message[i+1][j] == 0 && message[i+1][j-1] > 0) {
						translate([block_width*j+fudge, -block_width*i+fudge, 0]) {
							// Also corner-connected to the block to the lower-right
							if(message[i][j+1] == 0 && message[i+1][j+1] > 0) {
								%s([xy2, xy1%s]);
							}
							else {
								%s([xy1, xy1%s]);
							}
						}
					}
					// if connected only by a corner to the block to the lower-right
					else if(message[i+1][j] == 0 && message[i][j+1] == 0 && message[i+1][j+1] > 0) {
						translate([block_width*j, -block_width*i+fudge, 0]) {
							%s([xy1, xy1%s]);
						}
					}
					else {
						// This is just your average block
						translate([block_width*j, -block_width*i, 0]) {
							%s([xy+fudge/2, xy+fudge/2%s]);
						}
					}
				}
			}
		}
	}
}
""" %	(
		width,
		height,
	"""translate([0, -block_width*(message_rows-1), 0]) {
		cube([block_width*message_cols, block_width*message_rows, 1]);
	}
	""" if not dxf else "",
		'square' if dxf else 'cube',
		'' if dxf else ', block_z*message[i][j]',
		'square' if dxf else 'cube',
		'' if dxf else ', block_z*message[i][j]',
		'square' if dxf else 'cube',
		'' if dxf else ', block_z*message[i][j]',
		'square' if dxf else 'cube',
		'' if dxf else ', block_z*message[i][j]'
	)

if __name__ == '__main__':
	args = get_args()
	filename = 'qr2cad.scad'

	# Generates an RGB array, given a url, using the google chart API
	[data, width, height] = get_image_data(args.url)

	# Outputs a matrix that OpenSCAD can use
	matrix = create_matrix(data, args.zheight, width)

	# Outputs a .scad file that can be used to create a .stl or .dxf file
	create_scad(matrix, filename, width, height, args.maxdim, args.dxf)
	if args.make:
		# Outputs a .dxf or .stl
		make_scad(args.dxf, filename)
