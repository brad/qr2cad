#!/usr/bin/python
# -*- coding: utf-8 -*-
u"""
Copyright (C) 2011-2014 Brad Pitcher <bradpitcher@gmail.com>

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""

import os
import qrcode
import subprocess

from argparse import ArgumentParser
from PIL import Image
from StringIO import StringIO


def get_args():
    parser = ArgumentParser(description='Convert qr codes to CAD objects')
    parser.add_argument('content', metavar='CONTENT', type=str, help='The content you want to create a qr code for.')
    parser.add_argument('-x', dest='dxf', action='store_const', const=True, default=False, help='Defaults to .stl by default, this option changes output to .dxf')
    parser.add_argument('-m', dest='make', action='store_const', const=True, default=False, help='Outputs qr2cad.scad by default, this options makes the result into a .dxf or .stl')
    parser.add_argument('-d', dest='maxdim', type=int, default=74, help='The maximum size in mm to make the x or y dimension.')
    parser.add_argument('-z', dest='zheight', type=int, default=5, help='The max z-height of the text, defaults to 5. Not relevant for .dxf files')
    return parser.parse_args()

def get_image_data(data):
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)

    im = qr.make_image()
    return [list(im.getdata()), im.size[0], im.size[1]]

def create_matrix(data, width):
    white = 255
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
            line.append(0 if data[i] == white else 1)
            i += 4
        else:
            i += 1

    return matrix

def create_scad(matrix, filename, width, height, zheight, maxdim, dxf):
    scad_width = (width-2)/2
    scad_height = (height-2)/2
    if width > height:
        scale = [float(maxdim)/scad_width, (maxdim*float(scad_height)/scad_width)/scad_height, 1]
    else:
        scale = [(maxdim*float(scad_width)/scad_height)/scad_width, float(maxdim)/scad_height, 1]
    f = open(filename, 'w')
    f.write("""
2d = %s;
fudge = 0.01;
block_z = %i;
block_size = 2;
matrix_rows = %i;
matrix_cols = %i;
""" % ('true' if dxf else 'false', zheight, scad_height/2, scad_width/2))
    # Format the matrix nicely
    f.write('\nmatrix = [\n')
    for line in matrix:
        f.write('%s,\n' % (repr(line)))
    f.write('];')
    f.write(display_matrix_core(scale))
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

def display_matrix_core(scale):
    return """
module block(bit, x, y, z, 2d) {
    if(2d) {
        square([x, y]);
    }
    else {
        cube([x, y, z*bit]);
    }    
}

scale(%s) translate([-block_size*matrix_cols/2, block_size*(matrix_rows/2-1), 0]) {
    if( ! 2d) {
        translate([0, -block_size*(matrix_rows-1), 0]) {
            cube([block_size*matrix_cols, block_size*matrix_rows, 1]);
        }
    }
    translate([0, 0, 1]) {
        for(i = [0 : matrix_rows-1]) {
            for(j = [0 : matrix_cols-1]) {
                if(matrix[i][j] != 0) {
                    translate([block_size*j, -block_size*i, 0]) {
                        if(i == 0 && j == matrix_cols-1) {
                            // Draw the top right corner block normal size
                            block(matrix[i][j], block_size, block_size, block_z, 2d);
                        }
                        else if(i == 0) {
                            // Draw blocks on the top row with a x fudge factor added
                            block(matrix[i][j], block_size+fudge, block_size, block_z, 2d);
                        }
                        else if(j == matrix_cols-1) {
                            // Draw blocks on the right column with a y fudge factor added
                            block(matrix[i][j], block_size, block_size+fudge, block_z, 2d);
                        }
                        else {
                            // For blocks that aren't on the edge, add a fudge factor so they are connected to other blocks
                            block(matrix[i][j], block_size+fudge, block_size+fudge, block_z, 2d);
                        }
                    }
                }
            }
        }
    }
}
""" % (repr(scale))

if __name__ == '__main__':
    args = get_args()
    filename = 'qr2cad.scad'

    # Generates an RGB array, given content, using the google chart API
    [data, width, height] = get_image_data(args.content)

    # Outputs a matrix that OpenSCAD can use
    matrix = create_matrix(data, width)

    # Outputs a .scad file that can be used to create a .stl or .dxf file
    create_scad(matrix, filename, width, height, args.zheight, args.maxdim, args.dxf)
    if args.make:
        # Outputs a .dxf or .stl
        make_scad(args.dxf, filename)
