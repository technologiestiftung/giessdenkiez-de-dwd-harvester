def extract(weather_list, field):
    return [
        data_point[field]
        for data_point in weather_list
        if data_point[field] is not None
    ]
