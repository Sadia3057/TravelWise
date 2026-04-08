import pickle, os, random

BASE      = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR = os.path.join(BASE, "../models")

def get_db():
    """Import get_db lazily to avoid circular imports."""
    from app import get_db as _get_db
    return _get_db()

# ── Load ML model ──────────────────────────────────────────────────────────────
def _load():
    with open(os.path.join(MODEL_DIR, "rf_model.pkl"), "rb") as f:
        model = pickle.load(f)
    with open(os.path.join(MODEL_DIR, "encoders.pkl"), "rb") as f:
        encoders = pickle.load(f)
    return model, encoders

try:
    RF_MODEL, ENCODERS = _load()
except Exception as e:
    RF_MODEL, ENCODERS = None, {}
    print(f"Warning: Could not load ML model: {e}")

# ── Interest → destination-type mapping ───────────────────────────────────────
INTEREST_TYPE_MAP = {
    "beaches":     ["Beach"],
    "hills":       ["Hill Station"],
    "adventure":   ["Adventure", "Hill Station"],
    "history":     ["Heritage"],
    "nature":      ["Nature", "Hill Station"],
    "spiritual":   ["Spiritual"],
    "famous":      ["Heritage","Beach","Hill Station","Adventure","Nature","Spiritual","City","Lake","Desert","Island","Forest","Wildlife"],
    "wildlife":    ["Nature","Forest","Wildlife"],
    "food":        ["Heritage","Spiritual","Nature","City"],
    "nightlife":   ["Beach","City"],
    "photography": ["Heritage","Hill Station","Nature","Beach","Adventure","Lake","Desert","Island","City","Forest","Wildlife"],
    "trekking":    ["Adventure","Hill Station","Forest"],
    "lakes":       ["Lake","Hill Station","Nature"],
    "desert":      ["Desert"],
    "islands":     ["Island","Beach"],
    "waterfalls":  ["Nature","Forest"],
    "temples":     ["Spiritual","Heritage"],
    "forts":       ["Heritage"],
    "backwaters":  ["Nature","Lake"],
    "skiing":      ["Hill Station","Adventure"],
    "surfing":     ["Beach"],
    "yoga":        ["Spiritual","Adventure"],
}


# ── Load destinations from Excel (data/destinations.xlsx) ─────────────────────
def _load_destinations():
    """
    Reads all destination details from data/destinations.xlsx.
    Falls back to empty list if file not found.
    Each row becomes a destination dict matching the original structure.
    """
    import pandas as pd
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../data")
    excel_path = os.path.join(data_dir, "destinations.xlsx")

    if not os.path.exists(excel_path):
        print(f"WARNING: destinations.xlsx not found at {excel_path}")
        return []

    df = pd.read_excel(excel_path, sheet_name="Destinations")
    destinations = []
    for _, row in df.iterrows():
        # Skip empty rows
        if pd.isna(row.get('Name')) or str(row.get('Name','')).strip() == '':
            continue

        # Parse comma-separated interests and highlights
        def parse_list(val):
            if pd.isna(val) or str(val).strip() == '':
                return []
            return [x.strip().lower() for x in str(val).split(',') if x.strip()]

        def parse_highlights(val):
            if pd.isna(val) or str(val).strip() == '':
                return []
            return [x.strip() for x in str(val).split(',') if x.strip()]

        destinations.append({
            "name":          str(row['Name']).strip(),
            "type":          str(row['Type']).strip(),
            "state":         str(row.get('State', '')).strip(),
            "region":        str(row.get('Region', '')).strip(),
            "accommodation": int(row.get('Accommodation (₹/night)', 1500) or 1500),
            "food":          int(row.get('Food (₹/day)', 500) or 500),
            "entry_fee":     int(row.get('Entry Fee (₹)', 0) or 0),
            "travel_time":   float(row.get('Travel Time (hrs)', 5) or 5),
            "rating":        float(row.get('Rating (out of 5)', 4.0) or 4.0),
            "interests":     parse_list(row.get('Interests (comma separated)', '')),
            "highlights":    parse_highlights(row.get('Highlights (comma separated)', '')),
            "desc":          str(row.get('Description', '')).strip(),
        })

    print(f"Loaded {len(destinations)} destinations from destinations.xlsx")
    return destinations

DESTINATIONS = _load_destinations()

# ── Activities by destination type ────────────────────────────────────────────
PLACE_ACTIVITIES = {
    "Beach":       ["Morning walk on the beach","Water sports & snorkelling","Sunset cruise","Local seafood dinner","Beach bonfire","Parasailing"],
    "Hill Station":["Sunrise viewpoint trek","Cable car ride","Local market visit","Nature walk through forests","Stargazing","Scenic drive"],
    "Heritage":    ["Fort/palace guided tour","Heritage walk in old city","Museum tour","Traditional cuisine dinner","Cultural show","Craft shopping"],
    "Nature":      ["Wildlife safari","Waterfall trek","Boat ride","Bird watching","Organic farm visit","Jungle walk"],
    "Adventure":   ["White water rafting","Rock climbing","Mountain biking","Camping & bonfire","Zip-lining","High-altitude trek"],
    "Spiritual":   ["Morning Aarti ceremony","Temple visits","Meditation session","Heritage ghats walk","Local food trail","Sunset prayer"],
    "Wildlife":    ["Jeep safari","Elephant safari","Bird watching","Naturalist walk","Night safari","Nature photography"],
    "City":        ["Old city heritage walk","Food trail","Shopping","Museum visits","Nightlife","Rooftop dining"],
    "Desert":      ["Camel safari","Sand dune sunset","Desert camp","Stargazing","Cultural folk show","4x4 dune bashing"],
    "Island":      ["Snorkelling","Scuba diving","Glass-bottom boat","Beach picnic","Coral reef tour","Sea kayaking"],
    "Lake":        ["Boat ride","Lakeside walk","Photography session","Bird watching","Kayaking","Sunrise viewing"],
    "Forest":      ["Jungle trek","Wildlife spotting","Waterfall hike","Canopy walk","Camping","Night trail"],
}


