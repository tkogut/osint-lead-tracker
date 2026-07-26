---
tags: ["#NotebookLM", "#ExpertKnowledge"]
date_synced: "2026-07-26"
---

# Raport Techniczno-Proceduralny: Ekosystem CST2021 oraz LSI 2021 (Perspektywa Finansowa 2021–2027)
*Dokument przygotowany na potrzeby bazy wiedzy (Knowledge Base) w systemie Antigravity.*

---

## 1. Architektura i Moduły Centralnego Systemu Teleinformatycznego (CST2021)

Centralny System Teleinformatyczny 2021 (**CST2021**) stanowi bezpośredniego następcę systemu SL2014 [15, 26]. Jest to kluczowe narzędzie teleinformatyczne wspierające procesy monitorowania, ewaluacji, zarządzania finansowego, weryfikacji oraz audytów programów polityki spójności w Polsce w perspektywie finansowej 2021–2027 [14, 15, 16]. 

### Podział Użytkowników i Dostępów [16, 17]
Ekosystem CST2021 dzieli użytkowników na dwie główne grupy o zróżnicowanych uprawnieniach:
1. **Użytkownicy zewnętrzni**: Beneficjenci i wnioskodawcy realizujący projekty, posiadający dostęp do wybranych, dedykowanych aplikacji (np. WOD2021, SL2021 Projekty, SM EFS, BK2021) [16].
2. **Użytkownicy instytucjonalni**: Pracownicy instytucji szczebla krajowego i regionalnego (np. Instytucji Pośredniczących), posiadający uprawnienia do wszystkich modułów systemu w ramach swojej właściwości merytorycznej [16, 17].

### Kluczowe Moduły i Aplikacje Ekosystemu [18, 19, 20, 21, 22, 23, 24]
* **SZT2021 (System Zarządzania Tożsamością)**: Wspólna dla wszystkich użytkowników bramka logowania (Single Sign-On - SSO), weryfikująca tożsamość za pomocą loginu i hasła [18].
* **Administracja (z modułem eSZOP)**: Moduł zarządzający bezpieczeństwem, danymi osobowymi, słownikami systemowymi oraz Szczegółowym Opisem Priorytetów programu (SZOP) [18].
* **WOD2021 (Wniosek o Dofinansowanie)**: Moduł wspierający proces wyboru projektów, obsługujący tworzenie i ocenę wniosków aplikacyjnych [19]. Dane z tego modułu są automatycznie eksportowane do modułu projektowego [19].
* **SL2021 Projekty**: Aplikacja służąca do bieżącego rozliczania i zarządzania projektami od momentu podpisania umowy o dofinansowanie [20, 151]. Odpowiada m.in. za gromadzenie danych o wnioskach o płatność, harmonogramach finansowych, personelu czy zamówieniach publicznych [20].
* **SL2021 Certyfikacja**: Narzędzie dedykowane procesom certyfikacji wydatków, księgowaniu, obsłudze zaliczek i tworzeniu zestawień dla Komisji Europejskiej [22].
* **BK2021 (Baza Konkurencyjności)**: Portal przeznaczony do publikacji zapytań ofertowych i zbierania ofert w celu realizacji zasady konkurencyjności [21, 201].
* **SM EFS (System Monitorowania EFS)**: Narzędzie służące do ewidencji i monitorowania uczestników projektów finansowanych z Europejskiego Funduszu Społecznego Plus (EFS+) [24, 209].
* **e-Kontrole**: Dedykowana aplikacja do koordynacji, przeprowadzania i dokumentowania kontroli projektów [22].
* **Kontrole Krzyżowe**: Algorytmiczne narzędzie analityczne typu BigData, służące do wykrywania podwójnego dofinansowania tych samych wydatków (faktur) na poziomie krajowym [23, 225, 271].
* **SKANER**: Narzędzie analityczne zapobiegające konfliktom interesów, integrujące dane beneficjentów i osób powiązanych z zewnętrznymi rejestrami publicznymi (np. KRS, CEIDG, CRBR, SL2014) [23, 193, 194].
* **SR2021 (System Raportujący)**: Środowisko analityczne oparte na kostkach danych, służące do generowania niestandardowych raportów i audytów jakościowych [24].

### Adresy Środowisk Ekosystemu CST2021 [153]
* **Bramka SSO / Logowanie główne**: `https://sso.cst2021.gov.pl/` (Szkoleniowe: `https://szkol.cst2021.gov.pl/`)
* **SKANER**: `https://skaner.gov.pl/`
* **Kontrole Krzyżowe**: `https://kk.cst2021.gov.pl/`
* **Baza Konkurencyjności (BK2021)**: `https://bazakonkurencyjnosci.funduszeeuropejskie.gov.pl/` (Szkoleniowe: `https://szkol-bazakonkurencyjnosci.funduszeeuropejskie.gov.pl/`)
* **System Monitorowania EFS**: `https://sm.efs.gov.pl/` (Szkoleniowe: `https://szkol.sm.efs.gov.pl/`)
* **Service Desk (SD2020)**: `https://sd.sl.gov.pl/`

