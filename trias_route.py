#!/usr/bin/env python3
import sys
import argparse
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

TRIAS_URL_DEFAULT = "http://ogdtrias.verbundlinie.at:8183/stv/trias"

NS = {
    "trias": "http://www.vdv.de/trias",
    "siri": "http://www.siri.org.uk/siri",
}

def iso_z(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")

def escape_xml(s: str) -> str:
    return (s.replace("&", "&amp;")
             .replace("<", "&lt;")
             .replace(">", "&gt;")
             .replace('"', "&quot;")
             .replace("'", "&apos;"))

def post_trias(url: str, xml: str, timeout: int = 25) -> str:
    r = requests.post(
        url,
        data=xml.encode("utf-8"),
        headers={"Content-Type": "text/xml", "Accept": "text/xml"},
        timeout=timeout,
    )
    r.raise_for_status()
    # Force UTF-8 to avoid mojibake (Ã¼ etc.)
    return r.content.decode("utf-8", errors="replace")

def build_location_request(query: str, max_results: int = 10, language: str = "de") -> str:
    ts = iso_z(datetime.now(timezone.utc))
    q = escape_xml(query)
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<Trias xmlns="{NS["trias"]}" xmlns:siri="{NS["siri"]}" version="1.2">
  <ServiceRequest>
    <siri:RequestTimestamp>{ts}</siri:RequestTimestamp>
    <siri:RequestorRef>joanneum-route-cli</siri:RequestorRef>
    <RequestPayload>
      <LocationInformationRequest>
        <InitialInput>
          <LocationName><Text>{q}</Text><Language>{language}</Language></LocationName>
        </InitialInput>
        <Restrictions>
          <NumberOfResults>{max_results}</NumberOfResults>
        </Restrictions>
      </LocationInformationRequest>
    </RequestPayload>
  </ServiceRequest>
</Trias>'''

def pick_best_location(xml_text: str):
    root = ET.fromstring(xml_text)
    results = root.findall(".//trias:LocationResult", NS)
    if not results:
        return None

    candidates = []
    for lr in results:
        prob = 0.0
        p = lr.findtext("trias:Probability", default="", namespaces=NS).strip()
        if p:
            try: prob = float(p)
            except ValueError: prob = 0.0

        loc = lr.find("trias:Location", NS)
        if loc is None:
            continue

        sp_ref = None
        sp_name = None
        sp = loc.find("trias:StopPoint", NS)
        if sp is not None:
            sp_ref = sp.findtext("trias:StopPointRef", default=None, namespaces=NS)
            sp_name = sp.findtext("trias:StopPointName/trias:Text", default=None, namespaces=NS)

        loc_name = loc.findtext("trias:LocationName/trias:Text", default=None, namespaces=NS)
        display = sp_name or loc_name or "(unknown)"

        lat = loc.findtext("trias:GeoPosition/trias:Latitude", default=None, namespaces=NS)
        lon = loc.findtext("trias:GeoPosition/trias:Longitude", default=None, namespaces=NS)
        if lat is None or lon is None:
            continue
        try:
            lat_f = float(lat); lon_f = float(lon)
        except ValueError:
            continue

        candidates.append({
            "prob": prob,
            "display": display,
            "ref": sp_ref,
            "lat": lat_f,
            "lon": lon_f,
        })

    if not candidates:
        return None

    candidates.sort(key=lambda x: x["prob"], reverse=True)
    return candidates[0], candidates[:10]

def build_trip_request(origin, dest, max_results: int = 6,
                       include_realtime: bool = True,
                       dep_time_utc: datetime | None = None) -> str:
    ts = iso_z(datetime.now(timezone.utc))
    if dep_time_utc is None:
        dep_time_utc = datetime.now(timezone.utc)
    dep = iso_z(dep_time_utc)

    rt = "true" if include_realtime else "false"

    def loc_block(loc):
        if loc.get("ref"):
            r = escape_xml(loc["ref"])
            return f"<StopPointRef>{r}</StopPointRef>"
        return (f"<GeoPosition><Longitude>{loc['lon']:.6f}</Longitude>"
                f"<Latitude>{loc['lat']:.6f}</Latitude></GeoPosition>")

    return f'''<?xml version="1.0" encoding="UTF-8"?>
<Trias xmlns="{NS["trias"]}" xmlns:siri="{NS["siri"]}" version="1.2">
  <ServiceRequest>
    <siri:RequestTimestamp>{ts}</siri:RequestTimestamp>
    <siri:RequestorRef>joanneum-route-cli</siri:RequestorRef>
    <RequestPayload>
      <TripRequest>
        <Origin>
          <LocationRef>
            {loc_block(origin)}
          </LocationRef>
        </Origin>
        <Destination>
          <LocationRef>
            {loc_block(dest)}
          </LocationRef>
        </Destination>

        <DepArrTime>{dep}</DepArrTime>

        <Params>
          <NumberOfResults>{max_results}</NumberOfResults>
          <IncludeRealtimeData>{rt}</IncludeRealtimeData>
          <IncludeTrackSections>false</IncludeTrackSections>
        </Params>
      </TripRequest>
    </RequestPayload>
  </ServiceRequest>
</Trias>'''

def fmt_hms_from_iso(s: str) -> str:
    if not s:
        return "-"
    try:
        t = s.split("T", 1)[1].replace("Z", "")
        return t[:8]
    except Exception:
        return s

def first_text(elem, paths):
    for p in paths:
        v = elem.findtext(p, default="", namespaces=NS)
        if v is not None:
            v = v.strip()
            if v:
                return v
    return ""

def geo_as_text(scope, start=True):
    base = ".//trias:LegStart" if start else ".//trias:LegEnd"
    lat = first_text(scope, [f"{base}//trias:Latitude"])
    lon = first_text(scope, [f"{base}//trias:Longitude"])
    if lat and lon:
        return f"({lat},{lon})"
    return "?"

def parse_tripleg(leg_elem):
    timed = leg_elem.find("trias:TimedLeg", NS)
    cont  = leg_elem.find("trias:ContinuousLeg", NS)

    # --- ContinuousLeg (walk etc.)
    if cont is not None:
        o = first_text(cont, [
            ".//trias:LegStart/trias:StopPointName/trias:Text",
            ".//trias:LegStart/trias:LocationName/trias:Text",
        ]) or geo_as_text(cont, start=True)

        d = first_text(cont, [
            ".//trias:LegEnd/trias:StopPointName/trias:Text",
            ".//trias:LegEnd/trias:LocationName/trias:Text",
        ]) or geo_as_text(cont, start=False)

        dep = first_text(cont, [
            ".//trias:LegStart/trias:Time",
            ".//trias:LegStart/trias:EstimatedTime",
            ".//trias:LegStart/trias:TimetabledTime",
        ])
        arr = first_text(cont, [
            ".//trias:LegEnd/trias:Time",
            ".//trias:LegEnd/trias:EstimatedTime",
            ".//trias:LegEnd/trias:TimetabledTime",
        ])

        return {
            "mode": "walk",
            "line": "-",
            "from": o,
            "to": d,
            "dep": fmt_hms_from_iso(dep),
            "arr": fmt_hms_from_iso(arr),
        }

    # --- TimedLeg (public transport)
    if timed is not None:
        board_name = first_text(timed, [
            ".//trias:LegBoard/trias:StopPointName/trias:Text",
            ".//trias:LegStart/trias:StopPointName/trias:Text",
        ]) or geo_as_text(timed, start=True)

        alight_name = first_text(timed, [
            ".//trias:LegAlight/trias:StopPointName/trias:Text",
            ".//trias:LegEnd/trias:StopPointName/trias:Text",
        ]) or geo_as_text(timed, start=False)

        dep = first_text(timed, [
            ".//trias:LegBoard//trias:EstimatedTime",
            ".//trias:LegBoard//trias:TimetabledTime",
            ".//trias:LegStart//trias:EstimatedTime",
            ".//trias:LegStart//trias:TimetabledTime",
            ".//trias:LegStart//trias:Time",
        ])
        arr = first_text(timed, [
            ".//trias:LegAlight//trias:EstimatedTime",
            ".//trias:LegAlight//trias:TimetabledTime",
            ".//trias:LegEnd//trias:EstimatedTime",
            ".//trias:LegEnd//trias:TimetabledTime",
            ".//trias:LegEnd//trias:Time",
        ])

        mode = first_text(timed, [
            ".//trias:Service//trias:Mode//trias:PtMode",
            ".//trias:Mode//trias:PtMode",
        ]) or "-"

        line = first_text(timed, [
            ".//trias:Service//trias:PublishedLineName/trias:Text",
            ".//trias:PublishedLineName/trias:Text",
        ]) or "-"

        # Direction / destination text (optional)
        dest_txt = first_text(timed, [
            ".//trias:Service//trias:DestinationText/trias:Text",
            ".//trias:DestinationText/trias:Text",
        ])

        return {
            "mode": mode,
            "line": line,
            "to_headsign": dest_txt or "",
            "from": board_name,
            "to": alight_name,
            "dep": fmt_hms_from_iso(dep),
            "arr": fmt_hms_from_iso(arr),
        }

    # unknown leg type
    return {"mode": "-", "line": "-", "from": "?", "to": "?", "dep": "-", "arr": "-"}

def parse_trip_response(xml_text: str):
    root = ET.fromstring(xml_text)
    trips = []
    for tr in root.findall(".//trias:TripResult", NS):
        trip = tr.find("trias:Trip", NS)
        if trip is None:
            continue

        start = fmt_hms_from_iso(trip.findtext("trias:StartTime", default="", namespaces=NS))
        end   = fmt_hms_from_iso(trip.findtext("trias:EndTime", default="", namespaces=NS))

        legs = []
        for leg in trip.findall("trias:TripLeg", NS):
            legs.append(parse_tripleg(leg))

        trips.append({"start": start or "-", "end": end or "-", "legs": legs})
    return trips

def print_connections(connections, max_results: int):
    if not connections:
        print("No trips found.")
        return
    for idx, c in enumerate(connections[:max_results], start=1):
        print(f"\n=== Connection {idx}: {c['start']} -> {c['end']} ===")
        for l in c["legs"]:
            if l["mode"] == "walk":
                print(f"  {l['dep']}–{l['arr']}  WALK        {l['from']} -> {l['to']}")
            else:
                head = f" -> {l['to_headsign']}" if l.get("to_headsign") else ""
                print(f"  {l['dep']}–{l['arr']}  {l['mode'].upper():5}  {l['line']:<6}  {l['from']} -> {l['to']}{head}")

def main():
    ap = argparse.ArgumentParser(description="TRIAS TripRequest route finder (CLI).")
    ap.add_argument("--url", default=TRIAS_URL_DEFAULT, help="TRIAS endpoint URL")
    ap.add_argument("--from", dest="origin", default="Bürgergasse 18, 8010 Graz", help="Origin address/text")
    ap.add_argument("--to", dest="dest", default="Dreierschützengasse 10, 8020 Graz", help="Destination address/text")
    ap.add_argument("--max", type=int, default=5, help="Max connections to show")
    ap.add_argument("--rt", action="store_true", help="Include realtime data (IncludeRealtimeData=true)")
    ap.add_argument("--plan-only", action="store_true", help="Force plan data only (IncludeRealtimeData=false)")
    ap.add_argument("--debug", action="store_true", help="Debug output")
    args = ap.parse_args()

    include_rt = False if args.plan_only else True
    if args.rt:
        include_rt = True

    o_resp = post_trias(args.url, build_location_request(args.origin, 10))
    picked = pick_best_location(o_resp)
    if not picked:
        print(f"ERROR: Could not resolve origin: {args.origin}")
        sys.exit(2)
    best_o, cand_o = picked

    d_resp = post_trias(args.url, build_location_request(args.dest, 10))
    picked = pick_best_location(d_resp)
    if not picked:
        print(f"ERROR: Could not resolve destination: {args.dest}")
        sys.exit(2)
    best_d, cand_d = picked

    print("Origin chosen:")
    print(f"  {best_o['display']}  ({best_o['lat']:.6f}, {best_o['lon']:.6f})  ref={best_o['ref']}")
    print("Destination chosen:")
    print(f"  {best_d['display']}  ({best_d['lat']:.6f}, {best_d['lon']:.6f})  ref={best_d['ref']}")

    if args.debug:
        print("\n[debug] Origin candidates (top):")
        for c in cand_o:
            print(f"  p={c['prob']:.6f}  {c['display']}  ({c['lat']:.6f},{c['lon']:.6f}) ref={c['ref']}")
        print("\n[debug] Destination candidates (top):")
        for c in cand_d:
            print(f"  p={c['prob']:.6f}  {c['display']}  ({c['lat']:.6f},{c['lon']:.6f}) ref={c['ref']}")

    trip_xml = build_trip_request(best_o, best_d, max_results=max(1, args.max), include_realtime=include_rt)
    trip_resp = post_trias(args.url, trip_xml)

    if args.debug:
        print("\n[debug] Raw Trip response (first 1200 chars):")
        print(trip_resp[:1200])

    trips = parse_trip_response(trip_resp)
    print_connections(trips, args.max)

if __name__ == "__main__":
    try:
        main()
    except requests.HTTPError as e:
        resp = getattr(e, "response", None)
        if resp is not None:
            try:
                body = resp.content.decode("utf-8", errors="replace")
            except Exception:
                body = resp.text
            print(f"ERROR: HTTP {resp.status_code}: {body[:1200]}")
        else:
            print(f"ERROR: {e}")
        sys.exit(1)
    except requests.RequestException as e:
        print(f"ERROR: request failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)