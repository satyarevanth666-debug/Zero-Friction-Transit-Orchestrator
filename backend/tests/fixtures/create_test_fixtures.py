"""Script to build high-fidelity offline test fixtures in data/fixtures/."""

import io
import os
import zipfile


def make_zip(file_dict: dict[str, str]) -> bytes:
    """Create in-memory zip bytes from filename -> content string mapping."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for fname, content in file_dict.items():
            z.writestr(fname, content.strip())
    return buf.getvalue()


def generate_fixtures(base_dir: str = "data/fixtures") -> None:
    os.makedirs(base_dir, exist_ok=True)

    # 1. Valid Rail GTFS (includes >24:00:00 time, calendar, calendar_dates)
    rail_files = {
        "agency.txt": """
agency_id,agency_name,agency_url,agency_timezone
IR,Indian Railways,https://indianrailways.gov.in,Asia/Kolkata
""",
        "stops.txt": """
stop_id,stop_name,stop_lat,stop_lon
BZA,Vijayawada Junction,16.5186,80.6200
GTL,Guntakal Junction,15.1667,77.3667
DMM,Dharmavaram Junction,14.4172,77.7180
HUP,Hindupur Railway Station,13.8299,77.4950
SC,Secunderabad Junction,17.4339,78.5017
HYB,Hyderabad Deccan,17.3920,78.4680
""",
        "routes.txt": """
route_id,agency_id,route_short_name,route_long_name,route_type
R_12785,IR,12785,Kacheguda - Mysuru Superfast Express,2
R_17215,IR,17215,Vijayawada - Dharmavaram Express,2
R_12769,IR,12769,Seven Hills Express,2
""",
        "trips.txt": """
route_id,service_id,trip_id,trip_headsign
R_17215,CAL_DAILY,TRIP_BZA_DMM_1,Dharmavaram Express
R_17215,CAL_DAILY,TRIP_BZA_DMM_OVERNIGHT,Dharmavaram Night Express
R_12785,CAL_WEEKDAYS,TRIP_SC_DMM_1,Mysuru Express
""",
        "calendar.txt": """
service_id,monday,tuesday,wednesday,thursday,friday,saturday,sunday,start_date,end_date
CAL_DAILY,1,1,1,1,1,1,1,20260101,20261231
CAL_WEEKDAYS,1,1,1,1,1,0,0,20260101,20261231
""",
        "calendar_dates.txt": """
service_id,date,exception_type
CAL_DAILY,20261105,2
CAL_WEEKDAYS,20261108,1
""",
        "stop_times.txt": """
trip_id,arrival_time,departure_time,stop_id,stop_sequence
TRIP_BZA_DMM_1,14:00:00,14:10:00,BZA,1
TRIP_BZA_DMM_1,18:30:00,18:35:00,GTL,2
TRIP_BZA_DMM_1,20:45:00,20:50:00,DMM,3
TRIP_BZA_DMM_OVERNIGHT,22:00:00,22:15:00,BZA,1
TRIP_BZA_DMM_OVERNIGHT,25:30:00,25:35:00,GTL,2
TRIP_BZA_DMM_OVERNIGHT,27:45:00,27:50:00,DMM,3
TRIP_SC_DMM_1,19:00:00,19:05:00,SC,1
TRIP_SC_DMM_1,23:40:00,23:45:00,GTL,2
TRIP_SC_DMM_1,25:15:00,25:20:00,DMM,3
""",
    }
    with open(os.path.join(base_dir, "gtfs_rail.zip"), "wb") as f:
        f.write(make_zip(rail_files))

    # 2. Valid APSRTC Bus GTFS
    bus_files = {
        "agency.txt": """
agency_id,agency_name,agency_url,agency_timezone
APSRTC,Andhra Pradesh State Road Transport Corporation,https://apsrtc.ap.gov.in,Asia/Kolkata
""",
        "stops.txt": """
