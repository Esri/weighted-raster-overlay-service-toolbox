##-------------------------------------------------------------------------------
# Name        : Distance.py
# ArcGIS Version: ArcGIS 10.1
# Script Version: 2.3
# Name of Company : Environmental System Research Institute
# Author        : ESRI raster solutions team
# Date          : 09-05-2014
# Purpose 	    : To export images(AOIs) from ArcGIS Image Services for analysis
# Created	    : 05-09-2014
# LastUpdated  	: 05-09-2014
# Required Argument : To be loaded and run from within ArcMap
# with user arguments
#
# <Output file>
# Optional Argument : None
# Usage         :  Load using ArcMap catalog browser.
# Copyright	    : Copyright 2015 Esri
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#       http://www.apache.org/licenses/LICENSE-2.0
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#-------------------------------------------------------------------------------

import arcpy
from arcpy.sa import *
import os,sys
from arcpy import env

aa = os.path.dirname(os.path.realpath(__file__))

def edensity(fcpath,fcname,outraster,cellsize,rmask):
    try:
        arcpy.CheckOutExtension("Spatial")
        arcpy.env.workspace = os.path.dirname(fcpath)
#        arcpy.env.workspace = fcpath
        arcpy.env.mask = rmask
        outedc = EucDistance(fcpath,"#",cellsize)
        outedc.save(outraster)
        return str(arcpy.GetMessages(0))
    except:
        return str(arcpy.GetMessages(0))


def main():
    pass

if __name__ == '__main__':
    main()
if len(sys.argv)<> 5:
    print " number of inputs are invalid"
    print " <Input Feature Class> <output Raster Path> <cell size > <mask file>"
    sys.exit()

infcpath = sys.argv[1] #"C:\\Image_Mgmt_Workflows\\LandscapeModeler\\Data_for_PB_testing\\Data_for_rasterization_testing"
fcname  = os.path.basename(infcpath) #"roads.shp"
outraster = sys.argv[2] #"c:\\temp\\todel\\dd1suuss1.tif"
cellsize = sys.argv[3] #"1000"
mask = sys.argv[4] #"C:\\Image_Mgmt_Workflows\\LandscapeModeler\\Data_for_PB_testing\\Data_for_rasterization_testing\\aquifers.shp"
edensityout = edensity(infcpath,fcname,outraster,cellsize,mask)
print edensityout
print " Process Done"
