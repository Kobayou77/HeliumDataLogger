'''
Helium Logger
=============
ver 0.0
with python2

kobayou
'''
from kivy.config import Config
#Config.set('graphics', 'width', '800')
#Config.set('graphics', 'height', '480')

#import necessarities
import time
import threading
from datetime import datetime
from kivy.uix.widget import Widget
from kivy.app import App
from os.path import dirname, join
from kivy.uix.progressbar import ProgressBar
from kivy.lang import Builder
from kivy.properties import NumericProperty, StringProperty, BooleanProperty,\
    ListProperty
from kivy.properties import ObjectProperty
from kivy.clock import Clock
from kivy.animation import Animation
from kivy.uix.screenmanager import Screen, ScreenManager
from kivy.base import runTouchApp
from kivy.uix.spinner import Spinner
from kivy.graphics import Color, Ellipse, Rectangle
from kivy.core.text import Label as CoreLabel

#import magnet


#build window with KVLanguage file
Builder.load_file('mainWindow.kv')

#GPIO settings

import RPi.GPIO as GPIO

GPIO.setmode(GPIO.BCM)
GPIO.setup(25, GPIO.OUT)

GPIO.setmode(GPIO.BCM)
SPICLK = 11
SPIMOSI = 10
SPIMISO = 9
SPICS = 8

GPIO.setup(SPICLK, GPIO.OUT)
GPIO.setup(SPIMOSI, GPIO.OUT)
GPIO.setup(SPIMISO, GPIO.IN)
GPIO.setup(SPICS, GPIO.OUT)


#GPIO read AD converter
def readadc(adcnum, clockpin, mosipin, misopin, cspin):
    if adcnum > 7 or adcnum < 0:
        return -1
    GPIO.output(cspin, GPIO.HIGH)
    GPIO.output(clockpin, GPIO.LOW)
    GPIO.output(cspin, GPIO.LOW)

    commandout = adcnum
    commandout |= 0x18
    commandout <<= 3
    for i in range(5):
        if commandout & 0x80:
            GPIO.output(mosipin, GPIO.HIGH)
        else:
            GPIO.output(mosipin, GPIO.LOW)
        commandout <<= 1
        GPIO.output(clockpin, GPIO.HIGH)
        GPIO.output(clockpin, GPIO.LOW)
    adcout = 0

    for i in range(13):
        GPIO.output(clockpin, GPIO.HIGH)
        GPIO.output(clockpin, GPIO.LOW)
        adcout <<= 1
        if i>0 and GPIO.input(misopin)==GPIO.HIGH:
            adcout |= 0x1
    GPIO.output(cspin, GPIO.HIGH)
    return adcout



# Declare MagnetSpinner inherited from Spinner
class MagnetSpinner(Spinner):
    def __init__(self, **kwargs):
        super(MagnetSpinner, self).__init__(**kwargs)
        keys = ['magnet', '600', '400', '200', '300', '300minus']
        self.text = keys[0]
        self.values = keys

