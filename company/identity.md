# Scent Blend — business identity

Public facts about the company this repo models. Sources are the company website, the English site, and the Czech ARES registry, all checked on 2026-10-29. Re-check the website facts when they are older than a few months; prices and the client list change. Private financial data stays in `data/` and `reports/` (excluded from Git).

## Legal entity

| Field | Value | Source |
| --- | --- | --- |
| Legal name | Scent Blend s.r.o. | ARES |
| IČO | 21260150 | ARES |
| DIČ | CZ21260150 | ARES, website footer |
| Legal form | s.r.o. (ARES code 112) | ARES |
| Entity registered | 2024-02-16 | ARES |
| Registered address | V Pitkovičkách 11, Pitkovice, 104 00 Praha 10 | ARES, website footer |
| NACE | 731 (advertising), 82100, 46 (wholesale), 47 (retail), 52100 (warehousing) | ARES |
| Business email | cooperation@scentblend.cz | website |
| Instagram | @scent_blend | website |
| Websites | https://www.scentblend.cz/ (Czech), https://scent-blend.com/ (English) | website |
| Bank | Raiffeisenbank, CZK account (from exports in `data/raw/`) | repo |

ARES record: https://ares.gov.cz/ekonomicke-subjekty/res/21260150

Known discrepancy: the website says "since 2020"; the s.r.o. was registered in February 2024. Treat 2020 as the brand's start, not the entity's. Do not use 2020 as the company age in investor or valuation material without confirming.

## What the company sells

Tagline on the site: "Your Stories Factory". Four service lines, as the website names them:

1. **Space scenting (aroma marketing).** Scent design plus automatic diffusers installed in commercial interiors. This is the recurring B2B business in `data/enriched/customer-notes.md`: quarterly or yearly fees per branch or site.
2. **Private label.** Scented products made under the client's brand, from recipe to packaging. Covers the one-off merchandise orders in the notes (for example Element-expo, Marie Grizan).
3. **Distribution.** Ready-to-sell scented products for marketplaces and retail chains.
4. **Brand experiences.** Scent activations for events and campaigns (for example Agentura Rubio).

Product range: candles, diffusers, refills, travel candles, Palo Santo, car fragrances, candle sand, deodorizing balls. Claims: IFRA certified, vegan, cruelty-free, paraben-free, made in the EU.

Target segments named on the site: HoReCa, wellness and spa, showrooms (fashion, jewellery, furniture), shopping centres, massage and cosmetic studios, brands, event and marketing agencies, hotels.

## B2C e-shop

Launched in 2026; the shop terms are dated 2026-07-15. Checkout through Stripe, ships worldwide (CZ, EU, rest of world zones). This explains the Stripe payouts in the bank export, which do not identify end customers.

Prices on 2026-10-29, incl. VAT:

| Item | Price |
| --- | --- |
| Scent Go Home diffuser (up to 50 m², Bluetooth app, 125 ml cartridge) | 1,190 CZK (55 USD on the English site) |
| Refill 1 × 125 ml | 399 CZK |
| Refill 3 × 125 ml | 1,049 CZK |
| Refill 5 × 125 ml | 1,796 CZK |
| Discovery set 5 × 50 ml | 899 CZK |

The e-shop is not yet a stream in `data/enriched/forecast-assumptions.csv`.

## References shown on the website

Logos listed under "brands that trust us". The site does not say what each relationship is.

Matches a client in the repo notes or bank receipts:
AAA Auto (AURES Holdings), Mototechna (notes call it "Moto-techno"), Farma Čapí hnízdo (notes: "Chapi Hnizdo"), Massage Propaganda, RE/MAX, Ponteo, Dorow Clinic, Oraculum (bank: "ORACULUM Company s.r", unverified).

Not in repo data (assumed past one-off or private-label work; unverified):
Dr. Max, Forbes, Sothys Paris, Playboy, Vogue, Cosmopolitan, Volvo, Volkswagen, ČSOB, Bruno Vassari, Rohlik.cz, Bang & Olufsen, Bořislavka, Smyssly, Fashion Arena Prague Outlet, Sephora.

Other site claims, unverified: 10,000+ products produced, 165+ brands, sales uplift "up to 30 %".

## Sales process (from the website)

Brand analysis → custom scent proposal → contract with agreed terms and budget → production, delivery, installation. Reply promised within 24 hours of an enquiry. B2B pricing is on request; the diffuser page advertises "B2B prices" and own-brand products for commercial spaces.

## Not known from public sources

Owners and team, bank account number, court file number (spisová značka), VAT registration date, B2B price list, supplier list, and the legal entity behind the 2020 brand start. Add these here when confirmed from documents.
