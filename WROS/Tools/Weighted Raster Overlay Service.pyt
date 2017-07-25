import arcpy
import types
import string, random, os
import xml
import xml.etree.cElementTree as ET
import numpy as np

class Toolbox(object):
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "Weighted Raster Overlay Service Tools"
        self.alias = "wroservice"

        # List of tool classes associated with this toolbox
        self.tools = [CreateWeightedOverlayMosaic]


class CreateWeightedOverlayMosaic(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Create Weighted Overlay Mosaic"
        self.description = "Creates a new mosaic dataset that you can use to share as a weighted raster overlay service on ArcGIS Online or your portal."
        self.description += "The output mosaic dataset contains the raster layers in the input map document."
        self.canRunInBackground = False
        self.inTableSchema=["title","rasterPath","Label","minRangeValue","maxRangeValue","SuitabilityVal","Description","NoDataVal","NoDataLabel","URL"]
        self.outMoFields=[('Title','String',50),('Description','String',1024),('Url','String',1024),('InputRanges','String',256),('NoDataRanges','String',256),('RangeLabels','String',1024),('NoDataRangeLabels','String',1024),('OutputValues','String',256),('Metadata','String',1024),('dataset_id','String',50)]
        self.updMoFields=["Title","RangeLabels","InputRanges","OutputValues"]
        self.updMoFieldsQuery=["Name"]
        self.rasterType='Raster Dataset'
        self.resampling='NEAREST'
        self.woXml='.aux.wo.xml'

    def getParameterInfo(self):
        """Define parameter definitions"""

        in_workspace = arcpy.Parameter(
        displayName="Output Geodatabase",
        name="in_workspace",
        datatype="DEWorkspace",
        parameterType="Required",
        direction="Input")

        # set a default workspace
        in_workspace.value=arcpy.env.workspace

        in_mosaicdataset_name = arcpy.Parameter(
        displayName="Mosaic Dataset Name",
        name="in_mosaicdataset_name",
        datatype="GPString",
        parameterType="Required",
        direction="Input")

        arcpy.env.outputCoordinateSystem = arcpy.SpatialReference(3857)

        outMosaic=arcpy.Parameter(
        displayName="Output Mosaic Dataset",
        name="outMosaic",
        datatype="DEMosaicDataset",
        parameterType="Derived",
        direction="Output")

        params = [in_workspace,in_mosaicdataset_name,outMosaic]

        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        # should check for advanced as this requires frequency tool
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""

        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        try:
            if (parameters[0].value):
                desc = arcpy.Describe(parameters[0].valueAsText)
                if desc.workspaceType != 'LocalDatabase':
                    parameters[0].setErrorMessage("Invalid workspace type: Use only file geodatabases for output workspace")
                    return

            if (parameters[1].value):
                if (str(parameters[0].value) != None or str(parameters[0]) != "#"):
                    mdPath = os.path.join(parameters[0].valueAsText,parameters[1].valueAsText)
                    if arcpy.Exists(mdPath):
                        parameters[1].setWarningMessage(parameters[1].valueAsText + ": Existing dataset will be overwritten.")

        # TODO: Most error handling (example: e1.message) is incorrect at py 3
        # you may seen this in the addmessages window - determine what the correct syntax is and fix all statements

        except Exception as e1:
            parameters[0].setErrorMessage(e1.message)
            return

        return

    def execute(self, parameters, messages):
        """The source code of the tool."""

        # validate the layers
        p=arcpy.mp.ArcGISProject("CURRENT")
        m=p.listMaps("*")[0]
        lyrs=m.listLayers()
        lyrCheck=[]
        lyrPaths=[]
        for l in lyrs:
            if l.isRasterLayer:
                if l.name in lyrCheck:
                    arcpy.AddError("This document contains duplicate raster layer names. Use uniquely named layers.")
                    return
                else:
                    lyrCheck.append(l.name)
                    if l.supports("DATASOURCE"):
                        lyrPaths.append(l.dataSource)

        outMosaic=""
        workspace=""
        rasterPaths=[]
        woXmls=[]

        try:

            # if there's no workspace set in param0, set it to the default workspace
            if (str(parameters[0].value) == None or str(parameters[0]) == "#"):
                arcpy.AddWarning("Setting workspace to {}".format(arcpy.env.workspace))
                workspace=arcpy.env.workspace
            else:
                workspace=parameters[0].valueAsText

            # make sure the workspace exists
            if arcpy.Exists(workspace)==False:
                arcpy.AddError("Workspace {} does not exist".format(workspace))
                return

            # describe the workspace to make sure it's an fGdb
            desc = arcpy.Describe(workspace)
            if desc.workspaceType != 'LocalDatabase':
                arcpy.AddError("Invalid workspace type: {}".format(workspace))
                return

            # if there's no output mosaic name (param1), exit
            if (str(parameters[1].value) == None or str(parameters[1]) == "#"):
                arcpy.AddError("Missing output mosaic name")
                return
            else:
                mosaicName=parameters[1].valueAsText

            # Create wo.xml files that contain input ranges, output values, and range labels
            if (self.AddWeightedOverlayRemapValues(lyrs)) == False:
                return

            # Create a mosaic path from param1 and 2
            outMosaic = os.path.join(workspace,mosaicName)

            # remove if it exists
            if arcpy.Exists(outMosaic):
                arcpy.Delete_management(outMosaic)
                arcpy.AddMessage(arcpy.GetMessages())

            arcpy.AddMessage("Creating mosaic...")

            # web mercator for all mosaics
            spatialref=arcpy.SpatialReference(3857)

            # Create the mosaic and get its output (for the output param)
            arcpy.AddMessage("Creating the mosaic dataset")
            res=arcpy.CreateMosaicDataset_management(workspace,mosaicName,spatialref,'#', '#', 'NONE', '#')

	    #JW edits on 7/18/17. Change the Mosaic interpolation mode to nearest neighbor
            res =arcpy.SetMosaicDatasetProperties_management(res, resampling_type='NEAREST')

            arcpy.AddMessage(arcpy.GetMessages())
	    
	    
        except Exception as e2:
            arcpy.AddError("Error creating the mosaic {}:{} ".format(outMosaic,e2.message))
            return

        try:
            # create additional fields for the mosaic
            arcpy.AddMessage("Adding weighted overlay fields to the mosaic dataset")
            for fldDef in self.outMoFields:
                fname=fldDef[0]
                ftype=fldDef[1]
                flength=fldDef[2]

                arcpy.AddField_management(outMosaic,fname,ftype,field_length=flength) 	
                #TODO - KW: Change this from Added Field to .AddMessage(arcpy.GetMessages())
                arcpy.AddMessage(arcpy.GetMessages())

        except Exception as e3:
            arcpy.AddError("Error adding fields to the mosaic {}: ".format(outMosaic,e3.message))
            return

        try:
            # add rasters from the map document to the mosaic
            arcpy.AddMessage("Adding rasters to the mosaic")
            
            # for each layer in lyrPaths -
            #  1. verify there's a layer.wo.xml
            #  2. append the layer and the layer.wo.xml to 2 lists
            for lyr in lyrPaths:
                # check for the wo.xml file
                inaux = "{}{}".format(lyr,self.woXml) #str(inras) + '.aux.wo.xml'
                if arcpy.Exists(inaux):
                    rasterPaths.append(lyr)
                    woXmls.append(inaux)
                else:
                    arcpy.AddWarning("{} is missing a wo.xml file.".format(lyr))
                    arcpy.AddWarning("{} will not be inserted into the mosaic".format(lyr))

            if len(rasterPaths) > 0:
                arcpy.AddRastersToMosaicDataset_management(outMosaic,self.rasterType,rasterPaths)
                arcpy.AddMessage(arcpy.GetMessages())
            else:
                arcpy.AddError("No layers in this map document have wo.xml files. Please run tool Add Weighted Overlay Data to create these files.")
                return

        except Exception as e7:
            arcpy.AddError("Error adding rasters to the mosaic {}: ".format(e7.message))
            return

        try:
            # loop through woXmls list
            arcpy.AddMessage("Updating mosaic with data from wo.xml files...")
            for woFile in woXmls:
                # Read data from each xml
                e = xml.etree.ElementTree.parse(woFile).getroot()
                title=e[0][0].text
                inputranges=e[0][1].text
                outputVals=e[0][2].text
                labels=e[0][3].text
                rasterFileName=e[0][4].text

                # create a where clause from title
		# JWTODO: change query based on title to based on rasterfilename
                where="{}='{}'".format(self.updMoFieldsQuery[0],rasterFileName)

                # update the mosaic with data from the wo.xml file
                # self.updMoFields = ["Title","RangeLabels","InputRanges","OutputValues"]
                with arcpy.da.UpdateCursor(outMosaic,self.updMoFields,where) as cursor:
                    for row in cursor:
                        row[0]=title
                        row[1]=labels
                        row[2]=inputranges
                        row[3]=outputVals
                        cursor.updateRow(row)


            arcpy.SetParameter(2,outMosaic)

        except Exception as e4:
            arcpy.AddError("Error adding data to the mosaic {}: ".format(mosaicFullPath,e4.message))
            return

        return

    def makeInputRanges(this,sourceRaster):
        # Creates input ranges from classified colorizers (or no colorizers)
        res=arcpy.GetRasterProperties_management(sourceRaster,"MINIMUM")
        minVal=float(str(res.getOutput(0)))
        res=arcpy.GetRasterProperties_management(sourceRaster,"MAXIMUM")
        maxVal=float(str(res.getOutput(0)))

        # Create an equal interval array of values
        sourceValues=np.linspace(minVal,maxVal,6,endpoint=True)

        inputRangesForRemap=""
        
        # TODO: if we don't have 5 equal intervals, we need to handle this better than exiting
        # can we create 3 equal intervals?
        # what happens if len(sourceValules)<=0?
        if len(sourceValues) != 6:
            return False, inputRangesForRemap

        else:
            #format into pairs of min-inclusive/max exclusive
            inputRangesForRemap+="{},{}".format(sourceValues[0],sourceValues[1]) #pair 1
            inputRangesForRemap+=",{},{}".format(sourceValues[1],sourceValues[2]) #pair 2
            inputRangesForRemap+=",{},{}".format(sourceValues[2],sourceValues[3]) #pair 3
            inputRangesForRemap+=",{},{}".format(sourceValues[3],sourceValues[4]) #pair 4
            maxVal=float(sourceValues[5])
            maxVal+=1
            inputRangesForRemap+=",{},{}".format(sourceValues[4],maxVal) #pair 5
            
        return True, inputRangesForRemap

    def makeDataFromUniqueColorizer(this,symb):
        # creates input ranges from unique value colorizer

        uvLabels=""
        uvRngs=""
        inRngs1=[]
        inRngs2=[]
        combinedRngs=[]
        outVals=""
        
        if symb.colorizer.field!='Value':
            arcpy.AddError("Unable to process this layer. Symbolize on Value field")
            return False

        else:
            for grp in symb.colorizer.groups:
                for itm in grp.items:
                    # Create a comma-delimited list of labels
                    if len(uvLabels) < 1:
                        uvLabels='{}'.format(itm.label)
                    else:
                        uvLabels+=',{}'.format(itm.label)

                    # build two lists of unique values
                    v1=itm.values[0]
                    inRngs1.append(float(v1))
                    v2=itm.values[0]
                    inRngs2.append(float(v2))

                    # create a comma-delimited list of output values
                    # for now, all output values are set to 5
                    if len(outVals)<1:
                        outVals='5'
                    else:
                        outVals+=',5'

            # combine the two range lists
            combinedRngs=inRngs1+inRngs2
            
            # convert to a string after sorting
            combinedRngs.sort()
            uvRngs=','.join(str(x) for x in combinedRngs)

        return True, uvRngs, outVals, uvLabels

    def AddWeightedOverlayRemapValues(this,mLyrs):
        try:
            if (mLyrs):
                rasterLayers=[]
                lyrCheck=[]

                # check for raster layers
                for l in mLyrs:
                    if (l.isRasterLayer):
                        if l.name in lyrCheck:
                            arcpy.AddError("This document contains duplicate raster layer names. Use uniquely named layers.")
                            return False
                        else:
                            lyrCheck.append(l.name)
                            rasterLayers.append(l)

                    else:
                        arcpy.AddWarning("Cannot process layer {}. Not a raster layer".format(l.name))

                # exit if there are none
                if len(rasterLayers)<1:
                    arcpy.AddError("There are no raster layers to process in this document")
                    return False
                else:
                    arcpy.AddMessage("Processing {} raster layers".format(len(rasterLayers)))

                # TODO - KW: some of the following variables are not used - remove them.
                rastertitle=""
                rasterpath=""
                rasterExtension=""
                outputValues=""
                labels=""

                rasterFileName = ""

                inras=""
                inaux=""

                # Process Unique values and stretch/classified colorizers
                for l in rasterLayers:
                    try:
                        arcpy.AddMessage("Processing layer {}...".format(l.name))
                        rastertitle=l.name # This is probably the layer name
                        # Create another variable that represents the toc layer name
                        rasterpath=l.dataSource
                        #layerDesc=l.description
                        rasterExtension="" # clear any values set

                        # Define raster file name from folder path
                        counter = rasterpath.rfind("\\") +1
                        rasterFileName = rasterpath[counter:len(rasterpath)]

                        # describe the raster to get its no data values & other info
                        desc=arcpy.Describe(l)
                        inras=desc.catalogPath
                        inaux="{}.aux.wo.xml".format(inras)
                        arcpy.AddMessage(inaux)

                        # check for an extension in the name (like foo.tif)
                        try:
                            rasterExtension=desc.extension

                            # remove it from the title
                            rastertitle=rastertitle.replace(rasterExtension,"")
                            if rastertitle.endswith("."):
                                rastertitle=rastertitle.replace(".","")
                            arcpy.AddWarning("Removed extension {} from layer {}".format(rasterExtension,rastertitle))

                            # remove it from file name
                            rasterFileName = rasterFileName.replace(rasterExtension, "")
                            if rasterFileName.endswith("."):
                                rasterFileName=rasterFileName.replace(".","")


                        except Exception as eExt:
                            arcpy.AddError("Extension error {}".format(eExt.message))
                            pass


                        # Process unique values differently than stretch/classified
                        sym=l.symbology

                        # string that represents min inclusive/max exclusive values
                        inputRanges=""

                        if hasattr(sym,'colorizer') and sym.colorizer.type == "RasterUniqueValueColorizer":
                            arcpy.AddMessage("{} is uvr".format(inras))
                            worked, inputRanges, outputValues, labels = this.makeDataFromUniqueColorizer(sym)
                            if worked==False:
                                arcpy.AddWarning("Could not create ranges for unique colorizer in {}".format(inras))
                                arcpy.AddMessage(arcpy.GetMessages())
                                continue
                                
                            arcpy.AddMessage("UVR ranges {}".format(inputRanges))
                            arcpy.AddMessage("UVR Values {}".format(outputValues))
                            arcpy.AddMessage("UVR Labels: {}".format(labels))
                            
                        else:
                            # no colorizer, try to the min-max values anyways
                            # check min and max values in the dataset
                            worked, inputRanges = this.makeInputRanges(inras)
                            if worked==False:
                                arcpy.AddWarning("Could not create ranges for {}".format(inras))
                                arcpy.AddMessage(arcpy.GetMessages())
                                continue

                            else:
                                # set outputValues and Range Labels
                                outputValues="1,3,5,7,9"
                                labels="Very Low, Low, Medium, High, Very High"
                       

                        # delete the wo.xml if it exists
                        if arcpy.Exists(inaux):
                            arcpy.Delete_management(inaux)
                            arcpy.AddMessage(arcpy.GetMessages())
                        else:
                            arcpy.AddMessage("Creating file {}".format(inaux))

                        # create the wo.xml file and write data to it.
                        pmdataset=ET.Element("PAMDataset")
                        metadata=ET.SubElement(pmdataset,"Metadata")
                        ET.SubElement(metadata,"MDI", key="Title").text=rastertitle
                        ET.SubElement(metadata,"MDI", key="InputRanges").text=inputRanges
                        ET.SubElement(metadata,"MDI", key="OutPutValues").text=outputValues
                        ET.SubElement(metadata,"MDI", key="RangeLabels").text=labels
                        ET.SubElement(metadata, "MDI", key="FileName").text=rasterFileName
                        tree=ET.ElementTree(pmdataset)
                        tree.write(inaux)

                        arcpy.AddMessage("input ranges {}".format(inputRanges))
                        arcpy.AddMessage(arcpy.GetMessages())


                    except Exception as e1:
                        arcpy.AddError("Exception occurred: {}".format(e1.message))
                        return False
            else:
                # TODO: map document references ArcGIS Desktop - figure out what correct term is (aprx?)
                # also - is aMapDoc declared and used? - if not remove it.
                arcpy.AddError("Invalid map document: {}".format(aMapdoc))
                return False

            return True

        except Exception as e:
            arcpy.AddError("Exception occurred: {}".format(e.message))
            return False
