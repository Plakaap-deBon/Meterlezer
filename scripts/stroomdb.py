import sqlite3
import datetime

class StroomDB(object):
	def __init__(self):
		self.db_url = 'stroom.db'
		self.con = None
		self.cur = None
		self.datetime_format = "%d-%m-%Y %H:%M:%S"

	def connect(self):
		"""
		Methode om de verbinding met de database tot stand te brengen. Als de database
		nog niet bestaat wordt hij aangemaakt met de standaard naam 'stroom.db' en een
		enkele tabel met twee kolommen: timestamp en waarde.
		Een script dat een instantie van StroomDB wil gebruiken moet expliciet deze methode
		aanroepen om de verbinding te maken.

		Vangt Exceptions vanuit de sqlite3 module op en geeft ze door met een bericht.
		"""
		try:
			self.con = sqlite3.connect(self.db_url)
			self.cur = self.con.cursor()
			self.cur.execute("CREATE TABLE IF NOT EXISTS waarden (timestamp TEXT, waarde INTEGER)")
			self.con.commit()
		except Exception as e:
			raise Exception("De verbinding met de database kon niet tot stand worden gebracht\n" + str(e))

	def insert_waarde(self, waarde):
		"""
		Voeg een uitgelezen waarde toe aan de database. Maakt een timestamp aan
		met behulp van de module datetime en voert vervolgens een insert uit met
		die timestamp en de waarde.

		Parameter:
		waarde: de uit de meter gelezen waarde die ingevoerd moet worden
		"""
		sql = "INSERT INTO waarden VALUES (?, ?)"
		timestamp = datetime.datetime.now().strftime(self.datetime_format)
		self.cur.execute(sql, (timestamp, waarde))
		self.con.commit()

	def haal_regels_op(self, limiet):
		"""
		Methode om regels op te halen uit de database. Regels bevatten een datum/tijd
		en de bijbehorende waarde. Ze worden aangeleverd als een lijst van tupels van
		de vorm (string, int).

		Parameter:
		limiet: deze parameter dient om het aantal opgehaalde regels te beperken. 
		Als limiet > 0 dan worden maximaal de recentste [limiet] aantal regels
		opgehaald. Als limiet <= 0 dan worden alle regels opgehaald. Dit kan gebruikt
		worden om te bepalen hoever er terug in de tijd gekeken wordt naar verbruik.

		Returns:
		Een lijst met tupels van de vorm (string, int). Als er geen waarden op te
		halen zijn dan wordt de lege lijst teruggegeven.
		"""
		regels = []
		if limiet > 0:
			sql = "SELECT timestamp, waarde FROM waarden "
			clause = "WHERE ROWID > (SELECT MAX(ROWID) FROM waarden) - (?)"
			regels = [row for row in self.cur.execute(sql + clause, (limiet,))]
		else:
			sql = "SELECT timestamp, waarde FROM waarden"
			regels = [row for row in self.cur.execute(sql)]
		return regels

	def close(self):
		"""
		Hulpmethode voor het sluiten van de verbinding. Helpt voorkomen dat
		Connection.close aangeroepen wordt op een Connection die reeds gesloten 
		en/of None is (hetgeen een fout opwerpt)
		"""
		if self.con is not None:
			self.con.close()