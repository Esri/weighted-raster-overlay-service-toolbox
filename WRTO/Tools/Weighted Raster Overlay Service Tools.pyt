#-------------------------------------------------------------------------------
# Name        : FeauteToRaser.pyt
# ArcGIS Version: ArcGIS 10.1
# Script Version: 2.3
# Name of Company : Environmental System Research Institute
# Author        : ESRI raster solutions team
# Date          : 09-05-2013
# Purpose 	    : To export images(AOIs) from ArcGIS Image Services for analysis
# Created	    : 05-09-2013
# LastUpdated  	: 05-09-2013
# Required Argument : To be loaded and run from within ArcMap
# with user arguments <URL> <MinX> <MaxX> <MinY> <MaxY> <SRS>
# <PixelSize> <Transfer:Compression> <Transfer:CompressionQuality> <Format>
# <Output file>
# Optional Argument : None
# Usage         :  Load using ArcMap catalog browser.
# Copyright	    : (c) ESRI 2013
# License	    : <your license>
#-------------------------------------------------------------------------------


import arcpy
from arcpy.sa import *
from arcpy import env
import sys, os
import subprocess
import time
from xml.dom import minidom
import tempfile
toolPath = os.path.dirname(os.path.realpath(__file__))
solutionLib_path = os.path.join(os.path.dirname(toolPath), "Scripts")
pythonPath = os.path.dirname(os.path.dirname(os.__file__)) + "/python.exe"
configBase = os.path.dirname(os.path.dirname(__file__)) + "/Parameter/Config/"
clrpath = os.path.dirname(os.path.dirname(__file__)) + "/Parameter/Colormaps"
parameterPath = os.path.dirname(os.path.dirname(__file__)) + "/Parameter/"


#Internal messages from aExport object get printed here.
def Messages(msg):
    arcpy.AddMessage(msg)


def readAUX(input):
    ret_aux = {}
    if os.path.exists(input):
        doc = minidom.parse(input)
    else:
        return ret_aux
    nodeName = 'MDI'
    parent_node = doc.getElementsByTagName('Metadata')[0]
    node_lst = doc.getElementsByTagName(nodeName)
    if (len(node_lst) == 0):
        return False

    for n in node_lst:
        if (n.parentNode != parent_node):
            continue
        try:
            key = str(n.getAttributeNode('key').nodeValue)
            ret_aux[key] = {'value' :  str(n.firstChild.nodeValue)}
        except Exception as exp:
            print str(exp)
    return ret_aux


def suffixExtractNames (path):

    filter = 'tif'
    ret_files = {}

    if (os.path.exists(path) == False):
        s = path.split(';')
        for sel_file in s:
            aux_ = '%s.aux.wo.xml' % (sel_file)
            ret_files[sel_file] = readAUX(aux_)
        return ret_files

    for r,d,f in os.walk(path):
        for file in f:
            extension = file[-3:]
            if (extension.lower() == filter):
                sel_file = os.path.join(r, file)
                aux_ = '%s.aux.wo.xml' % (sel_file)
                ret_files[sel_file] = readAUX(aux_)

    return ret_files

def updatepyPath(rftpath,pyPath):
    sm_doc = minidom.parse(rftpath)

    nodes = sm_doc.getElementsByTagName('Names')
    node = nodes[0].firstChild
    index_  = 0
    py_index_ = -1

    while (node != None):
        if (node.hasChildNodes() == False):
            node = node.nextSibling
            continue

        if (node.firstChild.nodeValue.lower() == 'pythonmodule'):
            py_index_ = index_
            break
        index_ += 1
        node = node.nextSibling
        pass


    if (py_index_ == -1):
        print ('\nPythonModule - Not found!')
        return False


    # modify values
    nodes = sm_doc.getElementsByTagName('Values')
    node = nodes[0].firstChild
    index_ = 0
    while (node != None):
        if (node.hasChildNodes() == False):
            node = node.nextSibling
            continue

        if (index_ == py_index_):
            node.firstChild.nodeValue = pyPath
            break
        index_ += 1
        node = node.nextSibling
        pass
    # ends

    # write updated
    f = open(rftpath, 'w+')
    f.write(sm_doc.toprettyxml())
    f.close()
    return True

