from scale_client.sensors.physical_sensor import PhysicalSensor

import logging
log = logging.getLogger(__name__)

class SerialPhysicalSensor(PhysicalSensor):
    """
    This class is specifically design to support data from serail port (USB)
    """

    def __init__(self, broker, sample_interval=10, **kwargs):
        super(SerialPhysicalSensor, self).__init__(broker, sample_interval=sample_interval, **kwargs)
        self._ser = None


    def on_start(self):
        if self._ser == None:
            import serial

            self._ser = serial.Serial('/dev/ttyUSB0')

        super(SerialPhysicalSensor, self).on_start()