# ── Per-destination GPS coordinates (all 370 destinations) ───────────────────
DEST_COORDS = {
    # Andhra Pradesh
    'Tirupati':(13.6288,79.4192),'Lepakshi':(13.8009,77.6082),
    'Srikalahasti':(13.6494,79.7064),'Gandikota':(14.8230,78.2762),
    'Nagarjuna Sagar':(16.5730,79.3167),'Visakhapatnam':(17.6868,83.2185),
    'Pulicat Lake':(13.4167,80.3167),'Amaravati':(16.5730,80.3563),
    'Horsley Hills':(13.6604,78.3999),'Araku Valley':(18.3273,82.8751),
    # Arunachal Pradesh
    'Pasighat':(28.0667,95.3333),'Ziro Valley':(27.5440,93.8300),
    'Along':(28.1667,94.8000),'Dirang':(27.3536,92.2396),
    'Bomdila':(27.2644,92.4206),'Mechuka':(28.6333,94.1833),
    'Namdapha':(27.5333,96.3833),'Roing':(28.1329,95.8333),
    'Tawang':(27.5861,91.8594),'Itanagar':(27.0844,93.6053),
    # Assam
    'Kamakhya Temple':(26.1665,91.7126),'Dibrugarh':(27.4728,94.9120),
    'Sivasagar':(26.9833,94.6333),'Guwahati':(26.1445,91.7362),
    'Pobitora':(26.2167,91.9667),'Tezpur':(26.6338,92.7928),
    'Kaziranga':(26.5775,93.1706),'Majuli':(26.9500,94.2000),
    'Haflong':(25.1667,93.0167),'Manas National Park':(26.7000,90.6333),
    # Bihar
    'Kesaria':(26.3167,84.8333),'Munger':(25.3750,86.4736),
    'Rajgir':(25.0283,85.4185),'Sasaram':(24.9451,84.0267),
    'Bodh Gaya':(24.6969,84.9914),'Pawapuri':(25.1333,85.5333),
    'Vikramshila':(25.3333,87.2833),'Vaishali':(25.9745,85.1280),
    'Patna':(25.5941,85.1376),'Nalanda':(25.1336,85.4446),
    # Chhattisgarh
    'Dongargarh':(21.1833,80.7500),'Sirpur':(21.3333,82.2167),
    'Kanger Valley':(18.8333,81.9833),'Chitrakote Falls':(19.1167,81.7167),
    'Achanakmar':(22.3333,81.5667),'Raipur':(21.2514,81.6296),
    'Bhoramdeo':(22.1667,81.4333),'Mainpat':(22.9167,83.4333),
    'Barnawapara':(21.2667,82.3167),'Jagdalpur':(19.0833,82.0167),
    # Goa
    'Cotigao Wildlife Sanctuary':(14.9833,74.0333),'Vagator':(15.6033,73.7416),
    'Old Goa Churches':(15.5007,73.9117),'Arambol':(15.6867,73.7042),
    'Calangute Beach':(15.5440,73.7552),'Panaji':(15.4909,73.8278),
    'Palolem Beach':(15.0100,74.0231),'Morjim Beach':(15.6333,73.7333),
    'Dudhsagar Falls':(15.3145,74.3145),'Goa':(15.2993,74.1240),
    # Gujarat
    'Rann of Kutch':(23.7333,70.8000),'Patan':(23.8500,72.1167),
    'Ahmedabad':(23.0225,72.5714),'Gir National Park':(21.1241,70.7904),
    'Dwarka':(22.2399,68.9676),'Palitana':(21.5222,71.8228),
    'Mandvi':(22.8333,69.3500),'Statue of Unity':(21.8381,73.7183),
    'Saputara':(20.5833,73.7500),'Somnath':(20.9001,70.3741),
    # Haryana
    'Faridabad':(28.4089,77.3178),'Pinjore Gardens':(30.7989,76.9294),
    'Kurukshetra':(29.9695,76.8783),'Morni Hills':(30.6833,77.1333),
    'Sohna':(28.2469,77.0444),'Sultanpur Bird Sanctuary':(28.4333,76.9167),
    'Rewari':(28.1981,76.6195),'Hisar':(29.1492,75.7217),
    'Panipat':(29.3909,76.9635),'Pinjore Gardens Chandigarh':(30.7989,76.9294),
    'Kapurthala':(31.3792,75.3808),
    # Himachal Pradesh
    'Kinnaur':(31.5833,78.5000),'Dharamshala':(32.2190,76.3234),
    'Chamba':(32.5533,76.1211),'Spiti Valley':(32.2432,78.0141),
    'Khajjiar':(32.5500,76.0500),'Kasol':(32.0100,77.3162),
    'Shimla':(31.1048,77.1734),'Dalhousie':(32.5357,75.9797),
    'Kullu':(31.9592,77.1089),'Manali':(32.2396,77.1887),
    # Jharkhand
    'Betla National Park':(23.9333,84.1000),'Ranchi':(23.3441,85.3096),
    'Jamshedpur':(22.8046,86.2029),'Giridih':(24.1883,86.3025),
    'Hazaribagh':(23.9972,85.3659),'Netarhat':(23.4833,84.2667),
    'Hundru Falls':(23.2167,85.5167),'Palamu Fort':(23.8500,84.0833),
    'Deoghar':(24.4847,86.6947),'Saranda Forest':(22.5000,85.5000),
    # Karnataka
    'Chikmagalur':(13.3153,75.7754),'Dandeli':(15.2667,74.6333),
    'Mysuru':(12.2958,76.6394),'Badami':(15.9167,75.6833),
    'Agumbe':(13.5028,75.0967),'Belur Halebidu':(13.1653,75.8631),
    'Kabini':(11.9150,76.3836),'Hampi':(15.3350,76.4600),
    'Gokarna':(14.5479,74.3188),'Coorg':(12.3375,75.8069),
    # Kerala
    'Munnar':(10.0889,77.0595),'Fort Kochi':(9.9637,76.2429),
    'Bekal':(12.3903,75.0337),'Palakkad':(10.7867,76.6548),
    'Kerala Backwaters':(9.4981,76.3388),'Thekkady':(9.6000,77.1667),
    'Wayanad':(11.6854,76.1320),'Kovalam':(8.3988,76.9784),
    'Varkala':(8.7379,76.7163),'Thrissur':(10.5276,76.2144),
    # Ladakh
    'Tso Moriri':(32.9000,78.3167),'Leh Ladakh':(34.1526,77.5771),
    'Pangong Lake':(33.7500,78.6667),'Alchi Monastery':(34.2167,77.1333),
    'Magnetic Hill Leh':(34.1833,77.5000),'Shanti Stupa Leh':(34.1667,77.5500),
    'Nubra Valley':(34.6167,77.5833),'Zanskar Valley':(33.5000,76.8333),
    'Hemis National Park':(33.8333,77.6667),'Moriri Wetland':(32.9000,78.3167),
    # Madhya Pradesh
    'Bandhavgarh':(23.7167,81.0333),'Sanchi':(23.4783,77.7395),
    'Gwalior':(26.2183,78.1828),'Khajuraho':(24.8318,79.9199),
    'Ujjain':(23.1793,75.7849),'Pench National Park':(21.7167,79.3000),
    'Bhedaghat':(23.1500,79.8000),'Mandu':(22.3500,75.3833),
    'Orchha':(25.3518,78.6406),'Pachmarhi':(22.4670,78.4340),
    # Maharashtra
    'Kolhapur':(16.7000,74.2333),'Lonavala':(18.7500,73.4083),
    'Panhala Fort':(16.8167,74.1167),'Nashik':(19.9975,73.7898),
    'Konkan Coast':(17.0000,73.2667),'Mahabaleshwar':(17.9239,73.6586),
    'Mumbai':(18.9667,72.8333),'Aurangabad':(19.8762,75.3433),
    'Alibaug':(18.6414,72.8722),'Pune':(18.5204,73.8567),
    # Manipur
    'Ukhrul':(25.1167,94.3667),'Loktak Lake':(24.5167,93.7833),
    'Keibul Lamjao':(24.5167,93.7500),'Senapati':(25.2667,93.9667),
    'Bishnupur Manipur':(24.6167,93.7667),'Kangla Fort':(24.8127,93.9372),
    'Moirang':(24.5000,93.7500),'Tamenglong':(24.9833,93.5167),
    'Moreh':(24.2333,94.2667),'Imphal':(24.8170,93.9368),
    # Meghalaya
    'Cherrapunjee':(25.2840,91.7265),'Tura':(25.5167,90.2167),
    'Jowai':(25.4500,92.2000),'Mawlynnong':(25.2036,91.9208),
    'Nohkalikai Falls':(25.2833,91.7167),'Mawsynram':(25.2998,91.5839),
    'Shillong':(25.5788,91.8933),'Double Decker Root Bridge':(25.3167,91.7333),
    'Dawki':(25.1833,92.0167),'Balpakram National Park':(25.3500,90.7000),
    # Mizoram
    'Lunglei':(22.8833,92.7333),'Vantawng Falls':(23.0833,92.5667),
    'Palak Dil':(22.3500,92.8167),'Phawngpui Blue Mountain':(22.5000,93.1167),
    'Tam Dil Lake':(23.3667,92.9167),'Aizawl':(23.1645,92.9376),
    'Murlen National Park':(23.1333,93.3333),'Reiek':(23.5667,92.8000),
    'Hmuifang':(23.4833,92.7667),'Champhai':(23.4500,93.3333),
    # Nagaland
    'Dzukou Valley':(25.5417,94.0833),'Hornbill Festival Kisama':(25.6167,94.1167),
    'Wokha':(26.1000,94.2667),'Dimapur':(25.9076,93.7272),
    'Mon Nagaland':(26.7167,95.0000),'Tuensang':(26.2667,94.8167),
    'Kohima':(25.6751,94.1086),'Mokokchung':(26.3167,94.5167),
    'Zunheboto':(25.9167,94.5167),'Phek':(25.6667,94.4667),
    # Odisha
    'Simlipal National Park':(21.8333,86.4167),'Chilika Lake':(19.7333,85.3333),
    'Konark':(19.8876,86.0952),'Puri':(19.8135,85.8312),
    'Raghurajpur':(20.0000,85.8667),'Sambalpur':(21.4667,83.9667),
    'Bhitarkanika':(20.7500,86.8833),'Daringbadi':(20.0667,84.0333),
    'Cuttack':(20.4625,85.8828),'Bhubaneswar':(20.2961,85.8245),
    # Punjab
    'Qila Mubarak Bathinda':(30.2098,74.9455),'Harike Wetland':(31.1574,74.9427),
    'Ropar':(30.9630,76.5286),'Anandpur Sahib':(31.2383,76.4982),
    'Muktsar Sahib':(30.4736,74.5148),'Fatehgarh Sahib':(30.6454,76.3929),
    'Patiala':(30.3398,76.3869),'Ludhiana':(30.9010,75.8573),
    'Amritsar':(31.6340,74.8723),
    # Rajasthan
    'Udaipur':(24.5854,73.7125),'Mount Abu':(24.5926,72.7156),
    'Jaisalmer':(26.9157,70.9083),'Chittorgarh':(24.8887,74.6269),
    'Ranthambore':(26.0173,76.5026),'Jaipur':(26.9124,75.7873),
    'Jodhpur':(26.2389,73.0243),'Pushkar':(26.4899,74.5511),
    'Bikaner':(28.0229,73.3119),'Ajmer':(26.4499,74.6399),
    # Sikkim
    'Yuksom':(27.3333,88.2333),'Ravangla':(27.3000,88.3667),
    'Pelling':(27.2975,88.2361),'Lachung':(27.6833,88.7500),
    'Zuluk':(27.2167,88.7667),'Namchi':(27.1667,88.3500),
    'Gangtok':(27.3314,88.6138),'Gurudongmar Lake':(27.8667,88.7167),
    'Tashiding':(27.3167,88.2833),'Kaluk':(27.3167,88.2833),
    # Tamil Nadu
    'Thanjavur':(10.7870,79.1378),'Chettinad':(10.1167,78.8500),
    'Ooty':(11.4102,76.6950),'Kanyakumari':(8.0883,77.5385),
    'Madurai':(9.9252,78.1198),'Rameswaram':(9.2881,79.3174),
    'Kodaikanal':(10.2381,77.4892),'Mahabalipuram':(12.6269,80.1927),
    'Mudumalai':(11.5500,76.6333),'Yercaud':(11.7750,78.2083),
    # Telangana
    'Ramappa Temple':(18.2578,79.9589),'Karimnagar':(18.4386,79.1288),
    'Khammam':(17.2473,80.1514),'Nizamabad':(18.6725,78.0941),
    'Warangal':(17.9784,79.5941),'Nagarjunasagar Telangana':(16.5730,79.3167),
    'Mahabubnagar':(16.7376,77.9875),'Medak Cathedral':(18.0444,78.2647),
    'Adilabad':(19.6640,78.5320),'Hyderabad':(17.3850,78.4867),
    # Tripura
    'Unakoti':(24.3167,92.0667),'Sepahijala Wildlife Sanctuary':(23.4833,91.3333),
    'Jampui Hills':(24.1333,92.2667),'Trishna Wildlife Sanctuary':(23.6833,91.5500),
    'Pilak':(23.1667,91.7000),'Dumboor Lake':(23.9167,91.9333),
    'Agartala':(23.8315,91.2868),'Kamalasagar':(23.7667,91.3000),
    'Ujjayanta Palace':(23.8315,91.2868),'Neermahal':(23.4833,91.2000),
    # Uttarakhand
    'Nainital':(29.3803,79.4636),'Rishikesh':(30.0869,78.2676),
    'Chopta':(30.3833,79.2167),'Auli':(30.5214,79.5654),
    'Kedarnath':(30.7352,79.0669),'Mussoorie':(30.4598,78.0664),
    'Valley of Flowers':(30.7167,79.6000),'Lansdowne':(29.8378,78.6865),
    'Jim Corbett':(29.5300,78.7747),'Haridwar':(29.9457,78.1642),
    # Uttar Pradesh
    'Chitrakoot':(25.2000,80.8833),'Dudhwa National Park':(28.5167,80.7167),
    'Mathura Vrindavan':(27.4924,77.6737),'Sarnath':(25.3761,83.0242),
    'Fatehpur Sikri':(27.0945,77.6625),'Ayodhya':(26.7922,82.1998),
    'Prayagraj':(25.4358,81.8464),'Agra':(27.1767,78.0081),
    'Lucknow':(26.8467,80.9462),'Varanasi':(25.3176,82.9739),
    # West Bengal
    'Sundarbans':(21.9497,89.1833),'Bishnupur Bengal':(23.0749,87.3176),
    'Cooch Behar':(26.3244,89.4457),'Dooars':(26.7000,89.3333),
    'Digha':(21.6268,87.5091),'Kalimpong':(27.0660,88.4680),
    'Murshidabad':(24.1800,88.2683),'Shantiniketan':(23.6802,87.6858),
    'Darjeeling':(27.0360,88.2627),'Kolkata':(22.5726,88.3639),
    # Andaman & Nicobar
    'Long Island Andaman':(12.3667,92.8500),'Andaman Islands':(11.7401,92.6586),
    'Baratang Island':(12.0167,92.7500),'Havelock Island':(12.0167,92.9833),
    'Cellular Jail':(11.6667,92.7500),'Neil Island':(11.8333,92.9000),
    'Jolly Buoy Island':(11.5167,92.6000),'Ross Island':(11.6667,92.7833),
    'Diglipur':(13.2667,92.9667),'Port Blair':(11.6234,92.7265),
    # Chandigarh
    'Elante Mall Area':(30.7046,76.8013),'Sukhna Lake':(30.7467,76.8192),
    'Rose Garden Chandigarh':(30.7400,76.7800),'Rock Garden Chandigarh':(30.7530,76.8110),
    'Chhatbir Zoo':(30.6500,76.6333),'Capitol Complex':(30.7600,76.8033),
    'Gurudwara Nada Sahib':(30.7167,76.8833),'Sector 17 Chandigarh':(30.7380,76.7900),
    'Morni Hills Chandigarh':(30.6833,77.1333),
    # Dadra & Nagar Haveli
    'Vanganga Lake Garden':(20.2667,73.0167),'Satmaliya Deer Sanctuary':(20.2333,73.0333),
    'Tribal Museum DNH':(20.2667,73.0167),'Hirwa Van Garden':(20.2667,73.0000),
    'Khanvel':(20.2000,73.0333),'Dudhni Lake':(20.3167,73.0000),
    'Swaminarayan Temple Silvassa':(20.2738,73.0168),'Amalsad':(20.5333,72.9500),
    'Silvassa':(20.2738,73.0168),'Madhuban Dam':(20.3167,73.0167),
    # Daman & Diu
    'Naida Caves':(20.4000,72.8500),'Ghoghla Beach':(20.7167,70.9000),
    "St Paul's Church Diu":(20.7139,70.9856),'Jallandhar Beach':(20.7000,70.9667),
    'Nagoa Beach Diu':(20.7000,70.9500),'INS Khukri Memorial':(20.7139,70.9856),
    'Diu Fort':(20.7139,70.9856),'Damanganga River':(20.3972,72.8325),
    'Devka Beach Daman':(20.4167,72.8333),'Daman':(20.3974,72.8328),
    # Delhi
    'Chandni Chowk':(28.6560,77.2310),'Qutub Minar':(28.5244,77.1855),
    'Lotus Temple':(28.5535,77.2588),"Humayun's Tomb":(28.5933,77.2507),
    'Red Fort':(28.6562,77.2410),'Akshardham Temple Delhi':(28.6127,77.2773),
    'India Gate':(28.6129,77.2295),'Purana Qila':(28.6084,77.2441),
    'Hauz Khas':(28.5494,77.2001),'Delhi':(28.6139,77.2090),
    # Jammu & Kashmir
    'Sonamarg':(34.2981,75.2875),'Srinagar':(34.0837,74.7973),
    'Patnitop':(33.0972,75.3189),'Pahalgam':(34.0161,75.3156),
    'Jammu':(32.7266,74.8570),'Dachigam National Park':(34.1167,74.8500),
    'Vaishno Devi':(33.0278,74.9500),'Gulmarg':(34.0483,74.3805),
    'Yusmarg':(33.8667,74.6667),'Bhaderwah':(32.9772,75.7311),
    # Lakshadweep
    'Lakshadweep':(10.5667,72.6417),'Bitra Island':(11.6000,72.1833),
    'Kavaratti':(10.5626,72.6369),'Bangaram Island':(11.3000,72.2667),
    'Minicoy Island':(8.2833,73.0333),'Kadmat Island':(11.2333,72.7833),
    'Agatti Island':(10.8667,72.2000),'Amini Island':(11.1167,72.7333),
    'Androth Island':(10.8167,73.6667),'Kalpeni Island':(10.0833,73.6333),
    # Puducherry
    'Paradise Beach Pondicherry':(11.9416,79.8083),'Serenity Beach':(11.9833,79.8500),
    'Yanam':(16.7333,82.2167),'French Quarter Pondicherry':(11.9342,79.8358),
    'Auroville':(12.0000,79.8167),'Sri Aurobindo Ashram':(11.9342,79.8358),
    'Karaikal':(10.9254,79.8380),'Ariyankuppam Mangroves':(11.9167,79.8333),
    'Pondicherry':(11.9416,79.8083),'Mahe Kerala Enclave':(11.7016,75.5347),
}

