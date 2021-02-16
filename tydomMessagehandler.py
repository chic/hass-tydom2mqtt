from cover import Cover
from light import Light
from boiler import Boiler
from electric import Electric
from window import Window
from unknown import Unknown
from alarm_control_panel import Alarm
from sensors import sensor

from http.server import BaseHTTPRequestHandler
from http.client import HTTPResponse
import urllib3
from io import BytesIO
import json
import sys
import logging


_LOGGER = logging.getLogger(__name__)

# Dicts
deviceAlarmKeywords = ['alarmMode','alarmState','alarmSOS','zone1State','zone2State','zone3State','zone4State','zone5State','zone6State','zone7State','zone8State','gsmLevel','inactiveProduct','zone1State','liveCheckRunning','networkDefect','unitAutoProtect','unitBatteryDefect','unackedEvent','alarmTechnical','systAutoProtect','sysBatteryDefect','zsystSupervisionDefect','systOpenIssue','systTechnicalDefect','videoLinkDefect', 'outTemperature']
deviceAlarmDetailsKeywords = ['alarmSOS','zone1State','zone2State','zone3State','zone4State','zone5State','zone6State','zone7State','zone8State','gsmLevel','inactiveProduct','zone1State','liveCheckRunning','networkDefect','unitAutoProtect','unitBatteryDefect','unackedEvent','alarmTechnical','systAutoProtect','sysBatteryDefect','zsystSupervisionDefect','systOpenIssue','systTechnicalDefect','videoLinkDefect', 'outTemperature']

deviceLightKeywords = ['level','onFavPos','thermicDefect','battDefect','loadDefect','cmdDefect','onPresenceDetected','onDusk']
deviceLightDetailsKeywords = ['onFavPos','thermicDefect','battDefect','loadDefect','cmdDefect','onPresenceDetected','onDusk']

deviceWindowKeywords = ['openState', 'config', 'battDefect', 'supervisionMode', 'intrusionDetect']

deviceDoorKeywords = ['openState']
deviceDoorDetailsKeywords = ['onFavPos','thermicDefect','obstacleDefect','intrusion','battDefect']

deviceCoverKeywords = ['position','onFavPos','thermicDefect','obstacleDefect','intrusion','battDefect']
deviceCoverDetailsKeywords = ['onFavPos','thermicDefect','obstacleDefect','intrusion','battDefect']

#climateKeywords = ['temperature', 'authorization', 'hvacMode', 'setpoint']

deviceBoilerKeywords = ['thermicLevel','delayThermicLevel','temperature','authorization','hvacMode','timeDelay','tempoOn','antifrostOn','openingDetected','presenceDetected','absence','loadSheddingOn','setpoint','delaySetpoint','anticipCoeff','outTemperature']
deviceElectricKeywords = ['thermicLevel','delayThermicLevel','temperature','authorization','hvacMode','timeDelay','tempoOn',
    'antifrostOn','openingDetected','presenceDetected','absence','loadSheddingOn','setpoint','delaySetpoint','anticipCoeff','outTemperature']

# Device dict for parsing
device_name = dict()
device_endpoint = dict()
device_type = dict()
# Thanks @Max013 !

