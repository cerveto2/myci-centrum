#!/usr/bin/env python3
"""Generátor výkresů samoobslužného mycího centra – studie variant rozmístění.

Souřadnice jsou v metrech. Globální rámec = pixely podkladu / MERITKO (osa y dolů, sever nahoře),
takže výkres přesně sedí na podklad z Affinity (podklad/planek.webp).
Prvky areálu se zadávají v rámci řady boxů:
  u = podél řady (kladně na východ), v = kolmo na řadu (kladně na jih),
  počátek = osa řady na západním čele boxu M1.

Spuštění:  python3 generuj.py   →  vystup/varianta-*.svg  +  vystup/prehled.html
Úpravy: rozměry nahoře v sekci PARAMETRY, každá varianta je jedna funkce varianta_*().
"""
import base64
import html
import io
import math
import unicodedata
from pathlib import Path

from PIL import Image

KOREN = Path(__file__).resolve().parent
VYSTUP = KOREN / "vystup"
PODKLAD = KOREN / "podklad" / "planek.webp"

# ---------------------------------------------------------------- PARAMETRY
MERITKO = 18.3          # px podkladu na 1 m (z kót 53,006 m a 17,371 m)
PRUH = 6.5              # jízdní pruh / ulička u kolmého stání (ČSN 73 6056 min. 6,0 m)
STANI = (3.0, 5.5)      # kolmé parkovací stání š × d – velkorysé (ČSN min. 2,5 × 5,0)
STANI_ZTP = 4.0         # šířka vyhrazeného stání pro ZTP (ČSN min. 3,5)
VYSAVAC_STANI = 4.0     # blok 9,2 m = stání 4,0 + ostrůvek 1,2 (2 vysavače + fukar) + stání 4,0
OSTRUVEK = 1.2
VYSAVAC_HLOUBKA = 6.0
# typy stánku (š × h v m) podle sortimentu – viz průzkum v přehledu
STANKY = {
    "maly": (3.0, 2.5, "KAVÁRNA\nkáva, pečivo"),            # dřevěný stánek / kontejner 10 stop
    "stredni": (6.1, 2.5, "OBČERSTVENÍ\npříprava jídel"),   # kontejner 20 stop nebo food truck
    "velky": (12.2, 2.5, "BISTRO\nkuchyně, sklad, WC"),      # kontejner 40 stop
}
BOX_M, BOX_TECH = 5.55, 4.65   # šířky boxů – dohromady 32,4 m jako v podkladu
RADA_HLOUBKA = 6.512    # hloubka řady boxů (kóta 6,512 m)


def px(x, y):
    return (x / MERITKO, y / MERITKO)


# ---------------------------------------------------------------- rám řady boxů
P0 = px(750, 616.7)
_UHEL = math.atan(-0.0711)
U = (math.cos(_UHEL), math.sin(_UHEL))
V = (-math.sin(_UHEL), math.cos(_UHEL))
UHEL_DEG = math.degrees(_UHEL)


def g(u, v):
    return (P0[0] + u * U[0] + v * V[0], P0[1] + u * U[1] + v * V[1])


def obd(u1, v1, u2, v2):
    return [g(u1, v1), g(u2, v1), g(u2, v2), g(u1, v2)]


class Primka:
    def __init__(self, a, b):
        self.a, self.b = a, b

    def y(self, x):
        (x1, y1), (x2, y2) = self.a, self.b
        return y1 + (y2 - y1) * (x - x1) / (x2 - x1)

    def prusecik(self, p, d):
        """Průsečík s přímkou p + t·d."""
        (x1, y1), (x2, y2) = self.a, self.b
        e = (x2 - x1, y2 - y1)
        det = d[0] * (-e[1]) - d[1] * (-e[0])
        rx, ry = x1 - p[0], y1 - p[1]
        t = (rx * (-e[1]) - ry * (-e[0])) / det
        return t

    def v(self, u):
        """Souřadnice v, ve které přímka protne kolmici na řadu v místě u."""
        return self.prusecik(g(u, 0), V)

    def s(self, other):
        t = other.prusecik(self.a, (self.b[0] - self.a[0], self.b[1] - self.a[1]))
        return (self.a[0] + t * (self.b[0] - self.a[0]), self.a[1] + t * (self.b[1] - self.a[1]))


# ---------------------------------------------------------------- pozemek (z podkladu)
LEVA_X = 131 / MERITKO                         # černá čára = budoucí opěrná zeď (hranice)
ZED = Primka(px(360, 272.5), px(1440, 285))    # hnědá opěrná zeď – jižní líc
JIH = Primka(px(110, 840.5), px(1400, 748.5))  # navržený kraj silnice = jižní hranice
VYCHOD = Primka(px(1405, 392), px(1430, 746))  # východní hranice (červená)
CERVENA_SEVER = Primka(px(400, 462.5), px(1300, 398.5))  # okraj plochy v současném návrhu
ZED_ZAPAD_X = 360 / MERITKO
VJEZD_Y = 258 / MERITKO
HRANA_X = LEVA_X + 0.3

POZEMEK = [
    (HRANA_X, VJEZD_Y),
    (ZED_ZAPAD_X, VJEZD_Y),
    (ZED_ZAPAD_X, ZED.y(ZED_ZAPAD_X)),
    ZED.s(VYCHOD),
    VYCHOD.s(JIH),
    (HRANA_X, JIH.y(HRANA_X)),
]

RADA_KONEC = 5 * BOX_M + BOX_TECH
H2 = RADA_HLOUBKA / 2
VYS_V = (-3.18, 2.34)                  # blok vysavačů (podklad: 5,5 m, mírně k severu)
VYS_A, PLAC, VYS_B = (-25.84, -16.64), (-16.64, -9.21), (-9.21, 0.0)
BLOK = 2 * VYSAVAC_STANI + OSTRUVEK
VYS_NOVE = (-H2, -H2 + VYSAVAC_HLOUBKA)  # ve variantách líc v ose s boxy, hloubka 6 m
SEVER_PRUH = -H2 - PRUH                # severní hrana výjezdového pruhu


def v_zed(u):
    return ZED.v(u)


def v_jih(u):
    return JIH.v(u)