class AUXTable():
    def __init__(self):
        self.iCursor = None

    def init(self, cfg_path, aux_output):

        # parse in template to get fields info
        try:
            arcpy.AddMessage(str(cfg_path))
            doc = minidom.parse(cfg_path)
        except:
            arcpy.AddMessage('failed to open the file' + str(cfg_path))
        nodeName = 'Field'
        parent_node = doc.getElementsByTagName(nodeName)

        self.fld_info = {'field' : {'info' : {}}}
        for n in parent_node:
            try:
                field_name = str(n.firstChild.nextSibling.firstChild.nodeValue)
                if (field_name.lower() == 'dataset_id'):
                    continue
                self.fld_info['field']['info'][field_name] = {
                'type' : n.firstChild.nextSibling.nextSibling.nextSibling.firstChild.nodeValue,
                'len' : n.firstChild.nextSibling.nextSibling.nextSibling.nextSibling.nextSibling.firstChild.nodeValue
                }
            except Exception as exp:
                print str(exp)
                return False
        # ends

        # let's create the table
        self.aux_output = aux_output
        try:
            print ('Creating [%s]..' % self.aux_output)
            (p, n) = os.path.split(self.aux_output)
            arcpy.CreateTable_management(p, n)
            for fld in self.fld_info['field']['info'].keys():
                arcpy.AddField_management(self.aux_output, fld, self.fld_info['field']['info'][fld]['type'], '#', '#', self.fld_info['field']['info'][fld]['len'], '#')
            print ('Done.')

        except Exception as exp:
            print ('Error: [%s]' % (str(exp)))
            return False
        # ends

        try:
            self.iCursor = arcpy.InsertCursor(self.aux_output)
        except Exception as exp:
            print ('Error: [%s]' % (str(exp)))
            return False

        return True


    def close (self):
        if (self.iCursor is not None):
            del self.iCursor
        try:
            pass

        except Exception as exp:
            return False
        return True



    def insertRecord (self, record):

        if (self.iCursor is None):
            print ('Error: internal/insertRecord');
            return False

        if (record is None):
            return False

        if (('field' in record) == False):
            return False

        if (('info' in record['field']) == False):
            return False

        try:
            row = self.iCursor.newRow()
            for fld in record['field']['info']:
                if (('value' in record['field']['info'][fld]) == False):
                    continue
                if (record['field']['info'][fld]['value'] is not None):
                    try:
                        row.setValue(fld, record['field']['info'][fld]['value'])
                    except Exception as exp:
                        print ('Warning: (insetRecord[%s], [%s])' % (fld, str(exp)))
            self.iCursor.insertRow(row)
        except Exception as exp:
            print ('Err: [%s]' % str(exp))
            return False
        finally:
            row = None
            del row

        return True


class Toolbox(object):
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "Weighted Raster Overlay Service Tools"
        self.alias = "wrot"

        # List of tool classes associated with this toolbox
        self.tools = [featuretoRaster,configurerasterfields,optimizeRaster,buildMosiac]