class TydomMessageHandler():


    def __init__(self, incoming_bytes, tydom_client, mqtt_client):
            # print('New tydom incoming message')
            self.incoming_bytes = incoming_bytes
            self.tydom_client = tydom_client
            self.cmd_prefix = tydom_client.cmd_prefix
            self.mqtt_client = mqtt_client

    async def incomingTriage(self):
        bytes_str = self.incoming_bytes
        if self.mqtt_client == None: #If not MQTT client, return incoming message to use it with anything.
            return bytes_str
        else:
            incoming = None
            first = str(bytes_str[:40]) # Scanning 1st characters
            try:
                if ("Uri-Origin: /refresh/all" in first in first):
                    pass
                elif ("PUT /devices/data" in first) or ("/devices/cdata" in first):
                    # print('PUT /devices/data message detected !')
                    try:
                        incoming = self.parse_put_response(bytes_str)
                        await self.parse_response(incoming)
                    except:
                        print(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
                        print('RAW INCOMING :')
                        print(bytes_str)
                        print('END RAW')
                        print(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
                elif ("scn" in first):
                    try:
                        incoming = get(bytes_str)
                        await self.parse_response(incoming)
                        print('Scenarii message processed !')
                        print("##################################")
                    except:
                        print(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
                        print('RAW INCOMING :')
                        print(bytes_str)
                        print('END RAW')
                        print(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
                elif ("POST" in first):
                    try:
                        incoming = self.parse_put_response(bytes_str)
                        await self.parse_response(incoming)
                        print('POST message processed !')
                    except:
                        print(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
                        print('RAW INCOMING :')
                        print(bytes_str)
                        print('END RAW')
                        print(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
                elif ("HTTP/1.1" in first): #(bytes_str != 0) and
                    response = self.response_from_bytes(bytes_str[len(self.cmd_prefix):])
                    incoming = response.data.decode("utf-8")
                    try:
                        await self.parse_response(incoming)
                    except:
                        print(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
                        print('RAW INCOMING :')
                        print(bytes_str)
                        print('END RAW')
                        print(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
                else:
                    print("Didn't detect incoming type, here it is :")
                    print(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
                    print('RAW INCOMING :')
                    print(bytes_str)
                    print('END RAW')
                    print(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")

            except Exception as e:
                print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
                print('receiveMessage error')
                print('RAW :')
                print(bytes_str)
                print("Incoming payload :")
                print(incoming)
                print("Error :")
                print(e)
                print('Exiting to ensure systemd restart....')
                sys.exit() #Exit all to ensure systemd restart

    # Basic response parsing. Typically GET responses + instanciate covers and alarm class for updating data
    async def parse_response(self, incoming):
        data = incoming
        msg_type = None

        first = str(data[:40])
        # Detect type of incoming data
        if (data != ''):
            if ("id_catalog" in data): #search for id_catalog in all data to be sure to get configuration detected
                print(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
                print('Incoming message type : config detected')
                msg_type = 'msg_config'
            elif ("id" in first):
                print(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
                print('Incoming message type : data detected')
                msg_type = 'msg_data'
            elif ("doctype" in first):
                print('Incoming message type : html detected (probable 404)')
                msg_type = 'msg_html'
                print(data)
            elif ("productName" in first):
                print(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
                print('Incoming message type : Info detected')
                msg_type = 'msg_info'
                # print(data)
            else:
                print('Incoming message type : no type detected')
                print(data)

            if not (msg_type == None):
                try:
                    if (msg_type == 'msg_config'):
                        parsed = json.loads(data)
                        #print(parsed)
                        await self.parse_config_data(parsed=parsed)

                    elif (msg_type == 'msg_data'):
                        parsed = json.loads(data)
                        # Chic : debugging message
                        #print("Debug incoming Data")
                        #print(parsed)
                        await self.parse_devices_data(parsed=parsed)
                    elif (msg_type == 'msg_html'):
                        print("HTML Response ?")
                    elif (msg_type == 'msg_info'):
                        pass
                    else:
                        # Default json dump
                        print()
                        print(json.dumps(parsed, sort_keys=True, indent=4, separators=(',', ': ')))
                except Exception as e:
                    print('Cannot parse response !')
                    # print('Response :')
                    # print(data)
                    if (e != 'Expecting value: line 1 column 1 (char 0)'):
                        print("Error : ", e)
                        print(parsed)
            print('Incoming data parsed successfully !')
            return(0)

    async def parse_config_data(self, parsed):
        print("Parsing config data")
        print(parsed)
        for i in parsed["endpoints"]:
            # Get list of shutter
            # print(i)
            device_name[i["id_device"]] = i["name"]
            device_type[i["id_device"]] = i["last_usage"]
            device_endpoint[i["id_device"]] = i["id_endpoint"]

            if i["last_usage"] == '' :
                device_type[i["id_device"]] = 'unknown'
  
            print('Configuration updated')

    async def parse_devices_data(self, parsed):
        for i in parsed:
            for endpoint in i["endpoints"]:
                if endpoint["error"] == 0 and len(endpoint["data"]) > 0:
                    try:
                        attr_device = {}
                        class_name = "Unknown"
                        device_id = i["id"]
                        endpoint_id = endpoint["id"]
                        name_of_id = self.get_name_from_id(endpoint_id)
                        type_of_id = self.get_type_from_id(endpoint_id)

                        _LOGGER.debug("======[ DEVICE INFOS ]======")
                        _LOGGER.debug("ID {}".format(device_id))
                        _LOGGER.debug("ENDPOINT ID {}".format(endpoint_id))
                        _LOGGER.debug("Name {}".format(name_of_id))
                        _LOGGER.debug("Infos {}".format(endpoint["data"]))
                        _LOGGER.debug("Type {}".format(type_of_id))
                        _LOGGER.debug("==========================")


                        print_id = None
                        if len(name_of_id) != 0:
                            print_id = name_of_id
                        else:
                            print_id = device_id

                        attr_device['device_id'] = device_id
                        attr_device['endpoint_id'] = endpoint_id
                        attr_device['id'] =  type_of_id + '_' +str(device_id)+'_'+str(endpoint_id)
                        attr_device['name'] = print_id
                        

                        attr_device['device_type'] = type_of_id

                        if type_of_id == 'light':
                            attr_device['light_name'] = print_id
                            class_name = "Light"
                            
                        if type_of_id == 'shutter':
                            attr_device['cover_name'] = print_id
                            attr_device['device_type'] = 'cover'
                            class_name = "Cover"

                        if type_of_id == 'belmDoor':
                            attr_device['door_name'] = print_id
                            attr_device['device_type'] = 'sensor'
                            class_name = "Sensor"
                            

                        if type_of_id == 'windowFrench' or type_of_id == 'window':
                            attr_device['door_name'] = print_id
                            attr_device['device_type'] = 'window'
                            class_name = "Window"

                        if type_of_id == 'boiler':
                            attr_device['device_type'] = 'climate'
                            class_name = "Boiler"
                            
                        if type_of_id == 'electric' or type_of_id == 'hvac':
                            attr_device['device_type'] = 'climate'
                            class_name = "Electric"
                        
                        
                        if type_of_id == 'alarm':
                            attr_device['alarm_name']="Tyxal Alarm"
                            attr_device['device_type'] = 'alarm_control_panel'
                            class_name = "Alarm"
                        

                        for elem in endpoint["data"]:
                            _LOGGER.debug("CURRENT ELEM={}".format(elem))
                            # endpoint_id = None

                            elementName = None
                            elementValue = None
                            elementValidity = None

                            elementName = elem["name"]
                            elementValue = elem["value"]
                            elementValidity = elem["validity"]
                            
                            if elementValidity == 'upToDate':
                                attr_device[elementName] = elementValue
                            

                    except Exception as e:
                        print('msg_data error in parsing !')
                        print(e)

                    if class_name == "Cover":
                        new_cover = Cover(tydom_attributes=attr_device, mqtt=self.mqtt_client) 
                        await new_cover.update()
                    elif class_name == "Sensor":
                        new_door = sensor(elem_name='openState', tydom_attributes_payload=attr_device, attributes_topic_from_device='useless', mqtt=self.mqtt_client)
                        await new_door.update()
                    elif class_name == "Window":
                        new_window = Window(tydom_attributes=attr_device, tydom_client=self.tydom_client, mqtt=self.mqtt_client) 
                        await new_window.update()

                    elif class_name == "Unknown":
                        new_unknown = Unknown(tydom_attributes=attr_device, tydom_client=self.tydom_client, mqtt=self.mqtt_client) 
                        await new_unknown.update()
                    elif class_name == "Light":
                        new_light = Light(tydom_attributes=attr_device, mqtt=self.mqtt_client) #NEW METHOD
                        await new_light.update()
                    elif class_name == "Boiler":
                        new_boiler = Boiler(tydom_attributes=attr_device, tydom_client=self.tydom_client, mqtt=self.mqtt_client) #NEW METHOD
                        await new_boiler.update()
                    elif class_name == "Electric":
                        new_electric = Electric(tydom_attributes=attr_device, tydom_client=self.tydom_client, mqtt=self.mqtt_client) #NEW METHOD
                        await new_electric.update()
                   # Get last known state (for alarm) # NEW METHOD
                    elif class_name == "Alarm":
                        # print(attr_alarm)
                        state = None
                        sos_state = False
                        maintenance_mode = False
                        out = None
                        try:
                            # {
                            # "name": "alarmState",
                            # "type": "string",
                            # "permission": "r",
                            # "enum_values": ["OFF", "DELAYED", "ON", "QUIET"]
                            # },
                            # {
                            # "name": "alarmMode",
                            # "type": "string",
                            # "permission": "r",
                            # "enum_values": ["OFF", "ON", "TEST", "ZONE", "MAINTENANCE"]
                            # }

                            if ('alarmState' in attr_device and attr_device['alarmState'] == "ON") or ('alarmState' in attr_device and attr_device['alarmState']) == "QUIET":
                                state = "triggered"

                            elif 'alarmState' in attr_device and attr_device['alarmState'] == "DELAYED":
                                state = "pending"

                            if 'alarmSOS' in attr_device and attr_device['alarmSOS'] == "true":
                                state = "triggered"
                                sos_state = True

                            elif 'alarmMode' in attr_device and attr_device ["alarmMode"]  == "ON":
                                state = "armed_away"
                            elif 'alarmMode' in attr_device and attr_device["alarmMode"]  == "ZONE":
                                state = "armed_home"
                            elif 'alarmMode' in attr_device and attr_device["alarmMode"]  == "OFF":
                                state = "disarmed"
                            elif 'alarmMode' in attr_device and attr_device["alarmMode"]  == "MAINTENANCE":
                                maintenance_mode = True
                                state = "disarmed"

                            if 'outTemperature' in attr_device:
                                out = attr_device["outTemperature"]

                            if (sos_state == True):
                                print("SOS !")

                            if not (state == None):
                                # print(state)
                                alarm = "alarm_tydom_"+str(endpoint_id)
                                # print("Alarm created / updated : "+alarm)
                                alarm = Alarm(current_state=state, tydom_attributes=attr_device, mqtt=self.mqtt_client)
                                await alarm.update()

                        except Exception as e:
                            print("Error in alarm parsing !")
                            print(e)
                            pass
                    else:
                        print ("ERROR : can't change configuration")
                        pass

    # PUT response DIRTY parsing
    def parse_put_response(self, bytes_str):
        # TODO : Find a cooler way to parse nicely the PUT HTTP response
        resp = bytes_str[len(self.cmd_prefix):].decode("utf-8")
        fields = resp.split("\r\n")
        fields = fields[6:]  # ignore the PUT / HTTP/1.1
        end_parsing = False
        i = 0
        output = str()
        while not end_parsing:
            field = fields[i]
            if len(field) == 0 or field == '0':
                end_parsing = True
            else:
                output += field
                i = i + 2
        parsed = json.loads(output)
        return json.dumps(parsed)

    ######### FUNCTIONS

    def response_from_bytes(self, data):
        sock = BytesIOSocket(data)
        response = HTTPResponse(sock)
        response.begin()
        return urllib3.HTTPResponse.from_httplib(response)

    def put_response_from_bytes(self, data):
        request = HTTPRequest(data)
        return request

    def get_type_from_id(self, id):
        deviceType = ""
        if len(device_type) != 0 and id in device_type.keys():
            deviceType = device_type[id]
        else:
            print('{} not in dic device_type'.format(id))

        return(deviceType)

    # Get pretty name for a device id
    def get_name_from_id(self, id):
        name = ""
        if len(device_name) != 0 and id in device_name.keys():
            name = device_name[id]
        else:
            print('{} not in dic device_name'.format(id))
        return(name)


class BytesIOSocket:
    def __init__(self, content):
        self.handle = BytesIO(content)

    def makefile(self, mode):
        return self.handle

class HTTPRequest(BaseHTTPRequestHandler):
    def __init__(self, request_text):
        #self.rfile = StringIO(request_text)
        self.raw_requestline = request_text
        self.error_code = self.error_message = None
        self.parse_request()

    def send_error(self, code, message):
        self.error_code = code
        self.error_message = message
