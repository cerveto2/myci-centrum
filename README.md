# Samoobslužné mycí centrum – studie rozmístění

Stránka s variantami: `vystup/prehled.html` (na GitHub Pages se otevře rovnou z kořene).

- `generuj.py` – parametrický generátor výkresů (rozměry nahoře v PARAMETRY, každá varianta = funkce `varianta_*`)
- `podklad/planek.webp` – plánek z Affinity (měřítko 18,3 px/m)
- `vystup/varianta-*.svg` – výkresy 1:200 na A3, otevřou se v Affinity (vrstvy: podklad, plocha, prvky, hranice, provoz, kóty, razítko)

Přegenerování: `python3 generuj.py` (potřebuje Pillow).
