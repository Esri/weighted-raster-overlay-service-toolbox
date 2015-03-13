#   Copyright 2015 Esri
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#       http://www.apache.org/licenses/LICENSE-2.0
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
class KeyMetadata():

    def __init__(self):
        self.name = "Key Metadata Function"
        self.description = "Override key metadata in a function chain."
        self.propertyName = ''
        self.propertyValue = None
        self.bandNames = []


    def getParameterInfo(self):
        return [
            {
                'name': 'raster',
                'dataType': 'raster',
                'value': '',
                'displayName': "Raster",
                'required': True,
                'description': "The primary raster input."
            },
            {
                'name': 'property',
                'dataType': 'string',
                'value': 'IsWeightedOverlay',
                'displayName': "Property Name",
                'required': False,
                'description': "The name of the optional key metadata to override."
            },
            {
                'name': 'value',
                'dataType': 'string',
                'value': "True",
                'displayName': "Property Value",
                'required': False,
                'description': "The overriding new value of the key metadata."
            },
            {
                'name': 'bands',
                'dataType': 'string',
                'value': '',
                'displayName': "Band Names",
                'required': False,
                'description': "A comma-separated string representing updated band names."
            }
        ]


    def getConfiguration(self, **scalars):
        return {
            'invalidateProperties': 8,          # reset any key properties held by the parent function raster dataset
        }


    def updateRasterInfo(self, **kwargs):
        self.propertyName = kwargs.get('property', "")  # remember these user-specified scalar inputs
        self.propertyValue = kwargs.get('value', "")

        self.bandNames = []
        b = kwargs.get('bands', "").strip()
        if len(b) > 0:
            self.bandNames = b.split(',')

        return kwargs


    def updateKeyMetadata(self, names, bandIndex, **keyMetadata):
        if bandIndex == -1:
           if len(self.propertyName) > 0:
                keyMetadata[self.propertyName] = self.propertyValue
        elif bandIndex < len(self.bandNames):
            keyMetadata['bandname'] = self.bandNames[bandIndex]

        return keyMetadata
