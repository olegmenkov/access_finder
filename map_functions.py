import requests
from geopy.distance import geodesic


async def get_coordinates(district):
    """Получает координаты района Москвы через Nominatim API"""
    url = "https://nominatim.openstreetmap.org/search"
    params = {
        "q": f"{district}, Москва, Россия",
        "format": "jsonv2",
        "countrycodes": "RU",
        "limit": 1
    }
    headers = {"User-Agent": "MyAccessibilityApp/1.0"}
    response = requests.get(url, params=params, headers=headers)

    if response.status_code == 403:
        return None

    data = response.json()
    if data:
        return float(data[0]["lat"]), float(data[0]["lon"])
    return None


def get_address(lat, lon):
    """Определяет адрес места по его координатам через Nominatim Reverse API"""
    url = "https://nominatim.openstreetmap.org/reverse"
    params = {
        "lat": lat,
        "lon": lon,
        "format": "jsonv2",
        "zoom": 18,
        "addressdetails": 1
    }
    headers = {
        "User-Agent": "MyAccessibilityApp/1.0 (your_email@example.com)"
    }

    response = requests.get(url, params=params, headers=headers)

    if response.status_code == 403:
        print("Ошибка 403: Доступ к Nominatim Reverse API запрещён.")
        return "Адрес не найден"

    data = response.json()
    address = data.get("address", {})

    street = address.get("road", "Неизвестная улица")
    house_number = address.get("house_number", "№ не указан")
    apartment = address.get("hamlet", "")  # Иногда используется в OSM как номер квартиры

    return f"{street}, {house_number} {apartment}".strip()


async def get_accessible_places(lat, lon, category):
    """Запрашивает доступные места через Overpass API"""
    category_filters = {
        "кафе": 'node["amenity"="cafe"]["wheelchair"="yes"]',
        "магазины": 'node["shop"]["wheelchair"="yes"]',
        "транспорт": 'node["public_transport"]["wheelchair"="yes"]',
        "музеи": 'node["tourism"="museum"]["wheelchair"="yes"]',
        "больницы": 'node["amenity"="hospital"]["wheelchair"="yes"]'
    }
    if category not in category_filters:
        return []

    query = f"""
    [out:json];
    (
      {category_filters[category]}(around:5000,{lat},{lon});
    );
    out body;
    """

    url = "https://overpass-api.de/api/interpreter"
    headers = {"User-Agent": "MyAccessibilityApp/1.0"}
    response = requests.get(url, params={"data": query}, headers=headers)

    if response.status_code == 403:
        return []

    data = response.json()
    places = []
    for element in data.get("elements", []):
        name = element.get("tags", {}).get("name")
        if not name or any(place["name"] == name for place in places):
            continue
        place_lat = element.get("lat")
        place_lon = element.get("lon")
        distance = geodesic((lat, lon), (place_lat, place_lon)).meters
        places.append({"name": name, "lat": place_lat, "lon": place_lon, "distance": distance})

    return sorted(places, key=lambda x: x["distance"])[:5]

