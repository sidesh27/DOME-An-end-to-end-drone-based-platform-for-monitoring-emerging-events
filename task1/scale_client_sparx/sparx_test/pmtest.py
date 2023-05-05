import serial, time
import struct

ser = serial.Serial('/dev/ttyUSB0')

while True:
    data = []
    for i in range(0,10):
        datum = ser.read()
        data.append(datum)


    print("data:",data)
    
    pm25 = struct.unpack("<H", b''.join(data[2:4]))[0]
    pm10 = struct.unpack("<H", b''.join(data[4:6]))[0]

    print("PM2.5:",pm25)
    print("PM10:",pm10)

    print(type(pm25))

    print("PM2.5/10:",float(pm25)/10)
    print("PM10/10:",float(pm10)/10)

    time.sleep(2)
