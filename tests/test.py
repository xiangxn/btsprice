data={
        "default": {
            "core_exchange_factor": 1.20,
            "maintenance_collateral_ratio": 1750,
            "maximum_short_squeeze_ratio": 1100,
            "quote_asset": "BTS",
            "quote_asset_id": "1.3.0"
        },
        "GCNY": {
            "core_exchange_factor": 1.20,
            "maintenance_collateral_ratio": 1500,
            "maximum_short_squeeze_ratio": 1010,
            "quote_asset": "GDEX.BTC",
            "quote_asset_id": "1.3.2241"
        },
        "TUSD": {"maximum_short_squeeze_ratio": 1050}
    }

da = list(data)
print(da)