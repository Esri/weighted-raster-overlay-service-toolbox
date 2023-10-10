#-------------------------------------------------------------------------------
# Name        : Weighted Raster Overlay Service tools
# ArcGIS Version: ArcGIS 10.5
# Name of Company : Environmental System Research Institute
# Author        : Esri
# Copyright	    :    Copyright 2017 Esri
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
import locale
import os
import numpy as np

# Set the resampling method environment to Nearest
arcpy.env.resamplingMethod = "NEAREST"

# Commas are used as the range label delimiter in WRO mosaic attribute tables,
# and thus cannot be used within range labels. Define the delimiter substitution
# character as a global variable.
DELIM_SUB = ";"

class Toolbox(object):
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "Weighted Raster Overlay Service Tools"
        self.alias = "wroservice"

        # List of tool classes associated with this toolbox
        self.tools = [
            CreateWeightedOverlayMosaic,
            UpdateWROLayerInfo,
            UpdateWROClassification,
        ]

class UpdateWROClassification(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Update WRO Layer Classification"
        self.description = "Updates layer classification ranges in a weighted overlay mosaic."
        self.canRunInBackground = False
        self.mo_flds = ["Title", "RangeLabels", "InputRanges", "OutputValues"]


    def getParameterInfo(self):
        """Define parameter definitions"""
        in_mosaic = arcpy.Parameter(
        displayName="Input Weighted Overlay Mosaic",
        name="inMosaic",
        datatype="DEMosaicDataset",
        parameterType="Required",
        direction="Input")

        wro_lyr=arcpy.Parameter(
        displayName="WRO Mosaic Layer",
        name="in_mosaic_row",
        datatype="GPString",
        parameterType="Required",
        direction="Input")
        wro_lyr.filter.type = "ValueList"

        wro_title = arcpy.Parameter(
        displayName="WRO Layer Title",
        name="wroTitle",
        datatype="GPString",
        parameterType="Required",
        direction="Input")

        mosaic_lyr_data = arcpy.Parameter(
        displayName="Mosaic Layer Data",
        name="mosaicLayerData",
        datatype="GPValueTable",
        parameterType="Required",
        direction="Input")
        mosaic_lyr_data.columns = [
            ['GPString','Range Label'],
            ['GPDouble', 'Min Range'],
            ['GPDouble', 'Max Range'],
            ['GPLong', 'Suitability Value'],
        ]
        mosaic_lyr_data.filters[3].type = "ValueList"
        mosaic_lyr_data.filters[3].list = [0,1,2,3,4,5,6,7,8,9]

        out_mosaic=arcpy.Parameter(
        displayName="Output Mosaic Dataset",
        name="outMosaic",
        datatype="DEMosaicDataset",
        parameterType="Derived",
        direction="Output")
        out_mosaic.parameterDependencies = [in_mosaic.name]
        out_mosaic.schema.clone = True

        params = [in_mosaic, wro_lyr, wro_title, mosaic_lyr_data, out_mosaic]

        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True


    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        if (
            all(parameters[i].altered for i in range(4))
            and not any(parameters[i].hasBeenValidated for i in range(4))
        ):
            # Short-circuit updateParamers() when all parameters have been specified
            # up front (e.g. via Python interface)
            return

        if parameters[0].value:

            # Get list of layer names and populate WRO Mosaic Layer param
            names = []
            with arcpy.da.SearchCursor(parameters[0].value, "Name") as cur:
                for row in cur:
                    names.append(row[0])
            parameters[1].filter.list = names

            if not parameters[1].hasBeenValidated and parameters[1].altered:
                # Clear other params
                parameters[2].value = None
                parameters[3].value = None

                # Clear values
                label_list = []
                range_list = []
                suitability_list = []

                # Check for required mosaic dataset fields
                missing_flds = []
                fld_list = [fld.name for fld in arcpy.ListFields(parameters[0].value)]
                for fld in self.mo_flds:
                    if fld not in fld_list:
                        missing_flds.append(fld)

                # If any fields are missing, show them in an error message
                if missing_flds:
                    parameters[0].setErrorMessage("Missing fields {} in {}".format(missing_flds, parameters[0].valueAsText))
                    return

                # Get Layer Title and Mosaic Layer Data values for user-selected Mosaic Layer (param 1)
                if parameters[1].value: # and parameters[1].altered:
                    where = "Name = '" + parameters[1].valueAsText + "'"
                    with arcpy.da.SearchCursor(parameters[0].value, self.mo_flds, where) as cur:
                        row = cur.next()
                        self._labels = row[1]
                        self._ranges = row[2]
                        self._output_values = row[3]

                        if row[0]:
                            parameters[2].value = row[0]
                        if row[1]:
                            label_list = row[1].split(",")
                        if row[2]:
                            range_list = row[2].split(",")
                        if row[3]:
                            suitability_list = row[3].split(",")

                    # Write values to UI value table
                    out_values = []
                    for i in range(len(suitability_list)):
                        out_values.append([str(label_list[i]), float(range_list[i*2]), float(range_list[i*2+1]), int(suitability_list[i])])

                    parameters[3].value = out_values

        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        # Check for required mosaic dataset fields
        if parameters[0].value and not parameters[0].hasBeenValidated:
            missing_flds = []
            fld_list = [fld.name for fld in arcpy.ListFields(parameters[0].value)]
            for fld in self.mo_flds:
                if fld not in fld_list:
                    missing_flds.append(fld)
            # If any fields are missing, show them in an error message
            if missing_flds:
                parameters[0].setErrorMessage(
                    "Missing fields {} in {}".format(
                        missing_flds, parameters[0].valueAsText
                    )
                )

        # Verify max value of range matches min value of next range
        # and check range labels for unsupported characters
        if parameters[3].value:
            range_labels = []
            range_limits = []
            for val in parameters[3].value:
                range_labels.append(val[0])
                range_limits.append((val[1], val[2]))
            for label in range_labels:
                if "," in label:
                    parameters[3].setWarningMessage(
                        "Unsupported character '{}' in range labels will be replaced with '{}'".format(
                            ",", DELIM_SUB
                        )
                    )
                    break
            for i in range(len(range_limits) - 1):
                j = i + 1
                range_i_max = range_limits[i][1]
                range_j_min = range_limits[j][0]
                if range_i_max != range_j_min:
                    parameters[3].setErrorMessage(
                        "Range values mismatch: {} and {}".format(
                            range_i_max, range_j_min
                        )
                    )
                    break

        return


    def execute(self, parameters, messages):
        """The source code of the tool."""
        # Read parameters from UI
        mosaic_dataset = parameters[0].value
        name = parameters[1].valueAsText
        title = parameters[2].valueAsText
        value_tbl = parameters[3].value

        # Where clause
        where = "Name = '{}'".format(name)

        # Read values from value table
        range_limits = []
        range_labels = []
        output_values = []
        for rng_lbl, rng_min, rng_max, suit_val in value_tbl:
            if "," in rng_lbl:
                arcpy.AddWarning(
                    "Unsupported character '{}' in range label '{}' has been replaced with '{}'".format(
                        ",", rng_lbl, DELIM_SUB
                    )
                )
            range_limits.extend([str(rng_min), str(rng_max)])
            range_labels.append(rng_lbl.replace(",", DELIM_SUB))
            output_values.append(str(suit_val))
        range_limits = ",".join(range_limits)
        range_labels = ",".join(range_labels)
        output_values = ",".join(output_values)

        # Check for user changes
        changes = False

        # also get oid of selected row in the mosaic
        id=-1
        fields=list(self.mo_flds)
        fields.append("OID@")

        ##field=["Title", "RangeLabels", "InputRanges", "OutputValues","OID@"]
        with arcpy.da.SearchCursor(mosaic_dataset, fields, where) as cur:
            row = cur.next()
            if str(title) != str(row[0]):
                changes = True
                arcpy.AddMessage("Title:")
                arcpy.AddMessage("\tOriginal: " + str(row[0]))
                arcpy.AddMessage("\tNew: " + title)
            if str(range_labels).replace(", ", ",") != str(row[1]).replace(", ", ","):
                changes = True
                arcpy.AddMessage("Range Labels:")
                self.showMessages(row[1],range_labels)
            if range_limits != row[2]:
                changes = True
                arcpy.AddMessage("InputRanges:")
                self.showMessages(row[2],range_limits)
            if output_values != row[3]:
                changes = True
                arcpy.AddMessage("OutputValues:")
                self.showMessages(row[3],output_values)
            id=row[4]


        # Update Mosaic Dataset table with values from tool UI
        if changes:
            if title == "":
                title = None

            # Validate dataset min-max against value table
            # Export the mosaic's raster datasets paths
            raster_tbl = os.path.join("in_memory", "raster_paths")
            if arcpy.Exists(raster_tbl):
                arcpy.Delete_management(raster_tbl)

            arcpy.ExportMosaicDatasetPaths_management(parameters[0].value, raster_tbl)

            # where clause to search table by id from mosaic
            where1 = "SourceOID = " + str(id)

            arcpy.AddMessage("Querying {} using ID={}".format(raster_tbl,id))
            min_val = -1
            max_val = -1
            raster_path = ""

            # query the exported table to get the dataset's min/max value
            with arcpy.da.SearchCursor(raster_tbl, ["Path"], where1) as cur:
                for row in cur:
                    raster_path = row[0]
                    if arcpy.Exists(raster_path):
                        # Get min/max values
                        min_val = float(arcpy.GetRasterProperties_management(raster_path, "MINIMUM").getOutput(0))
                        max_val = float(arcpy.GetRasterProperties_management(raster_path, "MAXIMUM").getOutput(0))


            # compare to value table
            arcpy.AddMessage("Min-Max Values from dataset {} are {}-{}".format(raster_path,min_val,max_val))
            if str(value_tbl[0][1]) != str(min_val):
                value_tbl[0][1] = min_val
                arcpy.AddWarning("Set minimum range value to minimum cell value")
            elif float(value_tbl[-1][2]) <= float(max_val):
                arcpy.AddError("Maximum range value {} must be larger than maximum cell value {}".format(value_tbl[-1][2],max_val))
                return

            # Update record with user-defined values
            ##["Title", "RangeLabels", "InputRanges", "OutputValues"]
            with arcpy.da.UpdateCursor(mosaic_dataset, self.mo_flds, where) as cur:
                for row in cur:
                    try:
                        row = (title, range_labels, range_limits, output_values)
                        cur.updateRow(row)
                    except Exception as eIns:
                        arcpy.AddWarning("An error occurred while updating the mosaic: " + self.GetErrorMessage(eIns))


        else:
            arcpy.AddMessage("No changes found")

        return

    def showMessages(this,rowByIdx,paramTitle):
        if rowByIdx is None:
            arcpy.AddMessage("\tOriginal: Empty")
        else:
            arcpy.AddMessage("\tOriginal: " + rowByIdx)

        if paramTitle is None:
            arcpy.AddMessage("\tNew: Empty")
        else:
            arcpy.AddMessage("\tNew: " + paramTitle)

        return

class UpdateWROLayerInfo(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Update WRO Layer Info"
        self.description = "Lets you add descriptive information to a layer in your WRO Mosaic."
        self.canRunInBackground = False
        self.mo_flds = ["Title", "Description", "Url", "Metadata"]


    def getParameterInfo(self):
        """Define parameter definitions"""
        in_mosaic = arcpy.Parameter(
        displayName="Input Weighted Overlay Mosaic",
        name="inMosaic",
        datatype="DEMosaicDataset",
        parameterType="Required",
        direction="Input")

        wro_lyr=arcpy.Parameter(
        displayName="WRO Mosaic Layer",
        name="in_mosaic_row",
        datatype="GPString",
        parameterType="Required",
        direction="Input")

        wro_lyr.filter.type = 'ValueList'

        wro_title = arcpy.Parameter(
        displayName="WRO Layer Title",
        name="wroTitle",
        datatype="GPString",
        parameterType="Required",
        direction="Input")

        wro_lyr_desc = arcpy.Parameter(
        displayName="WRO Layer Description",
        name="wroLayerDescription",
        datatype="GPString",
        parameterType="Optional",
        direction="Input")

        wro_lyr_preview_url=arcpy.Parameter(
        displayName="WRO Layer Preview URL",
        name="wroLayerPreviewURL",
        datatype="GPString",
        parameterType="Optional",
        direction="Input")

        wro_lyr_info_url=arcpy.Parameter(
        displayName="WRO Layer Informational URL",
        name="wroLayerInfoURL",
        datatype="GPString",
        parameterType="Optional",
        direction="Input")

        out_mosaic=arcpy.Parameter(
        displayName="Output Mosaic Dataset",
        name="outMosaic",
        datatype="DEMosaicDataset",
        parameterType="Derived",
        direction="Output")

        out_mosaic.parameterDependencies=[in_mosaic.name]
        out_mosaic.schema.clone=True

        params = [in_mosaic ,wro_lyr, wro_title, wro_lyr_desc, wro_lyr_preview_url,
            wro_lyr_info_url, out_mosaic]

        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        if parameters[0].value:
            # clear the params
            if parameters[0].altered and not parameters[0].hasBeenValidated:
                parameters[1].value = None
                parameters[2].value = None
                parameters[3].value = None
                parameters[4].value = None
                parameters[5].value = None

            # Get list of layer names and populate WRO Mosaic Layer param
            names = []
            with arcpy.da.SearchCursor(parameters[0].value, "Name") as cur:
                for row in cur:
                    names.append(row[0])
            parameters[1].filter.list = names

            if parameters[1].altered and not parameters[1].hasBeenValidated:
                # Check for required mosaic dataset fields
                missing_flds = []
                fld_list = [fld.name for fld in arcpy.ListFields(parameters[0].value)]
                for fld in self.mo_flds:
                    if fld not in fld_list:
                        missing_flds.append(fld)
                # If any fields are missing, show them in an error message
                if missing_flds:
                    parameters[0].setErrorMessage("Missing fields {} in {}".format(missing_flds, parameters[0].valueAsText))
                    return

                # clear the params
                parameters[2].value = None
                parameters[3].value = None
                parameters[4].value = None
                parameters[5].value = None


                # Get Layer Title and Mosaic Layer Data values for user-selected Mosaic Layer (param 1)
                if parameters[1].value:
                    where = "Name = '" + parameters[1].valueAsText + "'"
                    ##["Title", "Description", "Url", "Metadata"]
                    with arcpy.da.SearchCursor(parameters[0].value, self.mo_flds, where) as cur:
                        row = cur.next()
##                        self._title = row[0]
##                        self._description = row[1]
##                        self._url = row[2]
##                        self._metadata = row[3]

                        if row[0]:
                            parameters[2].value = row[0]
                        if row[1]:
                            parameters[3].value = row[1]
                        if row[2]:
                            parameters[4].value = row[2]
                        if row[3]:
                            parameters[5].value = row[3]

        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""

        # Check urls
        if parameters[4].value:
            if not parameters[4].valueAsText.lower().startswith("http://") and not parameters[4].valueAsText.lower().startswith("https://"):
                parameters[4].setErrorMessage("Url must begin with http:// or https://")

        if parameters[5].value:
            if not parameters[5].valueAsText.lower().startswith("http://") and not parameters[5].valueAsText.lower().startswith("https://"):
                parameters[5].setErrorMessage("Url must begin with http:// or https://")

        return


    def execute(self, parameters, messages):
        """The source code of the tool."""
        # Read parameters from UI
        mosaic_dataset = parameters[0].value
        name = parameters[1].valueAsText
        title = parameters[2].valueAsText
        description = parameters[3].valueAsText
        url = parameters[4].valueAsText
        metadata = parameters[5].valueAsText

        # Where clause
        where = "Name = '" + name + "'"

        # Check for user changes
        changes = False
        ##["Title", "Description", "Url", "Metadata", "NoDataRanges", "NoDataRangeLabels"]
        with arcpy.da.SearchCursor(mosaic_dataset, self.mo_flds, where) as cur:
            row = cur.next()
            if title != row[0]:
                changes = True
                arcpy.AddMessage("Title:")
                arcpy.AddMessage("\tOriginal: " + row[0])
                arcpy.AddMessage("\tNew: " + title)
            if description != row[1]:
                changes = True
                arcpy.AddMessage("Description:")
                self.showMessages(row[1],description)
            if url != row[2]:
                changes = True
                arcpy.AddMessage("Url:")
                self.showMessages(row[2],url)
            if metadata != row[3]:
                changes = True
                arcpy.AddMessage("Metadata:")
##                arcpy.AddMessage("\tOriginal: " + row[3])
##                arcpy.AddMessage("\tNew: " + metadata)
                self.showMessages(row[3],metadata)

        # Update Mosaic Dataset table with values from tool UI
        if changes:
            if title == "":
                title = None
            if description == "":
                description = None
            if url == "":
                url = None
            if metadata == "":
                url = None

            # Update record with user-defined values
            ##["Title", "Description", "Url", "Metadata"]
            with arcpy.da.UpdateCursor(mosaic_dataset, self.mo_flds, where) as cur:
                for row in cur:
                    row = (title, description, url, metadata)
                    cur.updateRow(row)
        else:
            arcpy.AddMessage("No changes found")

        return

    def showMessages(this,rowByIdx,paramTitle):
        if rowByIdx is None:
            arcpy.AddMessage("\tOriginal: Empty")
        else:
            arcpy.AddMessage("\tOriginal: " + rowByIdx)

        if paramTitle is None:
            arcpy.AddMessage("\tNew: Empty")
        else:
            arcpy.AddMessage("\tNew: " + paramTitle)

        return


class CreateWeightedOverlayMosaic(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Create Weighted Overlay Mosaic"
        self.description = "Creates a new mosaic dataset that you can use to share as a weighted raster overlay service on ArcGIS Online or your portal."
        self.description += "The output mosaic dataset contains the raster layers in the input map document."
        self.canRunInBackground = False
        self.inTableSchema=["title","rasterPath","Label","minRangeValue","maxRangeValue","SuitabilityVal","Description","NoDataVal","NoDataLabel","URL"]
        self.outMoFields=[('Title','String',1024),('Description','String',1024),('Url','String',1024),('InputRanges','String',2048),('NoDataRanges','String',256),('RangeLabels','String',1024),('NoDataRangeLabels','String',1024),('OutputValues','String',256),('Metadata','String',1024),('dataset_id','String',1024)]
        self.updMoFields=["Title","RangeLabels","InputRanges","OutputValues"]
        self.updMoFieldsQuery=["Name"]
        self.resampling='NEAREST'

        self.outMoFields2=[['Title','TEXT','Title',1024],['Description','TEXT','Description',1024],['Url','TEXT','Url',1024],['InputRanges','TEXT','InputRanges',2048],['NoDataRanges','TEXT','NoDataRanges',256],['RangeLabels','TEXT','RangeLabels',1024],['NoDataRangeLabels','TEXT','NoDataRangeLabels',1024],['OutputValues','TEXT','OutputValues',256],['Metadata','TEXT','Metadata',1024],['dataset_id','TEXT','dataset_id',1024]]


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

        in_visible_only = arcpy.Parameter(
        displayName="Visible Layers Only",
        name="in_visible_only",
        datatype="GPBoolean",
        parameterType="Optional",
        direction="Input")

        params = [in_workspace,in_mosaicdataset_name,outMosaic,in_visible_only]

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

                # Show error if invalid characters are in mosiac dataset name.
                chars = set(" ~`!@#$%^&*(){}[]-+=<>,.?|")
                datasetName = str(parameters[1].value)
                if any((c in chars) for c in datasetName):
                    parameters[1].setErrorMessage("Invalid mosaic dataset name.")
                    return

        except Exception as e1:
            parameters[0].setErrorMessage(self.GetErrorMessage(e1))
            return

        return

    def execute(self, parameters, messages):
        """The source code of the tool."""

        p=arcpy.mp.ArcGISProject("CURRENT")
        m = p.activeMap
        if (not m):
            maps = p.listMaps("*")
            if (maps and (len(maps) > 0)):
                m = maps[0]
        if (not m):
            arcpy.AddError("There is no map to process")
            return

        visibleOnly = parameters[3].value
        lyrsinit=m.listLayers()
        lyrs = []
        lyrCheck=[]
        outMosaic=""
        workspace=""

        for l in lyrsinit:
            addLayer = True
            if l.isRasterLayer:

                d=arcpy.Describe(l)
                #arcpy.AddMessage(l.longName+ " "+d.datasetType+" - "+l.dataSource)
                #arcpy.AddMessage(l.name+ ", isWebLayer: "+str(l.isWebLayer)+", visible: "+str(l.visible))

                if addLayer and visibleOnly and (not l.visible):
                    addLayer = False

                if addLayer and hasattr(d,'datasetType'):
                    if d.datasetType=="MosaicDataset":
                        addLayer = False
                        arcpy.AddMessage("Cannot process mosaic dataset {}".format(l.name))

                if addLayer and l.isWebLayer:              
                    addLayer = False
                    arcpy.AddMessage("Cannot process web layer {}".format(l.name))

                if addLayer and (not l.supports("DATASOURCE")):              
                    addLayer = False
                    arcpy.AddMessage("Layer has no datasource {}".format(l.name))

                if addLayer and ((l.longName.find("\\Boundary") > 0) or (l.longName.find("\\Footprint") > 0) or (l.longName.find("\\Image") > 0)):
                    addLayer = False
                    arcpy.AddMessage("Layer not processed - " + l.longName)

                if addLayer and (l.name in lyrCheck):
                    addLayer = False
                    arcpy.AddMessage("This map contains duplicate raster layer names. Use uniquely named layers {}".format(l.name))

                if addLayer:
                    arcpy.AddMessage("Layer - " + l.longName)
                    lyrs.append(l)
                    lyrCheck.append(l.name)

        try:

            # if (True):
            #     arcpy.AddError("zzz short-circuit")
            #     return
        
            if (not lyrs):
                arcpy.AddError("There are no raster layers to process in this map")
                return

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
              
            # Create layer data that contains input ranges, output values, and range labels
            worked, lyrData = self.AddWeightedOverlayRemapValues(lyrs)
            if worked == False:
                return
            if (not lyrData):
                arcpy.AddError("No layers in this map document have layer data.")
                return

            # Create a mosaic path from param1 and 2
            outMosaic = os.path.join(workspace,mosaicName)

            # remove if it exists
            if arcpy.Exists(outMosaic):
                arcpy.Delete_management(outMosaic)
                arcpy.AddMessage(arcpy.GetMessages())

            arcpy.AddMessage("Creating mosaic...")

            # web mercator for all mosaics
            spatialref=arcpy.SpatialReference(3857) # @todo

            # Create the mosaic and get its output (for the output param)
            arcpy.AddMessage("Creating the mosaic dataset")
            res = arcpy.CreateMosaicDataset_management(workspace,mosaicName,spatialref,'#', '#', 'NONE', '#')

        except Exception as e2:
            arcpy.AddError("Error creating the mosaic {}: {}".format(outMosaic,self.GetErrorMessage(e2)))
            return

        try:
            # create additional fields for the mosaic
            arcpy.AddMessage("Adding weighted overlay fields to the mosaic dataset...")
            arcpy.AddFields_management(outMosaic,self.outMoFields2)
            # for fldDef in self.outMoFields:
            #     fname=fldDef[0]
            #     ftype=fldDef[1]
            #     flength=fldDef[2]

            #     arcpy.AddField_management(outMosaic,fname,ftype,field_length=flength)
            #     arcpy.AddMessage(arcpy.GetMessages())

        except Exception as e3:
            arcpy.AddError("Error adding fields to the mosaic {}: {}".format(outMosaic,self.GetErrorMessage(e3)))
            return

        try:
            #Change the Mosaic resampling type to Nearest Neighbor
            arcpy.AddMessage("Setting resampling type...")
            res = arcpy.SetMosaicDatasetProperties_management(res, resampling_type='NEAREST')
            arcpy.AddMessage(arcpy.GetMessages())

        except Exception as e_resampling:
            arcpy.AddError("Error setting resampling type {}: {}".format(outMosaic,self.GetErrorMessage(e_resampling)))
            return

        try:
            # add rasters from the map document to the mosaic
            arcpy.AddMessage("Adding rasters to the mosaic")

            calcStats = True
            rasters = []
            for item in lyrData:
                l = item[5]
                rasters.append(l.dataSource)
                if l.isWebLayer:
                    calcStats = False
            if len(rasters) > 0:
                arcpy.AddRastersToMosaicDataset_management(outMosaic,"Raster Dataset",rasters)
                arcpy.AddMessage(arcpy.GetMessages())
            else:
                arcpy.AddError("No layers in this map document have layer data.")
                #arcpy.AddError("No layers in this map document have layer data. Please run tool Add Weighted Overlay Data to create these files.")
                return

            #bnd = "outMosaic" + r"\boundary"

            #Calculate statistics
            if calcStats:
                arcpy.AddMessage("Calculating statistics...")
                arcpy.CalculateStatistics_management(outMosaic)
                arcpy.AddMessage("Calculated statistics on mosaic dataset.")

        except Exception as e7:
            arcpy.AddError("Error adding rasters to the mosaic {}: {}".format(outMosaic,self.GetErrorMessage(e7)))
            return

        try:
            # loop through layer data list
            arcpy.AddMessage("Updating mosaic with data from layer...")
            for item in lyrData:
                # Read data from each layer file
                title=item[0]
                inputranges=item[1]
                outputVals=item[2]
                labels=item[3]
                rasterFileName=item[4]

                # create a where clause from rasterfilename
                where="{}='{}'".format(self.updMoFieldsQuery[0],rasterFileName)

                arcpy.AddMessage('Updating {}'.format(title))

                # update the mosaic with data from the lyrData list
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
            arcpy.AddError("Error adding data to the mosaic {}: {}".format(outMosaic,self.GetErrorMessage(e4)))
            return

        return

    def makeInputRanges(this,layer,sourceRaster):
        # Creates input ranges from classified colorizers (or no colorizers)
        res=arcpy.GetRasterProperties_management(layer,"MINIMUM")
        minVal=float(str(res.getOutput(0)))
        res=arcpy.GetRasterProperties_management(layer,"MAXIMUM")
        maxVal=float(str(res.getOutput(0)))

        # Create an equal interval array of values
        sourceValues=np.linspace(minVal,maxVal,6,endpoint=True)

        inputRangesForRemap=""

        # Array must have 6 items
        if len(sourceValues) != 6:
            arcpy.AddWarning("Could not compute equal intervals in Raster {}".format(layer.name))
            return False, inputRangesForRemap

        # Check if all items in the array are the same
        if (sourceValues[0] == sourceValues[1] == sourceValues[2] == sourceValues[3]
            == sourceValues[4] == sourceValues[5]):
            ## all items in the array are the same!
            arcpy.AddWarning("Raster {} has same min and max value".format(layer.name))

            # create the max exclusive value
            maxVal=float(sourceValues[5])
            maxVal+=1

            # Create a single pair range
            inputRangesForRemap+="{},{}".format(sourceValues[4],maxVal) #has only 1 pair

            arcpy.AddWarning("Range for raster {} is {}".format(layer.name, inputRangesForRemap))
            arcpy.AddMessage(arcpy.GetMessages())

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

    # creates input ranges from raster classify colorizer
    def makeDataFromClassifyColorizer(this,layer,rsDataset,symb):
        classLabels=""
        classRngs=""
        inRngs1=[]
        inRngs2=[]
        outVals=""

        try:

            # see if we can read info from the colorizer:
            # first we need the raster dataset's min value
            res=arcpy.GetRasterProperties_management(layer,"MINIMUM")
            minVal=float(str(res.getOutput(0)))

            #add the min value to the inRngs1 list to set the classification's min value
            inRngs1.append(minVal)
            inRngs2.append(minVal)

            # loop through the breaks
            breaks="{}".format(symb.breakCount)
            for brk in symb.classBreaks:
                # populate inRngs for input values
                v1=brk.upperBound
                inRngs1.append(v1)
                v2=brk.upperBound
                inRngs2.append(v2)

                # Set all output values to 5 for now
                if len(outVals)<1:
                    outVals='5'
                else:
                    outVals+=',5'

            worked, classRngs = this.createInputRangesForRemap(inRngs1,inRngs2)

            #combine the two lists
            combinedRngs=inRngs1+inRngs2

            # sort, remove the 1st and last 2 items
            # then increment the last item, and finally convert it to strings
            # do this to create a list of min-inclusive,max-exlusive values for the raster remap function
            combinedRngs.sort()
            for x in [0,-1]: combinedRngs.remove(combinedRngs[x])

            lastValue=combinedRngs[-1]
            lastValue+=1
            combinedRngs.remove(combinedRngs[-1])
            combinedRngs.append(lastValue)
            thematicRange=','.join(str(x) for x in combinedRngs)

            arcpy.AddMessage("Input Ranges: " + str(thematicRange))

            # populate labels using the thematicRange
            labelsLst=thematicRange.split(",")
            labelsLst2=list(zip(labelsLst[0::2],labelsLst[1::2]))

            #format back into a string
            for l in labelsLst2:
                if len(classLabels) < 1:
                    classLabels='{} to {}'.format(l[0],l[1])
                else:
                    classLabels+=',{} to {}'.format(l[0],l[1])

            return worked, thematicRange, outVals, classLabels

        except Exception as e:
            arcpy.AddError("Exception occurred: {}".format(this.GetErrorMessage(e)))
            return False,"","",""


    # creates input ranges from unique value colorizer
    def makeDataFromUniqueColorizer(this,layer,rsDataset,symb):
        uvLabels=""
        uvRngs=""
        inRngs1=[]
        inRngs2=[]
        outVals=""

        try:

            # If the colorizer symbolizes on a field other than Value:
            # Fetch the Values from the raster's attribute table
            # and match them to the values and labels in the colorizer
            if symb.colorizer.field != 'Value':
                # Create a list of list that contains values and labels
                vals=[]
                for grp in symb.colorizer.groups:
                    for itm in grp.items:
                        vals.append([itm.values[0],itm.label])

                arcpy.AddMessage("Colorizer values and labels {}".format(vals))
                arcpy.GetMessages()

                # check for a value field
                d=arcpy.Describe(layer)
                foundValue=False
                for f in d.fields:
                    if f.name.lower()=="value": foundValue=True

                if foundValue==False:
                    arcpy.AddWarning("Raster {} has no value field".format(layer.name))
                    return False

                # get values and the colorizer field from the raster into a list of lists
                fields=["Value",symb.colorizer.field]
                rasterVals=[]
                with arcpy.da.SearchCursor(layer, fields) as cursor:
                    for row in cursor:
                        rasterVals.append([row[0],row[1]])

                # these two lists should be the same size
                if len(rasterVals) != len(vals):
                    arcpy.AddWarning("Could not determine raster values and raster colorizer values")
                    arcpy.GetMessages()
                    return False, "",[], ""

                # iterate through rasterValues and reach into vals to build a list of input ranges, outVals and uvLabels
                for rasterValue in rasterVals:
                    # format input ranges
                    inRngs1.append(float(rasterValue[0]))
                    inRngs2.append(float(rasterValue[0]))

                    # rasterValue[1] is the row value (the symb.colorizer.field)
                    for colorizerValue in vals:
                        if rasterValue[1].lower()==colorizerValue[0].lower():
                            # use the colorizerValue[1] (the label from the sym.colorizer) as our uvLabel
                            lbl = colorizerValue[1]
                            if "," in lbl:
                                arcpy.AddWarning(
                                    "Unsupported character '{}' in range label '{}' has been replaced with '{}'".format(
                                        ",", lbl, DELIM_SUB
                                    )
                                )
                                lbl = lbl.replace(",", DELIM_SUB)
                            if len(uvLabels) < 1:
                                uvLabels='{}'.format(lbl)
                            else:
                                uvLabels+=',{}'.format(lbl)

                    # create a comma-delimited list of output values
                    # for now, all output values are set to 5
                    if len(outVals)<1:
                        outVals='5'
                    else:
                        outVals+=',5'

                worked, uvRngs = this.createInputRangesForRemap(inRngs1,inRngs2)

            else:
                # Colorizer symbolizes on Value field
                for grp in symb.colorizer.groups:
                    for itm in grp.items:
                        try:
                            # handle locale setting for seperators (,.) in numbers
                            locale_decimal = locale.localeconv()["decimal_point"]
                            v1 = "".join(e for e in itm.values[0] if e.isdigit() or e == locale_decimal)
                            lbl = "".join(e for e in itm.label if e.isdigit() or e == locale_decimal)
                            
                            # Replace commas in range labels
                            if "," in lbl:
                                arcpy.AddWarning(
                                    "Unsupported character '{}' in range label '{}' has been replaced with '{}'".format(
                                        ",", lbl, DELIM_SUB
                                    )
                                )
                                lbl = lbl.replace(",", DELIM_SUB)

                            # build two lists of unique values
                            inRngs1.append(float(v1))
                            inRngs2.append(float(v1))

                            # Create a comma-delimited list of labels
                            if len(uvLabels) < 1:
                                uvLabels='{}'.format(lbl)
                            else:
                                uvLabels+=',{}'.format(lbl)

                            # create a comma-delimited list of output values
                            # for now, all output values are set to 5
                            if len(outVals)<1:
                                outVals='5'
                            else:
                                outVals+=',5'

                        except Exception as eInner:
                            arcpy.AddWarning("Exception occurred: {}".format(this.GetErrorMessage(eInner)))

                # format list unique values into comma delimited string of min-inclusive/max-exclusive values
                worked, uvRngs = this.createInputRangesForRemap(inRngs1,inRngs2)

            return worked, uvRngs, outVals, uvLabels

        except Exception as e:
            arcpy.AddError("Exception occurred: {}".format(this.GetErrorMessage(e)))
            return False,"","",""


    ## Returns a comma delimited string that represents min-inclusive, max-exclusive ranges
    ## for the remap function
    def createInputRangesForRemap(this,rangeList1,rangeList2):
        try:

            # combine the two range lists
            combinedRngs=rangeList1+rangeList2

            # sort, remove the 1st and change the last items, and finally convert it to strings
            # do this to create a list of min-inclusive,max-exlusive values for the raster remap function
            combinedRngs.sort()
            combinedRngs.remove(combinedRngs[0])
            lastValue=combinedRngs[-1]
            lastValue+=1
            combinedRngs.append(lastValue)
            thematicRange=','.join(str(x) for x in combinedRngs)

            return True, thematicRange

        except Exception as e:
            arcpy.AddError("Exception occurred: {}".format(this.GetErrorMessage(e)))
            return False,""


    def AddWeightedOverlayRemapValues(this,mLyrs):
        try:
            if (mLyrs):
                rasterLayers=[]
                lyrCheck=[]
                lyrData =[]

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

                rastertitle=""
                rasterpath=""
                rasterExtension=""
                outputValues=""
                labels=""
                rasterFileName = ""
                inras=""
                rasData=[]

                # Process Unique values and stretch/classified colorizers
                for l in rasterLayers:
                    try:
                        arcpy.AddMessage("Processing layer {}...".format(l.name))
                        rastertitle=l.name
                        rasterpath=l.dataSource
                        rasterFileName = rasterpath
                        rasterExtension=""

                        # Define raster file name from folder path
                        idx = rasterFileName.rfind("\\") 
                        if (idx != -1):
                          rasterFileName = rasterFileName[idx+1:len(rasterFileName)]
                        if (l.isWebLayer):
                          idx = rasterFileName.rfind("/ImageServer")
                          if (idx != -1):
                            rasterFileName = rasterFileName[0:idx]
                            idx = rasterFileName.rfind("/") 
                            if (idx != -1):
                                rasterFileName = rasterFileName[idx+1:len(rasterFileName)]
                            arcpy.AddMessage("rasterFileNameeeeeeeeeee "+rasterFileName)

                        # describe the raster to get its no data values & other info
                        desc=arcpy.Describe(l)
                        inras=desc.catalogPath

                        # check for an extension in the name (like foo.tif)
                        try:
                            rasterExtension=desc.extension

                            # remove it from the title
                            if (type(rastertitle) == str) and (type(rasterExtension) == str) and (len(rasterExtension) > 0):
                                ext = "." + rasterExtension
                                if rastertitle.endswith(ext):
                                    rastertitle = rastertitle[0:len(rastertitle) - len(ext)]
                                    arcpy.AddMessage("Removed extension {} from layer {}".format(ext,rastertitle))

                            # remove it from file name
                            if (type(rasterFileName) == str) and (type(rasterExtension) == str) and (len(rasterExtension) > 0):
                                ext = "." + rasterExtension
                                if rasterFileName.endswith(ext):
                                    rasterFileName = rasterFileName[0:len(rasterFileName) - len(ext)]

                        except Exception as eExt:
                            arcpy.AddError("Extension error {}".format(this.GetErrorMessage(eExt)))
                            pass

                        # Process unique values differently than stretch/classified
                        sym=l.symbology

                        # string that represents min inclusive/max exclusive values
                        inputRanges=""

                        # http://pro.arcgis.com/en/pro-app/tool-reference/data-management/get-raster-properties.htm
                        # Process GENERIC, ELEVATION, PROCESSED AND SCIENTIFIC rasters by computing an equal interval classification
                        # Process THEMATIC rasters as unique values/categorical
                        rasterSourcetypeResult = arcpy.GetRasterProperties_management(l, "SOURCETYPE")
                        rasterSourcetype = rasterSourcetypeResult.getOutput(0)
                        arcpy.AddMessage("{} is {}".format(rastertitle, rasterSourcetype))

                        # @todo do we need the THEMATIC check
                        #if rasterSourcetype.upper() == "THEMATIC" or (hasattr(sym,'colorizer') and sym.colorizer.type=='RasterUniqueValueColorizer'):
                        if (hasattr(sym,'colorizer') and sym.colorizer.type=='RasterUniqueValueColorizer'):
                            worked, inputRanges, outputValues, labels = this.makeDataFromUniqueColorizer(l,inras,sym)
                            if worked==False:
                                arcpy.AddWarning("Could not create ranges for unique colorizer in {}".format(rastertitle))
                                arcpy.AddMessage(arcpy.GetMessages())
                                continue

                        elif rasterSourcetype.upper() == "VECTOR_UV" or rasterSourcetype.upper() == "VECTOR_MAGDIR":
                            arcpy.AddWarning("Skipping data type of VECTOR_UV or VECTOR_MAGDIR {}".format(rastertitle))
                            arcpy.AddMessage(arcpy.GetMessages())
                            continue

                        elif (hasattr(sym,'colorizer') and sym.colorizer.type=='RasterClassifyColorizer'):
                            worked, inputRanges, outputValues, labels = this.makeDataFromClassifyColorizer(l,inras,sym.colorizer)
                            if worked==False:
                                arcpy.AddWarning("Could not create ranges for classified colorizer in {}".format(rastertitle))
                                arcpy.AddMessage(arcpy.GetMessages())
                                continue

                        else:
                            # no colorizer, try to the min-max values anyways
                            # check min and max values in the dataset
                            try:
                                worked, inputRanges = this.makeInputRanges(l,inras)
                            except Exception as e_inputRanges:
                                arcpy.AddWarning("Error creating input ranges for layer {}: {}".format(rastertitle, this.GetErrorMessage(e_inputRanges)))
                                # @todo - continue with a default set of ranges?
                                # continue
                                worked = True
                                inputRanges = "1.0,50.0,50.0,100.0,100.0,150.0,150.0,200.0,200.0,256.0"
                                arcpy.AddWarning("Using default set of input ranges for layer {}".format(rastertitle))
                                

                            if worked==False:
                                arcpy.AddWarning("Could not create ranges for {}".format(rastertitle))
                                arcpy.AddMessage(arcpy.GetMessages())
                                continue

                            else:
                                # set outputValues and Range Labels
                                outputValues="1,3,5,7,9"
                                labels="Very Low,Low,Medium,High,Very High"

                        rasData=(rastertitle,inputRanges,outputValues,labels,rasterFileName,l)
                        lyrData.append(rasData)

                    except Exception as e1:
                        arcpy.AddError("Exception occurred: {}".format(this.GetErrorMessage(e1)))
                        return False, []
            else:
                arcpy.AddError("Invalid ArcGIS Project")
                return False, []

            return True, lyrData

        except Exception as e:
            arcpy.AddError("Exception occurred: {}".format(this.GetErrorMessage(e)))
            return False, []

    # Get exception message if available, otherwise use exception.
    def GetErrorMessage(this, e):
        if hasattr(e, 'message'):
            return e.message
        else:
            return e
