# FTL: Faster Than Light — srpski prevod (Serbian translation)

**Srpski prevod igre FTL: Faster Than Light** (latinica) za verziju 1.6 / Advanced Edition, kao [Slipstream](https://github.com/Vhati/Slipstream-Mod-Manager) mod.
Prevedeni su ceo tekst igre, glavni meni i slike sa natpisima, a fontovi su dopunjeni slovima č ć š ž đ.

**Unofficial Serbian translation of FTL: Faster Than Light** (Latin script) for version 1.6 / Advanced Edition, packaged as a Slipstream mod. → [English description](#english)

Ključne reči: FTL srpski, FTL na srpskom, prevod FTL igre na srpski jezik, srpska lokalizacija, FTL Faster Than Light Serbian, Serbian language mod, Srpski.

## Šta je prevedeno
- **Tekst:** ceo tekst igre (5.099 od 5.176 stringova): događaji, misije, brodovi, oružje, dronovi, augmentacije, posada, sektori, obuka, dostignuća i saveti. Na engleskom su ostali samo nazivi tastera, imena i licence.
- **Slike sa natpisima:** dugmad glavnog menija, UČITAVANJE, natpisi pauze, NEMA GORIVA, PROMAŠAJ i OTPOR.
- **Fontovi:** dodata su slova č ć š ž đ (Č Ć Š Ž Đ).


## Instalacija
1. Instaliraj [Slipstream Mod Manager](https://github.com/Vhati/Slipstream-Mod-Manager). Radi na Windowsu, Linuxu i macOS-u, sa Steam i GOG verzijom igre.
2. Kopiraj `FTL-Srpski.ftl` u Slipstreamov folder `mods/`. Fajl je na stranici Releases, a možeš ga napraviti i sam sa `python3 tools/build.py`, posle čega je u `dist/`.
3. Pokreni Slipstream, štikliraj mod i klikni **Patch**.
4. U igri izaberi Options → Change Language → **Srpski**.

Mod zauzima mesto poljskog jezika jer je spisak jezika ugrađen u igru. Za uklanjanje u Slipstreamu odštikliraj sve modove i klikni Patch.

## English
**FTL: Faster Than Light — Serbian translation (Latin script).** This is an unofficial, fan-made Serbian localization for FTL 1.6 (Advanced Edition), installed with Slipstream Mod Manager.

- Translates the whole game text (5,099 of 5,176 strings): events, quests, ships, weapons, drones, augments, crew, sectors, the tutorial, achievements and tips.
- Replaces the images with baked-in text: the main menu buttons, loading screen, pause banners, NO FUEL and MISS/RESIST.
- Adds the Serbian letters č ć š ž đ to the game's bitmap fonts.
- The language list is hardcoded in the game, so Serbian replaces the Polish slot. Pick **Srpski** under Options → Change Language.
- Fully revertible: unpatch in Slipstream to restore the original game.

**Install:** get [Slipstream Mod Manager](https://github.com/Vhati/Slipstream-Mod-Manager/releases), put `FTL-Srpski.ftl` in its `mods/` folder, tick the mod and click **Patch**.

Translated by **Milan Janković**. Not affiliated with Subset Games.

## Razvoj (development)
| Alat | Namena |
|---|---|
| `tools/prepare.py` | izvlači originalne fajlove iz `ftl.dat` u `src/orig/` i engleski tekst u `src/en/` |
| `src/sr/*.tsv` | prevod (`ključ<TAB>tekst`, escape sekvence `\n` i `\1` kao u igri) |
| `tools/check.py` | provera placeholdera, preloma redova, dozvoljenih znakova i pokrivenosti fontova |
| `tools/todo.py GRUPA N` | sledećih N neprevedenih stringova |
| `tools/build.py` | pravi `dist/FTL-Srpski.ftl` |
| `tools/serbian_glyphs.py` | dodaje č ć š ž đ u fontove igre |
| `tools/images.py` | slike sa natpisima (glavni meni, UČITAVANJE, pauza, NEMA GORIVA, PROMAŠAJ...), iscrtane fontovima igre; `--preview x.png` pravi poređenje sa poljskim originalima (potrebni numpy i scipy) |

Pravila prevoda i terminologija su u [glossary.md](glossary.md).