---

## 2. Lokalny System Informatyczny (LSI 2021) – Przykład FE SL

Lokalny System Informatyczny (**LSI 2021**) jest uruchamiany na poziomie regionalnym (np. w województwie śląskim dla programu FE SL 2021-2027) w celu odciążenia beneficjentów i wsparcia procesów, których nie obsługuje system centralny (np. naborów ekspertów, terminarzy płatności, formularzy zgłaszania zmian, sprawozdań z trwałości) [51, 52, 53].

### Zarządzanie i Uprawnienia w LSI 2021 [57, 58]
* **Główny Administrator (CI-PRS)**: Umiejscowiony w Departamencie Cyfryzacji i Informatyki Urzędu Marszałkowskiego (CI) [57, 58, 259, 264]. Odpowiada za całościowe zarządzanie uprawnieniami, wydajność systemu, bezpieczeństwo teleinformatyczne oraz usuwanie zaawansowanych błędów [59, 60, 61]. Kontakt: `lsi2021@slaskie.pl` [57].
* **Administratorzy Instytucji**: Umiejscowieni w departamentach merytorycznych oraz Instytucjach Pośredniczących (ŚCP, WUP) [57, 58]. Odpowiadają za wsparcie użytkowników, modyfikację danych w ramach swoich uprawnień i koordynację audytów spójności [63, 65, 66].

### Środowiska Techniczne LSI 2021 [54]
Dostęp do systemu realizowany jest na kilku dedykowanych poziomach środowiskowych:
1. **Produkcyjne**: `https://lsi2021.slaskie.pl` (Wydział Ekspertów: `https://lsi2021-ekspert.slaskie.pl/`)
2. **Szkoleniowe**: `https://lsi2021-szkol.slaskie.pl`
3. **Testowe**: `https://lsi2021-test.slaskie.pl`
4. **Deweloperskie**: `https://lsi2021-dev.slaskie.pl` (Wydział Ekspertów: `https://lsi2021-ekspert-dev.slaskie.pl/`)

---

## 3. Integracja, Interfejsy API i Wymiana Danych (MWD)

Kluczowym elementem spójności danych w perspektywie 2021–2027 jest zautomatyzowana integracja systemów regionalnych (LSI) z systemem centralnym (CST2021).

### Moduł Wymiany Danych (MWD) i Interfejs API [20, 21, 148, 149]
Integracja techniczna odbywa się za pomocą **Modułu Wymiany Danych (MWD)**, który udostępnia dwukierunkowy interfejs programistyczny **API** pod adresem:
`https://api.cst2021.gov.pl` [20, 21]

* **Zakres Wymiany Danych** [149]:
  * Słowniki aplikacji Administracja (np. dane słownikowe instytucji).
  * Dane dotyczące ogłoszonych naborów wniosków.
  * Dane o projektach (wnioski o dofinansowanie, umowy o dofinansowanie, aneksy).
  * Dane zgromadzone w module SM FST (Fundusz Sprawiedliwej Transformacji).
* **Wymagania i Częstotliwość** [148, 149]:
  * Instytucje mają obowiązek dbać o jakość przesyłu i stosować regułę "drugiej pary oczu" przy weryfikacji [148].
  * Synchronizacja danych za pomocą API musi odbywać się **nie rzadziej niż raz na 2 dni robocze**, o ile w danym okresie wprowadzono do LSI nowe dane przeznaczone do eksportu [149, 150].

### API Bazy Konkurencyjności (BK2021) [11]
Wokół API samej Bazy Konkurencyjności występują istotne uwarunkowania techniczne, które należy uwzględnić przy projektowaniu automatyzacji:
* **Brak Oficjalnego Publicznego API**: Ministerstwo Funduszy i Polityki Regionalnej **nie udostępnia otwartej, udokumentowanej (np. w standardzie OpenAPI/Swagger) usługi REST API** dla zewnętrznych deweloperów do masowego pobierania danych [11].
* **Wewnętrzne REST API (Wykorzystywane do Scrapingu)**: Portal Bazy Konkurencyjności jest aplikacją typu SPA (React) [10]. Komunikuje się on asynchronicznie z wewnętrznymi punktami końcowymi REST API zlokalizowanymi w ścieżce bazowej:
  `https://bazakonkurencyjnosci.funduszeeuropejskie.gov.pl/api/` [11]
  Zewnętrzne platformy monitorujące przetargi pobierają dane, analizując i skrapując te wewnętrzne endpointy (np. pobieranie plików załączników z `/api/files/{id}`) [11, 10].

