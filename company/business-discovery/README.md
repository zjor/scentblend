# Scent Blend — business discovery session

Prepared for 30 October 2026.

- [Adapted English SVG](scentblend-discovery-en.svg): seven branches covering direction, people, sales, offers, operations, money and data. Start here for the session.
- [Original Russian SVG](business-checkup-original-ru.svg): all six branches and questions from the supplied image, with spelling and punctuation cleaned up.
- [Editable question bank](question-bank.md): the adapted questions as Markdown for taking notes.

Both SVGs contain selectable, editable text, vector shapes and connectors, with no external assets. Open in a browser and zoom, or import into a vector editor. They are large scrollable maps, intended for screen use or large-format printing rather than a single A4 page. Rebuild with `python3 company/business-discovery/build_maps.py` after editing the source trees.

## Run the session

Use the questions as prompts, not a mandatory questionnaire. Start with “Show me a recent customer from first enquiry to delivery and payment.” Follow the actual work and ask what happens when it goes wrong. Capture the team's language before proposing standard terminology or software.

Suggested 120-minute agenda (adjust to the available time):

| Minutes | Focus | Capture |
| --- | --- | --- |
| 0–10 | Purpose and business model | Active lines, desired outcomes, main constraint |
| 10–25 | People and responsibilities | Roles, decisions, dependencies, capacity |
| 25–60 | One recurring B2B customer end to end | Sales, contract, site, device, refill, service, invoice, payment |
| 60–80 | Contrasting cases | Private-label order and shop order; relevant exceptions |
| 80–100 | Objects, records and money | Definitions, IDs, relationships, authoritative systems, gaps |
| 100–115 | Growth and priorities | Three problems or opportunities, evidence, impact and effort |
| 115–120 | Read-back and next steps | Owners, due dates, unresolved questions |

If time is short, finish one real workflow and its exceptions before opening another. Park unresolved questions with an evidence owner.

## Capture the ontology

Treat the following as candidate entities to validate, not an established data model:

Customer legal entity, brand/group, contact, site, lead/opportunity, quote, agreement, service line, product/SKU, scent recipe/version, supplier, batch, stock location, device, installation, service visit, support ticket, order/order line, shipment, invoice/invoice line, payment/refund and responsible person/role.

For each entity, record:

| Term used by the team | Definition / real example | Unique identifier | Important fields | States / changes | Relationships and cardinality | Owner / authoritative record |
| --- | --- | --- | --- | --- | --- | --- |
| | | | | | | |

Ask whether one legal entity can have many sites, one contract can cover multiple sites, one site can have several devices, and one payment can settle several invoices. Capture partial payment and device relocation history. Separate brand names from legal entities and opportunities from signed obligations. Record how changes are dated and who can make them.

For each process, record:

| Trigger | Input / object | Steps and responsible role | Handoff / acceptance | Output / changed state | Exception | Tool / evidence | Delay / measure |
| --- | --- | --- | --- | --- | --- | --- | --- |
| | | | | | | | |

For decisions and open questions, record:

| Fact / hypothesis / unknown | Evidence or example | Impact | Next action | Owner | Due date | Success measure |
| --- | --- | --- | --- | --- | --- | --- |
| | | | | | | |

## Context and interpretation

The adaptation uses [company/identity.md](../../company/identity.md), [financial documentation](../../finance/README.md), and private working customer notes in `data/enriched/customer-notes.md`. It includes internal reconciliation prompts and should be treated as an internal workshop document. Working notes are not verified contracts; the map deliberately asks for evidence rather than presenting their commercial terms as facts. No private financial amounts are reproduced.

The original assumes separate departments and gives significant attention to video/content production. The adaptation asks who performs each function without assuming a department exists. It adds installed equipment, replenishment, suppliers, custom production, e-commerce fulfilment and financial reconciliation. Marketing channel ownership and results sit within demand and sales.

The original's wording equates LTV with a client lifecycle; it is retained for fidelity. In the session, distinguish customer lifetime value (economic value over a relationship) from lifecycle stages. NPS is a recommendation measure, not a complete measure of satisfaction. Ask what is actually measured and how.

Known context is distinguished from discovery: the business has four publicly described service lines plus a B2C shop; the actual team, systems, operational rules, data ownership and relationship cardinalities still need to be established. Bank receipts alone do not establish revenue timing, margin or customer-level settlement.

## Russian adaptation with initial context

- [Russian Scent Blend SVG](scentblend-discovery-ru.svg) — expanded to eight areas, with source-labelled context and open questions.
- [Russian question bank](question-bank-ru.md) — includes space for session notes.
- [Russian facilitation guide and source notes](session-guide-ru.md) — explains additions, evidence status, and LinkedIn retrieval limits.

Rebuild this version with `python3 company/business-discovery/build_maps_ru.py`. It uses the shared renderer in `build_maps.py`; the original Russian redraw and English map remain separate artifacts.

## Reusable framework

- [Merged discovery framework (Russian)](framework-ru.md) — session contract, 12 blocks of questions, facilitation moves, capture templates and post-session steps. Merges the structure of an observed external check-up session (details under NDA), the strategy-workbook pre-work sheet and the Scent Blend map; each question is tagged by source.
