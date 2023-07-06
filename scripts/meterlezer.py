import PySimpleGUI as sg
import datetime
from uitlezer import Uitlezer, MatchNotFoundException, ConversionException, SerialException
from stroomplotter import Stroomplotter
from stroomdb import StroomDB
import sys
import traceback

event_log = 'log.txt'
init_file = 'config.txt'
datetime_format = "%d-%m-%Y %H:%M:%S"

settings = {}
with open(init_file) as h: # laden van instellingen uit bestand
	for l in h:
		if not l.startswith('#'):
			t1, t2 = l.strip().split(':')
			settings[t1] = t2

def write_to_log(boodschap, traceback):
	"""
	Hulpfunctie voor schrijven naar log
	Parameter traceback is een lijst, traceback[-1] pakt daar het laatste element uit.
	"""
	with open(event_log, 'a') as h:
		timestamp = datetime.datetime.now().strftime(datetime_format)
		trace = str(traceback[-1]) + "\n" if traceback is not None else ""
		h.write("{}  {}\n{}".format(timestamp, boodschap, trace))


# Instanties van de hulpklassen voor uitlezen, plotten en interactie met database.
# Uitlezer krijgt verwijzingen naar juiste seriële poort en het logbestand mee.
lezer = Uitlezer(settings['serial_port'], event_log)
plotter = Stroomplotter(settings)
db = StroomDB()
try:
	db.connect()
except Exception as e:
	write_to_log(str(e), traceback.extract_stack())
	sys.exit() # geen werkende database? Dan moeten we stoppen

#
# **** GUI SETUP ****
#

# waarden voor GUI afmeting en uiterlijk
sg.theme(settings['gui_theme'])
screen_size = (settings['screen_width'], settings['screen_height']) # native raspberry pi touch screen resolutie
number_font_size = int(settings['number_font_size'])
number_font = (settings['number_font'], number_font_size)
number_height = number_font_size

# maak GUI hoofdvenster layout
main_layout = [
		[sg.Text('', key='teller', font=number_font)],
		[sg.Button('GRAFIEK', key='Plot', font=('Futura', 14))],
		[sg.Button('AFSLUITEN', key='Exit', font=('Futura', 14))]
		]

# maak hoofdvenster
main_window = sg.Window('Meterlezer', main_layout, location=(0,0), 
	size=(screen_size[0], screen_size[1]), keep_on_top=True, 
	element_justification='center', element_padding=(30,30)).Finalize()
main_window.Maximize()


#
# ****** MAIN PROGRAM ******
#
write_to_log("programma gestart", None)

# variabele voor plotvenster moet geinitialiseerd zijn buiten de lus.
plot_window = None

# De gui event loop moet een timeout hebben om blokkeren te voorkomen. Omdat bij elke
# doorgang van de lus de meter uitgelezen wordt en mogelijk naar database geschreven 
# wordt, moet dit een realistische waarde zijn (in ms). 1000 = 1 sec ~ 1 uitlezing/sec.
event_loop_timeout = int(settings['event_loop_timeout'])

# blok_lengte bepaalt hoeveel waarden er in een lijst worden bijgehouden voordat
# het gemiddelde van die lijst wordt weggeschreven naar de database.
# In combinatie met event_loop_timeout een manier om de instroom aan gegevens
# te beinvloeden. Bij een lengte van 0 wordt elke uitlezing weggeschreven.
blok_lengte = int(settings['blok_lengte'])

# initialiseer blok buiten de lus
blok = []

# hoeveel rijen er uit db opgehaald worden om te plotten
max_plot_waarden = int(settings['max_plot_waarden'])

# hou het aantal exceptions bij openen/sluiten van seriële poort in de gaten
serial_errors = 0
max_serial_errors = int(settings['max_serial_errors'])

if __name__ == '__main__':
	# event loop
	while True:
		# check gui voor events
		window, event, values = sg.read_all_windows(timeout=event_loop_timeout)
		
		if event == 'Exit':  # event: hoofdvenster gesloten
			write_to_log("programma afgesloten door gebruiker", None)
			break

		if event == 'Plot':  # event: op knop 'plot' geklikt
			plot_layout = [
			[sg.Text('Verbruik in Watt, gemiddelde per 10 minuten:', key='label', font=('Futura', 24))],
			[sg.Canvas(size=(420,360), key='-CANVAS-')],
			[sg.Button('SLUIT VENSTER', key='Exit2', pad=((0,0),(10,0)), font=('Futura', 14))]
			]
			plot_window = sg.Window('', plot_layout, location=(0,0), 
				size=(screen_size[0], screen_size[1]), 
				keep_on_top=True, element_justification='center').Finalize()
			plot_window.Maximize()
			regels = db.haal_regels_op(max_plot_waarden)
			fig1, figure_x, figure_y, figure_w, figure_h = plotter.maak_data(regels)
			canvas_elem = plot_window['-CANVAS-'].TKCanvas
			canvas_elem.Size=(int(figure_w),int(figure_h))
			fig_agg = plotter.teken_figuur(canvas_elem, fig1)
		
		if event == 'Exit2':  # event: plotvenster gesloten (op 'sluiten' geklikt)
			plotter.close()
			plot_window.close()

		# Lees de meter uit. 
        # Als lezer er niet in slaagt om de juiste regels te herkennen wordt een 
        # MatchNotFoundException opgegooid. Als er wel een string gevonden is maar de 
        # omzetting naar int mislukt, dan volgt er een ConversionException. In beide 
        # gevallen wordt de waarde van het tupel op (0,0) gezet en een melding in het log gemaakt. 
        # Het programma wordt niet afgebroken, behalve als het aantal fouten met de seriële poort 
        # boven het maximum uit komt of bij een onverwachte fout.
		try:
			power_tupel = lezer.lees_meter_uit()
		except SerialException as e:
			write_to_log(str(e), traceback.extract_stack())
			if serial_errors < max_serial_errors:
				serial_errors += 1
				power_tupel = (0,0)
			else:
				# bij te veel fouten met de seriële poort: stoppen
				write_to_log("Meer fouten met seriële poort dan toegestaan, programma afgebroken", 
					traceback.extract_stack())
				break
		except MatchNotFoundException as e2:
			write_to_log(str(e2), traceback.extract_stack())
			power_tupel = (0,0)
		except ConversionException as e3:
			write_to_log(str(e3), traceback.extract_stack())
			power_tupel = (0,0)
		except IndexError as e4:
			write_to_log(str(e4), traceback.extract_stack())
			power_tupel = (0,0)
		except Exception as e5:
			write_to_log(str(e5), traceback.extract_stack())
			break # onverwachte fout: breek programma af

		# Bepaal op basis van de waarden in het tupel wat er op het scherm getoond wordt
		if power_tupel[0] > 0: # er wordt stroom van het net geleverd
			main_window['teller'].update(value=str(power_tupel[0]), text_color='yellow')
			blok.append(power_tupel[0])
		elif power_tupel[1] < 0: # er wordt stroom teruggeleverd
			main_window['teller'].update(value=str(power_tupel[1]), text_color='green')
			blok.append(power_tupel[1])
		else: # de meter staat precies op nul!! (of er was een fout: check log)
			main_window['teller'].update('0', text_color='magenta')
			blok.append(0)

		if len(blok) == blok_lengte: # blok lengte bereikt, schrijf blok weg naar db
			db.insert_waarde(int(sum(blok) / len(blok))) # gemiddelde
			# db.insert_waarde(sorted(blok)[int(len(blok) / 2)]) # mediaan
			blok = []

	# we zijn uit de event loop
	db.close()
	main_window.close()
	sys.exit()