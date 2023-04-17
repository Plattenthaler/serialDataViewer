#Ursprung bildet "oszilloskop" beispiel von animation.FuncAnimation
#mit zusätzlichen elementen
#
#
#"pip install pyserial" nicht normal serial!!!
#
#
#Programm muss gestartet werden mit:
#c:\Users\User\Desktop>serialDataViewer.py COM4 115200

# Tested with: 
# Python            3.8.1

# scipy             1.10.1
# pysinewave        0.0.6
# pyserial          3.5
# matplotlib        3.7.0
# numpy             1.24.2
# cx-Freeze         6.6 (6.14.4 installation error on Windows)

import numpy as np
#from   scipy.stats import norm
from   matplotlib.lines import Line2D
from   matplotlib.widgets import Slider, Button, RadioButtons, TextBox, CheckButtons
import matplotlib.pyplot as plt
import matplotlib.mlab   as mlab
import matplotlib.animation as animation
from   serial import Serial
import sys
import serial.tools.list_ports
from   pysinewave import SineWave #fuer tonausgabe
import warnings #supress np warnings
import os
import time
import datetime
from inspect import currentframe, getframeinfo

frameinfo = getframeinfo(currentframe())


def check_write_permission():
    write_permition = False
    try:
        file=open("test.txt","a")
        file.close()
        os.remove("test.txt")
        write_permition = True
    except Exception as e:
        print(getframeinfo(currentframe()).lineno, e)
        write_permition = False
    return write_permition

def substring_after(s, delim):
    return s.partition(delim)[2]

def substring_before(s, delim):
    return s.partition(delim)[0]
    
#if nanmean is aplyed over a empty array (filled with "nan") a runtimewarning occures.
def numpy_nan_mean(a):
    if np.isnan(a[0]):
        return np.NaN 
    else:
        return np.nanmean(a)

# Mouse tracking diplay left and right values in navigation bar for datetime64
# # https://stackoverflow.com/questions/21583965/matplotlib-cursor-value-with-two-axes/53678689
def make_format(current, other):
    # current and other are axes
    def format_coord(x, y):
        # x, y are data coordinates
        # convert to display coords
        display_coord = current.transData.transform((x,y))
        inv = other.transData.inverted()
        # convert back to data coords with respect to ax
        ax_coord = inv.transform(display_coord)
        coords = [ax_coord, (x, y)]
        string = str(round(x,2))+ " : "
        #print(coords)
        for x_, y_  in coords:
            string += str(round(y_, 3)) + "; "
        return string

    return format_coord    

try:
    from version import Version
except Exception:
    class Version:
        def __init__(self):
            self.string_firsttag = "X.X-update-git-hooks"
            self.string_reltag = "X.X-0-ffffffff"


        
        