def _haversine_km(name1: str, name2: str) -> float:
    """
    Distance in km between two locations.
    Uses per-destination GPS coords first, falls back to state capital coords.
    """
    import math as _math
    # Try dest coords first
    c1 = DEST_COORDS.get(name1)
    c2 = DEST_COORDS.get(name2)
    # Fall back to state coords
    if not c1: c1 = STATE_COORDS.get(name1, (20.0, 78.0))
    if not c2: c2 = STATE_COORDS.get(name2, (20.0, 78.0))
    R  = 6371.0
    dlat = _math.radians(c2[0] - c1[0])
    dlon = _math.radians(c2[1] - c1[1])
    a = (_math.sin(dlat/2)**2 +
         _math.cos(_math.radians(c1[0])) * _math.cos(_math.radians(c2[0])) *
         _math.sin(dlon/2)**2)
    return 2 * R * _math.asin(_math.sqrt(a))

_ISLAND_STATES = {'Andaman & Nicobar', 'Lakshadweep'}
_ISLAND_DESTS  = {
    'Long Island Andaman','Andaman Islands','Baratang Island','Havelock Island',
    'Cellular Jail','Neil Island','Jolly Buoy Island','Ross Island','Diglipur',
    'Port Blair','Lakshadweep','Bitra Island','Kavaratti','Bangaram Island',
    'Minicoy Island','Kadmat Island','Agatti Island','Amini Island',
    'Androth Island','Kalpeni Island',
}

