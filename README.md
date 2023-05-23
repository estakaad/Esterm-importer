# Skriptid terminikogude importimiseks

Terminikogud, mida on vaja Ekilexi laadida, erinevad oma ülesehituselt ja formaadilt. Siin on skriptid nende erikujuliste failide parsimiseks ning transformeerimiseks ühtsele JSON formaadile. mida aktsepteerib Ekilexi Term API.

- parse_esterm.py - XML vormingus Estermi terminikogu parsimiseks. Tagastab kolm faili JSON objektidega (Esterm, lennunduse terminid, allikad). Neid JSON objekte API praegu (veel) ei aktsepteeri, need on loodud, silmas pidades arendusse minevat API täiendust.
- parse_excel.py - Exceli failis leiduva terminikogu parsimiseks. Tagastab faili JSON objektidega, mida praegune API aktsepteerib.
- api_requests.py - Ekilexi Term API päringute tegemiseks.