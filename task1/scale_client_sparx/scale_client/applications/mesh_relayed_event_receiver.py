import re
import subprocess
import json

from pprint import pprint
import asyncore, socket

import time
from time import sleep

from scale_client.core.threaded_application import ThreadedApplication
from scale_client.core.relayed_sensed_event import RelayedSensedEvent
from scale_client.core.sensed_event import SensedEvent
from scale_client.core.application import Application

import logging
log = logging.getLogger(__name__)

class AsyncoreReceiverUDP(asyncore.dispatcher, RelayedSensedEvent, Application):
    def __init__(self, broker, **kwargs):
        asyncore.dispatcher.__init__(self)
        Application.__init__(self, broker, **kwargs)
       
        self.relayedSensedEvent = RelayedSensedEvent()
        self.relayedSensedEvent.__init__()

        # Bind to port 5005 on all interfaces
        self.create_socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.bind(('', 3868))

        self.relayedSensedEvents = {}
        self.relayedSensedEvents['temperature'] = {}
        self.relayedSensedEvents['temperature']['neighbors_sum'] = 0.0
        self.relayedSensedEvents['temperature']['neighbors_counter'] = 0
        self.relayedSensedEvents['temperature']['neighbors_average'] = 0.0

    # Even though UDP is connectionless this is called when it binds to a port
    def handle_connect(self):
        log.info("Started listening traffic from neighbor nodes ... ")
        
    # This is called everytime there is something to read
    def handle_read(self):
        data, addr = self.recvfrom(2048)
        #print "GOT DATA FROM NEIGHBOR"
        #print str(addr)+" >> "+data

        if data:
            self.relayedSensedEvent.load_data(data)

            if(self.relayedSensedEvent.sensor == 'temperature'):
                self.calculate_neighbors_average_temp()

            print "RELAYED EVENT"
            print self.relayedSensedEvent
            print "PUBLISHING EVENT"
            sensedEvent = self.convert_to_sensed_event(self.relayedSensedEvent)

            # Publish relayed events from neighbors 
            # to the application
            self.publish(sensedEvent)

    def calculate_neighbors_average_temp(self):
        self.relayedSensedEvents['temperature']['neighbors_sum'] += self.relayedSensedEvent.data['value']
        self.relayedSensedEvents['temperature']['neighbors_counter'] += 1

        # calculate avarage temparature of all neighbors after receiving 5 
        if(self.relayedSensedEvents['temperature']['neighbors_counter'] > 5):
            self.relayedSensedEvents['temperature']['neighbors_average'] = self.relayedSensedEvents['temperature']['neighbors_sum']/self.relayedSensedEvents['temperature']['neighbors_counter']
            self.relayedSensedEvents['temperature']['neighbors_average'] = round(self.relayedSensedEvents['temperature']['neighbors_average'], 2)
   
            # Publish avarage temparature 
            self.publish_neighbors_avarage_temp()

            # reset total temp and counter
            self.relayedSensedEvents['temperature']['neighbors_counter'] = 0
            self.relayedSensedEvents['temperature']['neighbors_sum'] = 0.0
        return True

    def publish_neighbors_avarage_temp(self):

        # TODO: all of this should be replaced with a proper call to creating a SensedEvent (using the newer API)
        data = {}
        data['event'] = 'MeshSensor'
        data['event_type'] = 'average_temperature'
        data['value'] = self.relayedSensedEvents['temperature']['neighbors_average']
        data['detail'] = {}
        data['detail']['temp_count'] = self.relayedSensedEvents['temperature']['neighbors_counter']
        data['detail']['temp_sum'] = round(self.relayedSensedEvents['temperature']['neighbors_sum'])
            
        try:
            encoded_data = json.dumps(data)
            event = SensedEvent(data, data['event'], 5)
            self.publish(event)
            log.info('Published neighbors avarage temperature to application. Data: ' + encoded_data)

            return True
        except:
            log.error('Invalid average temparature encoded data string')
            return False

    # This is called all the time and causes errors if you leave it out.
    def handle_write(self):
        pass

    def convert_to_sensed_event(self, relayedSensedEvent):
        # TODO: verify these parameters are correct and propagate them to the rest of the mesh logic
        event = SensedEvent(data=relayedSensedEvent.data, source=relayedSensedEvent,
                            priority=relayedSensedEvent.priority, event_type=relayedSensedEvent.source,
                            timestamp=relayedSensedEvent.timestamp,
                            metadata={"published": relayedSensedEvent.published})
        return event

def f(nsec, broker):
    AsyncoreReceiverUDP(broker)
    asyncore.loop()

class MeshRelayedEventReceiver(ThreadedApplication): 
    def on_start(self):
        self.run_in_background(f, 3, self._broker)
