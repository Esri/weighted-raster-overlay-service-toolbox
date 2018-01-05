# weighted-raster-overlay-service-toolbox

Tools to create and configure raster data for web-based weighted overlay to support suitability modeling. 

This python toolbox helps you create and configure a mosaic dataset for use in a web-based weighted overlay analysis service. You can use these services from web-based clients like [GeoPlanner for ArcGIS](http://doc.arcgis.com/en/geoplanner/) and [Web AppBuilder for ArcGIS](http://doc.arcgis.com/en/web-appbuilder/) to help find the best place or identify risks in an area. 

Note: This is an update to a previous toolbox. This update contains tools that are easier to use and work with ArcGIS Pro. To access the previous toolbox, please clone the branch wro2017.

![App](https://github.com/Esri/weighted-raster-overlay-service-toolbox/blob/master/Suitability%20Modeler%20in%20Web%20AppBuilder.png)

## Features
* Create Weighted Overlay Mosaic - Creates a new mosaic dataset for weighted overlay analysis. The tool writes all .tif raster layers in an ArcGIS Pro Contents Pane to the mosaic. Symbology information is read from each layer and written to fields within the mosaic. 

* Update WRO Layer Classification - Updates the title and classification ranges of a layer in a weighted overlay mosaic. This tool allows you to refine the classifications created by the Create Weighted Overlay Mosaic tool. 

* Update WRO Layer Info - Updates layer information in a weighted overlay mosaic. This tool allows you to change a layer's title and description, add a preview or informational URL and define a dataset value range as NoData. 


## Instructions

1. Fork and then clone the repo. 
2. Open ArcGIS Pro and browse to the python toolbox.
3. [Review this doc to setup your weighted overlay service](http://doc.arcgis.com/en/geoplanner/documentation/use-your-data-in-weighted-overlay.htm)

## Requirements

* ArcGIS Pro 2.01 or newer 
* ArcGIS Enterprise 10.5 or newer
* ArcGIS Image Server
* GeoPlanner for ArcGIS or Web AppBuilder

## Resources

* [GeoPlanner documentation](http://doc.arcgis.com/en/geoplanner)
* [Understanding weighted overlay in GeoPlanner](http://doc.arcgis.com/en/geoplanner/documentation/find-the-best-place-using-weighted-overlay.htm)
* [Build your own weighted raster overlay service](http://doc.arcgis.com/en/geoplanner/documentation/use-your-data-in-weighted-overlay.htm)
* [Web AppBuilder Suitability Modeler Widget](http://doc.arcgis.com/en/web-appbuilder/create-apps/widget-suitability-modeler.htm)
* [GeoPlanner on GeoNet](https://community.esri.com/community/gis/applications/geoplanner-for-arcgis)
* [Web AppBuilder on GeoNet](https://community.esri.com/community/gis/web-gis/web-appbuilder)
* [GeoPlanner blog](https://www.esri.com/search?filter=Blogs&q=geoplanner&search=Search)
* [Web AppBuilder blog](https://www.esri.com/search?filter=Blogs&q=Web%20AppBuilder&search=Search)
* [@ArcGISApps](https://twitter.com/ArcGISApps)

## Issues

Find a bug or want to request a new feature?  Please let us know by submitting an issue.

## Contributing

Esri welcomes contributions from anyone and everyone. Please see our [guidelines for contributing](https://github.com/esri/contributing).

## Licensing
Copyright 2015 Esri

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

A copy of the license is available in the repository's [license.txt]( https://github.com/ArcGIS/weighted-raster-overlay-service-toolbox/blob/master/license.txt) file.

[](Esri Tags: ArcGIS GeoPlanner weighted raster overlay service wro weightedOverlayService Suitability Risk Analysis Modeling Web ) 
[](Esri Language: Python)