class Scope(object):
    def __init__(self, ax, dt, serialPort, x_config="samples"):
        self.sinewave = SineWave(pitch = 5, pitch_per_second = 1000)
        self.serialPort = serialPort
        self.write_permission = check_write_permission()
        self.sendestatus = True #fuer toggeln der datenuebermittlung
        self.ylinlog = False #status y-achsen skalierung in lin oder logarythmisch 
        self.tonausgabe = False #status der Tonausgabe
        self.string_to_strip_after = ''
        self.string_to_strip_before = 'placeholder'
        self.ax_L = ax
        self.ax_L.tick_params(axis='y', colors='blue')
        self.ax_R = self.ax_L.twinx()
        self.ax_R.format_coord = make_format(self.ax_R, self.ax_L)
        self.ax_R.tick_params(axis='y', colors='red')
        self.dt = dt
        self.samples = 500 # wird durch submit uebernommen, wird sonst auch als Sekunden interpretiert
        self.npoints = self.samples #sind die waren samples!
        self.gleitt = self.npoints
        self.autoadjust = True
        self.datenausgabe = False
        self.sendetext = "t 165"
        self.dist_bins = 50 #Aufloesung der Verteilungsfunktion
        self.sample_period_duration = 100 #in ms
        self.tdata_c = [0] #for x-Values in counts
        self.tdata_t = np.empty(1, dtype='datetime64[us]') #for x-values as timestamp
        self.x_config = x_config # "samples" or "timestamp"
        self.ydata_L = [0]
        self.ydata_R = [np.nan]
        self.y_mittel_L = [0]
        self.y_mittel_R = [np.nan]
        if(self.x_config=="samples"):    
            x_arr = self.tdata_c
            self.ax_L.set_xlim(0, self.npoints)
        else:
            x_arr = self.tdata_t
            now=np.datetime64(datetime.datetime.now(), "us")
            self.ax_L.set_xlim(now, now + np.timedelta64(self.sample_period_duration*self.samples,"ms"))
        self.line_ymittel_L = Line2D(x_arr, self.y_mittel_L, color="blue", linestyle="--")
        self.line_ymittel_R = Line2D(x_arr, self.y_mittel_R, color="red" , linestyle="--")
        self.line_yval_L = Line2D(x_arr, self.ydata_L, color="blue")
        self.line_yval_R = Line2D(x_arr, self.ydata_R, color="red")
        self.ax_L.add_line(self.line_ymittel_L)
        self.ax_R.add_line(self.line_ymittel_R)
        self.ax_L.add_line(self.line_yval_L)
        self.ax_R.add_line(self.line_yval_R)
        self.ax_L.set_ylim(-.1, self.samples)
        #erase outputdocuments
        #open("data-out.txt","w").close()
        #open("dist-out.txt","w").close()
        #open("fft-out.txt","w").close()
        
        self.init_user_elements()
        self.check_connection()
        self.serial_connect()
        print("write permission: ",self.write_permission)
        
    def __del__(self):
        del self
        print("bye")
        
    def init_user_elements(self):    
        #die slider
        axcolor = 'lightgoldenrodyellow'
        self.skalierung_ymax = Slider(plt.axes([0.25, 0.08, 0.65, 0.02], facecolor=axcolor), 'Y Max', 10, 730.0 , valinit = 500)
        self.skalierung_ymin = Slider(plt.axes([0.25, 0.05, 0.65, 0.02], facecolor=axcolor), 'Y Min', 10, 730.0 , valinit = 0)
                        
        #drueckbutton
        self.mess_toggle_button =        Button(plt.axes([0.85, 0.95, 0.1, 0.04]), 'A-Mess', color=axcolor, hovercolor='0.975')
        self.fft_button =                Button(plt.axes([0.605, 0.91, 0.1, 0.04]), 'FFT', color=axcolor, hovercolor='0.975')
        self.dist_button =               Button(plt.axes([0.605, 0.87, 0.1, 0.04]), 'Dist', color=axcolor, hovercolor='0.975')
        self.sent_button =               Button(plt.axes([0.605, 0.95, 0.1, 0.04]), 'Senden', color=axcolor, hovercolor='0.975')
        self.reset_button =              Button(plt.axes([0.85, 0.91, 0.1, 0.04]), 'Reset', color=axcolor, hovercolor='0.975')
        self.single_autorange_button =   Button(plt.axes([0.85, 0.87, 0.1, 0.04]), '1x Y-auto', color=axcolor, hovercolor='0.975')
        self.connect_button =            Button(plt.axes([0.85, 0.83, 0.1, 0.04]), 'Con/Disc', color=axcolor, hovercolor='0.975')
        self.submit1_button =            Button(plt.axes([0.655, 0.005, 0.1, 0.04]), 'Submit', color=axcolor, hovercolor='0.975')
        
        #Eingabezeile 
        self.sent_box =                 TextBox(plt.axes([0.2, 0.95,   0.4, 0.04]), 'Befehl', initial=self.sendetext)
        self.sample_period_duration_box=TextBox(plt.axes([0.2, 0.91,   0.4, 0.04]), 'Sampletime ms', initial=str(self.sample_period_duration))
        self.dist_bins_box =            TextBox(plt.axes([0.2, 0.87,   0.4, 0.04]), 'N Bins', initial=str(self.dist_bins))
        self.string_strip_before_box =  TextBox(plt.axes([0.2, 0.83,   0.4, 0.04]), 'String after val', initial=self.string_to_strip_before)
        self.string_strip_after_box =   TextBox(plt.axes([0.2, 0.79,   0.4, 0.04]), 'String before val', initial=self.string_to_strip_after)
        self.samples_box =              TextBox(plt.axes([0.25, 0.005, 0.4, 0.04]), 'Samples', initial=str(self.samples))
        self.serial_status_text =       TextBox(plt.axes([0.605, 0.79,   0.345, 0.04]), '')
        #checkbox
        if self.x_config=="samples":
            checkbox_conf=(True, False, False, False, False)
        else:
            checkbox_conf=(True, False, False, False, True)
        self.check = CheckButtons(plt.axes([0.72, 0.85, 0.11, 0.14]), ('Y-Auto', 'Data-out', 'Y-Log', 'Ton', 'x time'), checkbox_conf)
               
        #Button events
        self.fft_button.on_clicked(self.fft_erstellen)
        self.dist_button.on_clicked(self.dist_erstellen)
        self.mess_toggle_button.on_clicked(self.mess_toggle_event)
        self.sent_button.on_clicked(self.sent)
        self.reset_button.on_clicked(self.reset)
        self.single_autorange_button.on_clicked(self.single_autorange)
        self.connect_button.on_clicked(self.serial_connect)
        self.submit1_button.on_clicked(self.submit_samples)
        
        #Checkbox Events
        self.check.on_clicked(self.funktion)
          
        #Text-Events
        self.sent_box.on_submit(self.textupdate_sent)
        self.sample_period_duration_box.on_submit(self.textupdate_periode_duration)
        self.dist_bins_box.on_submit(self.textupdate_dist_bins)
        self.samples_box.on_submit(self.textupdate_samples)
        
        #Slider-Events
        self.skalierung_ymin.on_changed(self.range_manuell_anpassen)
        self.skalierung_ymax.on_changed(self.range_manuell_anpassen)
        
    def mess_toggle_event(self, event):
        self.sendestatus = not self.sendestatus
        if self.sendestatus == True :
            self.serialPort.write(b"s 1\r")
            print("Serielles Senden an")
        else :
            self.serialPort.write(b"s 0\r")
            print("Serielles Senden aus")
    
    def sent(self, event):
        #self.serialPort.write(text.encode("utf-8"))
        self.serialPort.write(self.sendetext.encode("utf-8"))
        self.serialPort.write(b"\r")
        print(self.sendetext)
    
    def textupdate_sent(self, text):
        self.sendetext=text
    
    def textupdate_periode_duration(self, text):
        try:
            self.sample_period_duration = int(text)
            #print("FFT Zeitbasis: ",self.sample_period_duration," ms")
        except Exception as e:
            print(getframeinfo(currentframe()).lineno, e)
        
    def textupdate_dist_bins(self, text):
        try:
            self.dist_bins = int(text)
            #print("Intervalle in Verteilungsfunktion: ",self.dist_bins,)
        except Exception as e:
            print(getframeinfo(currentframe()).lineno, e)
    
    def textupdate_samples(self, text):
        try:
            self.samples = int(text)
            #print("Anzahl der Samples: ",self.samples)
        except Exception as e:
            print(getframeinfo(currentframe()).lineno, e)
    
    def funktion(self, label) : # Checkbox events
        if label == 'Y-Auto':
            self.autoadjust = not self.autoadjust
        elif label == 'Data-out':
            self.datenausgabe = not self.datenausgabe
        elif label == 'Y-Log':
            self.ylinlog = not self.ylinlog
            if self.ylinlog:
                self.ax_L.set_yscale('symlog')
                self.ax_R.set_yscale('symlog')
            else:
                self.ax_L.set_yscale('linear')
                self.ax_R.set_yscale('linear')
            self.single_autorange()
        elif label == 'Ton':
            self.tonausgabe = not self.tonausgabe
            if self.tonausgabe:
                self.sinewave.play()
            else:
                self.sinewave.stop()
        elif label == 'x time':
            print("switch to time-based X-Axis")
            time.sleep(2.5)
            print("switch to time-based X-Axis")
            
            self.serial_connect()
            if self.x_config=="samples":
                tmp_x_config="timestamp"
            else:
                tmp_x_config="samples"
            self.__init__(self.ax_L, self.dt, self.serialPort, x_config=tmp_x_config)
            plt.plot()
            
    def single_autorange(self, u=0):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=RuntimeWarning) # suppress numpy warnig: "All-NaN axis encountered" raised if empty y-datta is given
            ylim_min_l = np.nanmin(self.ydata_L)-(np.nanmax(self.ydata_L)-np.nanmin(self.ydata_L))/20
            ylim_max_l = np.nanmax(self.ydata_L)+(np.nanmax(self.ydata_L)-np.nanmin(self.ydata_L))/20
            if not(np.isnan(ylim_max_l)) and not(np.isnan(ylim_min_l)):
                if ylim_max_l != ylim_min_l:
                    self.ax_L.set_ylim(ylim_min_l,ylim_max_l)
            ylim_min_r = np.nanmin(self.ydata_R)-(np.nanmax(self.ydata_R)-np.nanmin(self.ydata_R))/20
            ylim_max_r = np.nanmax(self.ydata_R)+(np.nanmax(self.ydata_R)-np.nanmin(self.ydata_R))/20
            if not(np.isnan(ylim_max_r)) and not(np.isnan(ylim_min_r)):
                if ylim_max_r != ylim_min_r:
                    self.ax_R.set_ylim(ylim_min_r,ylim_max_r)
        
    def submit_samples(self, u=0):
        self.npoints = self.samples # übernahme der werte von der eingabebox
        self.reset()

    def range_manuell_anpassen(self, u=0):
        self.ax_L.set_ylim(10 ** (self.skalierung_ymin.val/100), 10 ** (self.skalierung_ymax.val/100))
        self.ax_R.set_ylim(10 ** (self.skalierung_ymin.val/100), 10 ** (self.skalierung_ymax.val/100))
        self.ax_L.figure.canvas.draw()

    def range_anpassen(self, u=0):
        if self.autoadjust == True :
            self.single_autorange(self)
        else:
            #self.ax_L.set_ylim(10 ** (self.skalierung_ymin.val/100), 10 ** (self.skalierung_ymax.val/100))
            pass
        self.ax_L.figure.canvas.draw()
        return self.line_yval_L, self.line_yval_R, self.line_ymittel_L, self.line_ymittel_R
    
    def fft_erstellen(self, g=3):
        #print(self.sent_box_fft_time.val)
        dt = int(self.sample_period_duration)/1000 #samplingtime in sekunden
        fa = 1.0/dt # scan frequency
        Y=np.fft.fft(np.hanning(len(self.ydata_L))*self.ydata_L)
        N = len(Y)
        X = np.linspace(0, fa/2, N, endpoint=True)
        #x = np.linspace(0, 2*np.pi, 400)
        #y = np.sin(x**2)
        fig2, ax2 = plt.subplots()
        #fig2.subplots_adjust(bottom=0.15)
        ax2.set_title(r'$\mathrm{FFT:}\ Freq=%.2f Hz,\ samples=%.0f,\ T=%.3f$ ms' %(fa, len(self.ydata_L), dt*1000))#"FFT-Plot Samplingfreq: " + str(fa) + "Hz, Periodendauer: " + str(dt*1000) + "ms") 
        ax2.plot(X,np.abs(Y))
        ax2.set_xscale('log')
        ax2.set_yscale('log')
        #ax2.set_ylim(0,max(Y[1:]))
        #plt.xlim(0.001, 10)
        plt.grid()
        plt.show()
    
    def dist_erstellen(self, g=3) :
        fig_verteilung, ax_verteilung = plt.subplots()
        sigma = np.std(self.ydata_L)
        #varianz = np.var(self.ydata_L)
        mu = np.nanmean(self.ydata_L)
        n, bins, patches = plt.hist(self.ydata_L, bins=self.dist_bins, density=True) #density -> normed distribution
        #y = mlab.normpdf( bins, mu, sigma) #old, not working
        gausverteilung =  1/(sigma * np.sqrt(2 * np.pi)) * np.exp( - (bins - mu)**2 / (2 * sigma**2) ) 
        l = plt.plot(bins, gausverteilung, 'r--', linewidth=2)
        
        #f=open("out.txt","a")
        try:
            if(self.write_permission):
                print ("bins=", bins, file=open("dist-out.txt","a"))
                print ("werte=",n, file=open("dist-out.txt","a"))
                print ("patches=",patches, file=open("dist-out.txt","a"))
        except Exception as e:
            print(getframeinfo(currentframe()).lineno, e)
        #f.close()
        
        #ax_verteilung.set_title("Verteilung mit sigm: " + str(standartabweichung) + " Varianz: " + str(varianz) + " und Mittelwert: " + str(mittelwert)) 
        ax_verteilung.set_title(r'$\mathrm{Histogram}\ \mu=%.1f,\ \sigma=%.3f$, Samples=%.0f Bins=%.0f' %(mu, sigma, len(self.ydata_L), self.dist_bins))
        
        #plt.axis([0, 10000, 0, 10])
        plt.grid(True)
        plt.show()
    
    def serial_connect(self, u=0):
        if (self.serialPort.isOpen()): # isOpen is deprecated but working
            self.serialPort.close()
            print("serial "+str(self.serialPort.port)+" closed")
        else:
            try:
                con_text=self.serial_status_text.text
                self.serialPort.port = substring_before(con_text, ",")
                baudrate = substring_before(con_text, ":")
                baudrate = substring_after(baudrate, ", ")
                self.serialPort.baudrate = baudrate
                self.serialPort.open()
                print("connect")
            except Exception as e:
                print(getframeinfo(currentframe()).lineno, e)
                print("-")
                print("-")
                print("-")
                print("Available Ports:")
                comportliste=serial.tools.list_ports.comports()
                for entry in comportliste:
                    print(entry)
        self.check_connection() 
        
    def check_connection(self):
        # ser.is_open returns also True, if the connection was (externaly) interrupted
        ser_is_open = False
        try:
            self.serialPort.inWaiting()
            ser_is_open = True
        except:
            ser_is_open = False
        if (ser_is_open):
                self.serial_status_text.set_val(str(self.serialPort.port + ", " + str(self.serialPort.baudrate) + ": Connected"))
        else:
            if(self.serial_status_text.text.find("Disconnected")<0): # just update this text once. Otherwise no external textupdate is possiblly. 
                self.serial_status_text.set_val(str(self.serialPort.port + ", " + str(self.serialPort.baudrate) + ": Disconnected"))

    def reset(self, g=0):
        #2 Daten anhaengen, damit auto x-einstellung funktioniert
        self.tdata_c.append(0)
        self.tdata_t = np.append(self.tdata_t, np.datetime64(datetime.datetime.now(), "us"))
        self.ydata_L.append(np.nanmean(self.ydata_L))
        if len(self.ydata_R) == np.count_nonzero(~np.isnan(self.ydata_L)): # suppress runtimewarning mean over empty array
            self.ydata_R.append(np.nanmean(self.ydata_R))
        else:
            self.ydata_R.append(0)
        del self.tdata_c[:-1  ]
        tmp_tmp=self.tdata_t[-1]
        self.tdata_t = np.empty(1, dtype='datetime64[us]')
        self.tdata_t[0]=tmp_tmp
        del self.ydata_L [:-1]
        del self.ydata_R [:-1]
        self.npoints = self.samples
        if(self.x_config=="samples"):
            self.ax_L.set_xlim(0, self.npoints)
            self.ax_R.set_xlim(0, self.npoints)   
        else:
            now=np.datetime64(datetime.datetime.now(), "us")
            upper_range=now + np.timedelta64(np.timedelta64(self.sample_period_duration*self.samples,"ms"),"s")
            self.ax_L.set_xlim(now,upper_range)
            self.ax_R.set_xlim(now,upper_range)
            pass
        self.gleitt=self.npoints
        self.ax_L.figure.canvas.draw()
    
    def update(self, i=0):
        i = 0;
        in_waiting = 0
        data_available = 0
        try: #Check the serial communication
            in_waiting = self.serialPort.inWaiting()
        except Exception as e:
            #print(getframeinfo(currentframe()).lineno, e)
            self.check_connection()
            return self.line_yval_L, self.line_yval_R, self.line_ymittel_L, self.line_ymittel_R
        read_data_len = 1000
        ydata_L = np.empty(read_data_len+1)
        ydata_R = np.empty(read_data_len+1)
        tdata_t = np.empty(read_data_len+1, dtype='datetime64[us]')
        ydata_L[:] = np.nan
        ydata_R[:] = np.nan
        #tdata_t[:] = np.nan
        while (in_waiting != 0) & (i<read_data_len):         
            try:
                inputline = self.serialPort.readline()# read a '\n' terminated line otherwise timeout
                in_waiting = self.serialPort.inWaiting()
            except Exception as e:
                print(getframeinfo(currentframe()).lineno, e)  
            try:
                inputline = inputline.decode('ascii').strip("\r\n")
            except Exception as e:
                print(getframeinfo(currentframe()).lineno, e)

            #String zuschneiden
            try:
                if self.string_strip_after_box.text!="":
                    inputline=substring_after(inputline, self.string_strip_after_box.text)
                if self.string_strip_before_box.text != "":
                    inputline=substring_before(inputline, self.string_strip_before_box.text)#self.string_strip_before_box #self.string_to_strip_before
                #print(inputline)
            except Exception as e:
                print(getframeinfo(currentframe()).lineno, e)
            if inputline != "": #weil bestätigung leerer string ist
                try:
                    if(inputline.find(";")==-1):  # If just one Value   
                        wert_L=float(inputline) # war int, hoffe das macht keine probleme
                        wert_R=float('nan')
                    else:
                        in_line_sp = inputline.split(";")
                        wert_L=float(in_line_sp[0])
                        wert_R=float(in_line_sp[1])
                        if(len(in_line_sp)>2):
                            print(in_line_sp[2:])

                    ydata_L[i] = wert_L
                    ydata_R[i] = wert_R
                    data_available +=1
                    if self.tonausgabe== True :
                        self.sinewave.set_frequency(wert_L*1.5+220)
                except Exception as e:
                    ydata_L[i] = np.nan
                    ydata_R[i] = np.nan
                    print(getframeinfo(currentframe()).lineno, e)
                tdata_t[i] = np.datetime64(datetime.datetime.now(), "us")
            else:
                #print("leerer string, befehl uebertragen!")
                pass
            i +=1
        
        if(data_available > 0):
            if (data_available>read_data_len*0.7):
                print("too much data", data_available)
            if len(self.ydata_L)==1: #um initialen wert zu entfernen
                self.ydata_L[0]=ydata_L[0]
                self.ydata_R[0]=ydata_R[0]

            if self.datenausgabe == True :
                ausgabetext = ""
                for ausg_i in range(i):
                    ausgabetext += str(tdata_t[ausg_i]) + "\t" + str(ydata_L[ausg_i])+ "\t" + str(ydata_R[ausg_i])+"\r\n"
                print(ausgabetext[:ausgabetext.find("\r")])
                if(self.write_permission):
                    print(ausgabetext, file=open("data-out.txt","a"))     

            self.ydata_L.extend(ydata_L[0:i].tolist())
            self.ydata_R.extend(ydata_R[0:i].tolist())
            self.tdata_t = np.append(self.tdata_t, tdata_t[0:i])
            self.tdata_c.extend(np.arange(self.tdata_c[-1]+1,self.tdata_c[-1]+i+1).tolist())
            
            self.ydata_L     = self.ydata_L   [-1 * self.npoints:]   # Auf bereich anpassen
            self.ydata_R     = self.ydata_R   [-1 * self.npoints:]   # Auf bereich anpassen
            self.tdata_t     = self.tdata_t   [-1 * self.npoints:]   # Auf bereich anpassen
            self.tdata_c     = self.tdata_c   [-1 * self.npoints:]   # Auf bereich anpassen

        if self.tdata_c[-1] > self.gleitt:  # reset the arrays
            self.gleitt = self.tdata_c[-1] + self.npoints*0.1
            if(self.x_config=="samples"):
                xmin=self.tdata_c[0]+ self.npoints*0.1
                xmax=self.tdata_c[-1] + self.npoints*0.1          
            else:
                delta= np.timedelta64(int(self.samples*self.sample_period_duration*0.1), "ms")
                xmin=self.tdata_t[0]+ delta
                xmax=self.tdata_t[-1] + delta
            self.ax_L.set_xlim(xmin,xmax)
            self.ax_R.set_xlim(xmin,xmax)
            if self.autoadjust == True :
                self.range_anpassen(self)
            else:
                #self.ax_L.set_ylim(10 ** (self.skalierung_ymin.val/100), 10 ** (self.skalierung_ymax.val/100))
                pass
            self.ax_L.figure.canvas.draw()
        if len(self.tdata_c)<self.samples and len(self.tdata_c)%int(self.samples/10): #for the initial filling
            if self.autoadjust == True :
                self.range_anpassen(self)
                self.ax_L.figure.canvas.draw()
        if(self.x_config=="samples"):    
            x_arr = self.tdata_c
        else:
            x_arr = self.tdata_t
        
        #Mittelwertbildung
        self.line_ymittel_L.set_data(x_arr, [np.nanmean(self.ydata_L)])
        self.line_ymittel_R.set_data(x_arr, [numpy_nan_mean(self.ydata_R)])
        self.line_yval_L.set_data(x_arr, self.ydata_L)
        self.line_yval_R.set_data(x_arr, self.ydata_R)
        
        return self.line_yval_L, self.line_yval_R, self.line_ymittel_L, self.line_ymittel_R

