# Household Bookkeeping – Automated Ingest PoC

## 1. Zielsetzung

Ziel dieses Projekts ist der Aufbau eines **self-hosted, Python-basierten Microservice-Systems** zur **automatisierten Erfassung von Haushaltsausgaben**, mit Fokus auf:

- strukturierter, maschinenlesbarer Datenerfassung
- reproduzierbarer Normalisierung
- regelbasierter, erklärbarer Kategorisierung
- langfristiger Eignung für Statistiken, Zeitreihenanalysen und Prognosen

Der initiale Fokus liegt bewusst auf **Datenqualität, Transparenz und Erweiterbarkeit**, nicht auf UI oder Skalierung.

---

## 2. Nicht-Ziele (bewusst ausgeschlossen)

- Kein Cloud-Zwang
- Kein Vendor-Lock-in
- Kein rein ML-basiertes Black-Box-System
- Keine direkte Finanzanalyse oder Forecasts im PoC
- Keine relationale Datenbank im ersten Schritt

---

## 3. Grundprinzipien

1. **Raw Data First**  
   Rohdaten werden unverändert gespeichert, um spätere Parser- und Regelverbesserungen zu ermöglichen.

2. **Determinismus vor Intelligenz**  
   Regeln sind nachvollziehbar, versionierbar und erklärbar.

3. **Schema vor Statistik**  
   Ein stabiles Schema ist Voraussetzung für belastbare Auswertungen.

4. **Service-Entkopplung**  
   Verarbeitungsschritte sind logisch getrennt, auch wenn sie physisch gemeinsam laufen können.

---

## 4. Architekturübersicht

```
           +-------------------+
           |   Client (CLI /   |
           |   Mobile / Script)|
           +---------+---------+
                     |
                     v
           +-------------------+
           |  Ingest Service   |
           |  (Text / Image)   |
           +---------+---------+
                     |
          +----------+----------+
          |                     |
          v                     v
+-------------------+   +----------------------+
| Receipt Ingest    |   | Other Ingest         |
| Service           |   | Services (future)    |
| (Household Book)  |   | e.g. contracts, docs |
+---------+---------+   +----------------------+
          |
          v
+-------------------+
| JSON File Storage |
+-------------------+
```

---

## 5. Services (logisch getrennt)

### 5.1 General Ingest Service

**Verantwortung**
- Annahme von:
  - Bildern (z. B. Kassenbons)
  - Text (OCR-Ergebnisse, E-Mail-Text, Copy-Paste)
- Speicherung der Rohdaten
- Erste Klassifikation des Inhalts (regelbasiert)

**Beispielhafte Endpunkte**
- `POST /ingest/image`
- `POST /ingest/text`

**Output**
- `ingest_result.json`
- Weiterleitung an spezialisierte Services

---

### 5.2 Household Receipt Ingest Service

**Verantwortung**
- Parsing von Kassenbons
- Extraktion von:
  - Händler
  - Datum/Zeit
  - Positionen
  - Steuerinformationen
- Normalisierung
- Regelbasierte Kategorisierung
- Persistenz als JSON

---

## 6. Datenpersistenz (PoC)

### 6.1 Warum JSON Files

- einfach versionierbar
- diff-fähig
- kein Migrationsaufwand im PoC
- später gut in SQL/NoSQL überführbar

### 6.2 Ordnerstruktur (Vorschlag)

```
data/
├── raw/
│   ├── images/
│   ├── ocr_text/
│   └── ingest_events/
├── canonical/
│   ├── receipts/
│   │   └── 2025/
│   │       └── 2025-12-29_kaufland.json
│   └── items/
├── rules/
│   ├── categories.yml
│   ├── normalization.yml
│   └── merchants.yml
└── schema/
    └── receipt.schema.json
```

---

## 7. Datenmodell (Canonical Receipt)

```json
{
  "schema_version": "1.0",
  "receipt": {
    "id": "uuid",
    "merchant": {
      "name": "Kaufland",
      "store_id": "DE7450"
    },
    "datetime": "2025-12-29T12:07:00+01:00",
    "currency": "EUR",
    "payment_method": "card"
  },
  "line_items": [
    {
      "line_id": "uuid",
      "name_raw": "KBio H-Milch",
      "name_clean": "kbio h milch",
      "tokens": ["milch", "haltbar", "bio"],
      "name_norm": "milch_haltbar_bio",
      "quantity": 6,
      "unit": "pcs",
      "unit_price": 1.25,
      "total": 7.50,
      "vat_rate": 0.07,
      "category": "groceries.dairy",
      "tags": ["bio"],
      "classification": {
        "engine": "rules",
        "rule_id": "groceries_dairy_milk",
        "confidence": 0.98
      }
    }
  ],
  "totals": {
    "total": 118.61,
    "vat_breakdown": [
      {"rate": 0.07, "gross": 109.17},
      {"rate": 0.19, "gross": 9.44}
    ]
  },
  "provenance": {
    "source_type": "image",
    "ocr_engine": "tesseract",
    "parser": "de_receipt_v1",
    "created_at": "2025-12-29T12:10:00+01:00"
  }
}
```

---

## 8. Normalisierung

### Ziele
- gleiche Produkte → gleicher `name_norm`
- robust gegen Händler-Abkürzungen
- reproduzierbar

### Schritte
1. Textbereinigung
2. Tokenisierung
3. Stopword-Filter
4. Synonym-Mapping
5. Canonical Key Generierung

---

## 9. Rule Engine

### Eigenschaften
- YAML-basiert
- priorisiert
- erklärbar
- versionierbar

---

## 10. Kategorien (Start-Set)

- groceries.produce
- groceries.dairy
- groceries.meat_fish
- groceries.bakery
- groceries.pantry
- groceries.snacks
- groceries.beverages
- groceries.spices_sauces
- groceries.frozen
- groceries.deposit
- household.cleaning
- household.paper
- household.hygiene
- other

---

## 11. Erweiterbarkeit

- Austausch von OCR-Engine
- Händler-spezifische Parser
- Zusätzliche Ingest-Services
- Migration von JSON → Datenbank
- Ergänzung durch ML-basierte Klassifikation

---

## 12. PoC-Scope

**Enthalten**
- Image/Text Ingest
- OCR
- Receipt Parsing
- Normalisierung
- Rule-basierte Kategorisierung
- JSON-Persistenz

**Nicht enthalten**
- UI
- Forecasting
- Multi-User
- Authentifizierung

---

## 13. Erfolgskriterium

Der PoC gilt als erfolgreich, wenn:
- ≥ 90 % der Positionen korrekt kategorisiert werden
- Regeln nachvollziehbar angepasst werden können
- Daten später ohne Verlust migrierbar sind
