# Anio für Home Assistant

Deutsch | [English](README.md)

Eine inoffizielle Home-Assistant-Integration für Anio-Kinderuhren. Sie
verbindet ein Anio-Cloudkonto mit Home Assistant und zeigt Uhren als Geräte,
ihre Standorte und Aktivitäten sowie Textnachrichten an.

> **Wichtig:** Dieses unabhängige Hobbyprojekt steht nicht mit ANIO GmbH in
> Verbindung und wird nicht von ihr unterstützt. Standortdaten können
> verzögert oder ungenau sein. Die Integration ist kein Sicherheits- oder
> Notfallsystem.

## Funktionen

- Zuletzt gemeldeten Standort, Akku und Diagnoseinformationen anzeigen.
- Einen neuen Standort anfordern, den Explorer-Modus steuern und einen
  zeitlich begrenzten Radar-Modus verwenden. Für das Klingeln der Uhr muss
  der Klingel-Schutz bewusst deaktiviert werden.
- Text und Emojis senden und den Chatverlauf unterstützter Uhren anzeigen.
- Anio-Aktivitäten einschließlich der Ereignisse von Anio-Zonen anzeigen.
- Mitgelieferte Standort-, Chat- und Aktivitätenkarten zum Dashboard hinzufügen.

Die verfügbaren Funktionen hängen von Uhr und Anio-Konfiguration ab.
Sprachnachrichten können derzeit weder abgespielt noch gesendet werden, auch
wenn eine Aufnahmeschaltfläche sichtbar ist. Beachte die
[Einschränkungen](#einschränkungen).

## Voraussetzungen

- Ein laufendes Home Assistant mit Marketplace (Home Assistant 2026.11 oder
  neuer) oder HACS (ältere Versionen).
- Ein Anio-Cloudkonto mit mindestens einer verknüpften Uhr sowie eine
  Internetverbindung von Home Assistant zur Anio-Cloud.
- Eine kompatible Home-Assistant-Version. Die unterstützte Mindestversion ist
  noch nicht festgelegt; Installation und Einrichtung müssen noch auf einer
  sauberen Home-Assistant-Instanz geprüft werden.

## Installation über Marketplace / HACS

### Marketplace (Home Assistant 2026.11 oder neuer)

1. **Einstellungen > Marketplace** öffnen und **Aus Link hinzufügen** wählen.
2. `https://github.com/kiencke/home-assistant-anio` eingeben und hinzufügen.
   Bei Aufforderung GitHub verbinden und als Typ **Integration** auswählen.
3. **Anio** öffnen und **Installieren** wählen.
4. Home Assistant neu starten.

### HACS (ältere Home-Assistant-Versionen)

1. HACS öffnen und im Drei-Punkte-Menü **Benutzerdefinierte Repositories**
   auswählen.
2. `https://github.com/kiencke/home-assistant-anio` eingeben, den Typ
   **Integration** auswählen und das Repository hinzufügen.
3. **Anio** in HACS öffnen und herunterladen.
4. Home Assistant neu starten.

Weitere Hinweise stehen in der
[Marketplace-Anleitung](https://www.home-assistant.io/integrations/marketplace/#custom-repositories)
und der [HACS-Anleitung](https://www.hacs.xyz/docs/faq/custom_repositories/).
Diese Installationswege wurden für dieses Projekt noch nicht validiert.

## Anio-Konto verbinden

1. **Einstellungen > Geräte & Dienste > Integration hinzufügen** öffnen.
2. **Anio (Inoffiziell)** suchen und E-Mail-Adresse und Passwort des
   Anio-Kontos eingeben.
3. Die vorgeschlagene App-UUID übernehmen oder das Feld für eine automatisch
   erzeugte Kennung leer lassen. Ein eigener Wert muss genau 16 hexadezimale
   Zeichen enthalten.
4. Die Einrichtung abschließen. Home Assistant erstellt für jede vom Konto
   gemeldete Uhr ein Gerät.

Falls Home Assistant später eine erneute Anmeldung anfordert, das Anio-Passwort
erneut eingeben. Die Einrichtung benötigt einen erfolgreichen ersten
Standortabruf; ein Cloud- oder Standortfehler kann sie auch nach erfolgreicher
Anmeldung verhindern.

## Dashboard und Bedienung

Im Bearbeitungsmodus des Dashboards eine Karte **Anio-Standort**, **Anio-Chat**
oder **Anio-Aktivitäten** hinzufügen und eine Uhr auswählen. Die Karten werden
automatisch registriert; eine zusätzliche Dashboard-Ressource ist nicht nötig.
Chat-Bedienelemente stehen nur für unterstützte Geräte zur Verfügung. Falls
eine Karte nach der Installation nicht gefunden wird, nach dem Neustart den
Browser neu laden.

Die [Dashboard-Beispiele](examples/dashboards) enthalten deutsche und
englische Sections-Ansichten. Eine Ansicht in die rohe Dashboard-Konfiguration
kopieren, `<device_slug>` und `<ha_device_id>` ersetzen und die Entity-IDs unter
**Einstellungen > Geräte & Dienste > Entitäten** prüfen. Entity-IDs können je
nach Sprache oder früherer Anpassung abweichen. Für die Geräte-ID die Uhr im
Chatkarten-Editor auswählen und dessen YAML-Konfiguration ansehen.

Die Standortkarte zeigt den Zeitpunkt des letzten Positions-Updates. Eine alte
Position ist nicht zwingend der aktuelle Standort der Uhr. **Standort
anfordern** bittet die Uhr um eine neue Ortung; der Status wird erst bei einem
neueren Positionszeitstempel auf „Aktualisiert“ gesetzt.

Der Radar-Modus fordert für begrenzte Zeit wiederholt eine Position an.
Vorbelegt sind 15 Minuten und ein Intervall von 90 Sekunden. Der Akkustand muss
bekannt sein und mindestens 20 % betragen; bei niedrigem oder unbekanntem Akku,
API-Ratenbegrenzung oder Zeitablauf stoppt der Modus. Um die Uhr klingeln zu
lassen, zuerst den **Klingel-Schutz** deaktivieren. Ruhezeiten und Schulmodus
werden für das Klingeln nicht automatisch erkannt.

## Abrufintervalle und Aktivitäten

Die Abrufintervalle lassen sich über **Konfigurieren** an der Integration ändern:

| Daten | Vorbelegung | Bereich |
| --- | --- | --- |
| Standort: Normal und Schulweg | 300 Sekunden | 60–1800 Sekunden, in 60-Sekunden-Schritten |
| Standort: Explorer | 60 Sekunden | 60–1800 Sekunden, in 60-Sekunden-Schritten |
| Aktivitäten | 60 Minuten | 1–1440 Minuten |

Die Einstellungen steuern die Cloudabfragen von Home Assistant, nicht das
Ortungsintervall der Uhr. Für den gemeinsamen Standort-Endpunkt wird das
kürzeste konfigurierte Intervall der gemeldeten Uhrmodi verwendet.

Die sichtbare Chatkarte aktualisiert sich alle 30 Sekunden; der Chat wird auch
nach erfolgreichen Standortabrufen und nach dem Senden abgerufen. Aktivitäten
werden beim Start, regelmäßig, beim Sichtbarwerden der Aktivitätenkarte und
über deren Aktualisierungsschaltfläche abgerufen. Automatisches Öffnen löst
höchstens alle 30 Sekunden einen Abruf aus; die Schaltfläche umgeht diese Sperre.

**Anio-Zonen** werden im Anio-System konfiguriert und sind keine
Home-Assistant-Zonen. Für Anzeige und Sortierung werden „Verlassen“-Zeitpunkte
auf ganze Sekunden gerundet und geschätzt um eine Minute vorgezogen. Dadurch
können andere Ereignisse umsortiert werden; der Originalzeitpunkt bleibt im
Aktivitätssensor erhalten. Servergrenzen und Seitennavigation der Historie
sind unbekannt; ältere oder verpasste Aktivitäten können daher fehlen.

## Datenschutz

Home Assistant speichert die Konto-E-Mail-Adresse, App-UUID und das
Refresh-Token; Passwort und Access-Token werden nicht im Konfigurationseintrag
gespeichert. Sichere Home-Assistant-Backups und das Konfigurationsverzeichnis.

Chatverlauf und Aktivitäten werden lokal gespeichert. Chatnachrichten,
Aktivitätstexte, Zonennamen und Zeitpunkte können in Entity-Attributen sichtbar
sein. Nachrichteninhalte können auch in Events erscheinen und vom Recorder
gespeichert werden. Die Aktivitätenliste ist vom Recorder ausgeschlossen, kann
aber für andere Integrationen und Personen mit Zugriff auf Entity-Zustände
sichtbar sein. Gespeicherte Historien und Entity-Zustände wachsen mit der Zeit.

Textnachrichten verwenden, sofern verfügbar, den Anzeigenamen der auslösenden
Home-Assistant-Person als Anio-Absender, sonst `HA`; dieser Name wird an die
Anio-Cloud gesendet. Emojis verwenden `HA`. Zugangsdaten, Tokens, rohe
API-Antworten, persönliche Nachrichten und genaue Standorte nicht in Issues
oder Screenshots veröffentlichen.

## Einschränkungen

- Die Integration verwendet eine inoffizielle Cloud-API und kann bei deren
  Änderung ausfallen. Verfügbarkeit und Kompatibilität aller Uhrenmodelle sind
  nicht überprüft.
- Positionszeitpunkt und letzte Netzwerkantwort sind unterschiedliche Werte;
  eine aktuelle Antwort bedeutet nicht zwingend eine aktuelle Position.
  GPS-Genauigkeit wird als Meter interpretiert, die API-Einheit ist aber nicht
  bestätigt. Geschwindigkeit und Richtung sind Rohwerte.
- Wiedergabe und Versand von Sprachnachrichten sind nicht implementiert. Die
  Emoji-Zuordnung wurde aus der App abgeleitet und nicht vollständig bestätigt.
- Aktivitäten werden anhand ihrer ID dedupliziert. Separate doppelte
  Zoneneinträge aus der Cloud können weiterhin erscheinen.

## Entwicklung und Lizenz

Die englische [Entwicklungsanleitung](docs/development.md) beschreibt Tests,
API-Hinweise und den optionalen Live-Smoke-Test. Das Projekt steht unter der
[MIT-Lizenz](LICENSE).
