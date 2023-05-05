from scale_client.sensors.physical_sensor import PhysicalSensor

import logging
log = logging.getLogger(__name__)

class WeatherPhysicalSensor(PhysicalSensor):
    def __init__(self, broker, interval=5, event_type="weather", **kwargs):
        super(WeatherPhysicalSensor, self).__init__(broker, interval=interval, event_type=event_type, **kwargs)
        self._weatherhat = None

    def on_start(self):
        if self._weatherhat is None:
            import scale_client.sensors.weatherhat as weatherhat
            self._weatherhat = weatherhat.WeatherHAT()

        super(WeatherPhysicalSensor, self).on_start()

    def read_raw(self):
        self._weatherhat.update(interval=self._sample_interval)

        log.info("Weather sensor get temp: %s, wind_direction: %s, wind_speed: %d" % 
            (self._weatherhat.temperature, self._weatherhat.wind_direction, self._weatherhat.wind_speed))        
 
        return {"temperature":self._weatherhat.temperature, "pressure":self._weatherhat.pressure, 
            "humidity":self._weatherhat.humidity, "relative_humidity":self._weatherhat.relative_humidity,
            "dew_point":self._weatherhat.dewpoint, "lux":self._weatherhat.lux, 
            "wind_direction":self._weatherhat.wind_direction, "wind_speed":self._weatherhat.wind_speed,
            "rain":self._weatherhat.rain, "rain_total":self._weatherhat.rain_total}