---

## 4. Procedury Zarządzania Systemem i Jakością Danych

Zarządzanie systemami opiera się na restrykcyjnych procedurach kontrolnych, których celem jest zachowanie spójności baz danych i bezpieczeństwa informacji.

### Audyt Spójności Danych (LSI vs CST) [241, 242, 243]
* **Częstotliwość**: Raz w miesiącu [243].
* **Metodyka**: Administratorzy instytucji generują zestawienia porównawcze w systemach centralnym i lokalnym [243].
* **Raportowanie**: Wyniki audytu są bezwzględnie rejestrowane w systemie MantisBT (platforma śledzenia błędów i rozwoju oprogramowania) **do 25. dnia każdego miesiąca** [241, 242, 271].

### Audyt Jakości Danych (AJD) CST2021 [242]
Realizowany jest dwutorowo:
1. **Miesięcznie**: Na podstawie samodzielnie wygenerowanych raportów AJD dostarczanych przez MFiPR [242].
2. **Kwartalnie**: Na podstawie zbiorczych raportów generowanych centralnie przez MFiPR [242].
Weryfikacja polega na wypełnieniu listy sprawdzającej w aplikacji **SR2021** [242]. Ewentualne wyłączenia z audytu wymagają złożenia formalnego wniosku według szablonu MFiPR [243].

### Audyt Aktywności Użytkowników [111, 112, 234, 237, 238, 239]
Aby zminimalizować ryzyko nieautoryzowanego dostępu, aktywność użytkowników posiadających konta operatorskie podlega cyklicznym przeglądom:
* **Częstotliwość**: 
  * W Urzędzie Marszałkowskim (IZ): Dwa razy do roku (czerwiec i grudzień) [110, 234] oraz kwartalnie w oparciu o raporty MFiPR [237].
  * W Wojewódzkim Urzędzie Pracy (IP): Raz na kwartał [112].
  * **Wyjątek**: W przypadku wprowadzenia stopnia alarmowego **BRAVO-CRP**, audyt aktywności musi być przeprowadzany **raz w miesiącu** [237].
* **Konsekwencje braku aktywności**: 
  * Jeśli użytkownik nie zalogował się do systemu centralnego (lub przynajmniej jednej z aplikacji) przez **6 miesięcy** (lub **3 miesiące** w IP/WUP i przy kwartalnym przeglądzie IZ), jego konto jest automatycznie **blokowane** [111, 112, 235, 238, 239].
  * Zablokowanie konta merytorycznego pociąga za sobą natychmiastowe odebranie uprawnień na instancji szkoleniowej [235, 238].

### Procedura Odstępstw od Zasad Zarządzania [244, 245, 246, 247, 248]
W sytuacjach nadzwyczajnych dopuszcza się odstępstwa od standardowych procedur operacyjnych:
* **Zasada Konsensusu**: Wprowadzenie jakiegokolwiek odstępstwa wymaga **jednomyślnej akceptacji wszystkich zaangażowanych instytucji** (RT, FS, FR, CI, WUP, ŚCP) [244, 247].
* **Forma**: Wniosek konsultowany jest drogą e-mailową (z oznaczeniem w temacie: `PROPOZYCJA ODSTĘPSTWA OD ZAPISÓW ZASAD ZARZĄDZANIA SYSTEMAMI INFORMATYCZNYMI SŁUŻĄCYMI DO OBSŁUGI FE SL 2021-2027`) [245].
* **Dokumentowanie**: Po uzyskaniu zgody sporządzana jest notatka służbowa w formacie PDF, podpisywana elektronicznie przez wszystkich Dyrektorów/Zastępców Dyrektorów i rejestrowana w centralnym rejestrze odstępstw prowadzonym przez RT-ZSPS [247, 248, 249].

### Rozwój Systemu i Metodyka SCRUM [146, 147]
Prace rozwojowe i optymalizacyjne nad systemem lokalnym LSI 2021 prowadzone są w zwinnej metodyce **SCRUM** [146]:
* **Product Backlog**: Zgłoszenia i błędy są na bieżąco rejestrowane przez instytucje w systemie MantisBT [146].
* **Sprints**: Zadania realizowane są w krótkich cyklach (tzw. Sprintach), które standardowo trwają **1 tydzień** (z opcją wydłużenia do 2 tygodni przy dużym wolumenie zgłoszeń) [146, 147].
* **Komunikacja**: Status prac oraz planowanie kolejnego Sprintu odbywają się na cyklicznych spotkaniach statusowych deweloperów i administratorów [146, 147].