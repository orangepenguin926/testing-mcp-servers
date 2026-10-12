"""Manipal Hospitals India - MCP server.

Tools:
  list_cities, list_hospitals, search_hospitals, get_hospital  -> built-in directory (offline)
  refresh_directory, fetch_live_details                        -> live pull from manipalhospitals.com
"""
import os
import re
import httpx
from bs4 import BeautifulSoup
from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    "manipal-hospitals-india",
    host=os.getenv("HOST", "0.0.0.0"),
    port=int(os.getenv("PORT", "8000")),
)
BASE = "https://www.manipalhospitals.com"
UA = {"User-Agent": "Mozilla/5.0 (manipal-mcp)"}

# (id, name, city, state, kind, address)  -- from manipalhospitals.com/hospitals (as of Sep 2026).
# Addresses only where confirmed; use fetch_live_details for the rest.
_RAW = [
    # Bengaluru, Karnataka
    ("blr-old-airport-road", "Manipal Hospital Old Airport Road", "Bengaluru", "Karnataka", "hospital", "98, HAL Old Airport Road, Kodihalli, Bengaluru 560017"),
    ("blr-whitefield", "Manipal Hospital Whitefield", "Bengaluru", "Karnataka", "hospital", None),
    ("blr-varthur-road", "Manipal Hospital Varthur Road", "Bengaluru", "Karnataka", "hospital", None),
    ("blr-jayanagar", "Manipal Hospital Jayanagar", "Bengaluru", "Karnataka", "hospital", None),
    ("blr-malleshwaram", "Manipal Hospital Malleshwaram", "Bengaluru", "Karnataka", "hospital", None),
    ("blr-yeshwanthpur", "Manipal Hospital Yeshwanthpur", "Bengaluru", "Karnataka", "hospital", None),
    ("blr-hebbal", "Manipal Hospital Hebbal", "Bengaluru", "Karnataka", "hospital", None),
    ("blr-sarjapur-road", "Manipal Hospital Sarjapur Road", "Bengaluru", "Karnataka", "hospital", None),
    ("blr-millers-road", "Manipal Hospital Millers Road", "Bengaluru", "Karnataka", "hospital", None),
    ("blr-yelahanka", "Manipal Hospital Yelahanka", "Bengaluru", "Karnataka", "hospital", None),
    ("blr-doddaballapur", "Manipal Hospital Doddaballapur", "Bengaluru", "Karnataka", "hospital", None),
    ("blr-electronics-city", "Manipal Hospital Electronics City", "Bengaluru", "Karnataka", "hospital", None),
    ("blr-kanakapura-road", "Manipal Hospital Kanakapura Road", "Bengaluru", "Karnataka", "hospital", None),
    ("blr-clinic-begur", "Manipal Clinic Begur", "Bengaluru", "Karnataka", "clinic", None),
    ("blr-clinic-brookefield", "Manipal Clinic Brookefield", "Bengaluru", "Karnataka", "clinic", None),
    ("blr-clinic-budigere", "Manipal Clinic Budigere", "Bengaluru", "Karnataka", "clinic", None),
    ("blr-clinic-indiranagar", "Manipal Clinic Indiranagar", "Bengaluru", "Karnataka", "clinic", None),
    ("blr-clinic-jayanagar", "Manipal Clinic Jayanagar", "Bengaluru", "Karnataka", "clinic", None),
    ("blr-clinic-sarjapur", "Manipal Clinic Sarjapur", "Bengaluru", "Karnataka", "clinic", None),
    ("blr-indira-clinic", "Manipal Indira Clinic", "Bengaluru", "Karnataka", "clinic", None),
    # Other Karnataka
    ("mysuru", "Manipal Hospital Mysuru", "Mysuru", "Karnataka", "hospital", None),
    ("mangaluru-kmc", "KMC Hospital (Manipal)", "Mangaluru", "Karnataka", "hospital", None),
    # Delhi NCR
    ("dwarka", "HCMCT Manipal Hospital Dwarka", "Delhi", "Delhi", "hospital", None),
    ("ghaziabad", "Manipal Hospital Ghaziabad", "Ghaziabad", "Uttar Pradesh", "hospital", None),
    ("gurugram", "Manipal Hospital Gurugram", "Gurugram", "Haryana", "hospital", None),
    # East
    ("bhubaneswar", "Manipal Hospital Bhubaneswar", "Bhubaneswar", "Odisha", "hospital", None),
    ("cuttack-clinic", "Manipal Clinic Cuttack", "Cuttack", "Odisha", "clinic", None),
    ("ranchi", "Bhagwan Mahavir Manipal Hospital", "Ranchi", "Jharkhand", "hospital", None),
    ("kol-broadway", "Manipal Hospital Broadway", "Kolkata", "West Bengal", "hospital", None),
    ("kol-dhakuria", "Manipal Hospital Dhakuria", "Kolkata", "West Bengal", "hospital", None),
    ("kol-em-bypass", "Manipal Hospital EM Bypass", "Kolkata", "West Bengal", "hospital", None),
    ("kol-mukundapur", "Manipal Hospital Mukundapur", "Kolkata", "West Bengal", "hospital", None),
    ("kol-salt-lake", "Manipal Hospital Salt Lake", "Kolkata", "West Bengal", "hospital", None),
    ("siliguri-rangapani", "Manipal Hospital Rangapani", "Siliguri", "West Bengal", "hospital", None),
    # West / North / South
    ("goa", "Manipal Hospital Goa", "Goa", "Goa", "hospital", None),
    ("goa-clinic-porvorim", "Manipal Clinic Porvorim", "Goa", "Goa", "clinic", None),
    ("jaipur", "Manipal Hospital Jaipur", "Jaipur", "Rajasthan", "hospital", "Sector 5, Main Sikar Road, Vidhyadhar Nagar, Jaipur 302039"),
    ("patiala", "Manipal Hospital Patiala", "Patiala", "Punjab", "hospital", None),
    ("pune-baner", "Manipal Hospital Baner", "Pune", "Maharashtra", "hospital", "Baner-Mhalunge Main Road, Baner, Pune 411045"),
    ("pune-kharadi", "Manipal Hospital Kharadi", "Pune", "Maharashtra", "hospital", None),
    ("pune-clinic-dhanori", "Manipal Clinic Dhanori", "Pune", "Maharashtra", "clinic", None),
    ("vijayawada", "Manipal Hospital Vijayawada", "Vijayawada", "Andhra Pradesh", "hospital", None),
    ("salem", "Manipal Hospital Salem", "Salem", "Tamil Nadu", "hospital", None),
]
HOSPITALS = [dict(zip(("id", "name", "city", "state", "kind", "address"), r)) for r in _RAW]
_live_index: dict[str, str] = {}  # name -> url, filled by refresh_directory


