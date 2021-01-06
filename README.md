# BVG Sensor Component for Home Assistant

The BVG Sensor can be used to display real-time public transport data for the city of Berlin within the BVG (Berliner Verkehrsbetriebe) route network. 
The sensor will display the minutes until the next departure for the configured station and direction. The provided data is in real-time and does include actual delays. If you want to customize the sensor you can use the provided sensor attributes. You can also define a walking distance from your home/work, so only departures that are reachable will be shown. 

During testing I found that the API frequently becomes unavailable, possibly to keep the amount of requests low. Therefore this component keeps a local copy of the data (90 minutes). The local data is only beeing used while "offline" and is beeing refreshed when the API endpoint becomes available again. 

You can check the status of the API Endpoint here: https://status.transport.rest/784879513

This component uses the API endpoint that provides data from the BVG HAFAS API by [Jannis Redmann](https://github.com/derhuerst/).
Without his fantastic work, this component would not possible!

# Installation

If you are using HomeAssitant Version 0.89 and beyond, simply copy the file bvgsensor.py into your ``/config/custom_components/bvgsensor/`` folder and rename it to ``sensor.py``. If it does not already exist, create the missing folders.

**Only valid for HomeAssistant Version lower than 0.89 as there were some breaking changes on how custom components will integrate with HomeAssistant from Version 0.89 and beyond...**

Simply copy the file bvgsensor.py into your ``/config/custom_components/sensor/`` folder. If it does not already exist, create the missing folders.

# Prerequisites

You will need to specify at least a ``stop_id`` and a ``direction`` for the connection you would like to display.

To find your ``stop_id`` use the following link: https://1.bvg.transport.rest/stations/nearby?latitude=52.52725&longitude=13.4123 and replace the values for ```latitude=``` and ```longitude=``` with your coordinates. You can get those e.g. from Google Maps.
Find your `stop_id` within the json repsonse in your browser. 

### Example:
You want to display the departure times from "U Rosa-Luxemburg-Platz" in direction to "Pankow"

#### get the stop_id:

Link: https://1.bvg.transport.rest/stations/nearby?latitude=52.52725&longitude=13.4123

``

{"type":"stop","id":"900000100016","name":"U Rosa-Luxemburg-Platz","location":{"type":"location","latitude":52.528187,"longitude":13.410405},"products":{"suburban":false,"subway":true,"tram":true,"bus":true,"ferry":false,"express":false,"regional":false},"distance":165}

``

Your ``stop_id`` for ``"U Rosa-Luxemburg-Platz"`` would be ``"900000100016"``

#### get the direction:

Specify the final destination (must be a valid station name) for the connection you want to display. In this example this would be ``Pankow``. If your route is beeing served by multiple lines with different directions, you can define multiple destinations in your config.

```yaml
# Example configuration.yaml entry
- platform: bvgsensor
    stop_id: your stop id
    direction: 
      - "destionation 1"
      - "destination 2"
````

# Configuration

To add the BVG Sensor Component to Home Assistant, add the following to your configuration.yaml file:

```yaml
# Example configuration.yaml entry
- platform: bvgsensor
    stop_id: your stop id
    direction: the final destination for your connection
````

- **stop_id** *(Required)*: The stop_id for your station.
- **direction** *(Required)*: One or more destinations for your route.
- **name** *(optional)*: Name your sensor, especially if you create multiple instance of the sensor give them different names. * (Default=BVG)*
- **walking_distance** *(optional)*: specify the walking distance in minutes from your home/location to the station. Only connections that are reachable in a timley manner will be shown. Set it to ``0`` if you want to disable this feature. *(Default=10)*
- **file_path** *(optional)*: path where you want your station specific data to be saved. *(Default= your home assistant config directory e.g. "conf/" )*

### Example Configuration:
```yaml
sensor:
  - platform: bvgsensor
    name: U2 Rosa-Luxemburg-Platz
    stop_id: "900000100016"
    direction: "Pankow"
    walking_distance: 5
    file_path: "/tmp/"
```