def compute_travel_time(from_state: str, dest_name: str, transport: str, dest_state: str = '') -> float:
    """
    Compute realistic travel time using per-destination GPS coordinates.
    Each of the 370 destinations has its own lat/lng so travel times vary
    even within the same state.
    """
    if not from_state:
        return 5.0

    # Use destination-specific coords; from_state is a state name so use DEST_COORDS
    # if it happens to match a city, otherwise use rough state centre coords
    _STATE_CENTRES = {
        'Andhra Pradesh':(15.9129,79.7400),'Arunachal Pradesh':(27.0844,93.6053),
        'Assam':(26.2006,92.9376),'Bihar':(25.5941,85.1376),
        'Chhattisgarh':(21.2787,81.8661),'Goa':(15.2993,74.1240),
        'Gujarat':(23.2156,72.6369),'Haryana':(29.0588,76.0856),
        'Himachal Pradesh':(31.1048,77.1734),'Jharkhand':(23.3441,85.3096),
        'Karnataka':(12.9716,77.5946),'Kerala':(8.5241,76.9366),
        'Madhya Pradesh':(23.2599,77.4126),'Maharashtra':(18.9667,72.8333),
        'Manipur':(24.8170,93.9368),'Meghalaya':(25.5788,91.8933),
        'Mizoram':(23.1645,92.9376),'Nagaland':(25.6751,94.1086),
        'Odisha':(20.9517,85.0985),'Punjab':(30.7333,76.7794),
        'Rajasthan':(26.9124,75.7873),'Sikkim':(27.3314,88.6138),
        'Tamil Nadu':(13.0827,80.2707),'Telangana':(17.3850,78.4867),
        'Tripura':(23.8315,91.2868),'Uttarakhand':(30.3165,78.0322),
        'Uttar Pradesh':(26.8467,80.9462),'West Bengal':(22.5726,88.3639),
        'Andaman & Nicobar':(11.7401,92.6586),'Chandigarh':(30.7333,76.7794),
        'Dadra & Nagar Haveli':(20.1809,73.0169),'Daman & Diu':(20.3974,72.8328),
        'Delhi':(28.6139,77.2090),'Jammu & Kashmir':(33.7782,76.5762),
        'Ladakh':(34.1526,77.5771),'Lakshadweep':(10.5667,72.6417),
        'Puducherry':(11.9416,79.8083),
    }
    from_coords = DEST_COORDS.get(from_state) or _STATE_CENTRES.get(from_state, (20.0, 78.0))
    dest_coords = DEST_COORDS.get(dest_name) or _STATE_CENTRES.get(dest_state or dest_name, (20.0, 78.0))

    import math as _math
    R = 6371.0
    dlat = _math.radians(dest_coords[0] - from_coords[0])
    dlon = _math.radians(dest_coords[1] - from_coords[1])
    a = (_math.sin(dlat/2)**2 +
         _math.cos(_math.radians(from_coords[0])) * _math.cos(_math.radians(dest_coords[0])) *
         _math.sin(dlon/2)**2)
    km = 2 * R * _math.asin(_math.sqrt(a))

    is_island = (dest_name in _ISLAND_DESTS or
                 dest_state in _ISLAND_STATES or
                 from_state in _ISLAND_STATES)

    if transport == 'Flight':
        t = km / 750 + 2.0
        if is_island: t += 1.5
        return round(max(1.5, t), 1)
    elif transport == 'Train':
        if is_island: return round(km / 750 + 4.0, 1)
        return round(max(2.0, km * 1.38 / 62.0), 1)
    elif transport == 'Bus':
        if is_island: return round(km / 750 + 4.0, 1)
        return round(max(3.0, km * 1.38 / 48.0), 1)
    elif transport == 'Car':
        if is_island: return round(km / 750 + 4.0, 1)
        return round(max(1.0, km * 1.38 / 58.0), 1)
    elif transport == 'Bike':
        if is_island: return round(km / 750 + 5.0, 1)
        return round(max(1.0, km * 1.38 / 50.0), 1)
    return round(km / 65.0, 1)

