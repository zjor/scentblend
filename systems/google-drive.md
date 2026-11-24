# Google Drive

Status: map read on 2026-11-24 through the Google Drive connector. Purposes are inferred from folder and file names; confirm with the folder owner before relying on them.

The shared folder **Scent Blend Disk** holds the company's working files. It is owned by `scentblend.factory@gmail.com` and shared read-only to team members.

- Root: [Scent Blend Disk](https://drive.google.com/drive/folders/1WLhCE5u5_4PttoJtAiIzRYPqWX-PAI20) — folder ID `1WLhCE5u5_4PttoJtAiIzRYPqWX-PAI20`
- Search inside one folder: `parentId = '<folder ID>'` (direct children) or `'<folder ID>' in ancestors` (whole subtree).

## Target state

Drive becomes blob storage only: images, design sources, signed PDFs, large binaries. Structured and editable content moves out:

| Content | Destination |
| --- | --- |
| Customers, leads, contacts, suppliers | Pipedrive ([CRM](crm.md)) |
| Price lists, product catalogue | Pipedrive products |
| Procedures, training, product knowledge | YouTrack knowledge base |
| Tasks and follow-ups | YouTrack [TM](https://scentblend.youtrack.cloud/projects/TM) |
| Signed contracts, certificates, brand assets, photos | Drive (stays), linked from CRM or YouTrack |

The **Migrate to** column below applies this rule per folder.

## Folder map

| Folder | Purpose | Look here for | Migrate to |
| --- | --- | --- | --- |
| [Ceníky a tabulky výroby](https://drive.google.com/drive/folders/1Hx6mVLpbQ4Rj1-GOu4bnChIyX5DsCseI) | Price lists and production tables | Fragrance price lists in EUR, EUR DE, CZK, CHF (`.xlsx`) | Pipedrive products |
| [Certifikáty a bezpečnostní listy](https://drive.google.com/drive/folders/18Ff05lmSZsTALcC_y3SRbOAulC6v2uOc) | Product certificates and safety data sheets (SDS) | Compliance documents for fragrances | Stays (blob); link from products. Empty or not shared on 2026-11-24 |
| [Content SB](https://drive.google.com/drive/folders/1mgpHP9ZX_d5HfgGLaL5kSbPgRSDweyiG) | Marketing content | `Photo/` — product and brand photos | Stays (blob) |
| [Dodavatele](https://drive.google.com/drive/folders/1pmsWPwc0zgSg2MBu4OmhjsDYNbrLRwuj) | Suppliers | `dodavatele.docx` — supplier list | Pipedrive organizations |
| [Events](https://drive.google.com/drive/folders/1iIKcJqkQVtElKjZTFfuc2N8YW2fxFwIC) | Event leads | `Email Contacts` sheet — contacts collected at events | Pipedrive contacts / leads |
| [Fonts, business card, sb factory main](https://drive.google.com/drive/folders/1AktImwPtzPJdcLVV5d_6zzlzuihmmceJ) | Brand design sources | `SB Factory Main.ai`, business card, Forbes brochure (93 MB), info sheet | Stays (blob) |
| [Klienti](https://drive.google.com/drive/folders/1zo_2Pux8-QMEM-splqcwB62Cp2FW7Itz) | One subfolder per customer, plus prospects and notes | Customer files (AAA auto, Kenny's Autocenter AG, Zios profi, …), `Potenciální klienti/`, `Client Card/`, `Komentáře a poznámky/` | Pipedrive organizations, leads and notes; files stay as blobs linked from the organization |
| [Logo](https://drive.google.com/drive/folders/1BWS1CgSt8kfV48XvASVh1kvdLyqpoFnx) | Logo files | `black/`, `red/`, `white/` variants | Stays (blob) |
| [Prezentace](https://drive.google.com/drive/folders/1zwIkmsGP1_PHMfwP9l1pJoe4fw-ygydr) | Sales decks and offers, one subfolder per segment or offer | Hotels & Resorts, Automotive, Aromatizace prostor, Private label, Candle Sand, candle containers, Christmas offer 2026, Scent Marketing Guide | Stays (blob); link from YouTrack KB |
| [Product documents](https://drive.google.com/drive/folders/1-XcwN2bT-W51J3iw6w7AG0d7DVTo1ggy) | Product specifications | — | YouTrack KB; empty or not shared on 2026-11-24 |
| [Smlouvy](https://drive.google.com/drive/folders/1wO89r9vYTkwZRbLIifDZJdWCDEC9OZQP) | Customer contract templates in CZ, EN, DE | `Smlouvy Aromatizace prostor …/` (scenting service), `Smlouvy MERCH …/` (merchandise) | Templates: YouTrack KB; signed contracts: stay (blob), linked from Pipedrive |
| [Tým](https://drive.google.com/drive/folders/1KifEL023DmhM4gww7_hMCvLafFvaOyRT) | Team agreements | `NDA/`, `Smlouvy/` (employment and cooperation contracts), one untitled doc (`Новый документ`) | Signed files stay (blob), linked from [company/team](../company/team/README.md) |
| [Vizitky, brožury, letáky](https://drive.google.com/drive/folders/1Z36d0Rzwyrsv1Z3T45SJUIWRlk2XN6pl) | Print materials | Business card, slide deck PDF, fonts sheet | Stays (blob) |
| [Školení](https://drive.google.com/drive/folders/10miCvU1SwdX7D9izaBaU8E5WdF1ff4xT) | Training | — | YouTrack KB; empty or not shared on 2026-11-24 |

## Where to look

- Prices → `Ceníky a tabulky výroby`
- A customer's files → `Klienti/<customer>`; the customer record itself → Pipedrive
- Sales deck or offer for a segment → `Prezentace/<segment>`
- Contract template → `Smlouvy`; staff agreement → `Tým`
- Logo or brand source file → `Logo`, `Fonts, business card, sb factory main`
- Photos → `Content SB/Photo`
