from scale_client.sensors.csi_physical_sensor import CSIPhysicalSensor

import logging
log = logging.getLogger(__name__)

class CameraPhysicalSensor(CSIPhysicalSensor):
    """
    This sensor captures image from a camera attached to a Raspberry Pi.
    """
    
    def __init__(self, broker, sample_interval=10, **kwargs):
        super(CameraPhysicalSensor, self).__init__(broker, sample_interval=sample_interval, **kwargs)