stop_id,stop_name,stop_lat,stop_lon
BZA_BUS,Pandit Nehru Bus Station,16.5085,80.6174
ATP_BUS,Anantapur Bus Station,14.6780,77.5950
DMM_BUS,Dharmavaram APSRTC Bus Stand,14.4110,77.7240
HUP_BUS,Hindupur Bus Stand,13.8260,77.4910
""",
        "routes.txt": """
route_id,agency_id,route_short_name,route_long_name,route_type
R_BUS_EXP,APSRTC,EXP-101,Amaravathi - Dharmavaram Express,3
R_BUS_DELUXE,APSRTC,DLX-202,Vijayawada - Hindupur Super Luxury,3
""",
        "trips.txt": """
route_id,service_id,trip_id,trip_headsign
R_BUS_EXP,CAL_BUS_ALL,TRIP_BUS_BZA_DMM_1,Dharmavaram
R_BUS_DELUXE,CAL_BUS_ALL,TRIP_BUS_BZA_HUP_1,Hindupur
""",
        "calendar.txt": """
service_id,monday,tuesday,wednesday,thursday,friday,saturday,sunday,start_date,end_date
CAL_BUS_ALL,1,1,1,1,1,1,1,20260101,20261231
""",
        "stop_times.txt": """
trip_id,arrival_time,departure_time,stop_id,stop_sequence
TRIP_BUS_BZA_DMM_1,15:30:00,15:45:00,BZA_BUS,1
TRIP_BUS_BZA_DMM_1,21:00:00,21:15:00,ATP_BUS,2
TRIP_BUS_BZA_DMM_1,22:30:00,22:35:00,DMM_BUS,3
TRIP_BUS_BZA_HUP_1,17:00:00,17:15:00,BZA_BUS,1
TRIP_BUS_BZA_HUP_1,23:15:00,23:30:00,ATP_BUS,2
TRIP_BUS_BZA_HUP_1,25:45:00,25:50:00,HUP_BUS,3
""",
    }
    with open(os.path.join(base_dir, "gtfs_bus_apsrtc.zip"), "wb") as f:
        f.write(make_zip(bus_files))

    # 3. Expired GTFS (end_date = 20231231)
    expired_files = dict(rail_files)
    expired_files["calendar.txt"] = """
service_id,monday,tuesday,wednesday,thursday,friday,saturday,sunday,start_date,end_date
CAL_DAILY,1,1,1,1,1,1,1,20230101,20231231
"""
    with open(os.path.join(base_dir, "expired_gtfs.zip"), "wb") as f:
        f.write(make_zip(expired_files))

    # 4. Corrupted GTFS (Orphan stop, negative dwell, time > 48h, duplicate sequence)
    corrupted_files = {
        "agency.txt": rail_files["agency.txt"],
        "stops.txt": rail_files["stops.txt"],
        "routes.txt": rail_files["routes.txt"],
        "trips.txt": rail_files["trips.txt"],
        "calendar.txt": rail_files["calendar.txt"],
        "stop_times.txt": """
trip_id,arrival_time,departure_time,stop_id,stop_sequence
TRIP_BZA_DMM_1,10:00:00,10:05:00,BZA,1
TRIP_BZA_DMM_1,12:00:00,11:50:00,GTL,2
TRIP_BZA_DMM_1,14:00:00,14:05:00,ORPHAN_NONEXISTENT,3
TRIP_BZA_DMM_OVERNIGHT,10:00:00,10:05:00,BZA,1
TRIP_BZA_DMM_OVERNIGHT,52:00:00,52:05:00,GTL,2
TRIP_SC_DMM_1,10:00:00,10:05:00,SC,1
TRIP_SC_DMM_1,12:00:00,12:05:00,GTL,1
""",
    }
    with open(os.path.join(base_dir, "corrupted_gtfs.zip"), "wb") as f:
        f.write(make_zip(corrupted_files))

    print(f"Generated test fixtures in {base_dir}")


if __name__ == "__main__":
    generate_fixtures()