# ── Transport cost by distance (travel_time in hours) ─────────────────────────
def _transport_cost_per_person(transport: str, travel_hours: float) -> int:
    """
    Calculate one-way transport cost per person based on mode and distance.
    travel_hours is the estimated travel time from destinations.xlsx.
    """
    h = float(travel_hours or 5)

    if transport == "Flight":
        # Base fare + distance premium. Short haul (<1.5h) ~₹3,500, long haul (>3h) ~₹7,000
        if h <= 1.5:   return 3500
        elif h <= 2.5: return 4500
        elif h <= 4:   return 6000
        else:          return 7500

    elif transport == "Train":
        # ~₹180–220 per hour of journey (sleeper/3AC blended)
        base = max(300, int(h * 200))
        return min(base, 2500)   # cap at ₹2,500

    elif transport == "Bus":
        # ~₹100–130 per hour
        base = max(200, int(h * 115))
        return min(base, 1500)

    elif transport == "Car":
        # Fuel + toll: ~₹12/km, avg speed 60km/h → ₹720/h shared by people
        # Return per person cost handled at call site
        return max(500, int(h * 700))   # ₹700/hr total car cost

    elif transport == "Bike":
        # Fuel + toll: ~₹8/km, avg speed 50km/h → ₹400/hr total
        return max(300, int(h * 400))   # total bike cost (shared)

    return int(h * 200)   # fallback