# ---------------------------------------------------------------- prvky výkresu
STYL = {
    "plocha":  'fill="#ececea" stroke="none"',
    "site":    'fill="url(#srafa-site)" stroke="#c8a400" stroke-width="0.08" stroke-dasharray="0.4 0.25"',
    "box":     'fill="#e3e1b0" stroke="#a5161b" stroke-width="0.22"',
    "tech":    'fill="#cf9a45" stroke="#a5161b" stroke-width="0.22"',
    "vysavac": 'fill="#d9c6f2" stroke="#7a3fc2" stroke-width="0.1"',
    "ostruvek": 'fill="#bdbdb8" stroke="#6b6b6b" stroke-width="0.08"',
    "plac":    'fill="#cfe8c4" stroke="#4a9a3a" stroke-width="0.1"',
    "stani":   'fill="#ffffff" stroke="#6b6b6b" stroke-width="0.08"',
    "ztp":     'fill="#dbe8f7" stroke="#2f6db5" stroke-width="0.1"',
    "kiosk":   'fill="#f39a3a" stroke="#8a4a10" stroke-width="0.15"',
    "terasa":  'fill="#f3e2c3" stroke="#b08a50" stroke-width="0.1"',
    "zelen":   'fill="#b9dca5" stroke="#6aa24f" stroke-width="0.06"',
    "prechod": 'fill="url(#zebra)" stroke="none"',
    "stanek":  'fill="url(#srafa-stanek)" stroke="#999" stroke-width="0.06" stroke-dasharray="0.3 0.2"',
}
PEVNE = {"box", "tech", "vysavac", "ostruvek", "plac", "stani", "ztp", "kiosk", "terasa", "zelen"}
STAVBY = {"box", "tech", "kiosk"}


class Vykres:
    def __init__(self, kod, nazev, popis):
        self.kod, self.nazev, self.popis = kod, nazev, popis
        self.prvky = []       # (druh, polygon, popisek, velikost písma)
        self.polohy = {}      # index prvku → vlastní poloha popisku
        self.sipky = []       # (druh, body)
        self.koty = []        # (a, b, text)
        self.znacky = []      # svg fragmenty (stoly, zařízení…)
        self.texty = []       # (bod, text, velikost, barva)
        self.plusy, self.minusy = [], []
        self.stolu = 0
        self.stanek = None

    def prvek(self, druh, body, popisek="", pismo=0.75, poloha=None):
        self.prvky.append((druh, body, popisek, pismo))
        self.polohy[len(self.prvky) - 1] = poloha

    def rect(self, druh, u1, v1, u2, v2, popisek="", pismo=0.75, poloha_uv=None):
        self.prvek(druh, obd(u1, v1, u2, v2), popisek, pismo, g(*poloha_uv) if poloha_uv else None)

    def sipka(self, druh, body):
        self.sipky.append((druh, body))

    def kota(self, a, b, text=None):
        d = math.dist(a, b)
        self.koty.append((a, b, text or f"{d:.2f}".replace(".", ",")))

    def kota_v(self, u, v1, v2):
        self.kota(g(u, v1), g(u, v2))

    def kota_u(self, u1, u2, v):
        self.kota(g(u1, v), g(u2, v))

    def retez_u(self, body_u, v):
        for a, b in zip(body_u, body_u[1:]):
            self.kota_u(a, b, v)

    def retez_v(self, u, body_v):
        for a, b in zip(body_v, body_v[1:]):
            self.kota_v(u, a, b)

    def text(self, bod, text, velikost=0.8, barva="#333"):
        self.texty.append((bod, text, velikost, barva))

    # --- skládané prvky
    def rada_boxu(self):
        u = 0.0
        for i, (nazev, sirka) in enumerate(
            [("M1", BOX_M), ("M2", BOX_M), ("TECH\nBOX", BOX_TECH), ("M3", BOX_M), ("M4", BOX_M), ("M5", BOX_M)]
        ):
            self.rect("tech" if nazev.startswith("TECH") else "box", u, -H2, u + sirka, H2, nazev, 1.0)
            if not nazev.startswith("TECH"):
                self.sipka("pruchod", [g(u + sirka / 2, 2.4), g(u + sirka / 2, -2.4)])
            u += sirka

    def blok_vysavacu(self, u1, u2, v1, v2, k_severu=True, koty=False):
        """Blok: stání | ostrůvek se 2 vysavači a fukarem | stání. Vjezd ze severu (nebo z jihu)."""
        s = (u2 - u1 - OSTRUVEK) / 2
        if koty:
            zadni = v2 + 0.7 if k_severu else v1 - 0.7
            self.retez_u([u1, u1 + s, u1 + s + OSTRUVEK, u2], zadni)
            self.kota_v(u1 - 0.6, v1, v2)
        self.rect("vysavac", u1, v1, u1 + s, v2, "stání\nu vysavače", 0.5)
        self.rect("vysavac", u2 - s, v1, u2, v2, "stání\nu vysavače", 0.5)
        o1, o2 = u1 + s, u1 + s + OSTRUVEK
        ov1, ov2 = (v1 + 1.0, v2) if k_severu else (v1, v2 - 1.0)
        self.rect("ostruvek", o1 + 0.1, ov1, o2 - 0.1, ov2)
        zad, cel = (ov2, ov1) if k_severu else (ov1, ov2)
        for t in (0.3, 0.62):
            x, y = g((o1 + o2) / 2, zad + (cel - zad) * t)
            self.znacky.append(f'<circle cx="{x:.3f}" cy="{y:.3f}" r="0.36" fill="#7a3fc2"/>')
        x, y = g((o1 + o2) / 2, zad + (cel - zad) * 0.08)
        self.znacky.append(
            f'<rect x="{x - 0.32:.3f}" y="{y - 0.32:.3f}" width="0.64" height="0.64" fill="#1f6fd1" '
            f'transform="rotate({UHEL_DEG:.2f} {x:.3f} {y:.3f})"/>'
        )

    def stani_rada(self, u_od, u_do, v1, v2, ztp_na_konci=False, ztp_na_zacatku=False, kota_v=None,
                   hloubka_na_zacatku=False):
        """Řada kolmých stání v pásu u_od–u_do; vrací počet. kota_v = kde okótovat první stání."""
        sirky = []
        zbyva = u_do - u_od
        if ztp_na_zacatku or ztp_na_konci:
            zbyva -= STANI_ZTP
        n = int(zbyva // STANI[0] + 1e-9)
        sirky = [STANI[0]] * n
        if ztp_na_zacatku:
            sirky.insert(0, STANI_ZTP)
        if ztp_na_konci:
            sirky.append(STANI_ZTP)
        u = u_od
        for s in sirky:
            ztp = s == STANI_ZTP
            self.rect("ztp" if ztp else "stani", u, v1, u + s, v2, "♿" if ztp else "P", 0.9 if ztp else 0.7)
            u += s
        if kota_v is not None and sirky:
            hrany = [u_od]
            for s in sirky[:3]:
                hrany.append(hrany[-1] + s)
            self.retez_u(hrany, kota_v)
            self.kota_v(u_od + 0.6 if hloubka_na_zacatku else u + 0.6, v1, v2)
        return len(sirky)

    def stoly(self, body_uv):
        for u, v in body_uv:
            x, y = g(u, v)
            self.znacky.append(f'<circle cx="{x:.3f}" cy="{y:.3f}" r="0.45" fill="#fff" stroke="#8a6a3a" stroke-width="0.07"/>')
            for du, dv in ((0.75, 0), (-0.75, 0), (0, 0.75), (0, -0.75)):
                cx, cy = g(u + du, v + dv)
                self.znacky.append(f'<circle cx="{cx:.3f}" cy="{cy:.3f}" r="0.2" fill="#8a6a3a"/>')
        self.stolu += len(body_uv)

    def kiosk(self, u1, v_sever, typ):
        """Stánek daného typu, okénko na jižní straně; vrací (u2, v_jih)."""
        w, h, nazev = STANKY[typ]
        u2, vj = u1 + w, v_sever + h
        rozmer = f"{w:.1f} × {h:.1f} m".replace(".", ",")
        popisek = f"{nazev.split(chr(10))[0]}\n{rozmer}" if w < 4 else f"{nazev}\n{rozmer}"
        self.rect("kiosk", u1, v_sever, u2, vj, popisek, 0.48 if w < 4 else 0.65)
        okno = min(2.4, w - 1.0)
        for k in range(1 if w < 8 else 2):
            c = u1 + w * (k + 1) / (2 if w < 8 else 3)
            a, b = g(c - okno / 2, vj), g(c + okno / 2, vj)
            self.znacky.append(
                f'<line x1="{a[0]:.3f}" y1="{a[1]:.3f}" x2="{b[0]:.3f}" y2="{b[1]:.3f}" stroke="#fff" stroke-width="0.25"/>'
            )
        self.stanek = typ
        return u2, vj

    def prechod(self, u1, u2, v1, v2):
        self.prvek("prechod", obd(u1, v1, u2, v2))

    # --- metriky
    def pocty(self):
        c = {}
        for druh, *_ in self.prvky:
            c[druh] = c.get(druh, 0) + 1
        terasa = sum(plocha(b) for d, b, *_ in self.prvky if d == "terasa")
        return {
            "parkovani": c.get("stani", 0) + c.get("ztp", 0),
            "ztp": c.get("ztp", 0),
            "vysavace": c.get("vysavac", 0),
            "mist_k_sezeni": self.stolu * 4,
            "terasa_m2": round(terasa),
            "kiosk": c.get("kiosk", 0),
        }


# ---------------------------------------------------------------- geometrie a kontroly
def plocha(poly):
    s = 0.0
    for i in range(len(poly)):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % len(poly)]
        s += x1 * y2 - x2 * y1
    return abs(s) / 2


