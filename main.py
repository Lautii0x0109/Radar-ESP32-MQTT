import machine
import time                              #importe de bibliotecas
import network
import micropython
import secrets
from hcsr04 import HCSR04
from machine import Pin,PWM
from machine import Pin, Timer
from umqtt.simple import MQTTClient
#red de wifi y clave
ssid = 'Wokwi-GUEST'
wifipassword = ''
#datos de sserver MQTT (Broker)
#Indicacion de datos MQTT Broker (SV Y PORT)
mqtt_server = 'io.adafruit.com'
port = 1883
user =  secrets.ADAFRUIT_IO_USERNAME
password = secrets.ADAFRUIT_IO_KEY
#ID y Topicos
client_id = 'RadarT_A'
topic_ON_OFF = 'lauti0109/feeds/ONOFFRADAR'                         #radar on/off
topic_TangoDelta = 'lauti0109/feeds/TANGODETECTADO'                 #deteccion o no
topic_Slider_distancia = 'lauti0109/feeds/Slider_distancia'         #valor variable de la distancia del sensor/radar

#variable controladora
radar_prendido = False
Slider_distancia = None

def funcion_callback(topic, msg):
    global radar_prendido 
    global Slider_distancia    #global para que este valor se puefa modificar (importante para q funque)
    dato = msg.decode('utf-8')
    topicrec = topic.decode('utf-8') 
    print("msg recibido " +topicrec+":"+dato)

    if topicrec == topic_ON_OFF:
        
        if dato == "ON":
            radar_prendido =True 
            print("Radar ON")
        else:
            radar_prendido =False
            print("Radar OFF")
    else:
        if topicrec == topic_Slider_distancia:
            try:
                Slider_distancia = int(dato)
                print("Umbral de deteccion", Slider_distancia, "cm")
            except ValueError:
                print("Error, valor no valido")   


#coneccion a acces point remoto / wifi
sta_if = network.WLAN(network.STA_IF)
sta_if.active(True)
#wifi on
sta_if.connect(ssid, wifipassword)
print("Conectando")
while not sta_if.isconnected():
    print(".",end="")
    time.sleep(0.1)
print("Coneccion exitosa :)")
#ver ip´s
print(sta_if.ifconfig())

#conexion al Broker MQTT
try:
    conexionMQTT = MQTTClient(client_id,mqtt_server,user=user,password=password,port=int(1883))
    conexionMQTT.set_callback(funcion_callback)
    conexionMQTT.connect()
    conexionMQTT.subscribe(topic_ON_OFF)
    conexionMQTT.subscribe(topic_Slider_distancia)
    print("Conectado al Broker MQTT")
except OSError as e:
    print("Fallo de conexion al broker, reiniciando...")
    time.sleep(6)
    machine.reset()


pwmServo = PWM(Pin(10,Pin.OUT))
pwmServo.freq(50)                           #ubicacion de pin servo

sensor = HCSR04(trigger_pin=2, echo_pin=3)      #ubicacion de pin sensor hc

led = Pin(8, Pin.OUT)                           #ubicacion del LED

def medicion_distancia(timer):
    try:
        if radar_prendido == True and Slider_distancia is not None:
            distancia = sensor.distance_cm()
            print('distancia continua:', distancia, "cm")           #funcion para medir ditancia todo el tiempo
            if distancia <= Slider_distancia:
                print("Tango detectado")
                led.value(1)
                conexionMQTT.publish(topic_TangoDelta, "1")
            else:
                print("sin actividad aerea enemiga")
                led.value(0)
                conexionMQTT.publish(topic_TangoDelta, "0")
    except OSError:
        print('error de medicion')


timer1 = Timer(0)
timer1.init(period=2000, mode=Timer.PERIODIC, callback=medicion_distancia)   #medicion de distancia cada 200ms

while True:

    try:
        conexionMQTT.check_msg()
        time.sleep_ms(500)
    except OSError as e:
        print("Error ",e)
        time.sleep(5)
        machine.reset()

    if radar_prendido==True:
        pwmServo.duty(25)           #25 = 0°
        time.sleep(0.5)
        pwmServo.duty(125)          #125 = 180°          #movimiento del servo
        time.sleep(0.9)
    else:
        time.sleep(0.1)
