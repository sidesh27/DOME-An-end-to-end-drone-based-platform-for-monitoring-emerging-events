from scale_client.sensors.serial_physical_sensor import SerialPhysicalSensor

import logging
log = logging.getLogger(__name__)

class PMPhysicalSensor(SerialPhysicalSensor):
    """
    This sensor captures pm2.5 and pm10 from SDS011 sensor
    """

    def __init__(self, broker, sample_interval=10, **kwargs):
        super(PMPhysicalSensor, self).__init__(broker, sample_interval=sample_interval, **kwargs)


    def read_raw(self):
        import struct

        data = []
        for i in range(0,10):
            datum = self._ser.read() 
	    data.append(datum)

        pm25 = struct.unpack("<H", b''.join(data[2:4]))[0]
        pm10 = struct.unpack("<H", b''.join(data[4:6]))[0]

        pm25 = float(pm25) / 10
        pm10 = float(pm10) / 10

        return {"pm2.5":pm25, "pm10":pm10}