def uvnitr(bod, poly, tol=0.05):
    x, y = bod
    for i in range(len(poly)):  # tolerance na hraně
        a, b = poly[i], poly[(i + 1) % len(poly)]
        if vzdalenost_k_usecce(bod, a, b) <= tol:
            return True
    c = False
    for i in range(len(poly)):
        (x1, y1), (x2, y2) = poly[i], poly[(i + 1) % len(poly)]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            c = not c
    return c


def vzdalenost_k_usecce(p, a, b):
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    t = max(0, min(1, ((p[0] - ax) * dx + (p[1] - ay) * dy) / (dx * dx + dy * dy)))
    return math.dist(p, (ax + t * dx, ay + t * dy))


def prekryv(p, q, tol=0.03):
    """SAT pro konvexní polygony; dotyk hranou se nepočítá."""
    for poly in (p, q):
        for i in range(len(poly)):
            a, b = poly[i], poly[(i + 1) % len(poly)]
            n = (b[1] - a[1], a[0] - b[0])
            ln = math.hypot(*n)
            n = (n[0] / ln, n[1] / ln)
            pp = [x * n[0] + y * n[1] for x, y in p]
            qq = [x * n[0] + y * n[1] for x, y in q]
            if max(pp) <= min(qq) + tol or max(qq) <= min(pp) + tol:
                return False
    return True


def zona_siti():
    u1 = RADA_KONEC + 0.15
    return [g(u1, v_zed(u1)), ZED.s(VYCHOD), VYCHOD.s(JIH), g(u1, v_jih(u1))]


def kontroly(vk):
    chyby = []
    pevne = [(d, b, p) for d, b, p, _ in vk.prvky if d in PEVNE]
    for d, b, p in pevne:
        if not all(uvnitr(x, POZEMEK) for x in b):
            chyby.append(f"{d} „{p.strip()}“ přesahuje pozemek")
        if d in STAVBY | {"terasa"} and prekryv(b, zona_siti()):
            chyby.append(f"{d} „{p.strip()}“ zasahuje do pásma sítí")
    for i in range(len(pevne)):
        for j in range(i + 1, len(pevne)):
            if prekryv(pevne[i][1], pevne[j][1]):
                chyby.append(f"překryv: {pevne[i][0]} × {pevne[j][0]}")
    return chyby


# ---------------------------------------------------------------- společné části
def zaklad(vk, sever_pruh_obousmerny=False):
    vk.rada_boxu()
    # vjezd → západní pruh → jižní pruh → boxy
    vk.sipka("mycka", [(10.0, VJEZD_Y + 0.6), (10.4, 33.5), g(-23.0, 6.1), g(30.5, 6.1)])
    vk.sipka("mycka", [g(31.0, -6.2), g(-23.0, -6.2), (14.2, 27.0), (14.6, VJEZD_Y + 0.6)])
    vk.text(((HRANA_X + ZED_ZAPAD_X) / 2, VJEZD_Y - 0.5), "VJEZD / VÝJEZD  z místní komunikace", 0.8, "#1f4e8c")
    if sever_pruh_obousmerny:
        vk.text(g(22.0, -H2 - 0.7), f"ulička {PRUH:.1f} m – obousměrně".replace(".", ","), 0.6, "#1f4e8c")
    # boxy: šířky, celková délka, hloubka; pásmo sítí; šířka vjezdu
    hrany, u = [0.0], 0.0
    for sirka in (BOX_M, BOX_M, BOX_TECH, BOX_M, BOX_M, BOX_M):
        u += sirka
        hrany.append(u)
    vk.retez_u(hrany, H2 + 0.8)
    vk.kota_u(0.0, RADA_KONEC, H2 + 1.8)
    vk.kota_v(RADA_KONEC + 0.9, -H2, H2)
    u_vychod = VYCHOD.prusecik(g(0, H2 + 3.0), U)
    vk.kota_u(RADA_KONEC, u_vychod, H2 + 3.0)
    vk.kota((HRANA_X, VJEZD_Y + 1.4), (ZED_ZAPAD_X, VJEZD_Y + 1.4))


def koty_pruhu(vk, vys_v=VYS_V, zapad_u=VYS_A[0], u_sever=16.0, u_vys=-2.0):
    vk.kota_v(u_sever + 2.0, H2, v_jih(u_sever + 2.0))
    vk.kota_v(u_vys, vys_v[1], v_jih(u_vys))
    a = g(zapad_u, 0)
    vk.kota((HRANA_X, a[1]), a)


def ostruvek_s_totemem(vk):
    """Uvolněný západní konec ostrova: zeleň s cenovým totemem, větší poloměr zatáčky."""
    vk.rect("zelen", -24.5, VYS_NOVE[0] + 0.8, -2 * BLOK - 0.6, VYS_NOVE[1] - 0.8, "zeleň\ntotem s ceníkem", 0.5)