class featuretoRaster(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Feature to Raster"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""

        inFC = arcpy.Parameter(
        displayName="Input Feature Class",
        name="inFC",
        datatype="DEFeatureClass",
        parameterType="Required",
        direction="Input")

        outputRaster = arcpy.Parameter(
        displayName="Output Raster",
        name="out_raster",
        datatype="GPRasterLayer",#"DERasterDataset",
        parameterType="Required",
        direction="Output")

        processname = arcpy.Parameter(
        displayName="Process Name",
        name="processname",
        datatype="GPString",
        parameterType="Required",
        direction="Input")
        processname.filter.type = "ValueList"
        processname.filter.list = ['Present/Absent','KeyAttribute','Density','Distance']

        infield = arcpy.Parameter(
            displayName="Field Name",
            name="infield",
            datatype="GpString",
            parameterType="Required",
            direction="Input")
#        infield.parameterDependencies = [inFC.name]
        infield.filter.type = "ValueList"

##        if infield.hasError == True:
##            infield.setWarningMessage = 'Field not Prenset'


        cellSize = arcpy.Parameter(
        displayName="Cell Size",
        name="cellSize",
        datatype="GPDouble",
        parameterType="Required",
        direction="Input")

        outputextent = arcpy.Parameter(
        displayName="Output Extent",
        name="outputextent",
        datatype="GPExtent",
        parameterType="Optional",
        direction="Input")

        snapraster = arcpy.Parameter(
        displayName="Snap Raster",
        name="snapraster",
        datatype="GPRasterLayer",
        parameterType="Optional",
        direction="Input")

        maskEnv = arcpy.Parameter(
        displayName="Mask Output",
        name="maskEnv",
        datatype=["DERasterDataset", "DEFeatureClass"],
        parameterType="Optional",
        direction="Input")

        searchradius = arcpy.Parameter(
        displayName="Search Radius",
        name="searchradius",
        datatype= "GPDouble",
        parameterType="Optional",
        direction="Input")


        params = [inFC,outputRaster,processname,cellSize,infield,outputextent,snapraster,maskEnv,searchradius]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        if parameters[2].altered and parameters[0].altered == True:
            flist = arcpy.ListFields(parameters[0].valueAsText)
            fieldList = []
            for each in flist:
                fieldList.append(each.name)
#            fieldList.append("None")
            parameters[4].filter.list = fieldList
            if parameters[2].valueAsText == 'Distance':
                fdesc = arcpy.Describe(parameters[0].valueAsText)
                parameters[4].value = str(fdesc.fields[0].name)
                parameters[4].enabled = False
            elif parameters[2].valueAsText == 'Present/Absent' or parameters[2].valueAsText == 'KeyAttribute' :
                parameters[8].enabled = False
                parameters[4].enabled = True
            else:
                parameters[4].enabled = True
                parameters[8].enabled = True
                fieldList.append("None")
                parameters[4].filter.list = fieldList

        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
#        if parameters[4].hasError

        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        arcpy.CheckOutExtension("Spatial")
        pname = parameters[2].valueAsText
        infc = parameters[0].valueAsText
        outRaster = parameters[1].valueAsText
        fieldName = parameters[4].valueAsText

        if (fieldName is None):
                fieldName = '#'

        csize = parameters[3].valueAsText
        fcprop = arcpy.Describe(infc)
        shapeType = fcprop.shapeType
        fcname = os.path.basename(infc)  #fcprop.name
        fcwrks = fcprop.path
        outextent = parameters[5].valueAsText

        if (outextent is None):
            outextent = "#"

        if (outextent != '#'):
            evalue = outextent.split(" ")
            arcpy.env.extent = outextent

        sraster = parameters[6].valueAsText
        rmask = parameters[7].valueAsText
        sRadius = parameters[8].valueAsText

#        arcpy.env.workspace = fcwrks
        env.workspace = fcwrks


        if (sraster is None):
            sraster = "#"
        if (sraster != '#'):
            arcpy.env.snapRaster = sraster
#            arcpy.AddMessage("added Snap raster")

        if (rmask is None):
            rmask = "#"

        if (rmask != '#'):
            arcpy.env.mask = rmask

        if (sRadius is None):
            sRadius = "#"

#            arcpy.AddMessage("added Mask")
#            arcpy.AddMessage(str(arcpy.env.mask))

        arcpy.AddMessage(str(rmask))
        if pname.lower() == 'density':

            if shapeType.lower() == 'polyline':
                arcpy.AddMessage("generating raster for Line Density")
                ldensity = LineDensity(infc,fieldName,csize,sRadius)
                ldensity.save(outRaster)
            elif shapeType.lower() == 'point':
                arcpy.AddMessage("generating raster for Point Density")
                pdensity = PointDensity(infc,fieldName,csize)
                pdensity.save(outRaster)
            else:
                arcpy.AddMessage("Input Geomerty should be line or Point, Input shape is " + str (shapeType.lower()))
        elif pname.lower() == 'distance':
            argsdist= []
            argsdist = [pythonPath, os.path.join(toolPath,'Distance.py')]
            argsdist.append(infc)
            argsdist.append(outRaster)
            argsdist.append(csize)
            argsdist.append(rmask)
            p = subprocess.Popen(argsdist, creationflags=subprocess.SW_HIDE, shell=True, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
            message = ''
            while True:
                message = p.stdout.readline()
                if not message:
                    break
                arcpy.AddMessage(message.rstrip())      #remove newline before adding.
            print " The process is completed"
            argsdist = []

        elif pname.lower() == 'keyattribute' or pname.lower() == 'present/absent':

            if shapeType.lower() == 'polyline':
                arcpy.AddMessage("generating raster for Line " + str(pname.lower()))
                arcpy.PolylineToRaster_conversion(infc,fieldName,outRaster,"#","#",csize)
            elif shapeType.lower() == 'polygon':
                arcpy.AddMessage("generating raster for Polygon " + str(pname.lower()))
                arcpy.PolygonToRaster_conversion(infc,fieldName,outRaster,"CELL_CENTER","#",csize)
            else:
                arcpy.AddMessage("Input Geomerty should be line or Polygon, Input shape is " + str (shapeType.lower()))
        else:
            arcpy.AddMessage("Invalid Process Name")
        return



class configurerasterfields(object):
    in_ras = ''
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Configure Raster Fields"
        self.description = ""
        self.canRunInBackground = False
        self.mkey ={}
#        self.in_ras = ""

    def getParameterInfo(self):
        """Define parameter definitions"""

        inRaster = arcpy.Parameter(
        displayName="Input Raster",
        name="inRaster",
        datatype="GPRasterLayer",#"DERasterDataset",
        parameterType="Required",
        direction="Input")

        title = arcpy.Parameter(
        displayName="Title",
        name="Title",
        datatype="GPString",
        parameterType="Optional",
        direction="Input")

##        colorMap = arcpy.Parameter(
##        displayName="Color Map file",
##        name="colormapFileName",
##        datatype="GPString",#"DERasterDataset",
##        parameterType="Optional",
##        direction="Input")
##        colorMap.filter.type = "ValueList"
##        colorMap.filter.list = colorMapFileList() #['clr']

        rdescription = arcpy.Parameter(
        displayName="Description",
        name="Description",
        datatype="GPString",
        parameterType="Optional",
        direction="Input")

        metadata = arcpy.Parameter(
        displayName="Metadata",
        name="Metadata",
        datatype="GPString",
        parameterType="Optional",
        direction="Input")

        url = arcpy.Parameter(
        displayName="URL",
        name="url",
        datatype="GPString",
        parameterType="Optional",
        direction="Input")

        disporder = arcpy.Parameter(
        displayName="Display Order",
        name="DisplayOrder",
        datatype="GPDouble",
        parameterType="Optional",
        direction="Input")

        mmr = arcpy.Parameter(
        displayName="Min Max Range",
        name="MinMaxRange",
        datatype="GPString",
        parameterType="Optional",
        direction="Input")

        inputRanges = arcpy.Parameter(
        displayName="Input Ranges",
        name="InputRanges",
        datatype="GPString",#"DERasterDataset",
        parameterType="Optional",
        direction="Input")

        outputValues = arcpy.Parameter(
        displayName="Output Values",
        name="OutPutValues",
        datatype="GPString",
        parameterType="Optional",
        direction="Input")

        noDataRanges = arcpy.Parameter(
        displayName="NoData Ranges",
        name="NoDataRanges",
        datatype="GPString",
        parameterType="Optional",
        direction="Input")

        rangeLabels = arcpy.Parameter(
        displayName="Range Labels",
        name="RangeLabels",
        datatype="GPString",
        parameterType="Optional",
        direction="Input")

        noDataRangeLabels = arcpy.Parameter(
        displayName="NoData Range Labels",
        name="NoDataRangeLabels",
        datatype="GPString",
        parameterType="Optional",
        direction="Input")

#        params = [inRaster,title,rdescription,metadata,url,disporder,inputRanges,outputValues,noDataRanges,rangeLabels,noDataRangeLabels,mmr]
        params = [inRaster,title,rdescription,metadata,url,inputRanges,outputValues,noDataRanges,rangeLabels,noDataRangeLabels]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        inras = parameters[0].valueAsText
        if parameters[0].altered:
            inras = arcpy.Describe(parameters[0].value).catalogPath


        if inras != configurerasterfields.in_ras:

            configurerasterfields.in_ras = inras

            inaux = str(inras) + '.aux.wo.xml'
            if os.path.exists(inaux) == True:

                doc = minidom.parse(inaux)
                self.mkey ={}
                key = "Description"
                mlist = doc.getElementsByTagName("Metadata")
                i = 0

                for each in mlist:
                    if str(mlist[i].parentNode.nodeName).lower() == 'pamdataset':
                        if mlist[i].hasChildNodes() == True:
                            ns = mlist[i].firstChild.nextSibling

                            while (ns != None):
                                if (not ns.firstChild is None):
                                    self.mkey[ns.firstChild.parentNode.attributes.item(0).value] = ns.firstChild.nodeValue

                                ns = ns.nextSibling.nextSibling
                    i = i+1
                for eachp in parameters:
                    if eachp.name == 'inRaster':
                        continue
                    valu = ''
                    if self.mkey.has_key(eachp.name):
                        valu = self.mkey[eachp.name]
#                            if (eachp.altered) == False:
                    eachp.value = valu
            else:
                for eachvalue in parameters:
                    if eachvalue.name == 'inRaster':
                        continue
                    valu = ''
                    eachvalue.value = valu
            return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""

        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
#        inRaster = parameters[0].valueAsText
        inRaster = arcpy.Describe(parameters[0].value).catalogPath
        auxxml = str(inRaster) + '.aux.wo.xml'
        arcpy.AddMessage(auxxml)
        ptitle = parameters[1].valueAsText
        pdescription = parameters[2].valueAsText
        pmetadata = parameters[3].valueAsText
        purl = parameters[4].valueAsText
#        pdisporder = parameters[5].valueAsText
        pinputRangers  = parameters[5].valueAsText
        poutputValues = parameters[6].valueAsText
        pnodataRanges = parameters[7].valueAsText
        prangeLabels = parameters[8].valueAsText
        pnodataRangeLabels = parameters[9].valueAsText
#        pmmcr = parameters[11].valueAsText
#        puplist = [ptitle, pdescription, pmetadata, purl,pdisporder, pinputRangers, poutputValues,pnodataRanges,prangeLabels,pnodataRangeLabels,pmmcr]#,colormapValue,colormapFileName]
        puplist = [ptitle, pdescription, pmetadata, purl,pinputRangers, poutputValues,pnodataRanges,prangeLabels,pnodataRangeLabels]#,colormapValue,colormapFileName]
#        sNNL = ['<MDI key="Title">','<MDI key="Description">', '<MDI key="Metadata">','<MDI key="url">', '<MDI key="DisplayOrder">','<MDI key="InputRanges">','<MDI key="OutPutValues">','<MDI key="NoDataRanges">','<MDI key="RangeLabels">','<MDI key="NoDataRangeLabels">','<MDI key="MinMaxRange">']#,'<MDI key="colormapValue">','<MDI key="colormapFileName">']
        sNNL = ['<MDI key="Title">','<MDI key="Description">', '<MDI key="Metadata">','<MDI key="url">', '<MDI key="InputRanges">','<MDI key="OutPutValues">','<MDI key="NoDataRanges">','<MDI key="RangeLabels">','<MDI key="NoDataRangeLabels">']#,'<MDI key="colormapValue">','<MDI key="colormapFileName">']
        eNNL = ['</MDI>','</MDI>', '</MDI>', '</MDI>','</MDI>','</MDI>','</MDI>','</MDI>','</MDI>']#,'</MDI>','</MDI>']
        buff = []

        try:
            if os.path.exists(auxxml) == True:
                auxExist = True
                new_buffer = []
                f = open(auxxml)
                org_buffer = f.readlines()
                for i in range (0, len(org_buffer)):
                    ln = org_buffer[i].strip()
                    if (ln == ''): continue;
                    print ln
                    new_buffer.append(org_buffer[i])
                f.close()
                buff = new_buffer
            else:
                auxExist = False
                buff.insert(0,'%s\n'% '<PAMDataset>')
                buff.insert(1,'%s\n'% '<Metadata>')
                buff.insert(2,'%s\n'% '</Metadata>')
                buff.insert(3,'%s\n'% '</PAMDataset>')
        except Exception as inf:
            arcpy.AddMessage(str(inf))
            return False


        inline = ""
        tempbuff = buff
#        if os.path.exists(auxxml) == True:
        for q in range (0,  len(puplist)):
            j = 0
            if str(puplist[q]) == 'None':
                puplist[q] = ''
            for mtag in tempbuff:
                j = j+1
                if mtag.lower().find(str(sNNL[q]).lower()) >= 0:
    #                        arcpy.AddMessage(str(j))
                    print (str(sNNL[q]).lower())
                    del buff[j-1]
                    break

            inline = inline + (sNNL[q]) + str(puplist[q]) + str(eNNL[q]) + '\n' + '\t\t'

        i = 0
        mpresent = False
        in_indx = 0
        for fnd in buff:

            if (fnd.lower().find('<metadata>') >= 0):
                if (str(buff[i-1]).lower().find('<pamdataset>') >= 0):
                    in_indx = i
                    break;
            i = i+1

        if in_indx == 0:
            buff.insert(1,'%s\n'%'<Metadata>')
            buff.insert(2,'%s\n'%'</Metadata>')
            arcpy.AddMessage("adding Metadata Node")
            in_indx = in_indx + 1

        in_buff = inline
        in_indx = in_indx + 1
        buff.insert(in_indx, '  %s\n' % (in_buff))
        arcpy.AddMessage(str(inline))

        # let's write out the updated fle.
        try:
            if auxExist == True:
                os.remove (auxxml)

            f = open(auxxml, 'w')
            f.writelines(buff)
            f.close()
        except Exception as inf:
            arcpy.AddMessage(str(inf))
            return False

        return

class optimizeRaster(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Optimize Raster"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""

        opInRaster = arcpy.Parameter(
        displayName="Input Raster",
        name="opInRaster",
        datatype="GPRasterLayer",#"DERasterDataset",
        parameterType="Required",
        direction="Input")


        opOutputExtent = arcpy.Parameter(
        displayName="Output Extent",
        name="outputextent",
        datatype="GPExtent",
        parameterType="Optional",
        direction="Input")

        opOutRaster = arcpy.Parameter(
        displayName="Output Raster",
        name="opOutRaster",
        datatype="GPRasterLayer",#"DERasterDataset",
        parameterType="Required",
        direction="Output")


        opinTrueRaster = arcpy.Parameter(
        displayName="Input True Raster or a numeric constant",
        name="opinTrueRaster",
        datatype=["GPRasterLayer","GPString"],#"DERasterDataset",
        parameterType="Required",
        direction="Input")
#        opinTrueRaster.value = 'None'

        opinFalseRaster = arcpy.Parameter(
        displayName="Input False Raster or Constant",
        name="opinFalseRaster",
        datatype=["GPRasterLayer","GPString"],#"DERasterDataset",
        parameterType="Required",
        direction="Input")
        opinFalseRaster.value = 'None'
#        opinFalseRaster.enabled = False

        opprocessname = arcpy.Parameter(
        displayName="Process Name",
        name="opprocessname",
        datatype="GPString",
        parameterType="Required",
        direction="Input")
        opprocessname.filter.type = "ValueList"
        opprocessname.filter.list = ['Filling Gaps','Remove Extraneous Zeros']
#        opprocessname.value = 'Filling Gaps'


        opexpression = arcpy.Parameter(
        displayName="Where Clause",
        name="opexpression",
        datatype="GPString",#GPSQLExpression",#"DERasterDataset",
        parameterType="Optional",
        direction="Output")

        params = [opInRaster,opprocessname,opOutRaster,opinTrueRaster,opinFalseRaster,opOutputExtent,opexpression]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""

        if parameters[3].altered == True:
            input_true_raster_val  = parameters[3].valueAsText
            if (input_true_raster_val is not None and
                input_true_raster_val != ''):

                if (arcpy.Exists(input_true_raster_val) == False):
                    if (input_true_raster_val.isnumeric() == False):
                        parameters[3].value = ''


        if parameters[1].altered == True:
            pname = parameters[1].valueAsText
            if pname.lower() == 'remove extraneous zeros':

#                parameters[3].value = "None"
                parameters[3].enabled = False
                parameters[3].value = "None"
                if parameters[4].value == "None":
                        parameters[4].value = ""
            else:
#                parameters[4].value = "None"
                parameters[3].enabled = True
                if parameters[4].value == "" or parameters[4].value == None:
                        parameters[4].value = "None"

        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        arcpy.CheckOutExtension("Spatial")
        opinraster = parameters[0].valueAsText
        opprocessname = parameters[1].valueAsText
        opextent = str(parameters[5].valueAsText)
        opoutraster = parameters[2].valueAsText
        opintrueR = parameters[3].valueAsText
        opinfalseR = str(parameters[4].valueAsText)
        opexpression = parameters[6].valueAsText
        env.workspace = os.path.dirname(opinraster)
        rname = os.path.basename(opinraster)
        if opintrueR == "None":
                opintrueR = "#"
        else:
            if arcpy.Exists(opintrueR) == False:
                arcpy.AddMessage("it's a constant")
                opintrueR = int(opintrueR)

        if opinfalseR == "None":
                opinfalseR = "#"
        else:
            if arcpy.Exists(opinfalseR) == False:
                arcpy.AddMessage("it's a constant")
                opinfalseR = int(opinfalseR)
        arcpy.AddMessage(opextent)

        if opextent != "None":
            opevalue = opextent.split(" ")
            arcpy.env.extent = opextent

        if opprocessname.lower() == 'remove extraneous zeros':
            #env.workspace = os.path.dirname(opinraster)
            outprez = SetNull(rname,opinfalseR,opexpression)
            outprez.save(opoutraster)
            arcpy.AddMessage(arcpy.GetMessages())
        elif opprocessname.lower() == 'filling gaps':
##            if opinfalseR == "None":
##                opinfalseR = "#"
##            if os.path.isfile(opintrueR) == False:
##                arcpy.AddMessage("its a constant")
##                opintrueR = int(opintrueR)
            outfg = Con(IsNull(rname),opintrueR,opinfalseR,opexpression)
            outfg.save(opoutraster)
            arcpy.AddMessage(arcpy.GetMessages())


        return


class buildMosiac(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Build Mosaic Dataset"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""

        inMXD = arcpy.Parameter(
        displayName="Map Document or Folder",
        name="inMXD",
        datatype=["DEMapDocument","DEWorkspace"],#"DERasterDataset",
        parameterType="Required",
        direction="Input")

##        md_name = arcpy.Parameter(
##        displayName="Mosaic Dataset",
##        name="md_name",
##        #datatype=["DEMosaicDataset","GPMosaicLayer"],
##        datatype="GPMosaicLayer",
##        parameterType="Required",
##        direction="Input")

        in_worksapce = arcpy.Parameter(
        displayName="Output Geodatabase",
        name="in_worksapce",
        datatype="DEType",
        parameterType="Required",
        direction="Input")

        in_mosaicdataset_name = arcpy.Parameter(
        displayName="Mosaic Dataset Name",
        name="in_mosaicdataset_name",
        datatype="GPString",
        parameterType="Required",
        direction="Input")

        clippingboundary = arcpy.Parameter(
        displayName="Clipping Boundary",
        name="clippingboundary",
        datatype="GPFeatureLayer",
        parameterType="Optional",
        direction="Input")


        params = [inMXD,in_worksapce,in_mosaicdataset_name]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        if (parameters[1].altered == True):
            gdbValue = parameters[1].valueAsText
            mdsValue = ''
            if (parameters[2].altered == True):
                mdsValue = parameters[2].valueAsText

            mdsDesc = arcpy.Describe(parameters[1].value)

            if hasattr(mdsDesc, "dataType"):

                if (mdsDesc.dataType == 'MosaicDataset'):

                    if (mdsValue != ''):
                        parameters[1].value = os.path.dirname(gdbValue)
                        if (parameters[2].valueAsText != os.path.basename(gdbValue)):
                            parameters[2].value = os.path.basename(gdbValue)
                    else:
                        parameters[1].value = os.path.dirname(gdbValue)
                        parameters[2].value = os.path.basename(gdbValue)

        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        arcpy.env.workspace = parameters[1].valueAsText
        if (parameters[1].altered == True):
#            desc = arcpy.Describe(parameters[1].valueAsText)

            if (parameters[2].altered == True):
                if (str(parameters[1].value) != None or str(parameters[1]) != "#"):
                    mdPath = os.path.join(parameters[1].valueAsText,parameters[2].valueAsText)
                    if arcpy.Exists(mdPath):
                        parameters[1].setWarningMessage(parameters[2].valueAsText + " Mosaic Dataset Exist, It will add the data to same Mosaic dataset")
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        inputpath = parameters[0].valueAsText
        gdbPath = parameters[1].valueAsText
        mdName = parameters[2].valueAsText
        mdPath = os.path.join(gdbPath,mdName)
        descin = arcpy.Describe(inputpath)
        if descin.datatype.lower() == 'mapdocument':
            mxdPath = inputpath
            arcpy.AddMessage("Scanning raster layers from the map Document")
            mxd = arcpy.mapping.MapDocument(mxdPath)
            df = arcpy.mapping.ListDataFrames(mxd)[0]
            gdbworkspace = os.path.dirname(mxdPath)
            inMDdatalist = ''
            for lyr in arcpy.mapping.ListLayers(mxd, '', df):
                try:
                    if lyr.isRasterLayer:
                        inMDdata = lyr.dataSource
#                        inMDdatalist.append(inMDdata)
                        inMDdatalist = inMDdatalist + inMDdata + ';'
                except:
                    arcpy.AddMessage(arcpy.GetMessages())
            inMDdatalist = inMDdatalist[:-1]

        elif descin.datatype.lower() == 'folder' or descin.datatype.lower() == 'rasterdataset' :
            inMDdatalist = inputpath
            arcpy.AddMessage("Creating Temp input Table")
        else:
            arcpy.AddMessage("Invalid Input ")
            return

#        arcpy.AddMessage(inMDdatalist)

        ret_info = suffixExtractNames(inMDdatalist)
        if (len(ret_info) == 0):
            # didn't get the list.
            exit(1)

        configName = 'LSM.xml'
        config = os.path.join(configBase , configName)
        rftpath = parameterPath + 'RasterFunctionTemplates/KeyMetadata.rft.xml'
        pyPath = parameterPath + 'RasterFunction/KeyMetadata.py'
        updatepyPath(rftpath, pyPath)
        objTable = AUXTable();

        (fd, filename) = tempfile.mkstemp()
        unique_table_name = os.path.basename(filename)
        intablePath = os.path.join(gdbPath, unique_table_name)
        init = objTable.init(config, intablePath)
        if (init == False):
            exit(0)

        print ('Adding records..')

        rec_count = 0
        for k in ret_info:
            insert_rec = {'field' : {'info' : {}}}
            ret_info[k]['Name'] = {'value' : os.path.basename(k)[:-4] }
            ret_info[k]['Raster'] = {'value' : k }
            insert_rec['field']['info'] = ret_info[k]

            if (objTable.insertRecord(insert_rec) == True):
                rec_count += 1

        print ('Total records inserted (%s)' % (rec_count))
        print ('Done.')
        objTable.close()    # close will delete the table.
        args= []
        args = [pythonPath, os.path.join(solutionLib_path,'MDCS.py'), '#gprun']
        inconfig = '-i:'+ config
        args.append(inconfig)
        data = '-s:'+ str(intablePath)

        md = '-m:' + str(mdPath)
        args.append(data)
        args.append(md)
        p = subprocess.Popen(args, creationflags=subprocess.SW_HIDE, shell=True, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        message = ''
        while True:
            message = p.stdout.readline()
            if not message:
                break
            arcpy.AddMessage(message.rstrip())      #remove newline before adding.
        print " The process is completed"
        args = []
        try:
            arcpy.AddMessage("Deleting temp Table : " + str(intablePath))
            arcpy.Delete_management(intablePath)
        except:
            arcpy.AddMessage("Failed to Remove the table")
        return