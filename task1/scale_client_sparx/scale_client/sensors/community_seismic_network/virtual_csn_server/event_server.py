# coding=utf-8

"""
Server to handle sensor events submitted by clients.

event data is available at the end of post_db method.
They can be retrieved from self.request_pb object

"""

import datetime
import logging
logging.basicConfig(filename='/var/log/csn_virtual_server', level=logging.DEBUG)

from scale_client.sensors.community_seismic_network.virtual_csn_server import api_handler, util
import sys

from scale_client.sensors.community_seismic_network.virtual_csn_server.messages import event_pb2

# Display time as a delta in seconds until delta is more than a year in size.
# Then, dislpay the system time for comparison.
DISPLAY_TIME_AS_DELTA_THRESHOLD = datetime.timedelta(days=365).total_seconds()

# SCALE client hard-coded parameters
#FIFO_FILE = "/var/run/scale_vs_csn.fifo"
SCALE_VS_MAGIC_LN = "$$$_SCALE_VS_MAGIC_LN_$$$"


class EventHandler(api_handler.ProtobufHandler):
    """
    Handles all incoming events submitted by clients.

    """

    REQUIRE_CLIENT = True
    REQUEST_OBJ = event_pb2.EventMessage
    RESPONSE_OBJ = event_pb2.EventResponse
	

    def post_pb(self, client_id_str=None):
        """
        Process event submitted by client.

        Parameters
        ----------
        client_id_str : string
            String version of the client submitting the sensor's data.

        Notes
        -----
        Logging of event data is done for future recoverability, but could be
        avoided by a number of strategies. One would be to encode more of the
        data in the submission URL. An example path might be::

            /api/v1/event/client_id/sensor_id/1.2_2.3_3.4

        Where the final path component is a _ delimited list of sensor
        reading(s) that triggered the event report. This has the advantage of
        mitigating the need for logging events but requires a more cumbersome
        url structure and data decoding process.

        """
        #TODO: make this not so hacky
        global _raw_event_queue

        current_time = util.system_time()
        if self.request_pb.event.HasField('date'):
            event_date_str = self.request_pb.event.date
        else:
            event_date_str = self.request_pb.client_signature.date
        if self.request_pb.HasField('latitude'):
            event_location = (self.request_pb.latitude,
                              self.request_pb.longitude)
        else:
            event_location = 'nul'

        event_date = util.parse_date(event_date_str)
        time_delta = round((current_time - event_date).total_seconds(), 3)
        time_delta_str = (str(time_delta)
                          if abs(time_delta) < DISPLAY_TIME_AS_DELTA_THRESHOLD
                          else api_handler.date_format(current_time))
        readings_str = [str(round(reading, 6))
                        for reading in self.request_pb.event.readings]
        logging.info('EventT%s: %s -> %s at %s(%s)',
                     self.request_pb.event.sensor_type,
                     self.request_pb.event.sensor_id,
                     readings_str,
                     event_date_str,
                     time_delta_str)

        self.write_response()
	
	"""

	self.request_pb.event instance holds the following data:

	sensor_id: 0
	sensor_type: ACCELEROMETER_3_AXIS
	readings: 0.0
	readings: 0.0
	readings: 1.05895996094
	date: "2014-04-13T19:36:43.205"
	event_count: 117
	time_window: 600

	self.request_pb.client_signature instance holds the following data:

  	date: "2014-04-13T19:42:17.744"
  	message_id: 678
  	signature: "f48d348f0862a281df95f3ef64ec2381f02818fb98a8b2df64b088ad5ba034fa"

	"""

	logging.info('Event data %s', self.request_pb)
	print (self.request_pb)
	print (SCALE_VS_MAGIC_LN)
        # _raw_event_queue.put(self.request_pb)
	sys.stdout.flush()
"""
	try:
		os.mkfifo(FIFO_FILE)
	except OSError:
		pass
	pipe_to_vs = open(FIFO_FILE, "w")
	pipe_to_vs.write(str(self.request_pb)+SCALE_VS_MAGIC_LN)
	pipe_to_vs.close()
"""
