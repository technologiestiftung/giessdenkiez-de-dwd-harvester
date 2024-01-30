from tqdm import tqdm
from typing import NamedTuple
import math


class Position(NamedTuple):
    lat: float
    lng: float


def offset(
    lat: float, lon: float, toEastInMeters: float, toSouthInMeters: float
) -> Position:
    AVERAGE_RADIUS_OF_EARTH_M = 6371000
    dLat = -1.0 * (toSouthInMeters / AVERAGE_RADIUS_OF_EARTH_M)
    dLon = toEastInMeters / (
        AVERAGE_RADIUS_OF_EARTH_M * (math.cos((math.pi * lat) / 180))
    )
    newLat = lat + (dLat * 180) / math.pi
    newLon = lon + (dLon * 180) / math.pi
    return Position(lat=newLat, lng=newLon)


def generateCylinderGeojson(trees):
    featureTemplate = {
        "type": "Feature",
        "properties": {
            "level": 1,
        },
        "geometry": {
            "coordinates": [],
            "type": "Polygon",
        },
        "id": "",
    }
    offsetMeters = 2
    features = []
    for tree in tqdm(trees):
        lat = float(tree[2])
        lng = float(tree[1])

        topLeft = offset(lat, lng, offsetMeters * 1.9, -offsetMeters * 2)
        topRight = offset(lat, lng, -offsetMeters * 1.5, -offsetMeters * 2)
        bottomLeft = offset(lat, lng, offsetMeters * 1.9, offsetMeters)
        bottomRight = offset(lat, lng, -offsetMeters * 1.5, offsetMeters)
        topLeftLat, topLeftLng = topLeft.lat, topLeft.lng
        topRightLat, topRightLng = topRight.lat, topRight.lng
        bottomLeftLat, bottomLeftLng = bottomLeft.lat, bottomLeft.lng
        bottomRightLat, bottomRightLng = bottomRight.lat, bottomRight.lng

        feature = {
            **featureTemplate,
            "id": tree[0],
            "properties": {
                "id": tree[0],
                "lat": lat,
                "lng": lng,
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [topLeftLng, topLeftLat],
                        [topRightLng, topRightLat],
                        [bottomRightLng, bottomRightLat],
                        [bottomLeftLng, bottomLeftLat],
                        [topLeftLng, topLeftLat],
                    ],
                ],
            },
        }
        features.append(feature)

    geojson = {"features": features, "type": "FeatureCollection"}

    return geojson