def blok_vysavacu_ostrov(vk, koty=False):
    """Oba bloky vedle sebe u boxů, bez volného placu."""
    vk.blok_vysavacu(-2 * BLOK, -BLOK, *VYS_NOVE, koty=koty)
    vk.blok_vysavacu(-BLOK, 0.0, *VYS_NOVE)
    ostruvek_s_totemem(vk)


def stanek_u_vjezdu(vk, typ, konec_terasy, prechod_u):
    """Stánek u zdi hned u vjezdu, terasa s pergolou před ním, zeleň a přechod k uličce."""
    vs = max(v_zed(-20.5), v_zed(konec_terasy)) + 0.4
    u2, vj = vk.kiosk(-20.5, vs, typ)
    if u2 < konec_terasy - 0.5:
        vk.rect("zelen", u2 + 0.3, max(v_zed(u2), v_zed(konec_terasy)) + 0.3, konec_terasy, vj, "zeleň / sklad", 0.55)
    vk.rect("terasa", -20.5, vj, konec_terasy, SEVER_PRUH - 1.0, "terasa s pergolou", 0.6,
            ((-20.5 + konec_terasy) / 2, SEVER_PRUH - 1.6))
    hloubka = SEVER_PRUH - 1.0 - vj
    rady = (vj + 1.5, vj + 3.9) if hloubka >= 5.4 else (vj + 1.6,)
    sloupce = [-18.9 + 2.9 * i for i in range(6) if -18.9 + 2.9 * i < konec_terasy - 1.2]
    vk.stoly([(u, v) for u in sloupce for v in rady])
    vk.rect("zelen", -20.5, SEVER_PRUH - 1.0, prechod_u - 1.0, SEVER_PRUH - 0.1)
    vk.rect("zelen", prechod_u + 1.0, SEVER_PRUH - 1.0, konec_terasy, SEVER_PRUH - 0.1)
    vk.prechod(prechod_u - 1.0, prechod_u + 1.0, SEVER_PRUH, VYS_NOVE[0])
    # kóty: zeď → stánek → terasa → zeleň → ulička; šířka terasy
    vk.retez_v(-21.1, [v_zed(-21.1), vs, vj, SEVER_PRUH - 1.0, SEVER_PRUH])
    vk.kota_u(-20.5, konec_terasy, SEVER_PRUH + 0.6)
    return vs, vj


TXT_PRUH = f"{PRUH:.1f}".replace(".", ",")


# ---------------------------------------------------------------- VARIANTY
def varianta_1():
    vk = Vykres("V1", "Parkování u vjezdu, stánek uprostřed",
                "Malá kavárna 3,0 × 2,5 m (káva, pečivo) naproti vysavačům, hosté parkují v kapse u vjezdu.")
    zaklad(vk, sever_pruh_obousmerny=False)
    blok_vysavacu_ostrov(vk, koty=True)
    # parkovací kapsa podél zdi u vjezdu (auta čelem ke zdi)
    pocet, hrany, cela = 0, [-21.0], []
    u = -21.0
    for s_ in (STANI[0],) * 3 + (STANI_ZTP,):
        vz = max(v_zed(u), v_zed(u + s_)) + 0.3
        ztp = s_ == STANI_ZTP
        vk.rect("ztp" if ztp else "stani", u, vz, u + s_, vz + STANI[1], "♿" if ztp else "P", 0.9 if ztp else 0.7)
        if pocet == 0:
            vk.kota_v(u - 0.6, vz, vz + STANI[1])
        u += s_
        hrany.append(u)
        cela.append(vz + STANI[1])
        pocet += 1
    vk.retez_u(hrany, max(cela) + 0.6)
    kapsa_konec = u
    # malý stánek (káva, pečivo) uprostřed terasy naproti východnímu bloku vysavačů
    t1, t2 = kapsa_konec + 0.8, kapsa_konec + 0.8 + 9.0
    vs = max(v_zed(t1), v_zed(t2)) + 0.4
    k1 = (t1 + t2 - STANKY["maly"][0]) / 2
    k2, vj = vk.kiosk(k1, vs, "maly")
    vk.rect("zelen", t1, vs, k1 - 0.3, vj)
    vk.rect("zelen", k2 + 0.3, vs, t2, vj)
    vk.rect("terasa", t1, vj, t2, SEVER_PRUH - 1.0, "terasa s pergolou", 0.6, ((t1 + t2) / 2, SEVER_PRUH - 1.6))
    vk.stoly([(u, vj + 1.6) for u in (t1 + 1.5, t1 + 4.5, t1 + 7.5)])
    prechod_u = -BLOK + VYSAVAC_STANI + OSTRUVEK / 2       # proti ostrůvku východního bloku
    vk.rect("zelen", t1, SEVER_PRUH - 1.0, prechod_u - 1.0, SEVER_PRUH - 0.1)
    vk.rect("zelen", prechod_u + 1.0, SEVER_PRUH - 1.0, t2, SEVER_PRUH - 0.1)
    vk.prechod(prechod_u - 1.0, prechod_u + 1.0, SEVER_PRUH, VYS_NOVE[0])
    vk.retez_v(t2 + 0.4, [v_zed(t2 + 0.4), vs, vj, SEVER_PRUH - 1.0, SEVER_PRUH])
    vk.kota_u(t1, t2, SEVER_PRUH + 0.6)
    pocet += vk.stani_rada(t2 + 0.8, 31.0, SEVER_PRUH - STANI[1], SEVER_PRUH, kota_v=SEVER_PRUH + 0.6)
    vk.sipka("host", [(12.0, VJEZD_Y + 0.6), (12.8, 24.0), g(-15.5, -12.6)])
    vk.sipka("pesi", [g(-14.0, -13.6), g(t1 + 1.0, vj + 0.8)])
    vk.sipka("pesi", [g(prechod_u, -2.0), g(prechod_u, SEVER_PRUH - 0.4)])
    koty_pruhu(vk, VYS_NOVE, -24.5)
    vk.kota_v(-17.0, -H2, SEVER_PRUH)
    vk.kota_v(-17.5, SEVER_PRUH, v_zed(-17.5) + 0.3 + STANI[1])
    vk.plusy = [
        "Hosté stánku zaparkují v kapse hned u vjezdu a do provozu myčky nevjíždějí. Ulička podél boxů zůstává jednosměrná.",
        "Stánek s terasou je uprostřed, blízko vysavačů i boxů. Přechod od ostrůvku vede rovnou na terasu.",
        "Vysavače jsou pohromadě u boxů, auta k nim zajíždějí po cestě k výjezdu.",
        f"Celkem {pocet} velkorysých stání: 4 v kapse u vjezdu (z toho 1 ZTP) a zbytek podél zdi pro zákazníky myčky.",
    ]
    vk.minusy = [
        "Kapsa leží ve vyjížděcím pruhu u výjezdu. Kdo couvá z kapsy, kříží auta, která odjíždějí z myčky.",
        "Stánek není z vjezdu tak vidět jako stánek přímo u vjezdu, terasa je blíž hluku vysokotlakých pistolí.",
        "Malá kavárna (káva, pečivo, bez vaření) je nejlevnější na provoz a stačí jí 1 obsluha, ale teplé jídlo neudělá. Terasa je mělká (asi 4,8 m) s jednou řadou stolů.",
    ]
    return vk


