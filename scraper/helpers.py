import re


def _determine_car_colour(car_html: str) -> str:
    if re.search(r"Pearl White", car_html):
        return "Pearl White"
    elif re.search(r"Solid Black", car_html):
        return "Solid Black"
    elif re.search(r"Deep Blue Metallic", car_html):
        return "Deep Blue Metallic"
    elif re.search(r"Stealth Grey", car_html):
        return "Stealth Grey"
    elif re.search(r"Quicksilver", car_html):
        return "Quicksilver"
    elif re.search(r"Ultra Red", car_html):
        return "Ultra Red"
    return "UNKNOWN"
