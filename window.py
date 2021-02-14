import json
import time
from datetime import datetime
from sensors import sensor

window_config_topic = "homeassistant/binary_sensor/tydom/{id}/config"
window_values_topic = "window/tydom/{id}/state_topic"


#temperature = current_temperature_topic 
#setpoint= temperature_command_topic
#temperature_unit=C
#"modes": ["STOP", "ANTI-FROST","ECO", "COMFORT"],
#####################################
#setpoint (seulement si thermostat)
#temperature (intérieure, seulement si thermostat)
#anticipCoeff 30 (seulement si thermostat)

#thermicLevel STOP ECO ...
#auhorisation HEATING
#hvacMode NORMAL None (si off)
#timeDelay : 0
#tempoOn : False
#antifrost True False
#openingdetected False
#presenceDetected False
#absence False
#LoadSheddingOn False

#outTemperature float
##################################

# climate_json_attributes_topic = "climate/tydom/{id}/state"
# State topic can be the same as the original device attributes topic !
class Window:

    def __init__(self, tydom_attributes, tydom_client=None, mqtt=None):
        
        self.attributes = tydom_attributes
        self.device_id = self.attributes['device_id']
        self.endpoint_id = self.attributes['endpoint_id']
        self.id = self.attributes['id']
        self.name = self.attributes['name']
        self.mqtt = mqtt
        self.tydom_client = tydom_client

    async def setup(self):
        self.device = {}
        self.config = {}
        self.device['manufacturer'] = 'Delta Dore'
        self.device['name'] = self.name
        self.device['identifiers'] = self.id
        
        self.config['name'] = self.name
        #self.device['model'] = 'sensor'

        self.config_topic = window_config_topic.format(id=self.id)

        self.config['state_topic'] = window_values_topic.format(id=self.id)   
        self.config['payload_on'] = True
        self.config['payload_off'] = False
        self.config['device_class'] = 'window'
        
        self.config['value_template'] =  "{{ value_json.intrusionDetect }}"
        self.config['unique_id'] = self.id

        if (self.mqtt != None):
            self.mqtt.mqtt_client.publish(self.config_topic, json.dumps(self.config), qos=0)

    async def update(self):
        await self.setup()
        
        # Chic Debug

        if (self.mqtt != None):
            self.mqtt.mqtt_client.publish(self.config['state_topic'],json.dumps(self.attributes), qos=0)

   