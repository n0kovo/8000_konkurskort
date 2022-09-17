import requests
from bs4 import BeautifulSoup
import pandas as pd
import requests
from tqdm import tqdm
import math
import json
import folium
from folium.plugins import MarkerCluster
import re
import json



def get_industrial_sites(bbox):

    locations = []
    query = f"""[out:json][timeout:25][bbox:{bbox}];
    (
    node["landuse"="industrial"];
    way["landuse"="industrial"];
    relation["landuse"="industrial"];
    );
    out center;
    """

    url =  "https://overpass-api.de/api/interpreter"

    req = requests.post(url, data={"data": query})
    elements = json.loads(req.text)["elements"]
    for element in elements:
        lat = element["center"]["lat"]
        lon = element["center"]["lon"]
        coordinate_tuple = (lat, lon)
        locations.append(coordinate_tuple)

    return locations



def get_adresseliste():
    dict_list = []
    total = 0
    coordinates = []
    links = []

    req = requests.get("https://www.konkurser.dk/konkurser/?q=%C3%85rhus+C&sortering=Konkursdekret&retning=Faldende&side=1")
    total_pages = math.ceil(int(req.text.split("Antal: ")[1].split("<br")[0])/25)

    pbar = tqdm(total=total_pages, leave=False)
    for side in range(total_pages):
        pbar.set_description(f"Scraper adresser fra side {side+1}")
        url = f"https://www.konkurser.dk/konkurser/?q=%C3%85rhus+C&sortering=Konkursdekret&retning=Faldende&side={side+1}"
        req = requests.get(url)
        soup = BeautifulSoup(req.text, "lxml")
        table = soup.find_all("table")[0]
        
        for link in table.find_all("a", href=True):
            href = link["href"]
            if "id=" in href:
                href = f"https://www.konkurser.dk{href}"
                text = link.text
                links.append((text, href))

        df = pd.read_html(req.text)[0]
        dict_list.append(df.to_dict())
        pbar.update()

    adresseliste = []
    for side in dict_list:    
        adresser = side["Adresse"]
        for i in adresser:
            adresseliste.append(f"{adresser.get(i)}, 8000 Aarhus C")
    
    return adresseliste, links



def num_split(s):
    return list(filter(None, re.split(r'(\d+)', s)))



def get_konkurser(adresseliste, links):
    konkurser = []
    pbar = tqdm(total=len(adresseliste), leave=False)
    for i, adresse in enumerate(adresseliste):
        pbar.set_description("Slår adressernes koordinater op")
        url = f"https://api.dataforsyningen.dk/adresser?q={adresse}&struktur=mini"
        req = requests.get(url)
        try:
            result = json.loads(req.text)[0]
        except IndexError:
            adresse_split = num_split(adresse)
            del adresse_split[2:-2]
            adresse = " ".join(adresse_split)
            url = f"https://api.dataforsyningen.dk/adresser?q={adresse}&struktur=mini"
            req = requests.get(url)
            try:
                result = json.loads(req.text)[0]
            except IndexError:
                pbar.write(f"ERROR: {adresse}")
                continue

        x_coord = result["x"]
        y_coord = result["y"]
        coordinate_tuple = (x_coord, y_coord)
        konkurser.append({"url": links[i], "coordinates": coordinate_tuple})
        pbar.update()
    
    return konkurser


adresseliste, links = get_adresseliste()
konkurser = get_konkurser(adresseliste, links)
  
    
map = folium.Map(location=[56.152935, 10.201331], zoom_start=14)

# Create marker groups
konkurs_feature_group = folium.FeatureGroup("Konkursboer")
industri_feature_group = folium.FeatureGroup("Industrikvarterer")

# Add konkursboer-group to map
for i, konkurs in enumerate(konkurser):
    url = konkurs["url"]
    coordinates = konkurs["coordinates"]
    info = f"<b>{links[i][0]}</b><br><br><a href=\"{links[i][1]}\">Vis på konkurser.dk</a>"
    folium.Marker([coordinates[1], coordinates[0]], popup=info, icon=folium.Icon(color="blue")).add_to(konkurs_feature_group)
konkurs_feature_group.add_to(map)

# Add industrial sites-group to map
bbox = "56.11626813,10.17165345,56.17448857,10.33170603" # Aarhus
for coordinates in get_industrial_sites(bbox):

    folium.Marker([coordinates[0], coordinates[1]], icon=folium.Icon(color="red")).add_to(industri_feature_group)
industri_feature_group.add_to(map)

folium.LayerControl().add_to(map)
map_file = "konkurskort.html"
map.save(map_file)
print(f"\nMap saved to {map_file}\n")