def varianta_2():
    vk = Vykres("V2", "Vysavače naproti boxům",
                "Občerstvení 6,1 × 2,5 m (kontejner 20 stop) u vjezdu, z boxu rovně k vysavači, ostrov = parkoviště.")
    zaklad(vk, sever_pruh_obousmerny=True)
    # vysavače podél zdi naproti boxům M1–M3, vjezd z jihu (z uličky)
    v_vys = (SEVER_PRUH - VYSAVAC_HLOUBKA, SEVER_PRUH)
    vk.blok_vysavacu(0.6, 0.6 + BLOK, *v_vys, k_severu=False, koty=True)
    vk.blok_vysavacu(0.6 + BLOK, 0.6 + 2 * BLOK, *v_vys, k_severu=False)
    # ostrov: parkování čelem od uličky (vjezd ze severu)
    pocet = vk.stani_rada(VYS_A[0], -0.3, VYS_NOVE[0], VYS_NOVE[0] + STANI[1], ztp_na_konci=True,
                          kota_v=VYS_NOVE[0] - 0.6, hloubka_na_zacatku=True)
    stanek_u_vjezdu(vk, "stredni", -8.0, -11.4)
    pocet += vk.stani_rada(-7.4, 0.0, SEVER_PRUH - STANI[1], SEVER_PRUH, kota_v=SEVER_PRUH + 0.6)
    pocet += vk.stani_rada(0.6 + 2 * BLOK + 0.5, 31.0, SEVER_PRUH - STANI[1], SEVER_PRUH)
    vk.sipka("host", [(12.0, VJEZD_Y + 0.6), (12.6, 25.5), g(-14.0, -5.0)])
    vk.sipka("vysavac", [g(BOX_M * 0.5, -H2 + 0.3), g(0.6 + VYSAVAC_STANI / 2, SEVER_PRUH - 2.5)])
    koty_pruhu(vk, (VYS_NOVE[0], VYS_NOVE[0] + STANI[1]), VYS_A[0])
    vk.kota_v(16.0, -H2, SEVER_PRUH)
    vk.kota_v(22.0, SEVER_PRUH, v_zed(22.0))
    vk.plusy = [
        "Z boxu se jede rovně přes uličku do stání u vysavače, nemusí se zatáčet.",
        "Ostrov na západě je celý pro hosty stánku, stání jsou blízko stánku i vjezdu.",
        "Kontejner 20 stop (6,1 × 2,5 m) unese jednoduchou přípravu jídel (gril, fritéza, digestoř). Vedle zbývá místo na sklad a zeleň a místo něj může stát i food truck.",
        f"{pocet} velkorysých parkovacích stání a 4 stání u vysavačů (4 m). Vysavače jsou u zdi, dál od jižní silnice.",
    ]
    vk.minusy = [
        "Kdo couvá od vysavače, vjíždí do uličky, kterou právě vyjíždějí auta z boxů. Konflikt je přímo před výjezdy.",
        "Ulička je obousměrná, hosté jedou proti autům z myčky (krátký úsek, asi 25 m).",
        "Pěší z ostrova přecházejí uličku mezi zaparkovanými auty.",
    ]
    return vk


# ---------------------------------------------------------------- SVG
def podklad_png():
    im = Image.open(PODKLAD).convert("RGB")
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=72)
    return base64.b64encode(buf.getvalue()).decode(), im.size


def poly_d(body):
    return "M" + " L".join(f"{x:.3f},{y:.3f}" for x, y in body) + " Z"


def stred(body):
    return (sum(x for x, _ in body) / len(body), sum(y for _, y in body) / len(body))


def svg_text(bod, text, velikost, barva="#222", uhel=UHEL_DEG, tucne=False):
    radky = text.split("\n")
    x, y = bod
    y0 = -(len(radky) - 1) * velikost * 0.55
    vaha = ' font-weight="600"' if tucne else ""
    tsp = "".join(
        f'<tspan x="0" y="{y0 + i * velikost * 1.1:.3f}">{html.escape(r)}</tspan>' for i, r in enumerate(radky)
    )
    return (
        f'<text transform="translate({x:.3f},{y:.3f}) rotate({uhel:.2f})" font-size="{velikost}" fill="{barva}"'
        f' text-anchor="middle" dominant-baseline="middle"{vaha}>{tsp}</text>'
    )


SIPKY = {
    "mycka": ("#1f6fd1", "0.22", ""),
    "pruchod": ("#1f6fd1", "0.14", ""),
    "host": ("#e07b00", "0.2", ' stroke-dasharray="0.8 0.4"'),
    "pesi": ("#2e8b2e", "0.14", ' stroke-dasharray="0.3 0.25"'),
    "vysavac": ("#7a3fc2", "0.18", ""),
}


