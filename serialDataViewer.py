#Ursprung bildet "oszilloskop" beispiel von animation.FuncAnimation
#mit zusätzlichen elementen
#
#
#"pip install pyserial" nicht normal serial!!!
#
#
#Programm muss gestartet werden mit:
#c:\Users\User\Desktop>serialDataViewer.py COM4 115200

#Tested with: 
#Python            3.8.1
#
#scipy             1.4.1
#pysinewave        0.0.6
#pyserial          3.5
#matplotlib        3.4.2
#numpy             1.20.3

import numpy as np
from   scipy.stats import norm
from   matplotlib.lines import Line2D
from   matplotlib.widgets import Slider, Button, RadioButtons, TextBox, CheckButtons
import matplotlib.pyplot as plt
import matplotlib.mlab   as mlab
import matplotlib.animation as animation
from   serial import Serial
import sys
import serial.tools.list_ports
from   pysinewave import SineWave #fuer tonausgabe


def substring_after(s, delim):
    return s.partition(delim)[2]

def substring_before(s, delim):
    return s.partition(delim)[0]

        
        
class Scope(object):
    def __init__(self, ax, maxt, dt, serialPort):
        self.sinewave = SineWave(pitch = 5, pitch_per_second = 1000)
        self.serialPort = serialPort
        self.sendestatus = True #fuer toggeln der datenuebermittlung
        self.ylinlog = False #status y-achsen skalierung in lin oder logarythmisch 
        self.tonausgabe = False #status der Tonausgabe
        self.string_to_strip_after = ''
        self.string_to_strip_bevore = 'placeholder'
        self.ax = ax
        self.dt = dt
        self.samples = 150 # wird durch submit uebernommen
        self.npoints = self.samples #sind die waren samples!
        self.gleitt = self.npoints
        self.maxt = maxt
        self.autoadjust = True
        self.datenausgabe = False
        self.sendetext = "t 165"
        self.dist_bins = 50 #Aufloesung der Verteilungsfunktion
        self.fft_time = 10 #in ms
        self.tdata = [0]
        self.ydata = [0]
        self.y_mittel = [0]
        self.line_ymittel = Line2D(self.tdata, self.y_mittel, color="black")
        self.line_yval = Line2D(self.tdata, self.ydata)
        self.ax.add_line(self.line_ymittel)
        self.ax.add_line(self.line_yval)
        self.ax.set_ylim(-.1, self.samples)
        self.ax.set_xlim(0, self.npoints)
        #erase outputdocuments
        #open("data-out.txt","w").close()
        open("dist-out.txt","w").close()
        open("fft-out.txt","w").close()
        
        
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
        self.submit1_button =            Button(plt.axes([0.655, 0.005, 0.1, 0.04]), 'Submit', color=axcolor, hovercolor='0.975')
        
        #Eingabezeile 
        self.sent_box =                 TextBox(plt.axes([0.2, 0.95,   0.4, 0.04]), 'Befehl', initial=self.sendetext)
        self.fft_time_box =             TextBox(plt.axes([0.2, 0.91,   0.4, 0.04]), 'Sampletime ms', initial=str(self.fft_time))
        self.dist_bins_box =            TextBox(plt.axes([0.2, 0.87,   0.4, 0.04]), 'N Bins', initial=str(self.dist_bins))
        self.string_strip_bevore_box =  TextBox(plt.axes([0.2, 0.83,   0.4, 0.04]), 'String after val', initial=self.string_to_strip_bevore)
        self.string_strip_after_box =   TextBox(plt.axes([0.2, 0.79,   0.4, 0.04]), 'String bevore val', initial=self.string_to_strip_after)
        self.samples_box =              TextBox(plt.axes([0.25, 0.005, 0.4, 0.04]), 'Samples', initial=str(self.samples))
        
        #checkbox
        self.check = CheckButtons(plt.axes([0.72, 0.85, 0.11, 0.14]), ('Y-Auto', 'Data-out', 'Y-Log', 'Ton'), (True, False, False, False))
        
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
    
    def textupdate_fft_time(self, text):
        try:
            self.fft_time = int(text)
            #print("FFT Zeitbasis: ",self.fft_time," ms")
        except Exception as e:
            print(e)
        
    def textupdate_dist_bins(self, text):
        try:
            self.dist_bins = int(text)
            #print("Intervalle in Verteilungsfunktion: ",self.dist_bins,)
        except Exception as e:
            print(e)
    
    def textupdate_samples(self, text):
        try:
            self.samples = int(text)
            #print("Anzahl der Samples: ",self.samples)
        except Exception as e:
            print(e)
    
    def funktion(self, label) : # Checkbox events
        if label == 'Y-Auto':
            self.autoadjust = not self.autoadjust
        elif label == 'Data-out':
            self.datenausgabe = not self.datenausgabe
        elif label == 'Y-Log':
            self.ylinlog = not self.ylinlog
            if self.ylinlog:
                self.ax.set_yscale('symlog')
            else:
                self.ax.set_yscale('linear')
            self.single_autorange
        elif label == 'Ton':
            self.tonausgabe = not self.tonausgabe
            if self.tonausgabe:
                self.sinewave.play()
            else:
                self.sinewave.stop()
    def single_autorange(self, u):
        self.ax.set_ylim(min(self.ydata)-(max(self.ydata)-min(self.ydata))/20,max(self.ydata)+(max(self.ydata)-min(self.ydata))/20)
    
    def submit_samples(self, u):
        self.npoints = self.samples # übernahme der werte von der eingabebox
        self.reset()

    def range_manuell_anpassen(self, u):
        self.ax.set_ylim(10 ** (self.skalierung_ymin.val/100), 10 ** (self.skalierung_ymax.val/100))
        self.ax.figure.canvas.draw()

    def range_anpassen(self, u):
        if self.autoadjust == True :
            self.single_autorange(self)
        else:
            #self.ax.set_ylim(10 ** (self.skalierung_ymin.val/100), 10 ** (self.skalierung_ymax.val/100))
            pass
        self.ax.figure.canvas.draw()
    
    def fft_erstellen(self, g=3):
        #print(self.sent_box_fft_time.val)
        dt = int(self.fft_time)/1000 #samplingtime in sekunden
        fa = 1.0/dt # scan frequency
        Y=np.fft.fft(np.hanning(len(self.ydata))*self.ydata)
        N = len(Y)
        X = np.linspace(0, fa/2, N, endpoint=True)
        #x = np.linspace(0, 2*np.pi, 400)
        #y = np.sin(x**2)
        fig2, ax2 = plt.subplots()
        #fig2.subplots_adjust(bottom=0.15)
        ax2.set_title(r'$\mathrm{FFT:}\ Freq=%.2f Hz,\ samples=%.0f,\ T=%.3f$ ms' %(fa, len(self.ydata), dt*1000))#"FFT-Plot Samplingfreq: " + str(fa) + "Hz, Periodendauer: " + str(dt*1000) + "ms") 
        ax2.plot(X,np.abs(Y))
        ax2.set_xscale('log')
        ax2.set_yscale('log')
        #ax2.set_ylim(0,max(Y[1:]))
        #plt.xlim(0.001, 10)
        plt.grid()
        plt.show()
    
    def dist_erstellen(self, g=3) :
        fig_verteilung, ax_verteilung = plt.subplots()
        sigma = np.std(self.ydata)
        #varianz = np.var(self.ydata)
        mu = np.mean(self.ydata)
        n, bins, patches = plt.hist(self.ydata, bins=self.dist_bins, density=True) #density -> normed distribution
        #y = mlab.normpdf( bins, mu, sigma) #old, not working
        y=norm.pdf( bins, mu, sigma) 
        l = plt.plot(bins, y, 'r--', linewidth=2)
        #f=open("out.txt","a")
        print ("bins=", bins, file=open("dist-out.txt","a"))
        print ("werte=",n, file=open("dist-out.txt","a"))
        print ("patches=",patches, file=open("dist-out.txt","a"))
        #f.close()
        
        #ax_verteilung.set_title("Verteilung mit sigm: " + str(standartabweichung) + " Varianz: " + str(varianz) + " und Mittelwert: " + str(mittelwert)) 
        ax_verteilung.set_title(r'$\mathrm{Histogram}\ \mu=%.1f,\ \sigma=%.3f$, Samples=%.0f Bins=%.0f' %(mu, sigma, len(self.ydata), self.dist_bins))
        
        #plt.axis([0, 10000, 0, 10])
        plt.grid(True)
        plt.show()
        
    def reset(self, g=0):
        mittelwert=np.mean(self.ydata)
        del self.tdata [:]
        del self.ydata [:]
        #2 Daten anhaengen, damit auto x-einstellung funktioniert
        self.tdata.append(0)
        self.ydata.append(mittelwert)
        self.npoints = self.samples
        self.ax.set_xlim(0, self.npoints)
        self.gleitt=self.npoints
        self.ax.figure.canvas.draw()
    
    def update(self, i):
        i = 0;
        while (self.serialPort.inWaiting() != 0) & (i<300):
            i +=1
            inputline = self.serialPort.readline()# read a '\n' terminated line otherwise timeout
            try:
                inputline = inputline.decode('ascii').strip("\r\n")
            except Exception as e:
                print(e)

            #String zuschneiden
            try:
                if self.string_strip_after_box.text!="" and self.string_strip_bevore_box.text != "":
                    inputline=substring_after(inputline, self.string_strip_after_box.text)
                    inputline=substring_before(inputline, self.string_strip_bevore_box.text)#self.string_strip_bevore_box #self.string_to_strip_bevore
                #print(inputline)
            except Exception as e:
                print(e)
            if inputline != "": #weil bestätigung leerer string ist
                try:
                    wert=float(inputline) # war int, hoffe das macht keine probleme
                    if len(self.ydata)==1: #um initialen wert zu entfernen
                        self.ydata[0]=wert
                    self.ydata.append(wert)
                    self.tdata.append(self.tdata[-1] + 1)
                    if self.datenausgabe == True :
                        print(self.ydata[-1])
                        print(self.ydata[-1], file=open("data-out.txt","a"))
                    if self.tonausgabe== True :
                        self.sinewave.set_frequency(wert*1.5+220)
                except Exception as e:
                    print(e)
            else:
                #print("leerer string, befehl uebertragen!")
                pass
            self.ydata     = self.ydata   [-1 * self.npoints:]
            self.tdata     = self.tdata   [-1 * self.npoints:]
        if self.tdata[-1] > self.gleitt:  # reset the arrays
            self.gleitt = self.tdata[-1] + self.npoints*0.1
            self.ax.set_xlim(self.tdata[0]+ self.npoints*0.1, self.tdata[-1] + self.npoints*0.1)
            if self.autoadjust == True :
                self.range_anpassen(self)
            else:
                #self.ax.set_ylim(10 ** (self.skalierung_ymin.val/100), 10 ** (self.skalierung_ymax.val/100))
                pass
            self.ax.figure.canvas.draw()
        if len(self.tdata)==10: #damit wertebreich zu beginn sinvoll angepasst wird
            if self.autoadjust == True :
                self.range_anpassen(self)
                self.ax.figure.canvas.draw()
        
        #Mittelwertbildung
        self.line_ymittel.set_data(self.tdata, [np.mean(self.ydata)])
        self.line_yval.set_data(self.tdata, self.ydata)
        
        return self.line_yval, self.line_ymittel,



