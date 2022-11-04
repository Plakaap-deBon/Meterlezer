import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib import dates as mdates
import numpy as np
from datetime import datetime

class Stroomplotter(object):
	"""
	Een klasse met twee methoden voor het maken en tonen van een figuur in de Meterlezer GUI

	"""

	def __init__(self, settings):
		self.datetime_format = "%d-%m-%Y %H:%M:%S"
		self.settings = settings
	
	def maak_data(self, regels):
		"""Methode voor het plotten van de figuur met verbruiksdata.

		Parameter: 
		regels: lijst van tupels (String, int) zoals gegenereerd door StroomDB.haal_regels_op.

		Returns: een tupel met de figuur en diens afmetingen
		"""

		xvals, yvals = [], []
		for t in regels: # vul xvals en yvals met de waarden uit parameter regels
			timestamp = datetime.strptime(t[0], self.datetime_format)
			xvals.append(mdates.date2num(timestamp))
			yvals.append(t[1])

		# zet xvals en yvals om naar numpy arrays
		xvals = np.array(xvals)
		yvals = np.array(yvals)

		fig, ax = plt.subplots()
		
		# configureer het uiterlijk van de figuur
		fig.set_facecolor(self.settings['fig_facecolor'])
		fig.set_figheight(3.60)
		ax.set_facecolor(self.settings['ax_facecolor'])
		ax.tick_params(axis='y', colors=self.settings['ax_ytick_color'])
		ax.grid(color='k', alpha=0.5)
		plt.axhline(y=0, color=self.settings['ax_hline_color'])
		for spine in ax.spines.values():
			spine.set_color(self.settings['ax_spine_color'])
		
		# configureer de weergave van datum/tijd op de x-as
		locator = mdates.AutoDateLocator(minticks=3, maxticks=8)
		formatter = mdates.ConciseDateFormatter(locator)
		ax.xaxis.set_major_locator(locator)
		ax.xaxis.set_major_formatter(formatter)

		# teken de lijn
		plt.plot(xvals, yvals, color=self.settings['plot_line_color'], linewidth=0.5)

		# vul de gebieden tussen de lijn en de x-as
		ax.fill_between(xvals, yvals, y2=0, where=(yvals > 0), 
			facecolor=self.settings['ax_fill_pos_color'], interpolate=True)
		ax.fill_between(xvals, yvals, y2=0, where=(yvals < 0), 
			facecolor=self.settings['ax_fill_neg_color'], interpolate=True)

		figure_x, figure_y, figure_w, figure_h = fig.bbox.bounds
		return(fig, figure_x, figure_y, figure_w, figure_h)

	def teken_figuur(self, canvas, figure):
		"""
		Methode om een figuur op een Canvas element te tekenen

		Parameters:
		canvas: een tkinter Canvas
		figure: de te tekenen figuur (zoals gegenereerd door methode maak_data)

		Returns: een FigureCanvasTkAgg object. De retourwaarde hoeft niet gebruikt
		te worden. Als de parameter canvas onderdeel is van een gui, dan
		wordt door het uitvoeren van deze methode de figuur op dat canvas getekend. 
		De methode roept hiertoe de relevante methoden van FigureCanvasTkAgg aan.
		"""
		figure_canvas_agg = FigureCanvasTkAgg(figure, canvas)
		figure_canvas_agg.draw()
		figure_canvas_agg.get_tk_widget().pack(side='top', fill='both', expand=1)
		return figure_canvas_agg

	def close(self):
		plt.close('all')