def _match(h, city=None, state=None, kind=None):
    return ((not city or city.lower() in h["city"].lower())
            and (not state or state.lower() in h["state"].lower())
            and (not kind or kind.lower() == h["kind"]))


@mcp.tool()
def list_cities() -> list[dict]:
    """Cities where Manipal Hospitals operate in India, as [{state, city, facilities}]."""
    counts: dict = {}
    for h in HOSPITALS:
        k = (h["state"], h["city"])
        counts[k] = counts.get(k, 0) + 1
    return [{"state": s, "city": c, "facilities": n} for (s, c), n in counts.items()]


@mcp.tool()
def list_hospitals(city: str = "", state: str = "", kind: str = "") -> list[dict]:
    """List Manipal facilities. Filter by city, state, and/or kind ('hospital' or 'clinic'). Empty = all."""
    return [h for h in HOSPITALS if _match(h, city, state, kind)]


@mcp.tool()
def search_hospitals(query: str) -> list[dict]:
    """Free-text search over name, city, state and address."""
    q = query.lower()
    return [h for h in HOSPITALS if q in " ".join(str(v) for v in h.values()).lower()]


@mcp.tool()
def get_hospital(hospital_id: str) -> dict:
    """Get one facility by id (see list_hospitals)."""
    for h in HOSPITALS:
        if h["id"] == hospital_id:
            return h
    return {"error": f"unknown id '{hospital_id}'"}


@mcp.tool()
async def refresh_directory() -> dict:
    """Scrape manipalhospitals.com/hospitals/ for current facility links (used by fetch_live_details)."""
    async with httpx.AsyncClient(headers=UA, timeout=30, follow_redirects=True) as c:
        r = await c.get(f"{BASE}/hospitals/")
        r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    for a in soup.find_all("a", href=True):
        txt = a.get_text(" ", strip=True)
        if re.search(r"manipal|kmc|mahavir", txt, re.I) and a["href"].startswith(("/", BASE)):
            href = a["href"] if a["href"].startswith("http") else BASE + a["href"]
            _live_index[txt] = href
    return {"found": len(_live_index), "links": "; ".join(f"{n} -> {u}" for n, u in _live_index.items())}


@mcp.tool()
async def fetch_live_details(hospital_name_or_url: str) -> dict:
    """Best-effort live pull of a hospital page (title, address, phones, specialities).
    Pass a full manipalhospitals.com URL, or a name matched against refresh_directory results."""
    url = hospital_name_or_url
    if not url.startswith("http"):
        if not _live_index:
            await refresh_directory()
        hits = [u for n, u in _live_index.items() if url.lower() in n.lower()]
        if not hits:
            return {"error": "no match; run refresh_directory and check names"}
        url = hits[0]
    if not url.startswith(BASE):
        return {"error": "only manipalhospitals.com URLs are allowed"}
    async with httpx.AsyncClient(headers=UA, timeout=30, follow_redirects=True) as c:
        r = await c.get(url)
        r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    text = soup.get_text("\n", strip=True)
    return {
        "url": url,
        "title": soup.title.string.strip() if soup.title and soup.title.string else None,
        "phones": ", ".join(sorted(set(re.findall(r"(?:\+91[\s-]?)?(?:1800[\s-]?\d{3}[\s-]?\d{4}|\d{5}[\s-]?\d{5})", text)))[:5]),
        "address": " | ".join([l for l in text.split("\n") if re.search(r"\b\d{6}\b", l)][:3]),
        "specialities": ", ".join(a.get_text(strip=True) for a in soup.select("a[href*='/specialities/'], a[href*='/centers-of-excellence/']"))[:1500],
    }


if __name__ == "__main__":
    # TRANSPORT=stdio for Claude Desktop; default streamable-http for Agentforce (endpoint: /mcp)
    mcp.run(transport=os.getenv("TRANSPORT", "streamable-http"))
