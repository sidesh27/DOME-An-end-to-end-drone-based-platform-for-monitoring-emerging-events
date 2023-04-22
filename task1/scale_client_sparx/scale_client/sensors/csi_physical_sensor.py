from scale_client.sensors.physical_sensor import PhysicalSensor
from datetime import datetime

import logging
log = logging.getLogger(__name__)

class CSIPhysicalSensor(PhysicalSensor):
    """
    This class is specifically designed to support camera sensor attached to the CSI (Camera Serial Interface) on a Raspberry Pi.
    """


    def __init__(self, broker, file_path = "scale_client/images/", sample_interval=10, **kwargs):
        super(CSIPhysicalSensor, self).__init__(broker, sample_interval=sample_interval, **kwargs)
        self._path = file_path
	self._camera = None
	self._stream = None
 
    def read_raw(self):
	import json
	if self._stream == None:
	    from io import BytesIO
            self._stream = BytesIO()
	#now = datetime.now()
	#now_string = now.strftime("%Y-%m-%d-%H-%M-%S")
        #self._camera.capture(self._path+now_string+".jpg")

	self._camera.capture(self._stream, 'jpeg')
	print("Camera Byte Array:")
	#print("Type:",type(self._stream))
	#print(self._stream.getvalue())
	self._stream.seek(0)
	#img = self._stream.read(500)
	img = self._stream.getvalue()
	img_str = img.decode('latin1')
	#print(img)
	print(type(img))
	#print(img.decode('latin1'))
	#print(img.decode('latin1').replace("'",'"'))
	#return self._stream.getvalue()
	return img_str
	test = "testtext"
	return test

    def on_start(self):
        if self._camera == None:
            from picamera import PiCamera

            self._camera = PiCamera()

        super(CSIPhysicalSensor, self).on_start()

