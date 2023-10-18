# Estermi ja lennunduse terminikogude import Ekilexi
## 1. Allikate import
### 1.1. Allikate parsimine
#### 1.1.1. Ekspert-tüüpi allikate parsimine
1.1.1.1. Terminoloogidelt on saadud Exceli tabel ekspertide infoga. Sellest võetakse kokkulepitu ja tehakse edasiseks töötlemiseks JSON fail.  
1.1.1.2. esterm.xml failis on allikaviited, mis viitavad ekspertidele. Fail parsitakse, filtreeritakse sellised viited välja ja koostatakse CSV fail, mis sisaldab allika tüüpi (EKSPERT, PÄRING jne) ja nime. Iga rea kohta kontrollitakse, kas selle kohta on andmeid Exceli tabelist tehtud failis. Kui jah, siis need andmed liidetakse. Kokku tuleb JSON fail, mis sisaldab massiivi Ekilexi API jaoks sobivas formaadis dictionarydest. 
#### 1.2. Tavaliste allikate parsimine
1.2.1. esterm.xml sisaldab allikakirjeid. Need on mõistekirjed, mille languageGrp elemendis on language elemendi atribuudi type väärtus "Allikas". 

    <language type="Allikas" lang="ET"/>

Sellised elemendid parsitakse ja neist koostatakse JSON fail, mis sisaldab massiivi Ekilexi API jaoks sobivas formaadis dictionarydest. 
### 1.2. Allikate importimine Ekilexi
#### 1.2.1. Tavaliste allikate importimine Ekilexi
1.2.1.1. Ekilexi API endpointi /api/source/create kasutades imporditakse sammus 1.2.1 loodud failis olevad allikad Ekilexi. Kui Ekilexis on juba olemas allikas, millel on täpselt samad nimed, kui imporditaval allikal, uut allikat ei looda. Pärast allikate importimist luuakse fail, mis sisaldab kõiki allikaid, mida püüti importida, ja nende ID-sid. (Samuti luuakse fail, mis sisaldab kõigi uute allikate ID-sid, et need pärast vajadusel kustutada.)
#### 1.2.2. Ekspert-tüüpi allikate importimine Ekilexi - TODO
1.2.2.1. Kuna on teada, et ekspert-tüüpi allikaid pole Ekilexi laaditud, siis nende puhul laaditakse Ekilexi API endpointi /api/source/create kasutades kõik allikad, mis leiduvad sammus 1.1.1.2 loodud failis. ID-d lisatakse allikatele ja luuakse neist uus JSON fail.
1.2.2.2. Tavaliste allikate ja ekspert-tüüpi allikate failid liidetakse üheks failiks.
### 1.3. Allikate ID-de mäppimine nende nimedega
1.3.1. Kuna järgmistes sammudes tuleb mõistekirjes leiduvatele allikaviidetele leida sobiv vaste allikate ID-de seast, luuakse siin sammus dictionary, mis sisaldab allikate ID-de mäppinguid nende nimedega. Failist ID-de otsimine võtab väga kaua aega, dictionaryst leiab ID kiiremini.
## 2. Mõisted
### 2.1. esterm.xml faili parsimine
2.1.1. Parsitakse mõistekirjed (conceptGrp), mis ei ole allikad ega valdkonnad. Allikaviidetele lisatakse allika ID-d. Tulemusest luuakse kaks faili: concepts.json ja aviation_concepts.json, sest esterm.xml sisaldab Estermi mõisteid ja lennunduse terminikogu mõisteid.
### 2.2. Keelendite kontroll
2.2.3. Ekilexi API endpointi /api/word/ids/{word}/{dataset}/{lang} kasutades kontrollitakse, kas keelendid (terminid) on juba Ühendsõnastikus olemas. Kui Ühendsõnastikus on üks vaste, kasutatakse selle ID-d. Kui keelendeid pole või on rohkem kui üks, luuakse uus. Lõpuks luuakse fail concepts_with_word_ids.json, mis sisaldab mõistekirjeid koos keelendite ID-dega. Sama protsess tuleb läbi teha nii Estermi kui ka lennunduse mõistetega. Peale selle luuakse failid keelenditega, mida ÜSis polnud või mida oli üle ühe.
### 2.3. Mõistete import
#### 2.3.1. Lennunduse terminikogu mõistete import  
2.3.1.1 Kasutades Ekilexi API endpointi api/term-meaning/save, imporditakse lennunduse terminikogu mõistekirjed.  
#### 2.3.2. Estermi terminikogu mõistete import  
2.3.2.1 Kasutades Ekilexi API endpointi api/term-meaning/save, imporditakse Estermi terminikogu mõistekirjed.
