# Meterlezer

Meterlezer is een eenvoudig programma in Python, bedoeld voor het uitlezen van een slimme meter en het tonen van actueel netto stroomverbruik in een GUI.

Het is geschreven voor gebruik op een Raspberry Pi die Linux draait.

De configuratie van het programma kan aangepast worden door de config.txt file te wijzigen.

De GUI toont altijd het huidige netto verbruik. Met een button kan geschakeld worden naar een grafiek die historisch verbruik toont.

Meterlezer maakt gebruik van PySimpleGUI, NumPy, MatPlotLib en SQLite3; die libraries moeten geinstalleerd zijn.

Meterlezer bestaat uit de volgende scripts:
- meterlezer.py: main program
- uitlezer.py: class en exceptions voor uitlezen van de (seriële) P1-poort
- stroomdb.py: class voor gegevensuitwisseling met lokale SQlite3 database
- stroomplotter.py: class voor maken en tonen van figuur in de GUI
