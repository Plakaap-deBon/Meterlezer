import datetime
import serial
import re
		

class MatchNotFoundException(Exception):
	"""
	Een custom Exception die opgegooid wordt als de regels die we zoeken niet gevonden
	worden in een opgehaald P1-telegram. Hiermee kan deze gebeurtenis gecommuniceerd worden.
	"""
	pass

class ConversionException(Exception):
	"""
	Een custom Exception die wordt opgegooid als het converteren van de stringwaarde
	naar een getal mislukt.
	"""
	pass

class SerialException(Exception):
	"""
	Een custom Exception die wordt opgegooid bij een fout in de communicatie
	met de seriële poort.
	"""
	pass

class Uitlezer(object):
	"""
	Een klasse met code voor het uitlezen van de P1-poort van een slimme meter (DSMR 5.0.2)

	Heeft een methode lees_meter_uit om actueel verbruik in Watt (op moment van aanroep)
	uit een DSMR informatietelegram te halen
	"""

	def __init__(self, port_string, log_file):
		""" 
		__init__ configureert een attribuut van type Serial met de gegevens voor communicatie
		met de P1-poort. Zie 'P1 Companion Standard' versie 5.0.2 van Netbeheer Nederland 
		voor documentatie. Voor andere meters en/of andere versies kan het zijn dat onderstaande 
		aangepast moet worden.

		Parameters:
		port_string: het pad naar de seriele poort waar de P1 kabel is aangesloten. Dit is
		platformafhankelijk en kan ook een USB poort zijn bij gebruik van een P1->USB kabel.

		log_file: een verwijzing naar een logbestand waar Uitlezer naartoe kan schrijven
		in het geval van een fout. Als dit logbestand niet bestaat dan wordt het aangemaakt.

		TODO: mathode __init__ uitbreiden zodat gebruiker object zelf kan configureren 
		"""
		self.event_log = log_file
		self.ser = serial.Serial()
		self.ser.baudrate = 115200
		self.ser.bytesize=serial.EIGHTBITS
		self.ser.parity=serial.PARITY_NONE
		self.ser.stopbits=serial.STOPBITS_ONE
		self.ser.xonxoff=0
		self.ser.rtscts=0
		self.ser.timeout=20
		self.ser.port = port_string

		# Patronen om de juiste telegramregels te herkennen en om het stukje 
		# met de waarde in kWh uit een regel te halen.
		self.pwr_in_patroon = b'1-0:1.7.0'
		self.pwr_out_patroon = b'1-0:2.7.0'
		self.kwh_patroon = re.compile('(.*)\\*')
		self.controle_patroon = re.compile('^\\d{2}\\.\\d{3}$')

	def lees_meter_uit(self):
		"""
		Functie voor het uitlezen van slimme meter via de P1-poort.
		
		Werpt Exceptions op bij de volgende problemen: communicatie seriële poort,
		het vinden van waarden in DSMR-telegram, conversie strings naar getallen.

		Returns:
		Een tupel met twee integers, resp. geleverd en teruggeleverd vermogen (in Watt).
		Als er geleverd wordt, wordt er niet teruggeleverd en v.v. Er is altijd dus
		minstens één van beide waarden nul.
		"""
		resultaat = (None, None)
		teller = 0 # telt hoeveel regels we doorlopen hebben
		limiet = 40 # om te zorgen dat we uit de while-lus kunnen
		# pwr_in_raw = None
		# pwr_out_raw = None
		pwr_in_str = None
		pwr_out_str = None

		if not self.ser.isOpen():
			try:
				self.ser.open() # open verbinding met de P1-poort
			except Exception as e:
				raise SerialException("Fout bij openen van seriële poort " + str(e))
		
		# loop regel voor regel door telegram zolang de waarden nog niet allebei gevonden zijn
		while pwr_in_str is None or pwr_out_str is None:
			line = self.ser.readline()
			teller += 1
			if teller >= limiet: # limiet bereikt zonder dat er een match is gevonden
				if self.ser.isOpen():
					self.ser.close()
				raise MatchNotFoundException("Geen match gevonden in telegram, limiet bereikt")
			if re.match(self.pwr_in_patroon, line): # de regel voor geleverde stroom
				kwh_match = self.kwh_patroon.search(str(line).split('(')[1])
				if kwh_match:
					pwr_in_str = kwh_match.group().strip('*')
				else:
					raise MatchNotFoundException("Geen match gevonden in regel: " + str(line))
			elif re.match(self.pwr_out_patroon, line): # de regel voor teruggeleverde stroom
				kwh_match = self.kwh_patroon.search(str(line).split('(')[1])
				if kwh_match:
					pwr_out_str = kwh_match.group().strip('*')
				else:
					raise MatchNotFoundException("Geen match gevonden in regel: " + str(line))
			else:
				pass

		# converteer de stringwaarden naar integers (Watt).
		try:
			pwr_in_final = int(self.controleer_waarde(pwr_in_str) * 1000)
			pwr_out_final = int(self.controleer_waarde(pwr_out_str) * -1000)
			resultaat = (pwr_in_final, pwr_out_final)
		except ConversionException as ce:
			self.write_to_log(str(ce))
			resultaat = (0,0)

		try:
			self.ser.close() # sluit verbinding met P1-poort
		except:
			raise SerialException("Fout bij het sluiten van seriële poort")
		return resultaat

	def controleer_waarde(self, s):
		"""
		Hulpmethode voor het controleren van strings nadat ze uitgelezen en op maat
		gesneden zijn, vóór conversie naar integers. Als deze controle mislukt dan
		is er iets mis met de vorm van de uitgelezen string. Bij testen lijkt dit
		sporadisch te gebeuren (TODO: wat is de oorzaak?)

		Parameter: de te controleren string s

		Returns: s geconverteerd naar float, als s de juiste vorm heeft
		"""
		error_string = "Probleem bij conversie naar int, waarde op nul gezet: [{}]\n{}"
		resultaat = 0
		if s is None:
			raise ConversionException(error_string.format(s, "string was None"))
		if re.match(self.controle_patroon, s):
			resultaat = float(s)
		else:
			s = s.strip() # toegevoegd vanwege conversion errors in log waar whitespace probleem lijkt
			if re.match(self.controle_patroon, s[:6]):
				try:
					resultaat = float(s[:6])
				except Exception as e:
					raise ConversionException(error_string.format(s, e))
			else:
				raise ConversionException(error_string.format(s, ""))
		return resultaat

	def write_to_log(self, boodschap):
		"""Hulpmethode voor het wegschrijven van een boodschap naar het logbestand"""
		timestamp = datetime.datetime.now().strftime("%d-%m-%Y %H:%M:%S")
		with open(self.event_log, 'a') as h:
			h.write("*Uitlezer\n{}  {}\n".format(timestamp, boodschap))
