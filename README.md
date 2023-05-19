# Meterlezer

Meterlezer is een eenvoudig programma in Python, bedoeld voor het uitlezen van een slimme meter en het tonen van actueel netto stroomverbruik in een GUI.

Het is geschreven voor gebruik op een Raspberry Pi die Linux draait. Sommige configuratiegegevens zijn nu nog hard coded, een doel voor een toekomstige update is om die configuratie flexibel te maken zodat de gebruiker het programma makkelijker kan tweaken en kan gebruiken op andere platforms.

De GUI toont altijd het huidige netto verbruik. Met een button kan geschakeld worden naar een grafiek die historisch verbruik toont.

Meterlezer maakt gebruik van PySimpleGUI, NumPy en MatPlotLib; die libraries moeten geinstalleerd zijn.