# ── ML feasibility prediction ──────────────────────────────────────────────────
def predict_feasibility(dest, budget, num_days, trip_type, season,
                        transport="Train", people=None, from_loc="", **kwargs):
    # People count — use passed value or default per trip type
    if people is None:
        people = {
            "Solo":    1,
            "Couple":  2,
            "Friends": 3,
            "Family":  4,
            "Senior":  2,
        }.get(trip_type, 1)
    people = max(1, int(people))

    per_night    = dest["accommodation"]
    per_day_food = dest["food"]
    entry        = dest["entry_fee"]
    # Use user-supplied travel_time if provided, else fall back to dataset value
    # Compute real travel time using per-destination GPS coordinates
    dest_name  = dest.get("name", "")
    dest_state = dest.get("state", "")
    travel_hours = compute_travel_time(from_loc, dest_name, transport, dest_state)
    travel_hours = max(0.5, travel_hours)

    # Accommodation: every 2 people share a room
    rooms       = max(1, (people + 1) // 2)
    accom_total = per_night * rooms * num_days

    # Food: per person per day
    food_total  = per_day_food * people * num_days

    # Entry fees: per person
    entry_total = entry * people

    # Activities & sightseeing: 15% of stay cost
    activities  = int((accom_total + food_total) * 0.15)

    # Transport: distance-based, return journey
    if transport in ("Car", "Bike"):
        # Car/Bike: total vehicle cost shared — not multiplied by people
        one_way_vehicle = _transport_cost_per_person(transport, travel_hours)
        transport_total = one_way_vehicle * 2   # return journey, shared cost
    else:
        one_way_pp      = _transport_cost_per_person(transport, travel_hours)
        transport_total = one_way_pp * people * 2   # return, per person

    # Shopping/misc per person per day
    misc_pp    = {
        "Solo":    300,
        "Couple":  350,
        "Friends": 400,
        "Family":  500,
        "Senior":  250,   # Seniors typically spend less on misc
    }.get(trip_type, 300)
    misc_total = misc_pp * people * num_days

    total_cost = accom_total + food_total + entry_total + activities + transport_total + misc_total

    if RF_MODEL and ENCODERS:
        try:
            dtype = dest["type"] if dest["type"] in ENCODERS["destination_type"].classes_ else "Heritage"
            dtype_enc   = ENCODERS["destination_type"].transform([dtype])[0]
            season_enc  = ENCODERS["season"].transform([season])[0]
            trip_enc    = ENCODERS["trip_type"].transform([trip_type])[0]
            traffic_enc = ENCODERS["traffic_density"].transform(["Medium"])[0]
            features = [[budget, dest["accommodation"], dest["food"], dest["entry_fee"],
                         dest["travel_time"], num_days, dest["rating"],
                         dtype_enc, season_enc, trip_enc, traffic_enc]]
            prob     = RF_MODEL.predict_proba(features)[0][1]
            feasible = prob >= 0.5
        except Exception:
            feasible = budget >= total_cost
            prob     = 0.9 if feasible else 0.2
    else:
        feasible = budget >= total_cost
        prob     = 0.9 if feasible else 0.2

    return {
        "feasible":         bool(feasible),
        "confidence":       float(round(prob * 100, 1)),
        "total_cost":       int(total_cost),
        "budget_remaining": int(max(0, budget - total_cost)),
        "people":           people,
        "travel_hours":     round(travel_hours, 1),
        "cost_breakdown": {
            "accommodation": int(accom_total),
            "food":          int(food_total),
            "entry_fee":     int(entry_total),
            "transport":     int(transport_total),
            "activities":    int(activities),
            "misc":          int(misc_total),
            "total":         int(total_cost),
        },
    }


# ── Recommendation engine ──────────────────────────────────────────────────────
def get_recommendations(from_loc, dest_area, budget, trip_type, num_days, transport, season, interests=None, people=None, travel_time=None):
    interests = [i.lower() for i in (interests or [])]
    allowed_types = set()
    if interests:
        for i in interests:
            for t in INTEREST_TYPE_MAP.get(i, []):
                allowed_types.add(t)

    results = []
    for dest in DESTINATIONS:
        # Filter 1: destination / state / region text match
        if dest_area:
            q = dest_area.lower().strip()
            if not (q in dest["name"].lower() or q in dest.get("state","").lower()
                    or q in dest.get("region","").lower() or q in dest["type"].lower()):
                continue
        # Filter 2: interest match
        if allowed_types:
            dest_ints = set(dest.get("interests",[]))
            if not (dest["type"] in allowed_types or dest_ints.intersection(set(interests))):
                continue

        analysis = predict_feasibility(dest, budget, num_days, trip_type, season,
                                           transport, people, from_loc=from_loc)
        score = dest["rating"] * 20
        if analysis["feasible"]: score += 30
        if interests:
            score += len(set(dest.get("interests",[])).intersection(set(interests))) * 8
        score += min(analysis["budget_remaining"] / max(budget,1) * 10, 10)

        # Fetch real reviews from DB for this destination
        try:
            db = get_db()
            rows = db.execute(
                "SELECT review_text, sentiment FROM reviews WHERE destination=?",
                (dest["name"],)
            ).fetchall()
            if rows:
                pos  = sum(1 for r in rows if r["sentiment"] == "Positive")
                neg  = sum(1 for r in rows if r["sentiment"] == "Negative")
                neu  = sum(1 for r in rows if r["sentiment"] == "Neutral")
                tot  = len(rows)
                if pos >= neg and pos >= neu:   overall = "Positive"
                elif neg >= pos and neg >= neu: overall = "Negative"
                else:                           overall = "Neutral"
                sentiment = {
                    "label":        overall,
                    "positive_pct": round(pos / tot * 100),
                    "total":        tot,
                }
            else:
                sentiment = {"label": "No Reviews", "positive_pct": 0, "total": 0}
        except Exception:
            sentiment = {"label": "No Reviews", "positive_pct": 0, "total": 0}
        matched = list(set(dest.get("interests",[])).intersection(set(interests))) if interests else []
        results.append({"destination": dest, "analysis": analysis, "score": round(score,1),
                         "sentiment": sentiment, "matched_interests": matched})

    results.sort(key=lambda x: (x["analysis"]["feasible"], x["score"]), reverse=True)
    return results[:10]


# ── Itinerary generator ────────────────────────────────────────────────────────
# ── Rich type+interest specific fillers for longer trips ─────────────────────
# Keyed by destination type — each has 20+ unique activities
TYPE_FILLERS = {
    "Heritage": [
        "Morning walk through the old city lanes",
        "Visit the local archaeological museum",
        "Explore lesser-known stepwells & ancient structures",
        "Photography walk through heritage quarters",
        "Attend a classical music or dance performance",
        "Visit the royal cenotaphs & tombs",
        "Explore the local textile & craft market",
        "Guided heritage walking tour of the old bazaar",
        "Visit a traditional haveli or mansion",
        "Interact with local artisans — pottery, weaving",
        "Watch the evening light & sound show",
        "Explore colonial-era buildings & churches",
        "Visit the local folklore museum",
        "Taste street food at the famous food street",
        "Attend a traditional puppet show or folk performance",
        "Visit a nearby fort or watchtower",
        "Explore the spice & antique markets",
        "Sunrise visit to the most iconic monument",
        "Boat ride on the nearest river or lake",
        "Photography session at the most picturesque ghat",
    ],
    "Nature": [
        "Early morning nature walk & birdwatching",
        "Visit a hidden waterfall nearby",
        "Riverside picnic & relaxation",
        "Stargazing session at night",
        "Visit a local organic farm",
        "Explore a forest trail on foot",
        "Butterfly & insect spotting walk",
        "Sunrise hike to a nearby hilltop",
        "Photography of local flora & fauna",
        "Village walk through tea/coffee/spice plantations",
        "Visit a natural cave or rock formation",
        "Canoe or kayak on a nearby lake",
        "Interaction with local tribal communities",
        "Visit a medicinal herb garden",
        "Explore a scenic meadow or valley",
        "Night jungle walk with a guide",
        "Visit the local eco-tourism centre",
        "Bird photography at a nearby wetland",
        "Explore a bamboo forest trail",
        "Campfire evening with local folk songs",
    ],
    "Hill Station": [
        "Sunrise trek to the nearest peak",
        "Visit a high-altitude lake",
        "Explore an apple/cherry orchard",
        "Paragliding or ziplining if available",
        "Visit a Buddhist monastery or hilltop temple",
        "Photography walk through misty valleys",
        "Local market visit for woolens & handicrafts",
        "Mountain biking on scenic trails",
        "Visit a waterfall accessible by trek",
        "Bonfire & stargazing in the evening",
        "Nature walk through oak & rhododendron forests",
        "Visit a village famous for local produce",
        "Yak or horse riding on mountain trails",
        "Hot chocolate & momos at a scenic café",
        "Explore a nearby glacial point or snow line",
        "Visit a heritage wooden temple",
        "Photography session at a mountain meadow",
        "River crossing or rappelling activity",
        "Visit a tea estate or herb garden",
        "Evening walk along a scenic ridge",
    ],
    "Beach": [
        "Sunrise yoga on the beach",
        "Kayaking along the coastline",
        "Snorkelling at a coral reef spot",
        "Deep sea fishing with local fishermen",
        "Visit a secluded hidden beach nearby",
        "Parasailing over the sea",
        "Explore a fishing village & fish market",
        "Sunset cruise on a catamaran",
        "Photography at the lighthouse",
        "Visit a mangrove forest by boat",
        "Try local coastal seafood cuisine",
        "Beach bonfire with live music",
        "Jet skiing & banana boat rides",
        "Glass-bottom boat ride",
        "Visit a beach fort or colonial ruin",
        "Scuba diving lesson for beginners",
        "Dolphin spotting boat trip",
        "Explore sea caves at low tide",
        "Beachside hammock & relaxation day",
        "Visit a turtle nesting beach",
    ],
    "Spiritual": [
        "Pre-dawn aarti at the main temple",
        "Meditation session at a riverside ashram",
        "Visit smaller lesser-known temples nearby",
        "Attend an evening prayer ceremony",
        "Pilgrimage walk along the sacred path",
        "Visit a sacred kund or holy tank",
        "Attend a yoga class at a local ashram",
        "Boat ride on the sacred river at sunrise",
        "Visit the market for religious artefacts & flowers",
        "Explore the ghats & observe daily rituals",
        "Interact with sadhus & spiritual seekers",
        "Visit a Jain or Buddhist monument nearby",
        "Attend a discourse or spiritual talk",
        "Explore the sacred forest or garden",
        "Visit a hilltop shrine by foot",
        "Attend the main evening aarti ceremony",
        "Photography of lamps & diyas at dusk",
        "Explore the pilgrimage town on foot",
        "Visit a charity kitchen (Langar/Bhandara)",
        "Sound healing or Vedic chanting session",
    ],
    "Wildlife": [
        "Early morning jeep safari — zone A",
        "Evening jeep safari — different zone",
        "Birdwatching walk at dawn",
        "Visit the nature interpretation centre",
        "Canter safari for open grasslands",
        "Elephant safari (where available)",
        "Night safari with a trained naturalist",
        "Photography safari with zoom lenses",
        "Walk along the forest buffer zone",
        "Visit a watering hole for wildlife sighting",
        "Crocodile or gharial spotting by boat",
        "Visit a rescue & rehabilitation centre",
        "Explore tribal villages on the forest edge",
        "Full-day deep forest expedition",
        "Sloth bear or leopard tracking walk",
        "Visit a butterfly park or insectarium",
        "Explore the forest canopy walkway",
        "Attend a ranger talk on conservation",
        "Star gazing in the forest at night",
        "Village cultural program in the evening",
    ],
    "Adventure": [
        "White water river rafting",
        "Rock climbing & rappelling session",
        "Bungee jumping or cliff jumping",
        "Paragliding over the valley",
        "Mountain biking on rugged trails",
        "Zip-lining through forest canopy",
        "High-altitude trekking to a pass",
        "ATV quad biking off-road",
        "Camping overnight under the stars",
        "Waterfall rappelling (canyoning)",
        "Skiing or snowboarding (if seasonal)",
        "Cave exploration & spelunking",
        "Bridge slithering & commando nets",
        "River crossing on a suspension bridge",
        "Archery & shooting range",
        "Obstacle course & team challenges",
        "Kayaking on a fast-moving river",
        "Hang gliding (if available)",
        "High-altitude lake trek",
        "Bonfire, BBQ & adventure camp night",
    ],
    "City": [
        "Explore the old city quarters on foot",
        "Visit the main city museum or art gallery",
        "Food tour — breakfast, lunch & dinner at iconic spots",
        "Visit a famous market or bazaar",
        "Explore the modern city skyline & viewpoint",
        "Visit a historic railway station or colonial building",
        "Attend a live performance or show",
        "Day trip to a nearby town or attraction",
        "Shopping at the famous local market",
        "Visit a contemporary art gallery",
        "Sunrise or sunset at a rooftop restaurant",
        "Explore a less-touristed neighbourhood",
        "Visit an iconic café or street food lane",
        "Photography walk in the heritage zone",
        "Metro or tram ride across the city",
        "Visit a planetarium or science centre",
        "Explore a weekend flea market",
        "Visit a botanical garden or city park",
        "Attend a food festival or cultural event",
        "Evening river cruise or city tour by bus",
    ],
    "Desert": [
        "Camel safari at sunrise",
        "Sand dune bashing in a 4x4",
        "Visit a desert village & interact with locals",
        "Stargazing in the open desert at night",
        "Photography at golden hour on the dunes",
        "Visit a desert fort or haveli",
        "Try traditional desert cuisine",
        "Folk music & dance around a bonfire",
        "Sunrise hot air balloon ride",
        "Explore a desert oasis & garden",
        "Visit a salt flat or dry lake bed",
        "Overnight camping in a luxury desert tent",
        "Visit a camel research & breeding farm",
        "Explore ancient desert trade route sites",
        "Visit a colourful textile market",
        "Desert cycle or mountain bike trail",
        "Kite flying on the open flat sand",
        "Visit a local potter or craft artisan",
        "Full moon walk on the sand dunes",
        "Visit a desert wildlife sanctuary",
    ],
    "Island": [
        "Glass-bottom boat ride over coral",
        "Scuba diving at a reef site",
        "Snorkelling with tropical fish",
        "Kayaking around the island coastline",
        "Visit a remote uninhabited island",
        "Sea walking (underwater walk)",
        "Night squid fishing with locals",
        "Sunrise photography on the beach",
        "Visit the island's historical museum",
        "Explore a mangrove creek by kayak",
        "Dolphin watching boat trip",
        "Visit a turtle nesting beach at night",
        "Semi-submarine or underwater observatory",
        "Island hopping by speedboat",
        "Explore a limestone cave",
        "Visit a pearl diving demonstration",
        "Beachside barbeque dinner",
        "Stargazing on a remote beach",
        "Coral nursery visit & restoration tour",
        "Local island cuisine cooking class",
    ],
}

# Default fallback for any unrecognised type
TYPE_FILLERS["default"] = TYPE_FILLERS["Heritage"]

FILLER_ACTIVITIES = TYPE_FILLERS["default"]  # kept for backward compat

def generate_itinerary(destination, num_days, trip_type):
    dest = next((d for d in DESTINATIONS if d["name"] == destination), None)
    if not dest:
        dest = {"name": destination, "type":"Heritage", "highlights":["Explore the city"], "state":""}

    dest_type  = dest["type"]
    activities = list(PLACE_ACTIVITIES.get(dest_type, PLACE_ACTIVITIES["Heritage"]))
    highlights = list(dest.get("highlights", []))

    # Build a non-repeating pool of sightseeing slots
    # Each middle day gets 1 highlight + 2 activities
    # Pool = highlights first, then fillers to cover any extra days
    middle_days  = max(0, num_days - 2)   # days between arrival & departure
    slots_needed = middle_days            # 1 highlight per middle day

    hl_pool = highlights[:]               # start with real highlights
    # Use type-specific fillers — no repeat from highlights
    type_key    = dest_type if dest_type in TYPE_FILLERS else "default"
    filler_pool = [f for f in TYPE_FILLERS[type_key] if f not in hl_pool]
    random.shuffle(filler_pool)
    while len(hl_pool) < slots_needed:
        if filler_pool:
            hl_pool.append(filler_pool.pop(0))
        else:
            hl_pool.append(f"Free exploration of {dest['name']}")

    # Non-repeating activity pool — shuffle a copy
    act_pool = activities[:]
    random.shuffle(act_pool)
    # Extend with shuffled repeats only if truly needed (very long trips)
    while len(act_pool) < middle_days * 2:
        extra = activities[:]
        random.shuffle(extra)
        act_pool.extend(extra)

    days = []
    act_idx = 0   # pointer into act_pool

    for day in range(1, num_days + 1):
        if day == 1:
            # Arrival day
            afternoon_hl = hl_pool[0] if hl_pool else "Evening city walk"
            schedule = [
                {"time":"09:00 AM","activity":f"Arrive in {dest['name']} & check-in","type":"travel"},
                {"time":"12:00 PM","activity":"Freshen up & local lunch","type":"food"},
                {"time":"03:00 PM","activity":afternoon_hl,"type":"sightseeing"},
                {"time":"07:00 PM","activity":"Welcome dinner at local restaurant","type":"food"},
            ]

        elif day == num_days and num_days > 1:
            # Departure day — use a highlight not yet used if possible
            used = {hl_pool[i] for i in range(min(day-1, len(hl_pool)))}
            remaining = [h for h in highlights if h not in used]
            last_hl = remaining[0] if remaining else (highlights[-1] if highlights else "Final sightseeing")
            schedule = [
                {"time":"08:00 AM","activity":"Breakfast & final packing","type":"food"},
                {"time":"10:00 AM","activity":last_hl,"type":"sightseeing"},
                {"time":"12:30 PM","activity":"Souvenir shopping at local market","type":"leisure"},
                {"time":"03:00 PM","activity":f"Departure from {dest['name']}","type":"travel"},
            ]

        else:
            # Middle days — unique highlight + 2 unique activities
            hl  = hl_pool[day - 1] if (day - 1) < len(hl_pool) else f"Explore {dest['name']} — Day {day}"
            a1  = act_pool[act_idx % len(act_pool)];  act_idx += 1
            a2  = act_pool[act_idx % len(act_pool)];  act_idx += 1
            schedule = [
                {"time":"07:30 AM","activity":a1,"type":"activity"},
                {"time":"10:30 AM","activity":hl,"type":"sightseeing"},
                {"time":"01:00 PM","activity":"Lunch at local restaurant","type":"food"},
                {"time":"03:30 PM","activity":a2,"type":"activity"},
                {"time":"07:30 PM","activity":"Dinner & relaxation","type":"food"},
            ]

        days.append({"day": day, "title": f"Day {day} — {dest['name']}", "schedule": schedule})

    return {"destination": dest["name"], "num_days": num_days, "trip_type": trip_type, "days": days}


# ── Destination coordinates (lat, lng) for Google Maps ────────────────────────
DEST_COORDS = {
    "Visakhapatnam":    (17.6868, 83.2185),
    "Tirupati":         (13.6288, 79.4192),
    "Araku Valley":     (18.3273, 82.8756),
    "Tawang":           (27.5860, 91.8594),
    "Ziro Valley":      (27.5425, 93.8225),
    "Kaziranga":        (26.6681, 93.3698),
    "Majuli":           (27.0000, 94.2167),
    "Guwahati":         (26.1445, 91.7362),
    "Bodh Gaya":        (24.6961, 84.9913),
    "Nalanda":          (25.1367, 85.4430),
    "Rajgir":           (25.0279, 85.4188),
    "Chitrakote Falls": (19.1077, 81.7079),
    "Jagdalpur":        (19.0742, 82.0363),
    "Goa":              (15.2993, 74.1240),
    "Rann of Kutch":    (23.8333, 69.7667),
    "Gir National Park":(21.1240, 70.8235),
    "Dwarka":           (22.2394, 68.9678),
    "Ahmedabad":        (23.0225, 72.5714),
    "Saputara":         (20.5763, 73.7541),
    "Kurukshetra":      (29.9695, 76.8783),
    "Manali":           (32.2432, 77.1892),
    "Shimla":           (31.1048, 77.1734),
    "Spiti Valley":     (32.2461, 78.0336),
    "Dharamshala":      (32.2190, 76.3234),
    "Kasol":            (32.0097, 77.3148),
    "Ranchi":           (23.3441, 85.3096),
    "Netarhat":         (23.4798, 84.2707),
    "Coorg":            (12.3375, 75.8069),
    "Hampi":            (15.3350, 76.4600),
    "Mysuru":           (12.2958, 76.6394),
    "Chikmagalur":      (13.3161, 75.7720),
    "Badami":           (15.9182, 75.6760),
    "Kerala Backwaters":(9.4981,  76.3388),
    "Munnar":           (10.0889, 77.0595),
    "Wayanad":          (11.6854, 76.1320),
    "Kovalam":          (8.3988,  76.9784),
    "Thrissur":         (10.5276, 76.2144),
    "Khajuraho":        (24.8318, 79.9199),
    "Bandhavgarh":      (23.7219, 81.0101),
    "Orchha":           (25.3519, 78.6400),
    "Pachmarhi":        (22.4675, 78.4341),
    "Bhedaghat":        (23.1477, 79.7930),
    "Mumbai":           (19.0760, 72.8777),
    "Aurangabad":       (19.8762, 75.3433),
    "Lonavala":         (18.7481, 73.4072),
    "Mahabaleshwar":    (17.9307, 73.6477),
    "Konkan Coast":     (16.9902, 73.3120),
    "Nashik":           (19.9975, 73.7898),
    "Imphal":           (24.8170, 93.9368),
    "Shillong":         (25.5788, 91.8933),
    "Cherrapunjee":     (25.2800, 91.7200),
    "Dawki":            (25.1958, 92.0267),
    "Aizawl":           (23.7271, 92.7176),
    "Kohima":           (25.6751, 94.1086),
    "Puri":             (19.8135, 85.8312),
    "Konark":           (19.8876, 86.0946),
    "Chilika Lake":     (19.7167, 85.3167),
    "Bhubaneswar":      (20.2961, 85.8245),
    "Amritsar":         (31.6340, 74.8723),
    "Anandpur Sahib":   (31.2340, 76.5010),
    "Jaipur":           (26.9124, 75.7873),
    "Udaipur":          (24.5854, 73.7125),
    "Jodhpur":          (26.2389, 73.0243),
    "Jaisalmer":        (26.9157, 70.9083),
    "Pushkar":          (26.4899, 74.5511),
    "Ranthambore":      (26.0173, 76.5026),
    "Mount Abu":        (24.5926, 72.7156),
    "Gangtok":          (27.3314, 88.6138),
    "Pelling":          (27.2939, 88.2087),
    "Lachung":          (27.6867, 88.7447),
    "Ooty":             (11.4102, 76.6950),
    "Mahabalipuram":    (12.6269, 80.1927),
    "Madurai":          (9.9252,  78.1198),
    "Kodaikanal":       (10.2381, 77.4892),
    "Thanjavur":        (10.7870, 79.1378),
    "Kanyakumari":      (8.0883,  77.5385),
    "Yercaud":          (11.7748, 78.2116),
    "Hyderabad":        (17.3850, 78.4867),
    "Warangal":         (17.9689, 79.5941),
    "Agartala":         (23.8315, 91.2868),
    "Agra":             (27.1767, 78.0081),
    "Varanasi":         (25.3176, 82.9739),
    "Mathura Vrindavan":(27.4924, 77.6737),
    "Lucknow":          (26.8467, 80.9462),
    "Ayodhya":          (26.7922, 82.1998),
    "Rishikesh":        (30.0869, 78.2676),
    "Haridwar":         (29.9457, 78.1642),
    "Nainital":         (29.3919, 79.4542),
    "Mussoorie":        (30.4598, 78.0664),
    "Auli":             (30.5243, 79.5671),
    "Valley of Flowers":(30.7283, 79.6050),
    "Kedarnath":        (30.7346, 79.0669),
    "Darjeeling":       (27.0360, 88.2627),
    "Kolkata":          (22.5726, 88.3639),
    "Sundarbans":       (21.9497, 88.8867),
    "Leh Ladakh":       (34.1526, 77.5771),
    "Andaman Islands":  (11.7401, 92.6586),
    "Pondicherry":      (11.9416, 79.8083),
    "Lakshadweep":      (10.5667, 72.6417),
    "Delhi":            (28.6139, 77.2090),
}

def get_dest_coords(name):
    """Return (lat, lng) for a destination name."""
    return DEST_COORDS.get(name, (20.5937, 78.9629))  # fallback = centre of India
# ── Sentiment Analysis using VADER ────────────────────────────────────────────
# VADER (Valence Aware Dictionary and sEntiment Reasoner) is a proper NLP
# sentiment library that understands context, negations, punctuation & intensity.
# Install: pip install vaderSentiment
try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
    _vader = SentimentIntensityAnalyzer()
    VADER_AVAILABLE = True
except ImportError:
    VADER_AVAILABLE = False

def analyze_sentiment(review, rating=None):
    """
    Sentiment analysis using VADER NLP — text only.
    Rating is ignored for sentiment (displayed separately as stars).
    """
    if VADER_AVAILABLE:
        scores   = _vader.polarity_scores(review)
        compound = scores["compound"]   # -1.0 (negative) to +1.0 (positive)

        if compound >= 0.05:
            label = "Positive"
        elif compound <= -0.05:
            label = "Negative"
        else:
            label = "Neutral"

        return {"score": round(compound, 3), "label": label}

    # Fallback if VADER not installed — neutral default
    return {"score": 0.0, "label": "Neutral"}

def analyze_sentiment_batch(reviews):
    if not reviews: return {"label":"Neutral","score":0.5,"positive_pct":50}
    results = [analyze_sentiment(r) for r in reviews]
    avg = sum(r["score"] for r in results) / len(results)
    # Normalise avg to 0-1 if VADER scores (-1 to 1)
    avg_norm = (avg + 1) / 2 if VADER_AVAILABLE else avg
    pos_pct  = sum(1 for r in results if r["label"] == "Positive") / len(results) * 100
    label    = "Positive" if avg_norm >= 0.55 else ("Negative" if avg_norm < 0.45 else "Neutral")
    return {"label": label, "score": round(avg, 3), "positive_pct": round(pos_pct)}

def generate_mock_reviews(destination):
    templates = [
        f"Visited {destination} last month — absolutely breathtaking views and wonderful hospitality!",
        f"{destination} was an amazing experience. The place is beautiful and peaceful.",
        f"Great destination! {destination} has excellent food and friendly locals. Highly recommend!",
        f"Loved every moment in {destination}. Stunning landscapes and memorable sunsets.",
        f"{destination} was a bit crowded during peak season but still beautiful.",
    ]
    return random.sample(templates, min(3, len(templates)))


# ── Chatbot ────────────────────────────────────────────────────────────────────
CHAT_RESPONSES = {
    "hello":     ["Hello! I'm your AI travel assistant. Where would you like to explore today? 🌍"],
    "hi":        ["Hi there! Ready to plan your perfect trip?"],
    "budget":    ["For budget planning: 40% accommodation, 30% food, 20% activities, 10% shopping."],
    "best time": ["Best time: North (Oct–Mar), South (Sep–Feb), Northeast (Oct–Apr), Beaches (Nov–Feb)."],
    "itinerary": ["I can generate a custom day-wise itinerary! Use the Trip Planner above."],
    "solo":      ["Solo in India: Rishikesh, Hampi, Varanasi — safe, affordable and soul-enriching!"],
    "family":    ["For families: Kerala, Goa, Jaipur are top picks — activities for all ages."],
    "friends":   ["Friends trip: Goa, Manali, or Ladakh! Beach parties, adventure and group treks."],
    "weather":   ["Hills (snow Oct–Mar), Beaches (sunny Nov–Feb), Plains (pleasant Oct–Mar)."],
    "transport": ["Flights (fastest), Trains (scenic & affordable), Buses (budget), Car (flexible)."],
    "default":   ["Ask me about destinations, budgets, best seasons, or any Indian state!"],
}

def chatbot_reply(message):
    msg = message.lower()
    for key, replies in CHAT_RESPONSES.items():
        if key in msg: return random.choice(replies)
    for dest in DESTINATIONS:
        if dest["name"].lower() in msg or dest["state"].lower() in msg:
            return (f"{dest['name']} in {dest['state']} is rated {dest['rating']}/5 ⭐. "
                    f"Top spots: {', '.join(dest['highlights'][:3])}. "
                    f"Est. cost: ₹{(dest['accommodation']+dest['food'])*3:,} for 3 days.")
    return random.choice(CHAT_RESPONSES["default"])