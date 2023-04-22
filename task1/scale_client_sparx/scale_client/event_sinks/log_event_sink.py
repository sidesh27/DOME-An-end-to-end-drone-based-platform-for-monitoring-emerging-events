from event_sink import EventSink
from datetime import datetime
import logging
import json
log = logging.getLogger(__name__)
# go ahead and set the logger to INFO here so that we always log the events in question
log.setLevel(logging.INFO)


class LogEventSink(EventSink):
    """
    This EventSink simply prints all sunk SensedEvents to log.info
    """

    def send_raw(self, encoded_event):
        msg = "event sunk: %s" % encoded_event
        log.info(msg)
        dic = json.loads(encoded_event)
        timestamp = dic['d']['timestamp']
        event = dic['d']['event']
        print(event)
        current = datetime.now()
        currentTime = current.strftime("%H:%M:%S")
        dic['d']['value']['timestamp'] = currentTime
        dic['d']['value']['id'] = event + "2"
        print(dic['d']['value'])
        path = "/home/pi/Desktop/data/"+event+"/"+str(timestamp)+".json"
        print(path)
        with open(path, "w+") as f:
            f.write(json.dumps(dic['d']['value']))