# Fixing random state for reproducibility
np.random.seed(19680801)

def main(args = None):
    
    version_string = "Serial Data Viewer by Sebastian Melzer | Version: " + Version().string_firsttag
    print(version_string)
    print("GIT-Tag: ",Version().string_reltag)
    print("current directory:", os.getcwd())
    if args is None:
        args = sys.argv
    port,baudrate =  'COM4', 115200
    print(args[0])
    if len(args) > 1:
        port = args[1]
    if len(args) > 2:
        baudrate = int(args[2])
    serial_port_connection=Serial()
    serial_port_connection.port = port
    serial_port_connection.baudrate = baudrate
    serial_port_connection.timeout = 10
        
    fig, ax = plt.subplots(num=version_string)
    fig.subplots_adjust(bottom=0.15, top=0.78)
    
    scope = Scope(ax, 0.01, serial_port_connection)
    
    ani = animation.FuncAnimation(fig, scope.update, interval=50, blit=True, save_count=500)
    #ani2 = animation.FuncAnimation(fig, scope.range_anpassen, interval=1000, blit=True, save_count=500)
    scope.textupdate_samples
    g1 = ax.grid(visible=True, which='major', color='k', linestyle='-', linewidth=0.5)
    g2 = ax.grid(visible=True, which='minor', color='k', linestyle='-', linewidth=0.2)
    ax.minorticks_on()
    plt.show()
    
    return "Das Programm ist nun zu ende"

if __name__ == '__main__':
    
    sys.exit(main())