def svg(vk, png, velikost):
    W, H = 84.0, 59.4           # A3 na šířku v metrech při 1:200
    X0, Y0 = 2.0, 7.5
    o = [
        f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
        f'width="420mm" height="297mm" viewBox="{X0} {Y0} {W} {H}" font-family="Helvetica, Arial, sans-serif">',
        "<defs>",
        '<pattern id="srafa-site" width="0.6" height="0.6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
        '<rect width="0.6" height="0.6" fill="#fff8d6"/><line x1="0" y1="0" x2="0" y2="0.6" stroke="#e0c040" stroke-width="0.12"/></pattern>',
        '<pattern id="srafa-stanek" width="0.8" height="0.8" patternUnits="userSpaceOnUse" patternTransform="rotate(-45)">'
        '<rect width="0.8" height="0.8" fill="#f6f6f6"/><line x1="0" y1="0" x2="0" y2="0.8" stroke="#bbb" stroke-width="0.08"/></pattern>',
        f'<pattern id="zebra" width="0.5" height="1" patternUnits="userSpaceOnUse" patternTransform="rotate({UHEL_DEG:.2f})">'
        '<rect width="0.5" height="1" fill="#ececea"/><rect width="0.25" height="1" fill="#ffffff"/></pattern>',
    ]
    for druh, (barva, *_rest) in SIPKY.items():
        o.append(
            f'<marker id="hrot-{druh}" viewBox="0 0 10 10" refX="7" refY="5" markerWidth="4" markerHeight="4" orient="auto-start-reverse">'
            f'<path d="M0,0 L10,5 L0,10 z" fill="{barva}"/></marker>'
        )
    o.append("</defs>")
    o.append(f'<rect x="{X0}" y="{Y0}" width="{W}" height="{H}" fill="#ffffff"/>')
    o.append(
        f'<clipPath id="orez"><rect x="{X0}" y="{Y0}" width="{W}" height="{H - 9.8}"/></clipPath>'
        f'<g id="podklad" class="podklad" opacity="0.35" clip-path="url(#orez)"><image x="0" y="0" width="{velikost[0] / MERITKO:.3f}" '
        f'height="{velikost[1] / MERITKO:.3f}" xlink:href="data:image/jpeg;base64,{png}" href="data:image/jpeg;base64,{png}"/></g>'
    )
    o.append(f'<g id="plocha"><path d="{poly_d(POZEMEK)}" {STYL["plocha"]}/></g>')
    zs = zona_siti()
    o.append(f'<g id="site"><path d="{poly_d(zs)}" {STYL["site"]}/>')
    c = stred(zs)
    o.append(svg_text(c, "pásmo sítí\nnestavět", 0.6, "#8a7000", -90) + "</g>")
    o.append('<g id="prvky">')
    for druh, body, popisek, pismo in vk.prvky:
        o.append(f'<path d="{poly_d(body)}" {STYL[druh]}/>')
    o.extend(vk.znacky)
    for i, (druh, body, popisek, pismo) in enumerate(vk.prvky):
        if popisek:
            barva = "#fff" if druh == "kiosk" else "#222"
            o.append(svg_text(vk.polohy.get(i) or stred(body), popisek, pismo, barva, tucne=druh in {"box", "tech", "kiosk"}))
    o.append("</g>")
    # zdi a hranice
    zx2 = 1440 / MERITKO
    zed = [(ZED_ZAPAD_X, ZED.y(ZED_ZAPAD_X)), (zx2, ZED.y(zx2)), (zx2, 437 / MERITKO)]
    o.append('<g id="hranice">')
    o.append(
        f'<polyline points="{" ".join(f"{x:.3f},{y:.3f}" for x, y in zed)}" fill="none" stroke="#8b5a2b" '
        'stroke-width="0.7" stroke-linejoin="miter" transform="translate(0,-0.35)"/>'
    )
    o.append(
        f'<line x1="{LEVA_X:.3f}" y1="{VJEZD_Y:.3f}" x2="{LEVA_X:.3f}" y2="{JIH.y(LEVA_X) + 1:.3f}" stroke="#111" stroke-width="0.35"/>'
    )
    jz, jv = (LEVA_X - 1, JIH.y(LEVA_X - 1)), VYCHOD.s(JIH)
    o.append(f'<line x1="{jz[0]:.3f}" y1="{jz[1]:.3f}" x2="{jv[0]:.3f}" y2="{jv[1]:.3f}" stroke="#d01010" stroke-width="0.25"/>')
    vs, vj = ZED.s(VYCHOD), VYCHOD.s(JIH)
    o.append(f'<line x1="{vs[0]:.3f}" y1="{vs[1]:.3f}" x2="{vj[0]:.3f}" y2="{vj[1]:.3f}" stroke="#d01010" stroke-width="0.2"/>')
    o.append(svg_text((LEVA_X - 0.9, 30.0), "opěrná zeď / hranice", 0.65, "#111", -90))
    o.append(svg_text(((ZED_ZAPAD_X + zx2) / 2, ZED.y((ZED_ZAPAD_X + zx2) / 2) - 1.1), "opěrná zeď (hnědá) · místní komunikace za ní", 0.65, "#8b5a2b", 0.66))
    sx = 40.0
    o.append(svg_text((sx, JIH.y(sx) + 1.0), "navržený kraj silnice = jižní hranice", 0.65, "#d01010", math.degrees(math.atan(-0.0713))))
    o.append("</g>")
    # šipky
    o.append('<g id="provoz">')
    for druh, body in vk.sipky:
        barva, sirka, extra = SIPKY[druh]
        o.append(
            f'<polyline points="{" ".join(f"{x:.3f},{y:.3f}" for x, y in body)}" fill="none" stroke="{barva}" '
            f'stroke-width="{sirka}" stroke-linejoin="round"{extra} marker-end="url(#hrot-{druh})"/>'
        )
    for bod, text, vel, barva in vk.texty:
        o.append(svg_text(bod, text, vel, barva, 0))
    o.append("</g>")
    # kóty
    o.append('<g id="koty">')
    for a, b, text in vk.koty:
        o.append(f'<line x1="{a[0]:.3f}" y1="{a[1]:.3f}" x2="{b[0]:.3f}" y2="{b[1]:.3f}" stroke="#000" stroke-width="0.05"/>')
        d = (b[0] - a[0], b[1] - a[1])
        ln = math.hypot(*d)
        n = (-d[1] / ln * 0.35, d[0] / ln * 0.35)
        for p in (a, b):
            o.append(f'<line x1="{p[0] - n[0]:.3f}" y1="{p[1] - n[1]:.3f}" x2="{p[0] + n[0]:.3f}" y2="{p[1] + n[1]:.3f}" stroke="#000" stroke-width="0.07"/>')
        uh = math.degrees(math.atan2(d[1], d[0]))
        if uh > 90 or uh < -90:
            uh += 180
        m = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
        o.append(
            f'<g transform="translate({m[0]:.3f},{m[1]:.3f}) rotate({uh:.2f})">'
            f'<rect x="{-(0.27 * len(text) + 0.3) / 2:.3f}" y="-0.8" width="{0.27 * len(text) + 0.3:.3f}" height="0.56" rx="0.25" fill="#fff" opacity="0.92"/>'
            f'<text y="-0.5" font-size="0.48" text-anchor="middle" dominant-baseline="middle">{text}</text></g>'
        )
    o.append("</g>")
    # rohové razítko + legenda
    o.append(rohove_razitko(vk, X0, Y0, W, H))
    o.append("</svg>")
    return "\n".join(o)