# Declare mainLogger inherited from screens
class MainLogger(Screen):
    magnet_spinner = ObjectProperty(None)

    is_logger_active=BooleanProperty(False)
    is_clock_active=BooleanProperty(False)
    is_control_disable=BooleanProperty(True)
    nowtime=StringProperty()
    startTime=StringProperty()
    startTime_forOutput=StringProperty()
    outputfile=StringProperty()

    is_area1_percent=BooleanProperty(True)
    #-------------------------------------------------------
    sampling_interval=NumericProperty(3.0)
    #V_ref
    V_reference=NumericProperty(5.17)
    #-------------------------------------------------------

    leftPercent=NumericProperty(100.0)
    leftPercent_st=StringProperty('100.0 %')
    totalflow=NumericProperty(0.0)
    totalflow_st=StringProperty('0.000 L')

    nowflow_st=StringProperty('0.000 L/min')

    is_area3_left=BooleanProperty(True)
    leftHelium=NumericProperty(999.000)
    leftHelium_st=StringProperty('000.000 L')


    #-----magnet setting-----
    def magMax(self, mag):
        if mag == '600':
            return 458.0
        elif mag == '400':
            return 128.72
        elif mag == '200':
            return 88.82
        elif mag == '300':
            return 74.0
        elif mag == '300minus':
            return 186.6
        else:
            return 0

    # Min Lhe Volume
    def magMin(self, mag):
        if mag == '600':
            return 410.3
        elif mag == '400':
            return 74.258
        elif mag == '200':
            return 40.632
        elif mag == '300':
            return 33.09
        elif mag == '300minus':
            return 132.95
        else:
            return 0

    # Announce Level Lhe Volume
    def magAnnounce(self, mag):
        if mag == '600':
            return 426.2
        elif mag == '400':
            return 81.77
        elif mag == '200':
            return 46.68
        elif mag == '300':
            return 37.85
        elif mag == '300minus':
            return 140.35
        else:
            return 0

    # calculate with formula (not credible)
    def magCalculate(self, mag, mm):
        if mag == '600':
            return 0.636 * mm + 140
        elif mag == '400':
            return 0.1878 * mm + 53.6
        elif mag == '200':
            if mm < 287:
                return 0.1512 * mm + 24
            else:
                return 0.1903 * mm + 12.7
        elif mag == '300':
            if mm < 287:
                return 0.119 * mm + 20
            else:
                return 0.186 * mm - 0.4
        elif mag == '300minus':
            return 0.185 * mm + 112.6
        else:
            return 0
    #------------------------

    #-----clock setting-----
    def on_clock(self,dt):
        self.nowtime = datetime.now().strftime("%Y/%m/%d %H:%M:%S")
    def start_clock(self):
        self.is_clock_active = True
        Clock.schedule_interval(self.on_clock, 1.0)
        pass
    # do not use
    def stop_clock(self):
        self.is_clock_active = False
        Clock.unschedule(self.on_clock)
        pass
    #-----------------------

    #-----area1 setting-----
    def switch_area1(self):
        if self.is_area1_percent:
            self.is_area1_percent = False
        else:
            self.is_area1_percent = True

    def switch_area3(self):
        if self.is_area3_left:
            self.is_area3_left = False
        else:
            self.is_area3_left = True

    #-----logger setting-----
    def on_logger(self,dt):
        #---exp---
        #r = rand.randrange(50)
        #read = 1114.425 + r / 1000
        gpiovalue = readadc(0, SPICLK, SPIMOSI, SPIMISO, SPICS)

        V_read = self.V_reference * gpiovalue / 4096
        read = (V_read - 1) / 4
        #print(V_read)
        self.nowflow_st = '{:.3f} L/min'.format(read)
        file = open(self.outputfile, 'a')
        file.write('{:.3f}\n'.format(read))
        file.close()
        #---------

        flow = read / 60 * self.sampling_interval
        flow = flow * 0.1786 / 124.8
        #print(flow)

        self.totalflow += flow
        self.totalflow_st = '{:.3f} L'.format(self.totalflow)
        #print(self.totalflow)

        self.leftHelium -= flow
        self.leftHelium_st = '{:.3f} L'.format(self.leftHelium)

        self.leftPercent = 100 - self.totalflow * 100/ (self.magMax(self.magnet_spinner.text) - self.magMin(self.magnet_spinner.text))
        self.leftPercent_st = '{:.1f} %'.format(self.leftPercent)

    def start_logger(self, mag):

        self.is_logger_active = True

        self.startTime = datetime.now().strftime("%Y/%m/%d %H:%M:%S")
        self.startTime_forOutput = datetime.now().strftime("%Y%m%d_%H%M%S")

        self.totalflow = (1-self.leftPercent/100)*(self.magMax(self.magnet_spinner.text) - self.magMin(self.magnet_spinner.text))
        self.totalflow_st = '{:.3f} L'.format(self.totalflow)
        #self.leftPercent = 100.0
        self.leftPercent_st = '{:.1f} %'.format(self.leftPercent)
        self.leftHelium = self.magMax(self.magnet_spinner.text) - self.totalflow
        self.leftHelium_st = '{:.3f} L'.format(self.leftHelium)

        #file output
        self.outputfile = '/home/pi/Documents/he_{}.txt'.format(self.startTime_forOutput)
        file = open(self.outputfile, 'w')
        file.write('Magnet : {}\n'.format(self.magnet_spinner.text))
        file.close()

        Clock.schedule_interval(self.on_logger, self.sampling_interval)
        pass

    def stop_logger(self):
        self.is_logger_active = False
        file = open(self.outputfile, 'a')
        file.close()

        Clock.unschedule(self.on_logger)
        self.totalflow_st = '{:.3f} L'.format(self.totalflow)
        pass

    def switch_control_disable(self):
        if self.is_control_disable:
            self.is_control_disable = False
        else:
            self.is_control_disable = True

    def switch_logger(self):
        if self.is_logger_active:
            self.is_logger_active = False
            self.stop_logger()
            self.is_control_disable = True
        else:
            if self.magnet_spinner.text == 'magnet':
                self.is_logger_active = False
                self.is_control_disable = True
            else:
                self.is_logger_active = True
                self.start_logger(self.magnet_spinner.text)
                self.is_control_disable = True

    def minus10p(self):
        self.leftPercent -= 10
        self.leftPercent_st = '{:.1f} %'.format(self.leftPercent)
        self.totalflow = (1-self.leftPercent/100)*(self.magMax(self.magnet_spinner.text) - self.magMin(self.magnet_spinner.text))
        self.totalflow_st = '{:.3f} L'.format(self.totalflow)


    def minus1p(self):
        self.leftPercent -= 1
        self.leftPercent_st = '{:.1f} %'.format(self.leftPercent)
        self.totalflow = (1-self.leftPercent/100)*(self.magMax(self.magnet_spinner.text) - self.magMin(self.magnet_spinner.text))
        self.totalflow_st = '{:.3f} L'.format(self.totalflow)

    def minusfine(self):
        self.leftPercent -= 0.1
        self.leftPercent_st = '{:.1f} %'.format(self.leftPercent)
        self.totalflow = (1-self.leftPercent/100)*(self.magMax(self.magnet_spinner.text) - self.magMin(self.magnet_spinner.text))
        self.totalflow_st = '{:.3f} L'.format(self.totalflow)

    def resetp(self):
        self.leftPercent = 100
        self.leftPercent_st = '{:.1f} %'.format(self.leftPercent)
        self.totalflow = (1-self.leftPercent/100)*(self.magMax(self.magnet_spinner.text) - self.magMin(self.magnet_spinner.text))
        self.totalflow_st = '{:.3f} L'.format(self.totalflow)

    def endapp(self):
        GPIO.cleanup()
        exit()

#create mainLogger instance
ml = MainLogger()

class TestApp(App):

    def build(self):
        ml.start_clock()
        return ml

if __name__ == '__main__':
    TestApp().run()
    GPIO.cleanup()
