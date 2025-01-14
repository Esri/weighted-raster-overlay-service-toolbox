# Weighted-raster-overlay-service toolbox
This python toolbox contains analysis tools that help prepare and configure data for a weighted overlay service. The tools apply the proper fields, properties, and metadata to your raster layers and mosaic dataset. The service can be used in web-based apps such as ArcGIS Experience Builder.

![image](https://user-images.githubusercontent.com/59451655/175434439-66f9121e-0866-46c7-bb8d-5569d595518e.png)


## Tools
|Toolname                      |Description   |
|------------------------------|--------------|
|Create Weighted Overlay Mosaic|Creates a new mosaic dataset for weighted overlay analysis. The tool writes supported imagery types in the ArcGIS Pro **Contents** pane to the mosaic. Symbology information is read from each layer and written to the fields within the mosaic.|
|Update WRO Layer Classification|Update WRO Layer Classification - Updates the title and classification ranges of a layer in a weighted overlay mosaic. This tool allows you to refine the classifications created by the Create Weighted Overlay Mosaic tool.|
|Update WRO Layer Info|Updates layer information in a weighted overlay mosaic. This tool allows you to change a layer's title and description. It can also add a preview or an informational URL.|

## Instructions
1. Download the toolbox by clicking on the **Code** drop-down arrow and choosing the **Download ZIP** option.
   ![image](https://user-images.githubusercontent.com/59451655/175216467-deea02ae-22d5-4f0f-b644-a87cf3d7f079.png)
2. Unzip the contents to a location you can access.
3. In ArcGIS Pro, right-click **Toolboxes** and select **Add New Toolbox**.
4. Browse to the WRO toolbox and add it.

The toolbox contains the three aforementioned script tools.

[Learn more about building a weighted overlay service with these scripts](https://doc.arcgis.com/en/geoplanner/latest/documentation/create-a-mosaic-dataset.htm)

## Resources

* [ArcGIS Experience Builder Suitability Modeler Widget](https://doc.arcgis.com/en/experience-builder/configure-widgets/suitability-modeler-widget.htm)

## Issues

Find a bug or want to request a new feature?  Please let us know by submitting an issue.

## Contributing

Esri welcomes contributions from anyone and everyone. Please see our [guidelines for contributing](https://github.com/esri/contributing).

## Licensing
Copyright 2025 Esri

Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with the License. You may obtain a copy of the License at http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific language governing permissions and
limitations under the License.

A copy of the license is available in the repository's [license.txt]( https://github.com/ArcGIS/weighted-raster-overlay-service-toolbox/blob/master/license.txt) file.