def rohove_razitko(vk, X0, Y0, W, H):
    y = Y0 + H - 9.6
    o = ['<g id="razitko">']
    o.append(f'<line x1="{X0 + 1}" y1="{y}" x2="{X0 + W - 1}" y2="{y}" stroke="#999" stroke-width="0.05"/>')
    o.append(svg_text((X0 + 1.2, y + 1.6), f"{vk.kod} – {vk.nazev}", 1.3, "#111", 0, True).replace('text-anchor="middle"', 'text-anchor="start"'))
    o.append(svg_text((X0 + 1.2, y + 3.2), vk.popis, 0.7, "#444", 0).replace('text-anchor="middle"', 'text-anchor="start"'))
    p = vk.pocty()
    radek = (f"Parkování {p['parkovani']} (ZTP {p['ztp']}) · stání u vysavačů {p['vysavace']} · "
             f"místa k sezení {p['mist_k_sezeni']} · terasa {p['terasa_m2']} m²")
    o.append(svg_text((X0 + 1.2, y + 4.6), radek, 0.7, "#444", 0).replace('text-anchor="middle"', 'text-anchor="start"'))
    o.append(svg_text((X0 + 1.2, y + 6.0), "Kóty v metrech · samoobslužné mycí centrum · studie rozmístění · 1:200 na A3 · podklad z Affinity, přesnost ±0,3 m · 23. 10. 2026", 0.55, "#777", 0).replace('text-anchor="middle"', 'text-anchor="start"'))
    # legenda
    lx, ly = X0 + 40.0, y + 1.0
    polozky = [
        ("box", "mycí box"), ("vysavac", "stání u vysavače"), ("ostruvek", "ostrůvek: ● vysavač ■ fukar"), ("stani", "parkovací stání"), ("ztp", "stání ZTP"),
        ("kiosk", "stánek"), ("terasa", "terasa / posezení"), ("zelen", "zeleň"), ("site", "pásmo sítí"),
    ]
    for i, (druh, txt) in enumerate(polozky):
        cx, cy = lx + (i // 4) * 10.0, ly + (i % 4) * 1.4
        o.append(f'<rect x="{cx}" y="{cy}" width="1.4" height="0.9" {STYL[druh]}/>')
        o.append(f'<text x="{cx + 1.8}" y="{cy + 0.7}" font-size="0.6" fill="#333">{txt}</text>')
    for i, (druh, txt) in enumerate([("mycka", "jízda myčkou"), ("host", "host stánku"), ("pesi", "pěší"), ("vysavac", "k vysavači")]):
        barva, sirka, extra = SIPKY[druh]
        cx, cy = lx + 30.0, ly + i * 1.4 + 0.45
        o.append(f'<line x1="{cx}" y1="{cy}" x2="{cx + 2.2}" y2="{cy}" stroke="{barva}" stroke-width="{sirka}"{extra} marker-end="url(#hrot-{druh})"/>')
        o.append(f'<text x="{cx + 3.0}" y="{cy + 0.25}" font-size="0.6" fill="#333">{txt}</text>')
    # severka
    sx, sy = X0 + W - 3.0, Y0 + 3.0
    o.append(f'<path d="M{sx},{sy - 1.5} L{sx + 0.7},{sy + 0.8} L{sx},{sy + 0.3} L{sx - 0.7},{sy + 0.8} Z" fill="#111"/>')
    o.append(f'<text x="{sx}" y="{sy - 1.9}" font-size="0.8" text-anchor="middle">S</text>')
    o.append("</g>")
    return "\n".join(o)


# ---------------------------------------------------------------- přehled HTML
def stanek_popis(typ):
    if not typ:
        return "–"
    w, h, nazev = STANKY[typ]
    return f"{nazev.split(chr(10))[0].capitalize()} {w:.1f} × {h:.1f} m".replace(".", ",")


def prehled(vykresy, svgs, chyby):
    radky = []
    for vk in vykresy:
        p = vk.pocty()
        radky.append(
            f"<tr><td><b>{vk.kod}</b> {html.escape(vk.nazev)}</td><td>{p['parkovani']} ({p['ztp']} ZTP)</td>"
            f"<td>{p['vysavace']}</td><td>{p['mist_k_sezeni'] or '–'}</td><td>{p['terasa_m2'] or '–'}</td>"
            f"<td>{html.escape(stanek_popis(vk.stanek))}</td></tr>"
        )
    karty = []
    for vk, s in zip(vykresy, svgs):
        s = s.replace('width="420mm" height="297mm"', 'width="100%"')
        ch = chyby[vk.kod]
        kontrola = (
            '<p class="ok">Kontrola: všechny prvky jsou uvnitř pozemku, nepřekrývají se a stavby nezasahují do pásma sítí.</p>'
            if not ch else "<p class='chyba'>Kontrola: " + "; ".join(map(html.escape, ch)) + "</p>"
        )
        karty.append(
            f'<section id="{vk.kod}"><h2>{vk.kod} – {html.escape(vk.nazev)}</h2><p class="popis">{html.escape(vk.popis)} '
            f'<a href="{html.escape(vk.soubor)}" download>Stáhnout výkres (SVG, A3)</a></p>'
            f'<div class="vykres">{s}</div><div class="hodnoceni"><div><h3>Plusy</h3><ul>'
            + "".join(f"<li>{html.escape(x)}</li>" for x in vk.plusy)
            + "</ul></div><div><h3>Minusy a rizika</h3><ul>"
            + "".join(f"<li>{html.escape(x)}</li>" for x in vk.minusy)
            + f"</ul></div></div>{kontrola}</section>"
        )
    return f"""<!doctype html><html lang="cs"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>Mycí centrum – varianty</title>
<style>
:root{{--bg:#fafaf8;--fg:#1d1d1b;--muted:#5d5d58;--line:#dcdcd6;--card:#fff}}
body{{margin:0;background:var(--bg);color:var(--fg);font:15px/1.5 -apple-system,Helvetica,Arial,sans-serif}}
main{{max-width:1180px;margin:0 auto;padding:24px 16px 64px}}
h1{{font-size:26px;margin:0 0 4px}} h2{{font-size:20px;margin:0 0 4px}} h3{{font-size:14px;margin:0 0 4px;text-transform:uppercase;letter-spacing:.04em;color:var(--muted)}}
.popis,.muted{{color:var(--muted);margin:0 0 12px}}
section{{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:18px;margin:20px 0}}
.vykres svg{{display:block;height:auto;border:1px solid var(--line);border-radius:6px}}
.hodnoceni{{display:grid;grid-template-columns:1fr 1fr;gap:20px;margin-top:14px}}
@media (max-width:760px){{.hodnoceni{{grid-template-columns:1fr}}}}
ul{{margin:0;padding-left:18px}} li{{margin:3px 0}}
table{{border-collapse:collapse;width:100%;background:var(--card)}} td,th{{border-bottom:1px solid var(--line);padding:7px 10px;text-align:left}}
th{{font-size:13px;color:var(--muted);font-weight:600}}
.ok{{color:#2e7d32;font-size:13px;margin:12px 0 0}} .chyba{{color:#b3261e;font-size:13px;margin:12px 0 0}}
label{{font-size:14px;user-select:none}}
body.bez-podkladu .podklad{{display:none}}
</style></head><body><main>
<h1>Samoobslužné mycí centrum – varianty rozmístění</h1>
<p class="muted">Studie nad plánkem z Affinity (1:200 na A3). Boxy M1–M5 a TECH BOX zůstávají na místě,
mění se vysavače, stánek, terasa a parkování. Rozměry jsou odměřené z obrázku s přesností asi ±0,3 m.</p>
<label><input type="checkbox" id="pk" checked> zobrazit původní plánek pod výkresem</label>
<h2 style="margin-top:20px">Srovnání</h2>
<table><tr><th>Varianta</th><th>Parkovací stání</th><th>Stání u vysavačů</th><th>Místa k sezení</th><th>Terasa m²</th><th>Stánek</th></tr>
{''.join(radky)}</table>
{''.join(karty)}
<section><h2>Průzkum: jak velký stánek na co</h2>
<p class="muted">Přehled běžných velikostí podle toho, co se ve stánku prodává. Rozměry jsou vnější (půdorys na pozemku).</p>
<table><tr><th>Typ</th><th>Rozměr</th><th>Plocha</th><th>Na co se hodí</th><th>Ve variantě</th></tr>
<tr><td>Dřevěný prodejní stánek / bouda</td><td>1,5 × 2,6 až 1,8 × 3,4 m; 3,0 × 2,0–2,5 m</td><td>4–8 m²</td><td>káva, pečivo, balené zboží – bez vaření, 1 obsluha</td><td>–</td></tr>
<tr><td>Kontejner 10 stop</td><td>3,0 × 2,44 m</td><td>~7 m²</td><td>malá kavárna, pekařský stánek, zmrzlina</td><td><b>V1</b> (3,0 × 2,5 m)</td></tr>
<tr><td>Food truck / přívěs</td><td>4,9–7,3 × 2,1–2,4 m (např. 5,93 × 2,08 m)</td><td>10–17 m²</td><td>street food s přípravou, dá se odvézt (zimní sezóna)</td><td>alternativa ke V2</td></tr>
<tr><td>Kontejner 20 stop</td><td>6,06 × 2,44 m (uvnitř 5,9 × 2,35 m)</td><td>~15 m²</td><td>rychlé občerstvení s přípravou: gril, fritéza, digestoř, dřez, 1–2 obsluha</td><td><b>V2</b> (6,1 × 2,5 m)</td></tr>
<tr><td>Kontejner 40 stop nebo 2× 20 stop</td><td>12,2 × 2,44 m nebo ~6,1 × 4,9 m</td><td>~30 m²</td><td>bistro: kuchyně, sklad, mytí nádobí, WC pro personál, víc obsluhy</td><td>– (vejde se na místo stánku ve V2)</td></tr>
</table>
<h3 style="margin-top:14px">Na co si dát pozor</h3><ul>
<li><b>Hygiena:</b> vyhláška 137/2004 Sb. má dnes většinu požadavků na provozovny zrušenou a řídí se hlavně předpisy EU. Kde se jídlo připravuje, počítejte s tekoucí teplou i studenou vodou, umyvadlem na ruce, odpadní vodou a chlazením. Konkrétní požadavky, včetně WC pro hosty u posezení, je potřeba odsouhlasit s krajskou hygienickou stanicí. Jednoznačný limit jsem nenašel. Jedna možnost je zpřístupnit hostům WC v TECH BOXu.</li>
<li><b>Stavební zákon:</b> drobné stavby do 40 m² (dřív 25 m²) jsou bez povolení jen za podmínek, mezi které nepatří podnikání (stanovisko MMR). Pevný stánek je proto rozumné počítat s povolením. Food truck se jako stavba nepovoluje, ale řeší se jeho stání a provozovna.</li>
<li><b>Přípojky:</b> bistro a stánek s přípravou potřebují elektřinu s vyšším příkonem, vodu a kanalizaci. Myčka je bude mít v TECH BOXu, takže je výhodné vést je k němu.</li>
</ul>
<p class="muted" style="font-size:13px">Zdroje: <a href="https://zlin.eu/file/6a902b949093704ff00edc68">zlin.eu – adventní stánky</a> ·
<a href="https://www.tuin.co.uk/pop-up-market-stall.html">Gadero – stánek 3 × 2 m</a> ·
<a href="https://kontainerindonesia.co.id/en/modified-containers/canteen-container/">kontejnerová kantýna 20 stop</a> ·
<a href="https://www.finn.no/379169610">food truck Renault Master</a> ·
<a href="https://hzscr.gov.cz/soubor/kku-kontejner-kuchyne-pdf.aspx">HZS – kuchyně ze 2 kontejnerů</a> ·
<a href="https://www.zakonyprolidi.cz/cs/2004-137">vyhláška 137/2004 Sb.</a> ·
<a href="https://www.estav.cz/cz/13032.pravni-aspekty-a-stavebni-povoleni-pro-montovane-stavby">estav.cz – drobné stavby</a> ·
<a href="https://mmr.gov.cz/getmedia/b487e588-beb8-431c-8119-56881bf2719b/MMR-37467-25-31-ze-dne-13-5-2025.pdf.aspx?ext=.pdf">MMR – stavba k prodeji</a></p>
</section>
<section><h2>Předpoklady</h2><ul>
<li>Plocha mezi hnědou opěrnou zdí a boxy je ve stejné úrovni jako myčka (kóty 415,7–416,2), červená čára nahoře je jen okraj plochy v původním návrhu.</li>
<li>Blok „2 vysavače a fukar“ (9,2 m) = stání 4,0 m + ostrůvek 1,2 m se 2 vysavači a fukarem + stání 4,0 m, hloubka 6,0 m.</li>
<li>Velkorysá stání: parkování 3,0 × 5,5 m, ZTP 4,0 × 5,5 m, ulička 6,5 m (ČSN 73 6056 vyžaduje min. 2,5 × 5,0 m, ZTP 3,5 m, uličku 6,0 m). U 2–20 stání aspoň jedno pro ZTP.</li>
<li>Stánek je v každé variantě jiné velikosti (viz průzkum níže), výdejní okénko vždy k terase.</li>
<li>Pásmo sítí = pruh mezi koncem řady boxů a východní hranicí. Dá se přes něj jezdit, ale nesmí se na něm stavět.</li>
</ul></section>
</main><script>
document.getElementById('pk').addEventListener('change',e=>document.body.classList.toggle('bez-podkladu',!e.target.checked));
</script></body></html>"""


def main():
    VYSTUP.mkdir(exist_ok=True)
    png, velikost = podklad_png()
    vykresy = [varianta_1(), varianta_2()]
    for stary in VYSTUP.glob("varianta-*.svg"):
        stary.unlink()
    svgs, chyby = [], {}
    for vk in vykresy:
        s = svg(vk, png, velikost)
        svgs.append(s)
        ascii_nazev = unicodedata.normalize("NFKD", vk.nazev.lower()).encode("ascii", "ignore").decode()
        vk.soubor = f"varianta-{vk.kod[1:]}-{ascii_nazev.replace(' ', '-').replace(',', '')}.svg"
        (VYSTUP / vk.soubor).write_text(s, encoding="utf-8")
        chyby[vk.kod] = kontroly(vk)
        print(vk.kod, vk.pocty(), "OK" if not chyby[vk.kod] else chyby[vk.kod])
    (VYSTUP / "prehled.html").write_text(prehled(vykresy, svgs, chyby), encoding="utf-8")
    # rozměry pro kontrolu
    print("pruhy: jih u boxů %.2f, jih u vysavačů %.2f, západ %.2f" % (
        v_jih(18) - H2, v_jih(-20) - VYS_V[1], g(VYS_A[0], 0)[0] - HRANA_X))
    print("sever: boxy→zeď u=32 %.2f, vysavače→zeď u=-21 %.2f, boxy→červená u=25 %.2f, červená→zeď u=25 %.2f, u=-20 %.2f" % (
        -H2 - v_zed(32), VYS_V[0] - v_zed(-21), -H2 - CERVENA_SEVER.v(25), CERVENA_SEVER.v(25) - v_zed(25),
        CERVENA_SEVER.v(-20) - v_zed(-20)))


if __name__ == "__main__":
    main()
