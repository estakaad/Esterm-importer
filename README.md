# Multiterm

Mida see programm teeb?

1. Võtab sisendiks XML vormingus terminibaasi
2. Nopib failist välja mõisted ja nende keele, definitsioonid ja nende keele.
3. Salvestab tulemuse dictionary'de list'ina.
4. Itereerib üle nende dictionary'de ja postitab neist igaühe Ekilexi API abil Ekilexi testbaasi terminikogusse Multitermi baas	("crudRoleDataset": "mlt").

Mis sel programmil viga on?
- Programm ei kontrolli, kas termin on juba baasis või mitte.
- Programm ei arvesta homonüümiaga.
- Definitsioonidest ei lähe impordil midagi kaduma, kuid need sisaldavad üleliigseid tag'e jmt.
