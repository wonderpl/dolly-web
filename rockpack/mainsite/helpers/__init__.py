try:
    import GeoIP
    geoip = GeoIP.open('/usr/share/GeoIP/GeoIP.dat', GeoIP.GEOIP_MEMORY_CACHE)
    geoip.set_charset(GeoIP.GEOIP_CHARSET_UTF8)
    get_country_code_from_address = geoip.country_code_by_addr
except Exception:
    get_country_code_from_address = lambda x: None