# Fixing random state for reproducibility
np.random.seed(19680801)

def main(args = None):

    if args is None:
        args = sys.argv
    port,baudrate =  'COM6', 115200
    print(args[0])
    if len(args) > 1:
        port = args[1]
    if len(args) > 2:
        baudrate = int(args[2])
    serial_port_connection=None
    while(serial_port_connection==None): # Falls keine Verbindung aufgebaut werden kann, erneut nach Port fragen
        try:
            serial_port_connection=Serial(port, baudrate, timeout=10) # 10 sek timeout
        except Exception as e:
            print(e)
            print("Available Ports:")
            comportliste=serial.tools.list_ports.comports()
            for entry in comportliste:
                print(entry)
            port=input("Enter Comport: eg \"COM4\"")
            if (port==""):
                port="COM4"
            try:
                baudrate=int(input("Enter Baudrate: eg \"115200\" "))
            except Exception as e:
                print(e)
                print("using 115200")
                baudrate=115200
    fig, ax = plt.subplots()
    fig.subplots_adjust(bottom=0.15, top=0.78)
    
    scope = Scope(ax, 10, 0.01, serial_port_connection) 
    #scope = Scope(ax2, 10, 0.01, Serial(port, baudrate))
    
    #Button events
    scope.fft_button.on_clicked(scope.fft_erstellen)
    scope.dist_button.on_clicked(scope.dist_erstellen)
    scope.mess_toggle_button.on_clicked(scope.mess_toggle_event)
    scope.sent_button.on_clicked(scope.sent)
    scope.reset_button.on_clicked(scope.reset)
    scope.single_autorange_button.on_clicked(scope.single_autorange)
    scope.submit1_button.on_clicked(scope.submit_samples)
    
    #Checkbox Events
    scope.check.on_clicked(scope.funktion)
    
    
    #Text-Events
    scope.sent_box.on_submit(scope.textupdate_sent)
    scope.fft_time_box.on_submit(scope.textupdate_fft_time)
    scope.dist_bins_box.on_submit(scope.textupdate_dist_bins)
    scope.samples_box.on_submit(scope.textupdate_samples)
    
    #Slider-Events
    scope.skalierung_ymin.on_changed(scope.range_manuell_anpassen)
    scope.skalierung_ymax.on_changed(scope.range_manuell_anpassen)
    
    ani = animation.FuncAnimation(fig, scope.update, interval=20, blit=True, save_count=500)
    scope.textupdate_samples
    g1 = ax.grid(visible=True, which='major', color='k', linestyle='-', linewidth=0.5)
    g2 = ax.grid(visible=True, which='minor', color='k', linestyle='-', linewidth=0.2)
    ax.minorticks_on()
    plt.show()
    
    return "das Programm ist nun zu ende"

if __name__ == '__main__':
    
    sys.exit(main())
