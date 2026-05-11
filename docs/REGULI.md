# Constituția Anti-Overengineering — Pulse

Aceste reguli sunt **obligatorii** pentru orice linie de cod scrisă sau modificată în acest proiect.
Valgono anche quando un modello AI genera codice — codul generat trebuie să le respecte sau e rescris înainte de a fi acceptat.

Oricând ai un dubiu: alege varianta cu **mai puține abstracții și mai puține linii**.

---

## Reguli fundamentale

```
REGULA 1 — Nicio abstracție preventivă
  Nu crea o funcție, un obiect sau un modul "pentru că ar putea fi util în viitor".
  Abstractizezi doar când ai 3+ cazuri REALE și identice care o cer.

REGULA 2 — Copiază înainte să abstractizezi
  Dacă o funcție e folosită în 2 locuri → copiaz-o.
  Dacă e folosită în 3+ locuri → atunci extrage o funcție comună.

REGULA 3 — Funcții liniare, nu imbricate
  O funcție face un singur lucru.
  Nicio imbricare mai adâncă de 2 niveluri de if/for.
  Dacă depășește 50 de linii → desparte-o în pași cu nume explicite.

REGULA 4 — Nume care descriu acțiunea
  resolve_channel(), fetch_new_videos(), send_notification()
  NU: handle_action(), process_data(), manage_state()

REGULA 5 — Zero pattern enterprise
  INTERZIS: clase abstracte (ABC), interfețe, factories, singleton,
            repository, service layer, dependency injection,
            decorator pattern, observer pattern, event bus.
  PERMIS: funcții libere, dataclass/BaseModel pentru date.

REGULA 6 — Raw SQL, nu ORM
  Toate interogările sunt raw SQL via fetch_all / fetch_one / fetch_value / execute.
  ORM-ul (select(Model).where(...)) este INTERZIS în cod de aplicație.
  Models.py există exclusiv pentru Alembic autogenerate.

REGULA 7 — Un singur proces
  Bot + scheduler rulează în același proces asyncio.
  Nu adăuga servicii separate (FastAPI, worker) fără nevoie demonstrată.

REGULA 8 — Comentariile explică DE CE, nu CE
  Codul explică ce. Comentariul explică doar ce e surprinzător sau are
  un motiv non-evident (workaround, constraint ascuns, bug specific).
  Niciun docstring multi-paragraf. Niciun comentariu care rescrie codul.

REGULA 9 — Erori clare, nu silențioase
  Fiecare apel extern (HTTP, DB, LLM, Telegram) are try/except explicit
  cu logger.error("ce s-a întâmplat", ...).
  Niciodată except Exception: pass.
  Dacă summary-ul e gol → nu trimite notificare, loghează eroarea.

REGULA 10 — Zero hardcoding
  Nicio credențială, URL sau valoare de configurare în cod.
  Totul în config.py via pydantic-settings din .env.
```

---

## Semne de alarmă (dacă le vezi, rescrie)

- Fișier care importă din alt fișier care importă din primul (circular)
- Clasă cu un singur scop care putea fi funcție
- Funcție care primește alt obiect "service" ca parametru (DI)
- Mai mult de 3 niveluri de directoare în `pulse/`
- Orice fișier numit `base.py`, `abstract.py`, `interface.py`, `factory.py`
- `from __future__ import annotations` fără motiv concret
- Orice `retry`, `backoff`, `circuit_breaker` custom
- `structlog`, `loguru` sau altceva în afară de stdlib `logging`
