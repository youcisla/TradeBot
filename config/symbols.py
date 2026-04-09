"""Tradeable symbols — auto-generated from MT5 broker scan.
    Do NOT edit manually. Run: python scripts/scan_broker_symbols.py
"""

from __future__ import annotations


# ── All known symbols by asset class ───────────────────────────

FOREX_MAJORS: list[str] = [
    "AUDUSD", "EURUSD", "GBPUSD", "USDCAD", "USDCHF",
    "USDJPY"
]

FOREX_CROSSES: list[str] = [
    "GBXUSD", "USDAED", "USDCNH", "USDHKD", "USDSGD",
    "USDZAR"
]

FOREX_S_SUFFIX: list[str] = [   # .s forex variants
    "AUDCAD.s", "AUDCHF.s", "AUDJPY.s", "AUDNZD.s", "AUDSGD.s",
    "AUDUSD.s", "CADCHF.s", "CADJPY.s", "CHFJPY.s", "EURAUD.s",
    "EURCAD.s", "EURCHF.s", "EURCZK.s", "EURDKK.s", "EURGBP.s",
    "EURHUF.s", "EURJPY.s", "EURNZD.s", "EURSGD.s", "EURUSD.s",
    "GBPAUD.s", "GBPCAD.s", "GBPCHF.s", "GBPJPY.s", "GBPNZD.s",
    "GBPSGD.s", "GBPUSD.s", "NZDCAD.s", "NZDCHF.s", "NZDJPY.s",
    "NZDSGD.s", "NZDUSD.s", "SGDJPY.s", "USDAED.s", "USDBRL.s",
    "USDCAD.s", "USDCHF.s", "USDCLP.s", "USDCOP.s", "USDCZK.s",
    "USDDKK.s", "USDHKD.s", "USDHUF.s", "USDIDR.s", "USDILS.s",
    "USDINR.s", "USDJPY.s", "USDKRW.s", "USDMXN.s", "USDNOK.s",
    "USDSEK.s", "USDSGD.s", "USDTHB.s", "USDTWD.s", "USDZAR.s"
]

COMMODITIES: list[str] = [
    "COPPER-Cs", "Cocoa-Cs", "Coffee-Cs", "Cotton-Cs", "GAS-Cs",
    "GASOIL-Cs", "GAUUSD.s", "NG-Cs", "OJ-Cs", "ROBUSTAft.s",
    "Soybean-Cs", "Sugar-Cs", "Wheat-Cs", "XAGUSD.s", "XAUEUR.s",
    "XAUJPY.s", "XAUUSD.s", "XPDUSD.s", "XPTUSD.s"
]

INDICES: list[str] = [   # Index CFDs (.s)
    "BVSPX.s", "CHINA50.s", "CHINA50ft.s", "CHINAH.s", "DJ30.s",
    "DJ30ft.s", "ES35.s", "EU50.s", "FRA40.s", "FRA40ft.s",
    "GER40.s", "GER40ft.s", "HK50.s", "HK50ft.s", "HKTECH.s",
    "JPN225ft.s", "NAS100.s", "NAS100ft.s", "NETH25.s", "Nikkei225.s",
    "SA40.s", "SGP20.s", "SP500.s", "SP500ft.s", "SPI200.s",
    "SWI20.s", "TWINDEX.s", "UK100.s", "UK100ft.s", "US2000.s",
    "USDX.s", "VIX.s"
]

ETFS: list[str] = [
    "AGG", "ARKB", "ARKG", "ARKK", "ARKQ",
    "ARKW", "BITB", "BITO", "BITQ", "BKCH",
    "BLCN", "BLOK", "BND", "BNDX", "BNO",
    "BTCO", "DBA", "DBC", "EEM", "EFA",
    "ESGV", "FAS", "FAZ", "FDN", "FXI",
    "GBTC", "GDX", "GDXJ", "GLD", "GOAU",
    "GOEX", "GRID", "GSG", "IBIT", "ICLN",
    "IWM", "IYW", "JNUG", "NUGT", "OIH",
    "QCLN", "QQQ", "RING", "SDS", "SGDJ",
    "SGDM", "SLVP", "SPY", "SPYX", "TAN",
    "USL", "USO", "VGT", "VSGX", "XLF",
    "XLK", "XOP"
]

CRYPTO: list[str] = [
    "ADAJPY", "ADAUSD", "ALGUSD", "ATMUSD", "AVAUSD",
    "BATUSD", "BCHJPY", "BCHUSD", "BERAUSD", "BNBUSD",
    "BTCBCH", "BTCETH", "BTCEUR", "BTCJPY", "BTCLTC",
    "BTCUSD", "BTCXAU", "CROUSD", "CRVUSD", "DOGUSD",
    "DOTUSD", "EOSUSD", "ETCUSD", "ETHBCH", "ETHEUR",
    "ETHJPY", "ETHLTC", "ETHUSD", "ETHXAU", "FILUSD",
    "GRTUSD", "HBARUSD", "HYPEUSD", "INCUSD", "IOTUSD",
    "LNKUSD", "LRCUSD", "LTCJPY", "LTCUSD", "MKRUSD",
    "NEOUSD", "NERUSD", "NXPCUSD", "OKBUSD", "ONDOUSD",
    "ONEUSD", "SANUSD", "SHBUSD", "SKYUSD", "SOLJPY",
    "SOLUSD", "SUSUSD", "TRUMPUSD", "TRXUSD", "UNIUSD",
    "USDTJPY", "WIFUSD", "WLDUSD", "WLFIUSD", "XLMJPY",
    "XLMUSD", "XRPJPY", "XRPUSD", "XTZUSD", "ZECUSD"
]

STOCK_CFDS: list[str] = [   # Individual stock CFDs
    "A", "AA", "AALB", "AALG", "AAPL",
    "ABBVIE", "ABDN", "ABNB", "ABT", "AC",
    "ACN", "ADBE", "ADI", "ADM", "ADP",
    "ADPR", "ADS", "ADSK", "ADYEN", "AENA",
    "AEP", "AFG", "AFL", "AFX", "AGNC",
    "AIG", "AKAM", "AKZA", "ALB", "ALGN",
    "ALIBABA", "ALK", "ALLC", "AMAT", "AMAZON",
    "AMCX", "AMD", "AMGN", "AMPF", "AMS",
    "AMT", "AMUN", "AMWL", "ANA", "ANTO",
    "AON", "APA", "APD", "APH", "APTV",
    "ASM", "ASRNL", "AT&T", "AUPH", "AUTO",
    "AVB", "AVGO", "AXP", "AZO", "BAC",
    "BAIDU", "BAP", "BAX", "BB", "BBWI",
    "BBY", "BDX", "BE", "BEI", "BEN",
    "BIIB", "BK", "BKG", "BKNG", "BKR",
    "BLDP", "BLK", "BLND", "BLNK", "BMBL",
    "BMRN", "BMW", "BMY", "BNGO", "BNR",
    "BNTX", "BNZL", "BOEING", "BOX", "BP",
    "BRBY", "BRKB", "BSX", "BUD", "BX",
    "CAH", "CAT", "CB", "CBOE", "CCH",
    "CCI", "CDI", "CDNS", "CFG", "CGC",
    "CHKP", "CHPT", "CHT", "CHTR", "CHWY",
    "CI", "CIM", "CISCO", "CITI", "CL",
    "CL-OIL.s", "CLNX", "CLX", "CMCSA", "CME",
    "CMI", "CNA", "CNC", "COF", "COIN",
    "COR", "COST", "COTY", "CPNG", "CPRI",
    "CRDA", "CRH", "CRM", "CRON", "CRWD",
    "CSX", "CTAS", "CTRA", "CTSH", "CVS",
    "CVX", "D", "DAL", "DASH", "DB1",
    "DBX", "DCC", "DD", "DDOG", "DE",
    "DELL", "DGC", "DHER", "DHI", "DHL",
    "DHR", "DIM", "DISNEY", "DKNG", "DLR",
    "DLTR", "DOCU", "DOW", "DTE", "DUK",
    "DVN", "DWNI", "DWS", "DXC", "DXCM",
    "EA", "EBAY", "ECL", "ED", "EDU",
    "EMN", "EMR", "ENPH", "ENT", "EOG",
    "EPD", "EQIX", "EQR", "ESL", "ESS",
    "ETD", "ETN", "ETSY", "EW", "EXC",
    "EXPE", "EXPN", "EXXON", "EZJ", "F",
    "FANG", "FAST", "FCEL", "FCX", "FDX",
    "FIE", "FIS", "FITB", "FLTR", "FME",
    "FOSL", "FOX", "FOXA", "FRA", "FRAS",
    "FRE", "FRES", "FSLR", "FTI", "FTNT",
    "FTV", "G24", "GD", "GE", "GEVO",
    "GFI", "GFS", "GILD", "GIS", "GLPG",
    "GLW", "GM", "GNRC", "GOOG", "GPN",
    "GPRO", "GRAB", "GRPN", "GRVY", "GS",
    "GT", "GWW", "HAL", "HBAN", "HCA",
    "HD", "HDB", "HEI", "HEN3", "HIK",
    "HLAG", "HLF", "HLMA", "HLT", "HNR1",
    "HOG", "HON", "HOOD", "HOT", "HPE",
    "HPQ", "HRB", "HSBCn", "HSX", "HSY",
    "HTHT", "HUBS", "HUM", "HUT", "HYLN",
    "IAC", "IBM", "IBN", "ICE", "ICL",
    "IDXX", "IHG", "III", "ILMN", "IMCD",
    "INCY", "INF", "INFY", "INO", "INSG",
    "INTEL", "INTU", "IOVA", "IP", "IQV",
    "IR", "ISRG", "ITRK", "ITV", "ITW",
    "IVZ", "JBL", "JCI", "JD", "JDI",
    "JMAT", "JNJ", "JPM", "KBX", "KDP",
    "KEY", "KGC", "KGF", "KGX", "KHC",
    "KKR", "KLAC", "KMI", "KO", "KODK",
    "KR", "KRN", "KSS", "LAC", "LAND",
    "LAUR", "LBTYK", "LC", "LCID", "LEG",
    "LEN", "LEVI", "LGEN", "LHX", "LI",
    "LLY", "LMT", "LOW", "LPL", "LRCX",
    "LSEG", "LULU", "LUMN", "LUV", "LVS",
    "LYB", "LYFT", "M", "MA", "MANU",
    "MAR", "MARA", "MAT", "MBG", "MBLY",
    "MCD", "MCHP", "MCK", "MCO", "MDLZ",
    "MDT", "MET", "META", "MFA", "MFC",
    "MGM", "MLM", "MMM", "MNDI", "MNG",
    "MNST", "MO", "MOH", "MOMO", "MPC",
    "MPLX", "MPWR", "MRCK", "MRK", "MRNA",
    "MRVL", "MS", "MSFT", "MTB", "MTCH",
    "MTX", "MUV2", "NBIX", "NBR", "NCLH",
    "NEE", "NEMD", "NET", "NFLX", "NGRID",
    "NIO", "NKE", "NN", "NOC", "NOW",
    "NSC", "NTAP", "NTES", "NTRS", "NUE",
    "NVIDIA", "NVS", "NWS", "NXPI", "NXT",
    "OCDO", "OIS", "OKE", "OKTA", "OMC",
    "OPFI", "ORCL", "ORLY", "OSTK", "OXY",
    "PANW", "PAYX", "PCAR", "PCG", "PDD",
    "PEG", "PENN", "PEP", "PFIZER", "PG",
    "PGR", "PH", "PINS", "PLAY", "PLD",
    "PLTR", "PLUG", "PM", "PNC", "POOL",
    "PPG", "PPL", "PRX", "PSA", "PSH",
    "PSN", "PSON", "PSX", "PTON", "PUM",
    "PVH", "PYPL", "QCOM", "QS", "RAA",
    "RACE", "RAND", "RBLX", "RCL", "REGN",
    "RF", "RGLD", "RIG", "RIVN", "RL",
    "RMV", "RNG", "ROK", "ROKU", "ROP",
    "ROST", "RR", "RRTL", "RSG", "RTO",
    "RTX", "RWE", "SBRY", "SBUX", "SCHW",
    "SDR", "SE", "SENS", "SGE", "SGRO",
    "SHL", "SHOP", "SHW", "SIG", "SIRI",
    "SLB", "SMG", "SMIN", "SMT", "SN",
    "SNAP", "SNOW", "SNPS", "SO", "SOFI",
    "SPCE", "SPG", "SPGI", "SPLK", "SPOT",
    "SPX", "SRE", "SRT3", "SSE", "STJ",
    "STT", "STZ", "SVT", "SW", "SWK",
    "SWKS", "SWR", "SY1", "SYF", "SYK",
    "SYY", "TCOM", "TDOC", "TEAM", "TEL",
    "TEVA", "TFC", "TGT", "TJX", "TLX",
    "TMO", "TMUS", "TOYOTA", "TRIP", "TRMB",
    "TROW", "TRST", "TRV", "TSLA", "TSM",
    "TSN", "TTD", "TTWO", "TW", "TWLO",
    "TXN", "U", "UA", "UAL", "UBER",
    "UKOUSD.s", "UKOUSDft.s", "UL", "ULTA", "UMC",
    "UNH", "UNP", "UPS", "UPST", "USB",
    "USOUSD.s", "UTDI", "UU", "VFC", "VFS",
    "VIRT", "VIS", "VISA", "VLO", "VMC",
    "VMW", "VNA", "VOW", "VPK", "VRTX",
    "VTRS", "VZ", "W", "WDAY", "WDC",
    "WEN", "WFC", "WISE", "WKHS", "WKL",
    "WM", "WMB", "WMT", "WPM", "WPP",
    "WTB", "WU", "WY", "WYNN", "XEL",
    "XPEV", "XRX", "YALA", "YUM", "YUMC",
    "Z", "ZAL", "ZBH", "ZBRA", "ZIM",
    "ZM", "ZTS"
]

BONDS: list[str] = [
    "EUB10Y", "EUB2Y", "EUB30Y", "EUB5Y", "EURIBOR3M",
    "LongGilt", "USNote10Y"
]

ALL_SYMBOLS: list[str] = (
    FOREX_MAJORS + FOREX_CROSSES + FOREX_S_SUFFIX
    + COMMODITIES + INDICES + ETFS + CRYPTO
    + STOCK_CFDS + BONDS
)


# ── Per-symbol pip value (from broker tick data) ────────────────
PIP_VALUES: dict[str, float] = {
    "A": 0.1,  # digits=2
    "AA": 0.1,  # digits=2
    "AALB": 0.001,  # digits=4
    "AALG": 0.1,  # digits=2
    "AAPL": 0.1,  # digits=2
    "ABBVIE": 0.1,  # digits=2
    "ABDN": 0.1,  # digits=2
    "ABNB": 0.1,  # digits=2
    "ABT": 0.1,  # digits=2
    "AC": 0.001,  # digits=4
    "ACN": 0.1,  # digits=2
    "ADAJPY": 0.01,  # digits=3
    "ADAUSD": 0.001,  # digits=4
    "ADBE": 0.1,  # digits=2
    "ADI": 0.1,  # digits=2
    "ADM": 0.1,  # digits=2
    "ADP": 0.1,  # digits=2
    "ADPR": 0.001,  # digits=4
    "ADS": 0.001,  # digits=4
    "ADSK": 0.1,  # digits=2
    "ADYEN": 0.001,  # digits=4
    "AENA": 0.001,  # digits=4
    "AEP": 0.1,  # digits=2
    "AFG": 0.1,  # digits=2
    "AFL": 0.1,  # digits=2
    "AFX": 0.001,  # digits=4
    "AGG": 0.1,  # digits=2
    "AGNC": 0.1,  # digits=2
    "AIG": 0.1,  # digits=2
    "AKAM": 0.1,  # digits=2
    "AKZA": 0.001,  # digits=4
    "ALB": 0.1,  # digits=2
    "ALGN": 0.1,  # digits=2
    "ALGUSD": 0.001,  # digits=4
    "ALIBABA": 0.1,  # digits=2
    "ALK": 0.1,  # digits=2
    "ALLC": 0.1,  # digits=2
    "AMAT": 0.1,  # digits=2
    "AMAZON": 0.1,  # digits=2
    "AMCX": 0.1,  # digits=2
    "AMD": 0.1,  # digits=2
    "AMGN": 0.1,  # digits=2
    "AMPF": 0.1,  # digits=2
    "AMS": 0.001,  # digits=4
    "AMT": 0.1,  # digits=2
    "AMUN": 0.001,  # digits=4
    "AMWL": 0.1,  # digits=2
    "ANA": 0.001,  # digits=4
    "ANTO": 0.1,  # digits=2
    "AON": 0.1,  # digits=2
    "APA": 0.1,  # digits=2
    "APD": 0.1,  # digits=2
    "APH": 0.1,  # digits=2
    "APTV": 0.1,  # digits=2
    "ARKB": 0.1,  # digits=2
    "ARKG": 0.1,  # digits=2
    "ARKK": 0.1,  # digits=2
    "ARKQ": 0.1,  # digits=2
    "ARKW": 0.1,  # digits=2
    "ASM": 0.001,  # digits=4
    "ASRNL": 0.001,  # digits=4
    "AT&T": 0.1,  # digits=2
    "ATMUSD": 0.01,  # digits=3
    "AUDCAD.s": 0.0001,  # digits=5
    "AUDCHF.s": 0.0001,  # digits=5
    "AUDJPY.s": 0.01,  # digits=3
    "AUDNZD.s": 0.0001,  # digits=5
    "AUDSGD.s": 0.0001,  # digits=5
    "AUDUSD": 0.0001,  # digits=5
    "AUDUSD.s": 0.0001,  # digits=5
    "AUPH": 0.1,  # digits=2
    "AUTO": 0.1,  # digits=2
    "AVAUSD": 0.1,  # digits=2
    "AVB": 0.1,  # digits=2
    "AVGO": 0.1,  # digits=2
    "AXP": 0.1,  # digits=2
    "AZO": 0.1,  # digits=2
    "BAC": 0.1,  # digits=2
    "BAIDU": 0.1,  # digits=2
    "BAP": 0.1,  # digits=2
    "BATUSD": 0.001,  # digits=4
    "BAX": 0.1,  # digits=2
    "BB": 0.1,  # digits=2
    "BBWI": 0.1,  # digits=2
    "BBY": 0.1,  # digits=2
    "BCHJPY": 10.0,  # digits=0
    "BCHUSD": 0.1,  # digits=2
    "BDX": 0.1,  # digits=2
    "BE": 0.1,  # digits=2
    "BEI": 0.001,  # digits=4
    "BEN": 0.1,  # digits=2
    "BERAUSD": 0.001,  # digits=4
    "BIIB": 0.1,  # digits=2
    "BITB": 0.1,  # digits=2
    "BITO": 0.1,  # digits=2
    "BITQ": 0.1,  # digits=2
    "BK": 0.1,  # digits=2
    "BKCH": 0.1,  # digits=2
    "BKG": 0.1,  # digits=2
    "BKNG": 0.1,  # digits=2
    "BKR": 0.1,  # digits=2
    "BLCN": 0.1,  # digits=2
    "BLDP": 0.1,  # digits=2
    "BLK": 0.1,  # digits=2
    "BLND": 0.1,  # digits=2
    "BLNK": 0.1,  # digits=2
    "BLOK": 0.1,  # digits=2
    "BMBL": 0.1,  # digits=2
    "BMRN": 0.1,  # digits=2
    "BMW": 0.001,  # digits=4
    "BMY": 0.1,  # digits=2
    "BNBUSD": 0.1,  # digits=2
    "BND": 0.1,  # digits=2
    "BNDX": 0.1,  # digits=2
    "BNGO": 0.1,  # digits=2
    "BNO": 0.1,  # digits=2
    "BNR": 0.001,  # digits=4
    "BNTX": 0.1,  # digits=2
    "BNZL": 0.1,  # digits=2
    "BOEING": 0.1,  # digits=2
    "BOX": 0.1,  # digits=2
    "BP": 0.1,  # digits=2
    "BRBY": 0.1,  # digits=2
    "BRKB": 0.1,  # digits=2
    "BSX": 0.1,  # digits=2
    "BTCBCH": 0.01,  # digits=3
    "BTCETH": 0.001,  # digits=4
    "BTCEUR": 0.1,  # digits=2
    "BTCJPY": 10.0,  # digits=0
    "BTCLTC": 0.01,  # digits=3
    "BTCO": 0.1,  # digits=2
    "BTCUSD": 0.1,  # digits=2
    "BTCXAU": 0.0001,  # digits=5
    "BUD": 0.1,  # digits=2
    "BVSPX.s": 0.1,  # digits=2
    "BX": 0.1,  # digits=2
    "CADCHF.s": 0.0001,  # digits=5
    "CADJPY.s": 0.01,  # digits=3
    "CAH": 0.1,  # digits=2
    "CAT": 0.1,  # digits=2
    "CB": 0.1,  # digits=2
    "CBOE": 0.1,  # digits=2
    "CCH": 0.1,  # digits=2
    "CCI": 0.1,  # digits=2
    "CDI": 0.001,  # digits=4
    "CDNS": 0.1,  # digits=2
    "CFG": 0.1,  # digits=2
    "CGC": 0.1,  # digits=2
    "CHFJPY.s": 0.01,  # digits=3
    "CHINA50.s": 10.0,  # digits=0
    "CHINA50ft.s": 1.0,  # digits=1
    "CHINAH.s": 0.1,  # digits=2
    "CHKP": 0.1,  # digits=2
    "CHPT": 0.1,  # digits=2
    "CHT": 0.1,  # digits=2
    "CHTR": 0.1,  # digits=2
    "CHWY": 0.1,  # digits=2
    "CI": 0.1,  # digits=2
    "CIM": 0.1,  # digits=2
    "CISCO": 0.1,  # digits=2
    "CITI": 0.1,  # digits=2
    "CL": 0.1,  # digits=2
    "CL-OIL.s": 0.01,  # digits=3
    "CLNX": 0.001,  # digits=4
    "CLX": 0.1,  # digits=2
    "CMCSA": 0.1,  # digits=2
    "CME": 0.1,  # digits=2
    "CMI": 0.1,  # digits=2
    "CNA": 0.1,  # digits=2
    "CNC": 0.1,  # digits=2
    "COF": 0.1,  # digits=2
    "COIN": 0.1,  # digits=2
    "COPPER-Cs": 0.001,  # digits=4
    "COR": 0.1,  # digits=2
    "COST": 0.1,  # digits=2
    "COTY": 0.1,  # digits=2
    "CPNG": 0.1,  # digits=2
    "CPRI": 0.1,  # digits=2
    "CRDA": 0.1,  # digits=2
    "CRH": 0.1,  # digits=2
    "CRM": 0.1,  # digits=2
    "CRON": 0.1,  # digits=2
    "CROUSD": 0.0001,  # digits=5
    "CRVUSD": 0.01,  # digits=3
    "CRWD": 0.1,  # digits=2
    "CSX": 0.1,  # digits=2
    "CTAS": 0.1,  # digits=2
    "CTRA": 0.1,  # digits=2
    "CTSH": 0.1,  # digits=2
    "CVS": 0.1,  # digits=2
    "CVX": 0.1,  # digits=2
    "Cocoa-Cs": 1.0,  # digits=1
    "Coffee-Cs": 0.001,  # digits=4
    "Cotton-Cs": 0.0001,  # digits=5
    "D": 0.1,  # digits=2
    "DAL": 0.1,  # digits=2
    "DASH": 0.1,  # digits=2
    "DB1": 0.001,  # digits=4
    "DBA": 0.1,  # digits=2
    "DBC": 0.1,  # digits=2
    "DBX": 0.1,  # digits=2
    "DCC": 0.1,  # digits=2
    "DD": 0.1,  # digits=2
    "DDOG": 0.1,  # digits=2
    "DE": 0.1,  # digits=2
    "DELL": 0.1,  # digits=2
    "DGC": 0.1,  # digits=2
    "DHER": 0.001,  # digits=4
    "DHI": 0.1,  # digits=2
    "DHL": 0.1,  # digits=2
    "DHR": 0.1,  # digits=2
    "DIM": 0.001,  # digits=4
    "DISNEY": 0.1,  # digits=2
    "DJ30.s": 0.1,  # digits=2
    "DJ30ft.s": 0.1,  # digits=2
    "DKNG": 0.1,  # digits=2
    "DLR": 0.1,  # digits=2
    "DLTR": 0.1,  # digits=2
    "DOCU": 0.1,  # digits=2
    "DOGUSD": 0.001,  # digits=4
    "DOTUSD": 0.01,  # digits=3
    "DOW": 0.1,  # digits=2
    "DTE": 0.1,  # digits=2
    "DUK": 0.1,  # digits=2
    "DVN": 0.1,  # digits=2
    "DWNI": 0.001,  # digits=4
    "DWS": 0.001,  # digits=4
    "DXC": 0.1,  # digits=2
    "DXCM": 0.1,  # digits=2
    "EA": 0.1,  # digits=2
    "EBAY": 0.1,  # digits=2
    "ECL": 0.1,  # digits=2
    "ED": 0.1,  # digits=2
    "EDU": 0.1,  # digits=2
    "EEM": 0.1,  # digits=2
    "EFA": 0.1,  # digits=2
    "EMN": 0.1,  # digits=2
    "EMR": 0.1,  # digits=2
    "ENPH": 0.1,  # digits=2
    "ENT": 0.1,  # digits=2
    "EOG": 0.1,  # digits=2
    "EOSUSD": 0.001,  # digits=4
    "EPD": 0.1,  # digits=2
    "EQIX": 0.1,  # digits=2
    "EQR": 0.1,  # digits=2
    "ES35.s": 0.1,  # digits=2
    "ESGV": 0.1,  # digits=2
    "ESL": 0.1,  # digits=2
    "ESS": 0.1,  # digits=2
    "ETCUSD": 0.01,  # digits=3
    "ETD": 0.1,  # digits=2
    "ETHBCH": 0.001,  # digits=4
    "ETHEUR": 0.1,  # digits=2
    "ETHJPY": 10.0,  # digits=0
    "ETHLTC": 0.001,  # digits=4
    "ETHUSD": 0.1,  # digits=2
    "ETHXAU": 0.0001,  # digits=5
    "ETN": 0.1,  # digits=2
    "ETSY": 0.1,  # digits=2
    "EU50.s": 0.1,  # digits=2
    "EUB10Y": 0.1,  # digits=2
    "EUB2Y": 0.1,  # digits=2
    "EUB30Y": 0.1,  # digits=2
    "EUB5Y": 0.1,  # digits=2
    "EURAUD.s": 0.0001,  # digits=5
    "EURCAD.s": 0.0001,  # digits=5
    "EURCHF.s": 0.0001,  # digits=5
    "EURCZK.s": 0.001,  # digits=4
    "EURDKK.s": 0.0001,  # digits=5
    "EURGBP.s": 0.0001,  # digits=5
    "EURHUF.s": 0.01,  # digits=3
    "EURIBOR3M": 0.01,  # digits=3
    "EURJPY.s": 0.01,  # digits=3
    "EURNZD.s": 0.0001,  # digits=5
    "EURSGD.s": 0.0001,  # digits=5
    "EURUSD": 0.0001,  # digits=5
    "EURUSD.s": 0.0001,  # digits=5
    "EW": 0.1,  # digits=2
    "EXC": 0.1,  # digits=2
    "EXPE": 0.1,  # digits=2
    "EXPN": 0.1,  # digits=2
    "EXXON": 0.1,  # digits=2
    "EZJ": 0.1,  # digits=2
    "F": 0.1,  # digits=2
    "FANG": 0.1,  # digits=2
    "FAS": 0.1,  # digits=2
    "FAST": 0.1,  # digits=2
    "FAZ": 0.1,  # digits=2
    "FCEL": 0.1,  # digits=2
    "FCX": 0.1,  # digits=2
    "FDN": 0.1,  # digits=2
    "FDX": 0.1,  # digits=2
    "FIE": 0.001,  # digits=4
    "FILUSD": 0.1,  # digits=2
    "FIS": 0.1,  # digits=2
    "FITB": 0.1,  # digits=2
    "FLTR": 0.1,  # digits=2
    "FME": 0.001,  # digits=4
    "FOSL": 0.1,  # digits=2
    "FOX": 0.1,  # digits=2
    "FOXA": 0.1,  # digits=2
    "FRA": 0.001,  # digits=4
    "FRA40.s": 0.1,  # digits=2
    "FRA40ft.s": 0.1,  # digits=2
    "FRAS": 0.1,  # digits=2
    "FRE": 0.001,  # digits=4
    "FRES": 0.1,  # digits=2
    "FSLR": 0.1,  # digits=2
    "FTI": 0.1,  # digits=2
    "FTNT": 0.1,  # digits=2
    "FTV": 0.1,  # digits=2
    "FXI": 0.1,  # digits=2
    "G24": 0.001,  # digits=4
    "GAS-Cs": 0.001,  # digits=4
    "GASOIL-Cs": 0.1,  # digits=2
    "GAUUSD.s": 0.1,  # digits=2
    "GBPAUD.s": 0.0001,  # digits=5
    "GBPCAD.s": 0.0001,  # digits=5
    "GBPCHF.s": 0.0001,  # digits=5
    "GBPJPY.s": 0.01,  # digits=3
    "GBPNZD.s": 0.0001,  # digits=5
    "GBPSGD.s": 0.0001,  # digits=5
    "GBPUSD": 0.0001,  # digits=5
    "GBPUSD.s": 0.0001,  # digits=5
    "GBTC": 0.1,  # digits=2
    "GBXUSD": 0.0001,  # digits=5
    "GD": 0.1,  # digits=2
    "GDX": 0.1,  # digits=2
    "GDXJ": 0.1,  # digits=2
    "GE": 0.1,  # digits=2
    "GER40.s": 0.1,  # digits=2
    "GER40ft.s": 0.1,  # digits=2
    "GEVO": 0.1,  # digits=2
    "GFI": 0.1,  # digits=2
    "GFS": 0.1,  # digits=2
    "GILD": 0.1,  # digits=2
    "GIS": 0.1,  # digits=2
    "GLD": 0.1,  # digits=2
    "GLPG": 0.001,  # digits=4
    "GLW": 0.1,  # digits=2
    "GM": 0.1,  # digits=2
    "GNRC": 0.1,  # digits=2
    "GOAU": 0.1,  # digits=2
    "GOEX": 0.1,  # digits=2
    "GOOG": 0.1,  # digits=2
    "GPN": 0.1,  # digits=2
    "GPRO": 0.1,  # digits=2
    "GRAB": 0.1,  # digits=2
    "GRID": 0.1,  # digits=2
    "GRPN": 0.1,  # digits=2
    "GRTUSD": 0.001,  # digits=4
    "GRVY": 0.1,  # digits=2
    "GS": 0.1,  # digits=2
    "GSG": 0.1,  # digits=2
    "GT": 0.1,  # digits=2
    "GWW": 0.1,  # digits=2
    "HAL": 0.1,  # digits=2
    "HBAN": 0.1,  # digits=2
    "HBARUSD": 0.0001,  # digits=5
    "HCA": 0.1,  # digits=2
    "HD": 0.1,  # digits=2
    "HDB": 0.1,  # digits=2
    "HEI": 0.001,  # digits=4
    "HEN3": 0.001,  # digits=4
    "HIK": 0.1,  # digits=2
    "HK50.s": 10.0,  # digits=0
    "HK50ft.s": 0.1,  # digits=2
    "HKTECH.s": 0.1,  # digits=2
    "HLAG": 0.001,  # digits=4
    "HLF": 0.1,  # digits=2
    "HLMA": 0.1,  # digits=2
    "HLT": 0.1,  # digits=2
    "HNR1": 0.001,  # digits=4
    "HOG": 0.1,  # digits=2
    "HON": 0.1,  # digits=2
    "HOOD": 0.1,  # digits=2
    "HOT": 0.001,  # digits=4
    "HPE": 0.1,  # digits=2
    "HPQ": 0.1,  # digits=2
    "HRB": 0.1,  # digits=2
    "HSBCn": 0.1,  # digits=2
    "HSX": 0.1,  # digits=2
    "HSY": 0.1,  # digits=2
    "HTHT": 0.1,  # digits=2
    "HUBS": 0.1,  # digits=2
    "HUM": 0.1,  # digits=2
    "HUT": 0.1,  # digits=2
    "HYLN": 0.1,  # digits=2
    "HYPEUSD": 0.1,  # digits=2
    "IAC": 0.1,  # digits=2
    "IBIT": 0.1,  # digits=2
    "IBM": 0.1,  # digits=2
    "IBN": 0.1,  # digits=2
    "ICE": 0.1,  # digits=2
    "ICL": 0.1,  # digits=2
    "ICLN": 0.1,  # digits=2
    "IDXX": 0.1,  # digits=2
    "IHG": 0.1,  # digits=2
    "III": 0.1,  # digits=2
    "ILMN": 0.1,  # digits=2
    "IMCD": 0.001,  # digits=4
    "INCUSD": 0.001,  # digits=4
    "INCY": 0.1,  # digits=2
    "INF": 0.1,  # digits=2
    "INFY": 0.1,  # digits=2
    "INO": 0.1,  # digits=2
    "INSG": 0.1,  # digits=2
    "INTEL": 0.1,  # digits=2
    "INTU": 0.1,  # digits=2
    "IOTUSD": 0.001,  # digits=4
    "IOVA": 0.1,  # digits=2
    "IP": 0.1,  # digits=2
    "IQV": 0.1,  # digits=2
    "IR": 0.1,  # digits=2
    "ISRG": 0.1,  # digits=2
    "ITRK": 0.1,  # digits=2
    "ITV": 0.1,  # digits=2
    "ITW": 0.1,  # digits=2
    "IVZ": 0.1,  # digits=2
    "IWM": 0.1,  # digits=2
    "IYW": 0.1,  # digits=2
    "JBL": 0.1,  # digits=2
    "JCI": 0.1,  # digits=2
    "JD": 0.1,  # digits=2
    "JDI": 0.1,  # digits=2
    "JMAT": 0.1,  # digits=2
    "JNJ": 0.1,  # digits=2
    "JNUG": 0.1,  # digits=2
    "JPM": 0.1,  # digits=2
    "JPN225ft.s": 0.1,  # digits=2
    "KBX": 0.001,  # digits=4
    "KDP": 0.1,  # digits=2
    "KEY": 0.1,  # digits=2
    "KGC": 0.1,  # digits=2
    "KGF": 0.1,  # digits=2
    "KGX": 0.001,  # digits=4
    "KHC": 0.1,  # digits=2
    "KKR": 0.1,  # digits=2
    "KLAC": 0.1,  # digits=2
    "KMI": 0.1,  # digits=2
    "KO": 0.1,  # digits=2
    "KODK": 0.1,  # digits=2
    "KR": 0.1,  # digits=2
    "KRN": 0.001,  # digits=4
    "KSS": 0.1,  # digits=2
    "LAC": 0.1,  # digits=2
    "LAND": 0.1,  # digits=2
    "LAUR": 0.1,  # digits=2
    "LBTYK": 0.1,  # digits=2
    "LC": 0.1,  # digits=2
    "LCID": 0.1,  # digits=2
    "LEG": 0.001,  # digits=4
    "LEN": 0.1,  # digits=2
    "LEVI": 0.1,  # digits=2
    "LGEN": 0.1,  # digits=2
    "LHX": 0.1,  # digits=2
    "LI": 0.1,  # digits=2
    "LLY": 0.1,  # digits=2
    "LMT": 0.1,  # digits=2
    "LNKUSD": 0.01,  # digits=3
    "LOW": 0.1,  # digits=2
    "LPL": 0.1,  # digits=2
    "LRCUSD": 0.001,  # digits=4
    "LRCX": 0.1,  # digits=2
    "LSEG": 0.1,  # digits=2
    "LTCJPY": 10.0,  # digits=0
    "LTCUSD": 0.1,  # digits=2
    "LULU": 0.1,  # digits=2
    "LUMN": 0.1,  # digits=2
    "LUV": 0.1,  # digits=2
    "LVS": 0.1,  # digits=2
    "LYB": 0.1,  # digits=2
    "LYFT": 0.1,  # digits=2
    "LongGilt": 0.1,  # digits=2
    "M": 0.1,  # digits=2
    "MA": 0.1,  # digits=2
    "MANU": 0.1,  # digits=2
    "MAR": 0.1,  # digits=2
    "MARA": 0.1,  # digits=2
    "MAT": 0.1,  # digits=2
    "MBG": 0.001,  # digits=4
    "MBLY": 0.1,  # digits=2
    "MCD": 0.1,  # digits=2
    "MCHP": 0.1,  # digits=2
    "MCK": 0.1,  # digits=2
    "MCO": 0.1,  # digits=2
    "MDLZ": 0.1,  # digits=2
    "MDT": 0.1,  # digits=2
    "MET": 0.1,  # digits=2
    "META": 0.1,  # digits=2
    "MFA": 0.1,  # digits=2
    "MFC": 0.1,  # digits=2
    "MGM": 0.1,  # digits=2
    "MKRUSD": 0.1,  # digits=2
    "MLM": 0.1,  # digits=2
    "MMM": 0.1,  # digits=2
    "MNDI": 0.1,  # digits=2
    "MNG": 0.1,  # digits=2
    "MNST": 0.1,  # digits=2
    "MO": 0.1,  # digits=2
    "MOH": 0.1,  # digits=2
    "MOMO": 0.1,  # digits=2
    "MPC": 0.1,  # digits=2
    "MPLX": 0.1,  # digits=2
    "MPWR": 0.1,  # digits=2
    "MRCK": 0.001,  # digits=4
    "MRK": 0.1,  # digits=2
    "MRNA": 0.1,  # digits=2
    "MRVL": 0.1,  # digits=2
    "MS": 0.1,  # digits=2
    "MSFT": 0.1,  # digits=2
    "MTB": 0.1,  # digits=2
    "MTCH": 0.1,  # digits=2
    "MTX": 0.001,  # digits=4
    "MUV2": 0.001,  # digits=4
    "NAS100.s": 0.1,  # digits=2
    "NAS100ft.s": 0.1,  # digits=2
    "NBIX": 0.1,  # digits=2
    "NBR": 0.1,  # digits=2
    "NCLH": 0.1,  # digits=2
    "NEE": 0.1,  # digits=2
    "NEMD": 0.001,  # digits=4
    "NEOUSD": 0.1,  # digits=2
    "NERUSD": 0.01,  # digits=3
    "NET": 0.1,  # digits=2
    "NETH25.s": 0.1,  # digits=2
    "NFLX": 0.1,  # digits=2
    "NG-Cs": 0.01,  # digits=3
    "NGRID": 0.1,  # digits=2
    "NIO": 0.1,  # digits=2
    "NKE": 0.1,  # digits=2
    "NN": 0.001,  # digits=4
    "NOC": 0.1,  # digits=2
    "NOW": 0.1,  # digits=2
    "NSC": 0.1,  # digits=2
    "NTAP": 0.1,  # digits=2
    "NTES": 0.1,  # digits=2
    "NTRS": 0.1,  # digits=2
    "NUE": 0.1,  # digits=2
    "NUGT": 0.1,  # digits=2
    "NVIDIA": 0.1,  # digits=2
    "NVS": 0.1,  # digits=2
    "NWS": 0.1,  # digits=2
    "NXPCUSD": 0.0001,  # digits=5
    "NXPI": 0.1,  # digits=2
    "NXT": 0.1,  # digits=2
    "NZDCAD.s": 0.0001,  # digits=5
    "NZDCHF.s": 0.0001,  # digits=5
    "NZDJPY.s": 0.01,  # digits=3
    "NZDSGD.s": 0.0001,  # digits=5
    "NZDUSD.s": 0.0001,  # digits=5
    "Nikkei225.s": 0.1,  # digits=2
    "OCDO": 0.1,  # digits=2
    "OIH": 0.1,  # digits=2
    "OIS": 0.1,  # digits=2
    "OJ-Cs": 0.001,  # digits=4
    "OKBUSD": 0.1,  # digits=2
    "OKE": 0.1,  # digits=2
    "OKTA": 0.1,  # digits=2
    "OMC": 0.1,  # digits=2
    "ONDOUSD": 0.001,  # digits=4
    "ONEUSD": 0.0001,  # digits=5
    "OPFI": 0.1,  # digits=2
    "ORCL": 0.1,  # digits=2
    "ORLY": 0.1,  # digits=2
    "OSTK": 0.1,  # digits=2
    "OXY": 0.1,  # digits=2
    "PANW": 0.1,  # digits=2
    "PAYX": 0.1,  # digits=2
    "PCAR": 0.1,  # digits=2
    "PCG": 0.1,  # digits=2
    "PDD": 0.1,  # digits=2
    "PEG": 0.1,  # digits=2
    "PENN": 0.1,  # digits=2
    "PEP": 0.1,  # digits=2
    "PFIZER": 0.1,  # digits=2
    "PG": 0.1,  # digits=2
    "PGR": 0.1,  # digits=2
    "PH": 0.1,  # digits=2
    "PINS": 0.1,  # digits=2
    "PLAY": 0.1,  # digits=2
    "PLD": 0.1,  # digits=2
    "PLTR": 0.1,  # digits=2
    "PLUG": 0.1,  # digits=2
    "PM": 0.1,  # digits=2
    "PNC": 0.1,  # digits=2
    "POOL": 0.1,  # digits=2
    "PPG": 0.1,  # digits=2
    "PPL": 0.1,  # digits=2
    "PRX": 0.001,  # digits=4
    "PSA": 0.1,  # digits=2
    "PSH": 0.1,  # digits=2
    "PSN": 0.1,  # digits=2
    "PSON": 0.1,  # digits=2
    "PSX": 0.1,  # digits=2
    "PTON": 0.1,  # digits=2
    "PUM": 0.001,  # digits=4
    "PVH": 0.1,  # digits=2
    "PYPL": 0.1,  # digits=2
    "QCLN": 0.1,  # digits=2
    "QCOM": 0.1,  # digits=2
    "QQQ": 0.1,  # digits=2
    "QS": 0.1,  # digits=2
    "RAA": 0.001,  # digits=4
    "RACE": 0.1,  # digits=2
    "RAND": 0.001,  # digits=4
    "RBLX": 0.1,  # digits=2
    "RCL": 0.1,  # digits=2
    "REGN": 0.1,  # digits=2
    "RF": 0.1,  # digits=2
    "RGLD": 0.1,  # digits=2
    "RIG": 0.1,  # digits=2
    "RING": 0.1,  # digits=2
    "RIVN": 0.1,  # digits=2
    "RL": 0.1,  # digits=2
    "RMV": 0.1,  # digits=2
    "RNG": 0.1,  # digits=2
    "ROBUSTAft.s": 1.0,  # digits=1
    "ROK": 0.1,  # digits=2
    "ROKU": 0.1,  # digits=2
    "ROP": 0.1,  # digits=2
    "ROST": 0.1,  # digits=2
    "RR": 0.1,  # digits=2
    "RRTL": 0.001,  # digits=4
    "RSG": 0.1,  # digits=2
    "RTO": 0.1,  # digits=2
    "RTX": 0.1,  # digits=2
    "RWE": 0.001,  # digits=4
    "SA40.s": 0.1,  # digits=2
    "SANUSD": 0.001,  # digits=4
    "SBRY": 0.1,  # digits=2
    "SBUX": 0.1,  # digits=2
    "SCHW": 0.1,  # digits=2
    "SDR": 0.1,  # digits=2
    "SDS": 0.1,  # digits=2
    "SE": 0.1,  # digits=2
    "SENS": 0.1,  # digits=2
    "SGDJ": 0.1,  # digits=2
    "SGDJPY.s": 0.01,  # digits=3
    "SGDM": 0.1,  # digits=2
    "SGE": 0.1,  # digits=2
    "SGP20.s": 0.1,  # digits=2
    "SGRO": 0.1,  # digits=2
    "SHBUSD": 0.001,  # digits=4
    "SHL": 0.001,  # digits=4
    "SHOP": 0.1,  # digits=2
    "SHW": 0.1,  # digits=2
    "SIG": 0.1,  # digits=2
    "SIRI": 0.1,  # digits=2
    "SKYUSD": 0.0001,  # digits=5
    "SLB": 0.1,  # digits=2
    "SLVP": 0.1,  # digits=2
    "SMG": 0.1,  # digits=2
    "SMIN": 0.1,  # digits=2
    "SMT": 0.1,  # digits=2
    "SN": 0.1,  # digits=2
    "SNAP": 0.1,  # digits=2
    "SNOW": 0.1,  # digits=2
    "SNPS": 0.1,  # digits=2
    "SO": 0.1,  # digits=2
    "SOFI": 0.1,  # digits=2
    "SOLJPY": 1.0,  # digits=1
    "SOLUSD": 0.1,  # digits=2
    "SP500.s": 0.1,  # digits=2
    "SP500ft.s": 0.1,  # digits=2
    "SPCE": 0.1,  # digits=2
    "SPG": 0.1,  # digits=2
    "SPGI": 0.1,  # digits=2
    "SPI200.s": 0.1,  # digits=2
    "SPLK": 0.1,  # digits=2
    "SPOT": 0.1,  # digits=2
    "SPX": 0.1,  # digits=2
    "SPY": 0.1,  # digits=2
    "SPYX": 0.1,  # digits=2
    "SRE": 0.1,  # digits=2
    "SRT3": 0.001,  # digits=4
    "SSE": 0.1,  # digits=2
    "STJ": 0.1,  # digits=2
    "STT": 0.1,  # digits=2
    "STZ": 0.1,  # digits=2
    "SUSUSD": 0.01,  # digits=3
    "SVT": 0.1,  # digits=2
    "SW": 0.001,  # digits=4
    "SWI20.s": 0.1,  # digits=2
    "SWK": 0.1,  # digits=2
    "SWKS": 0.1,  # digits=2
    "SWR": 0.1,  # digits=2
    "SY1": 0.001,  # digits=4
    "SYF": 0.1,  # digits=2
    "SYK": 0.1,  # digits=2
    "SYY": 0.1,  # digits=2
    "Soybean-Cs": 0.01,  # digits=3
    "Sugar-Cs": 0.0001,  # digits=5
    "TAN": 0.1,  # digits=2
    "TCOM": 0.1,  # digits=2
    "TDOC": 0.1,  # digits=2
    "TEAM": 0.1,  # digits=2
    "TEL": 0.1,  # digits=2
    "TEVA": 0.1,  # digits=2
    "TFC": 0.1,  # digits=2
    "TGT": 0.1,  # digits=2
    "TJX": 0.1,  # digits=2
    "TLX": 0.001,  # digits=4
    "TMO": 0.1,  # digits=2
    "TMUS": 0.1,  # digits=2
    "TOYOTA": 0.1,  # digits=2
    "TRIP": 0.1,  # digits=2
    "TRMB": 0.1,  # digits=2
    "TROW": 0.1,  # digits=2
    "TRST": 0.1,  # digits=2
    "TRUMPUSD": 0.01,  # digits=3
    "TRV": 0.1,  # digits=2
    "TRXUSD": 0.0001,  # digits=5
    "TSLA": 0.1,  # digits=2
    "TSM": 0.1,  # digits=2
    "TSN": 0.1,  # digits=2
    "TTD": 0.1,  # digits=2
    "TTWO": 0.1,  # digits=2
    "TW": 0.1,  # digits=2
    "TWINDEX.s": 0.1,  # digits=2
    "TWLO": 0.1,  # digits=2
    "TXN": 0.1,  # digits=2
    "U": 0.1,  # digits=2
    "UA": 0.1,  # digits=2
    "UAL": 0.1,  # digits=2
    "UBER": 0.1,  # digits=2
    "UK100.s": 0.1,  # digits=2
    "UK100ft.s": 0.1,  # digits=2
    "UKOUSD.s": 0.01,  # digits=3
    "UKOUSDft.s": 0.01,  # digits=3
    "UL": 0.1,  # digits=2
    "ULTA": 0.1,  # digits=2
    "UMC": 0.1,  # digits=2
    "UNH": 0.1,  # digits=2
    "UNIUSD": 0.01,  # digits=3
    "UNP": 0.1,  # digits=2
    "UPS": 0.1,  # digits=2
    "UPST": 0.1,  # digits=2
    "US2000.s": 0.1,  # digits=2
    "USB": 0.1,  # digits=2
    "USDAED": 0.0001,  # digits=5
    "USDAED.s": 0.0001,  # digits=5
    "USDBRL.s": 0.0001,  # digits=5
    "USDCAD": 0.0001,  # digits=5
    "USDCAD.s": 0.0001,  # digits=5
    "USDCHF": 0.0001,  # digits=5
    "USDCHF.s": 0.0001,  # digits=5
    "USDCLP.s": 0.1,  # digits=2
    "USDCNH": 0.0001,  # digits=5
    "USDCOP.s": 0.1,  # digits=2
    "USDCZK.s": 0.0001,  # digits=5
    "USDDKK.s": 0.0001,  # digits=5
    "USDHKD": 0.0001,  # digits=5
    "USDHKD.s": 0.0001,  # digits=5
    "USDHUF.s": 0.01,  # digits=3
    "USDIDR.s": 1.0,  # digits=1
    "USDILS.s": 0.0001,  # digits=5
    "USDINR.s": 0.01,  # digits=3
    "USDJPY": 0.01,  # digits=3
    "USDJPY.s": 0.01,  # digits=3
    "USDKRW.s": 0.1,  # digits=2
    "USDMXN.s": 0.0001,  # digits=5
    "USDNOK.s": 0.0001,  # digits=5
    "USDSEK.s": 0.0001,  # digits=5
    "USDSGD": 0.0001,  # digits=5
    "USDSGD.s": 0.0001,  # digits=5
    "USDTHB.s": 0.0001,  # digits=5
    "USDTJPY": 0.01,  # digits=3
    "USDTWD.s": 0.01,  # digits=3
    "USDX.s": 0.01,  # digits=3
    "USDZAR": 0.0001,  # digits=5
    "USDZAR.s": 0.0001,  # digits=5
    "USL": 0.1,  # digits=2
    "USNote10Y": 0.1,  # digits=2
    "USO": 0.1,  # digits=2
    "USOUSD.s": 0.01,  # digits=3
    "UTDI": 0.001,  # digits=4
    "UU": 0.1,  # digits=2
    "VFC": 0.1,  # digits=2
    "VFS": 0.1,  # digits=2
    "VGT": 0.1,  # digits=2
    "VIRT": 0.1,  # digits=2
    "VIS": 0.001,  # digits=4
    "VISA": 0.1,  # digits=2
    "VIX.s": 0.01,  # digits=3
    "VLO": 0.1,  # digits=2
    "VMC": 0.1,  # digits=2
    "VMW": 0.1,  # digits=2
    "VNA": 0.001,  # digits=4
    "VOW": 0.001,  # digits=4
    "VPK": 0.001,  # digits=4
    "VRTX": 0.1,  # digits=2
    "VSGX": 0.1,  # digits=2
    "VTRS": 0.1,  # digits=2
    "VZ": 0.1,  # digits=2
    "W": 0.1,  # digits=2
    "WDAY": 0.1,  # digits=2
    "WDC": 0.1,  # digits=2
    "WEN": 0.1,  # digits=2
    "WFC": 0.1,  # digits=2
    "WIFUSD": 0.01,  # digits=3
    "WISE": 0.1,  # digits=2
    "WKHS": 0.1,  # digits=2
    "WKL": 0.001,  # digits=4
    "WLDUSD": 0.01,  # digits=3
    "WLFIUSD": 0.001,  # digits=4
    "WM": 0.1,  # digits=2
    "WMB": 0.1,  # digits=2
    "WMT": 0.1,  # digits=2
    "WPM": 0.1,  # digits=2
    "WPP": 0.1,  # digits=2
    "WTB": 0.1,  # digits=2
    "WU": 0.1,  # digits=2
    "WY": 0.1,  # digits=2
    "WYNN": 0.1,  # digits=2
    "Wheat-Cs": 0.01,  # digits=3
    "XAGUSD.s": 0.01,  # digits=3
    "XAUEUR.s": 0.1,  # digits=2
    "XAUJPY.s": 10.0,  # digits=0
    "XAUUSD.s": 0.1,  # digits=2
    "XEL": 0.1,  # digits=2
    "XLF": 0.1,  # digits=2
    "XLK": 0.1,  # digits=2
    "XLMJPY": 0.001,  # digits=4
    "XLMUSD": 0.001,  # digits=4
    "XOP": 0.1,  # digits=2
    "XPDUSD.s": 0.1,  # digits=2
    "XPEV": 0.1,  # digits=2
    "XPTUSD.s": 0.1,  # digits=2
    "XRPJPY": 0.01,  # digits=3
    "XRPUSD": 0.001,  # digits=4
    "XRX": 0.1,  # digits=2
    "XTZUSD": 0.001,  # digits=4
    "YALA": 0.1,  # digits=2
    "YUM": 0.1,  # digits=2
    "YUMC": 0.1,  # digits=2
    "Z": 0.1,  # digits=2
    "ZAL": 0.001,  # digits=4
    "ZBH": 0.1,  # digits=2
    "ZBRA": 0.1,  # digits=2
    "ZECUSD": 0.1,  # digits=2
    "ZIM": 0.1,  # digits=2
    "ZM": 0.1,  # digits=2
    "ZTS": 0.1,  # digits=2
}

# ── Contract sizes (from broker) ─────────────────────────
CONTRACT_SIZES: dict[str, float] = {
    "A": 1.0,
    "AA": 1.0,
    "AALB": 10.0,
    "AALG": 1.0,
    "AAPL": 1.0,
    "ABBVIE": 1.0,
    "ABDN": 100.0,
    "ABNB": 1.0,
    "ABT": 1.0,
    "AC": 10.0,
    "ACN": 1.0,
    "ADAJPY": 10000.0,
    "ADAUSD": 10000.0,
    "ADBE": 1.0,
    "ADI": 1.0,
    "ADM": 1.0,
    "ADP": 1.0,
    "ADPR": 10.0,
    "ADS": 10.0,
    "ADSK": 1.0,
    "ADYEN": 1.0,
    "AENA": 10.0,
    "AEP": 1.0,
    "AFG": 1.0,
    "AFL": 1.0,
    "AFX": 10.0,
    "AGG": 1.0,
    "AGNC": 1.0,
    "AIG": 1.0,
    "AKAM": 1.0,
    "AKZA": 10.0,
    "ALB": 1.0,
    "ALGN": 1.0,
    "ALGUSD": 10000.0,
    "ALIBABA": 1.0,
    "ALK": 1.0,
    "ALLC": 1.0,
    "AMAT": 1.0,
    "AMAZON": 1.0,
    "AMCX": 1.0,
    "AMD": 1.0,
    "AMGN": 1.0,
    "AMPF": 1.0,
    "AMS": 10.0,
    "AMT": 1.0,
    "AMUN": 10.0,
    "AMWL": 1.0,
    "ANA": 10.0,
    "ANTO": 10.0,
    "AON": 1.0,
    "APA": 1.0,
    "APD": 1.0,
    "APH": 1.0,
    "APTV": 1.0,
    "ARKB": 1.0,
    "ARKG": 1.0,
    "ARKK": 1.0,
    "ARKQ": 1.0,
    "ARKW": 1.0,
    "ASM": 10.0,
    "ASRNL": 10.0,
    "AT&T": 1.0,
    "ATMUSD": 1000.0,
    "AUDCAD.s": 100000.0,
    "AUDCHF.s": 100000.0,
    "AUDJPY.s": 100000.0,
    "AUDNZD.s": 100000.0,
    "AUDSGD.s": 100000.0,
    "AUDUSD": 100000.0,
    "AUDUSD.s": 100000.0,
    "AUPH": 1.0,
    "AUTO": 100.0,
    "AVAUSD": 100.0,
    "AVB": 1.0,
    "AVGO": 1.0,
    "AXP": 1.0,
    "AZO": 1.0,
    "BAC": 1.0,
    "BAIDU": 1.0,
    "BAP": 1.0,
    "BATUSD": 10000.0,
    "BAX": 1.0,
    "BB": 1.0,
    "BBWI": 1.0,
    "BBY": 1.0,
    "BCHJPY": 10.0,
    "BCHUSD": 10.0,
    "BDX": 1.0,
    "BE": 1.0,
    "BEI": 10.0,
    "BEN": 1.0,
    "BERAUSD": 100.0,
    "BIIB": 1.0,
    "BITB": 1.0,
    "BITO": 1.0,
    "BITQ": 1.0,
    "BK": 1.0,
    "BKCH": 1.0,
    "BKG": 10.0,
    "BKNG": 1.0,
    "BKR": 1.0,
    "BLCN": 1.0,
    "BLDP": 1.0,
    "BLK": 1.0,
    "BLND": 100.0,
    "BLNK": 1.0,
    "BLOK": 1.0,
    "BMBL": 1.0,
    "BMRN": 1.0,
    "BMW": 10.0,
    "BMY": 1.0,
    "BNBUSD": 10.0,
    "BND": 1.0,
    "BNDX": 1.0,
    "BNGO": 1.0,
    "BNO": 1.0,
    "BNR": 10.0,
    "BNTX": 1.0,
    "BNZL": 10.0,
    "BOEING": 1.0,
    "BOX": 1.0,
    "BP": 100.0,
    "BRBY": 10.0,
    "BRKB": 1.0,
    "BSX": 1.0,
    "BTCBCH": 1.0,
    "BTCETH": 1.0,
    "BTCEUR": 1.0,
    "BTCJPY": 1.0,
    "BTCLTC": 1.0,
    "BTCO": 1.0,
    "BTCUSD": 1.0,
    "BTCXAU": 1.0,
    "BUD": 1.0,
    "BVSPX.s": 1.0,
    "BX": 1.0,
    "CADCHF.s": 100000.0,
    "CADJPY.s": 100000.0,
    "CAH": 1.0,
    "CAT": 1.0,
    "CB": 1.0,
    "CBOE": 1.0,
    "CCH": 10.0,
    "CCI": 1.0,
    "CDI": 10.0,
    "CDNS": 1.0,
    "CFG": 1.0,
    "CGC": 1.0,
    "CHFJPY.s": 100000.0,
    "CHINA50.s": 1.0,
    "CHINA50ft.s": 1.0,
    "CHINAH.s": 1.0,
    "CHKP": 1.0,
    "CHPT": 1.0,
    "CHT": 1.0,
    "CHTR": 1.0,
    "CHWY": 1.0,
    "CI": 1.0,
    "CIM": 1.0,
    "CISCO": 1.0,
    "CITI": 1.0,
    "CL": 1.0,
    "CL-OIL.s": 1000.0,
    "CLNX": 10.0,
    "CLX": 1.0,
    "CMCSA": 1.0,
    "CME": 1.0,
    "CMI": 1.0,
    "CNA": 100.0,
    "CNC": 1.0,
    "COF": 1.0,
    "COIN": 1.0,
    "COPPER-Cs": 25000.0,
    "COR": 1.0,
    "COST": 1.0,
    "COTY": 1.0,
    "CPNG": 1.0,
    "CPRI": 1.0,
    "CRDA": 10.0,
    "CRH": 10.0,
    "CRM": 1.0,
    "CRON": 1.0,
    "CROUSD": 10000.0,
    "CRVUSD": 1000.0,
    "CRWD": 1.0,
    "CSX": 1.0,
    "CTAS": 1.0,
    "CTRA": 1.0,
    "CTSH": 1.0,
    "CVS": 1.0,
    "CVX": 1.0,
    "Cocoa-Cs": 10.0,
    "Coffee-Cs": 37500.0,
    "Cotton-Cs": 50000.0,
    "D": 1.0,
    "DAL": 1.0,
    "DASH": 1.0,
    "DB1": 10.0,
    "DBA": 1.0,
    "DBC": 1.0,
    "DBX": 1.0,
    "DCC": 10.0,
    "DD": 1.0,
    "DDOG": 1.0,
    "DE": 1.0,
    "DELL": 1.0,
    "DGC": 1.0,
    "DHER": 10.0,
    "DHI": 1.0,
    "DHL": 10.0,
    "DHR": 1.0,
    "DIM": 10.0,
    "DISNEY": 1.0,
    "DJ30.s": 1.0,
    "DJ30ft.s": 1.0,
    "DKNG": 1.0,
    "DLR": 1.0,
    "DLTR": 1.0,
    "DOCU": 1.0,
    "DOGUSD": 10000.0,
    "DOTUSD": 100.0,
    "DOW": 1.0,
    "DTE": 1.0,
    "DUK": 1.0,
    "DVN": 1.0,
    "DWNI": 10.0,
    "DWS": 10.0,
    "DXC": 1.0,
    "DXCM": 1.0,
    "EA": 1.0,
    "EBAY": 1.0,
    "ECL": 1.0,
    "ED": 1.0,
    "EDU": 1.0,
    "EEM": 1.0,
    "EFA": 1.0,
    "EMN": 1.0,
    "EMR": 1.0,
    "ENPH": 1.0,
    "ENT": 10.0,
    "EOG": 1.0,
    "EOSUSD": 10000.0,
    "EPD": 1.0,
    "EQIX": 1.0,
    "EQR": 1.0,
    "ES35.s": 1.0,
    "ESGV": 1.0,
    "ESL": 1.0,
    "ESS": 1.0,
    "ETCUSD": 100.0,
    "ETD": 1.0,
    "ETHBCH": 10.0,
    "ETHEUR": 1.0,
    "ETHJPY": 1.0,
    "ETHLTC": 10.0,
    "ETHUSD": 1.0,
    "ETHXAU": 1.0,
    "ETN": 1.0,
    "ETSY": 1.0,
    "EU50.s": 1.0,
    "EUB10Y": 1.0,
    "EUB2Y": 1.0,
    "EUB30Y": 1.0,
    "EUB5Y": 1.0,
    "EURAUD.s": 100000.0,
    "EURCAD.s": 100000.0,
    "EURCHF.s": 100000.0,
    "EURCZK.s": 100000.0,
    "EURDKK.s": 100000.0,
    "EURGBP.s": 100000.0,
    "EURHUF.s": 100000.0,
    "EURIBOR3M": 1.0,
    "EURJPY.s": 100000.0,
    "EURNZD.s": 100000.0,
    "EURSGD.s": 100000.0,
    "EURUSD": 100000.0,
    "EURUSD.s": 100000.0,
    "EW": 1.0,
    "EXC": 1.0,
    "EXPE": 1.0,
    "EXPN": 10.0,
    "EXXON": 1.0,
    "EZJ": 100.0,
    "F": 1.0,
    "FANG": 1.0,
    "FAS": 1.0,
    "FAST": 1.0,
    "FAZ": 1.0,
    "FCEL": 1.0,
    "FCX": 1.0,
    "FDN": 1.0,
    "FDX": 1.0,
    "FIE": 10.0,
    "FILUSD": 100.0,
    "FIS": 1.0,
    "FITB": 1.0,
    "FLTR": 10.0,
    "FME": 10.0,
    "FOSL": 1.0,
    "FOX": 1.0,
    "FOXA": 1.0,
    "FRA": 10.0,
    "FRA40.s": 1.0,
    "FRA40ft.s": 1.0,
    "FRAS": 100.0,
    "FRE": 10.0,
    "FRES": 100.0,
    "FSLR": 1.0,
    "FTI": 1.0,
    "FTNT": 1.0,
    "FTV": 1.0,
    "FXI": 1.0,
    "G24": 10.0,
    "GAS-Cs": 42000.0,
    "GASOIL-Cs": 100.0,
    "GAUUSD.s": 100.0,
    "GBPAUD.s": 100000.0,
    "GBPCAD.s": 100000.0,
    "GBPCHF.s": 100000.0,
    "GBPJPY.s": 100000.0,
    "GBPNZD.s": 100000.0,
    "GBPSGD.s": 100000.0,
    "GBPUSD": 100000.0,
    "GBPUSD.s": 100000.0,
    "GBTC": 1.0,
    "GBXUSD": 100000.0,
    "GD": 1.0,
    "GDX": 1.0,
    "GDXJ": 1.0,
    "GE": 1.0,
    "GER40.s": 1.0,
    "GER40ft.s": 1.0,
    "GEVO": 1.0,
    "GFI": 1.0,
    "GFS": 1.0,
    "GILD": 1.0,
    "GIS": 1.0,
    "GLD": 1.0,
    "GLPG": 10.0,
    "GLW": 1.0,
    "GM": 1.0,
    "GNRC": 1.0,
    "GOAU": 1.0,
    "GOEX": 1.0,
    "GOOG": 1.0,
    "GPN": 1.0,
    "GPRO": 1.0,
    "GRAB": 1.0,
    "GRID": 1.0,
    "GRPN": 1.0,
    "GRTUSD": 10000.0,
    "GRVY": 1.0,
    "GS": 1.0,
    "GSG": 1.0,
    "GT": 1.0,
    "GWW": 1.0,
    "HAL": 1.0,
    "HBAN": 1.0,
    "HBARUSD": 10000.0,
    "HCA": 1.0,
    "HD": 1.0,
    "HDB": 1.0,
    "HEI": 10.0,
    "HEN3": 10.0,
    "HIK": 10.0,
    "HK50.s": 1.0,
    "HK50ft.s": 1.0,
    "HKTECH.s": 1.0,
    "HLAG": 10.0,
    "HLF": 1.0,
    "HLMA": 10.0,
    "HLT": 1.0,
    "HNR1": 10.0,
    "HOG": 1.0,
    "HON": 1.0,
    "HOOD": 1.0,
    "HOT": 10.0,
    "HPE": 1.0,
    "HPQ": 1.0,
    "HRB": 1.0,
    "HSBCn": 1.0,
    "HSX": 100.0,
    "HSY": 1.0,
    "HTHT": 1.0,
    "HUBS": 1.0,
    "HUM": 1.0,
    "HUT": 1.0,
    "HYLN": 1.0,
    "HYPEUSD": 100.0,
    "IAC": 1.0,
    "IBIT": 1.0,
    "IBM": 1.0,
    "IBN": 1.0,
    "ICE": 1.0,
    "ICL": 1.0,
    "ICLN": 1.0,
    "IDXX": 1.0,
    "IHG": 10.0,
    "III": 10.0,
    "ILMN": 1.0,
    "IMCD": 10.0,
    "INCUSD": 10000.0,
    "INCY": 1.0,
    "INF": 100.0,
    "INFY": 1.0,
    "INO": 1.0,
    "INSG": 1.0,
    "INTEL": 1.0,
    "INTU": 1.0,
    "IOTUSD": 10000.0,
    "IOVA": 1.0,
    "IP": 1.0,
    "IQV": 1.0,
    "IR": 1.0,
    "ISRG": 1.0,
    "ITRK": 10.0,
    "ITV": 100.0,
    "ITW": 1.0,
    "IVZ": 1.0,
    "IWM": 1.0,
    "IYW": 1.0,
    "JBL": 1.0,
    "JCI": 1.0,
    "JD": 1.0,
    "JDI": 100.0,
    "JMAT": 10.0,
    "JNJ": 1.0,
    "JNUG": 1.0,
    "JPM": 1.0,
    "JPN225ft.s": 1.0,
    "KBX": 10.0,
    "KDP": 1.0,
    "KEY": 1.0,
    "KGC": 1.0,
    "KGF": 100.0,
    "KGX": 10.0,
    "KHC": 1.0,
    "KKR": 1.0,
    "KLAC": 1.0,
    "KMI": 1.0,
    "KO": 1.0,
    "KODK": 1.0,
    "KR": 1.0,
    "KRN": 10.0,
    "KSS": 1.0,
    "LAC": 1.0,
    "LAND": 100.0,
    "LAUR": 1.0,
    "LBTYK": 1.0,
    "LC": 1.0,
    "LCID": 1.0,
    "LEG": 10.0,
    "LEN": 1.0,
    "LEVI": 1.0,
    "LGEN": 100.0,
    "LHX": 1.0,
    "LI": 1.0,
    "LLY": 1.0,
    "LMT": 1.0,
    "LNKUSD": 100.0,
    "LOW": 1.0,
    "LPL": 1.0,
    "LRCUSD": 10000.0,
    "LRCX": 1.0,
    "LSEG": 10.0,
    "LTCJPY": 100.0,
    "LTCUSD": 100.0,
    "LULU": 1.0,
    "LUMN": 1.0,
    "LUV": 1.0,
    "LVS": 1.0,
    "LYB": 1.0,
    "LYFT": 1.0,
    "LongGilt": 1.0,
    "M": 1.0,
    "MA": 1.0,
    "MANU": 1.0,
    "MAR": 1.0,
    "MARA": 1.0,
    "MAT": 1.0,
    "MBG": 10.0,
    "MBLY": 1.0,
    "MCD": 1.0,
    "MCHP": 1.0,
    "MCK": 1.0,
    "MCO": 1.0,
    "MDLZ": 1.0,
    "MDT": 1.0,
    "MET": 1.0,
    "META": 1.0,
    "MFA": 1.0,
    "MFC": 1.0,
    "MGM": 1.0,
    "MKRUSD": 1.0,
    "MLM": 1.0,
    "MMM": 1.0,
    "MNDI": 10.0,
    "MNG": 100.0,
    "MNST": 1.0,
    "MO": 1.0,
    "MOH": 1.0,
    "MOMO": 1.0,
    "MPC": 1.0,
    "MPLX": 1.0,
    "MPWR": 1.0,
    "MRCK": 10.0,
    "MRK": 1.0,
    "MRNA": 1.0,
    "MRVL": 1.0,
    "MS": 1.0,
    "MSFT": 1.0,
    "MTB": 1.0,
    "MTCH": 1.0,
    "MTX": 10.0,
    "MUV2": 10.0,
    "NAS100.s": 1.0,
    "NAS100ft.s": 1.0,
    "NBIX": 1.0,
    "NBR": 1.0,
    "NCLH": 1.0,
    "NEE": 1.0,
    "NEMD": 10.0,
    "NEOUSD": 100.0,
    "NERUSD": 1000.0,
    "NET": 1.0,
    "NETH25.s": 1.0,
    "NFLX": 1.0,
    "NG-Cs": 10000.0,
    "NGRID": 10.0,
    "NIO": 1.0,
    "NKE": 1.0,
    "NN": 10.0,
    "NOC": 1.0,
    "NOW": 1.0,
    "NSC": 1.0,
    "NTAP": 1.0,
    "NTES": 1.0,
    "NTRS": 1.0,
    "NUE": 1.0,
    "NUGT": 1.0,
    "NVIDIA": 1.0,
    "NVS": 1.0,
    "NWS": 1.0,
    "NXPCUSD": 10000.0,
    "NXPI": 1.0,
    "NXT": 10.0,
    "NZDCAD.s": 100000.0,
    "NZDCHF.s": 100000.0,
    "NZDJPY.s": 100000.0,
    "NZDSGD.s": 100000.0,
    "NZDUSD.s": 100000.0,
    "Nikkei225.s": 1.0,
    "OCDO": 10.0,
    "OIH": 1.0,
    "OIS": 1.0,
    "OJ-Cs": 15000.0,
    "OKBUSD": 100.0,
    "OKE": 1.0,
    "OKTA": 1.0,
    "OMC": 1.0,
    "ONDOUSD": 1000.0,
    "ONEUSD": 100000.0,
    "OPFI": 1.0,
    "ORCL": 1.0,
    "ORLY": 1.0,
    "OSTK": 1.0,
    "OXY": 1.0,
    "PANW": 1.0,
    "PAYX": 1.0,
    "PCAR": 1.0,
    "PCG": 1.0,
    "PDD": 1.0,
    "PEG": 1.0,
    "PENN": 1.0,
    "PEP": 1.0,
    "PFIZER": 1.0,
    "PG": 1.0,
    "PGR": 1.0,
    "PH": 1.0,
    "PINS": 1.0,
    "PLAY": 1.0,
    "PLD": 1.0,
    "PLTR": 1.0,
    "PLUG": 1.0,
    "PM": 1.0,
    "PNC": 1.0,
    "POOL": 1.0,
    "PPG": 1.0,
    "PPL": 1.0,
    "PRX": 10.0,
    "PSA": 1.0,
    "PSH": 10.0,
    "PSN": 10.0,
    "PSON": 100.0,
    "PSX": 1.0,
    "PTON": 1.0,
    "PUM": 10.0,
    "PVH": 1.0,
    "PYPL": 1.0,
    "QCLN": 1.0,
    "QCOM": 1.0,
    "QQQ": 1.0,
    "QS": 1.0,
    "RAA": 10.0,
    "RACE": 1.0,
    "RAND": 10.0,
    "RBLX": 1.0,
    "RCL": 1.0,
    "REGN": 1.0,
    "RF": 1.0,
    "RGLD": 1.0,
    "RIG": 1.0,
    "RING": 1.0,
    "RIVN": 1.0,
    "RL": 1.0,
    "RMV": 100.0,
    "RNG": 1.0,
    "ROBUSTAft.s": 10.0,
    "ROK": 1.0,
    "ROKU": 1.0,
    "ROP": 1.0,
    "ROST": 1.0,
    "RR": 100.0,
    "RRTL": 10.0,
    "RSG": 1.0,
    "RTO": 100.0,
    "RTX": 1.0,
    "RWE": 10.0,
    "SA40.s": 1.0,
    "SANUSD": 1000.0,
    "SBRY": 100.0,
    "SBUX": 1.0,
    "SCHW": 1.0,
    "SDR": 10.0,
    "SDS": 1.0,
    "SE": 1.0,
    "SENS": 1.0,
    "SGDJ": 1.0,
    "SGDJPY.s": 100000.0,
    "SGDM": 1.0,
    "SGE": 100.0,
    "SGP20.s": 1.0,
    "SGRO": 10.0,
    "SHBUSD": 10000.0,
    "SHL": 10.0,
    "SHOP": 1.0,
    "SHW": 1.0,
    "SIG": 1.0,
    "SIRI": 1.0,
    "SKYUSD": 10000.0,
    "SLB": 1.0,
    "SLVP": 1.0,
    "SMG": 1.0,
    "SMIN": 10.0,
    "SMT": 10.0,
    "SN": 10.0,
    "SNAP": 1.0,
    "SNOW": 1.0,
    "SNPS": 1.0,
    "SO": 1.0,
    "SOFI": 1.0,
    "SOLJPY": 10.0,
    "SOLUSD": 10.0,
    "SP500.s": 1.0,
    "SP500ft.s": 1.0,
    "SPCE": 1.0,
    "SPG": 1.0,
    "SPGI": 1.0,
    "SPI200.s": 1.0,
    "SPLK": 1.0,
    "SPOT": 1.0,
    "SPX": 10.0,
    "SPY": 1.0,
    "SPYX": 1.0,
    "SRE": 1.0,
    "SRT3": 10.0,
    "SSE": 10.0,
    "STJ": 10.0,
    "STT": 1.0,
    "STZ": 1.0,
    "SUSUSD": 1000.0,
    "SVT": 10.0,
    "SW": 10.0,
    "SWI20.s": 1.0,
    "SWK": 1.0,
    "SWKS": 1.0,
    "SWR": 10.0,
    "SY1": 10.0,
    "SYF": 1.0,
    "SYK": 1.0,
    "SYY": 1.0,
    "Soybean-Cs": 500.0,
    "Sugar-Cs": 112000.0,
    "TAN": 1.0,
    "TCOM": 1.0,
    "TDOC": 1.0,
    "TEAM": 1.0,
    "TEL": 1.0,
    "TEVA": 1.0,
    "TFC": 1.0,
    "TGT": 1.0,
    "TJX": 1.0,
    "TLX": 10.0,
    "TMO": 1.0,
    "TMUS": 1.0,
    "TOYOTA": 1.0,
    "TRIP": 1.0,
    "TRMB": 1.0,
    "TROW": 1.0,
    "TRST": 100.0,
    "TRUMPUSD": 100.0,
    "TRV": 1.0,
    "TRXUSD": 100000.0,
    "TSLA": 1.0,
    "TSM": 1.0,
    "TSN": 1.0,
    "TTD": 1.0,
    "TTWO": 1.0,
    "TW": 100.0,
    "TWINDEX.s": 1.0,
    "TWLO": 1.0,
    "TXN": 1.0,
    "U": 1.0,
    "UA": 1.0,
    "UAL": 1.0,
    "UBER": 1.0,
    "UK100.s": 1.0,
    "UK100ft.s": 1.0,
    "UKOUSD.s": 1000.0,
    "UKOUSDft.s": 1000.0,
    "UL": 1.0,
    "ULTA": 1.0,
    "UMC": 1.0,
    "UNH": 1.0,
    "UNIUSD": 100.0,
    "UNP": 1.0,
    "UPS": 1.0,
    "UPST": 1.0,
    "US2000.s": 1.0,
    "USB": 1.0,
    "USDAED": 100000.0,
    "USDAED.s": 100000.0,
    "USDBRL.s": 100000.0,
    "USDCAD": 100000.0,
    "USDCAD.s": 100000.0,
    "USDCHF": 100000.0,
    "USDCHF.s": 100000.0,
    "USDCLP.s": 100000.0,
    "USDCNH": 100000.0,
    "USDCOP.s": 100000.0,
    "USDCZK.s": 100000.0,
    "USDDKK.s": 100000.0,
    "USDHKD": 100000.0,
    "USDHKD.s": 100000.0,
    "USDHUF.s": 100000.0,
    "USDIDR.s": 100000.0,
    "USDILS.s": 100000.0,
    "USDINR.s": 100000.0,
    "USDJPY": 100000.0,
    "USDJPY.s": 100000.0,
    "USDKRW.s": 100000.0,
    "USDMXN.s": 100000.0,
    "USDNOK.s": 100000.0,
    "USDSEK.s": 100000.0,
    "USDSGD": 100000.0,
    "USDSGD.s": 100000.0,
    "USDTHB.s": 100000.0,
    "USDTJPY": 100000.0,
    "USDTWD.s": 100000.0,
    "USDX.s": 100.0,
    "USDZAR": 100000.0,
    "USDZAR.s": 100000.0,
    "USL": 1.0,
    "USNote10Y": 1.0,
    "USO": 1.0,
    "USOUSD.s": 1000.0,
    "UTDI": 10.0,
    "UU": 10.0,
    "VFC": 1.0,
    "VFS": 1.0,
    "VGT": 1.0,
    "VIRT": 1.0,
    "VIS": 10.0,
    "VISA": 1.0,
    "VIX.s": 1000.0,
    "VLO": 1.0,
    "VMC": 1.0,
    "VMW": 1.0,
    "VNA": 10.0,
    "VOW": 10.0,
    "VPK": 10.0,
    "VRTX": 1.0,
    "VSGX": 1.0,
    "VTRS": 1.0,
    "VZ": 1.0,
    "W": 1.0,
    "WDAY": 1.0,
    "WDC": 1.0,
    "WEN": 1.0,
    "WFC": 1.0,
    "WIFUSD": 1000.0,
    "WISE": 10.0,
    "WKHS": 1.0,
    "WKL": 10.0,
    "WLDUSD": 1000.0,
    "WLFIUSD": 10000.0,
    "WM": 1.0,
    "WMB": 1.0,
    "WMT": 1.0,
    "WPM": 1.0,
    "WPP": 10.0,
    "WTB": 10.0,
    "WU": 1.0,
    "WY": 1.0,
    "WYNN": 1.0,
    "Wheat-Cs": 1000.0,
    "XAGUSD.s": 5000.0,
    "XAUEUR.s": 100.0,
    "XAUJPY.s": 100.0,
    "XAUUSD.s": 100.0,
    "XEL": 1.0,
    "XLF": 1.0,
    "XLK": 1.0,
    "XLMJPY": 10000.0,
    "XLMUSD": 10000.0,
    "XOP": 1.0,
    "XPDUSD.s": 10.0,
    "XPEV": 1.0,
    "XPTUSD.s": 10.0,
    "XRPJPY": 10000.0,
    "XRPUSD": 10000.0,
    "XRX": 1.0,
    "XTZUSD": 1000.0,
    "YALA": 1.0,
    "YUM": 1.0,
    "YUMC": 1.0,
    "Z": 1.0,
    "ZAL": 10.0,
    "ZBH": 1.0,
    "ZBRA": 1.0,
    "ZECUSD": 100.0,
    "ZIM": 1.0,
    "ZM": 1.0,
    "ZTS": 1.0,
}

# ── Asset class lookup ───────────────────────────────────
SYMBOL_CLASS: dict[str, str] = {
    "A": "stock_cfd",
    "AA": "stock_cfd",
    "AALB": "stock_cfd",
    "AALG": "stock_cfd",
    "AAPL": "stock_cfd",
    "ABBVIE": "stock_cfd",
    "ABDN": "stock_cfd",
    "ABNB": "stock_cfd",
    "ABT": "stock_cfd",
    "AC": "stock_cfd",
    "ACN": "stock_cfd",
    "ADAJPY": "crypto",
    "ADAUSD": "crypto",
    "ADBE": "stock_cfd",
    "ADI": "stock_cfd",
    "ADM": "stock_cfd",
    "ADP": "stock_cfd",
    "ADPR": "stock_cfd",
    "ADS": "stock_cfd",
    "ADSK": "stock_cfd",
    "ADYEN": "stock_cfd",
    "AENA": "stock_cfd",
    "AEP": "stock_cfd",
    "AFG": "stock_cfd",
    "AFL": "stock_cfd",
    "AFX": "stock_cfd",
    "AGG": "etf",
    "AGNC": "stock_cfd",
    "AIG": "stock_cfd",
    "AKAM": "stock_cfd",
    "AKZA": "stock_cfd",
    "ALB": "stock_cfd",
    "ALGN": "stock_cfd",
    "ALGUSD": "crypto",
    "ALIBABA": "stock_cfd",
    "ALK": "stock_cfd",
    "ALLC": "stock_cfd",
    "AMAT": "stock_cfd",
    "AMAZON": "stock_cfd",
    "AMCX": "stock_cfd",
    "AMD": "stock_cfd",
    "AMGN": "stock_cfd",
    "AMPF": "stock_cfd",
    "AMS": "stock_cfd",
    "AMT": "stock_cfd",
    "AMUN": "stock_cfd",
    "AMWL": "stock_cfd",
    "ANA": "stock_cfd",
    "ANTO": "stock_cfd",
    "AON": "stock_cfd",
    "APA": "stock_cfd",
    "APD": "stock_cfd",
    "APH": "stock_cfd",
    "APTV": "stock_cfd",
    "ARKB": "etf",
    "ARKG": "etf",
    "ARKK": "etf",
    "ARKQ": "etf",
    "ARKW": "etf",
    "ASM": "stock_cfd",
    "ASRNL": "stock_cfd",
    "AT&T": "stock_cfd",
    "ATMUSD": "crypto",
    "AUDCAD.s": "forex_cross",
    "AUDCHF.s": "forex_cross",
    "AUDJPY.s": "forex_cross",
    "AUDNZD.s": "forex_cross",
    "AUDSGD.s": "forex_cross",
    "AUDUSD": "forex_major",
    "AUDUSD.s": "forex_cross",
    "AUPH": "stock_cfd",
    "AUTO": "stock_cfd",
    "AVAUSD": "crypto",
    "AVB": "stock_cfd",
    "AVGO": "stock_cfd",
    "AXP": "stock_cfd",
    "AZO": "stock_cfd",
    "BAC": "stock_cfd",
    "BAIDU": "stock_cfd",
    "BAP": "stock_cfd",
    "BATUSD": "crypto",
    "BAX": "stock_cfd",
    "BB": "stock_cfd",
    "BBWI": "stock_cfd",
    "BBY": "stock_cfd",
    "BCHJPY": "crypto",
    "BCHUSD": "crypto",
    "BDX": "stock_cfd",
    "BE": "stock_cfd",
    "BEI": "stock_cfd",
    "BEN": "stock_cfd",
    "BERAUSD": "crypto",
    "BIIB": "stock_cfd",
    "BITB": "etf",
    "BITO": "etf",
    "BITQ": "etf",
    "BK": "stock_cfd",
    "BKCH": "etf",
    "BKG": "stock_cfd",
    "BKNG": "stock_cfd",
    "BKR": "stock_cfd",
    "BLCN": "etf",
    "BLDP": "stock_cfd",
    "BLK": "stock_cfd",
    "BLND": "stock_cfd",
    "BLNK": "stock_cfd",
    "BLOK": "etf",
    "BMBL": "stock_cfd",
    "BMRN": "stock_cfd",
    "BMW": "stock_cfd",
    "BMY": "stock_cfd",
    "BNBUSD": "crypto",
    "BND": "etf",
    "BNDX": "etf",
    "BNGO": "stock_cfd",
    "BNO": "etf",
    "BNR": "stock_cfd",
    "BNTX": "stock_cfd",
    "BNZL": "stock_cfd",
    "BOEING": "stock_cfd",
    "BOX": "stock_cfd",
    "BP": "stock_cfd",
    "BRBY": "stock_cfd",
    "BRKB": "stock_cfd",
    "BSX": "stock_cfd",
    "BTCBCH": "crypto",
    "BTCETH": "crypto",
    "BTCEUR": "crypto",
    "BTCJPY": "crypto",
    "BTCLTC": "crypto",
    "BTCO": "etf",
    "BTCUSD": "crypto",
    "BTCXAU": "crypto",
    "BUD": "stock_cfd",
    "BVSPX.s": "index",
    "BX": "stock_cfd",
    "CADCHF.s": "forex_cross",
    "CADJPY.s": "forex_cross",
    "CAH": "stock_cfd",
    "CAT": "stock_cfd",
    "CB": "stock_cfd",
    "CBOE": "stock_cfd",
    "CCH": "stock_cfd",
    "CCI": "stock_cfd",
    "CDI": "stock_cfd",
    "CDNS": "stock_cfd",
    "CFG": "stock_cfd",
    "CGC": "stock_cfd",
    "CHFJPY.s": "forex_cross",
    "CHINA50.s": "index",
    "CHINA50ft.s": "index",
    "CHINAH.s": "index",
    "CHKP": "stock_cfd",
    "CHPT": "stock_cfd",
    "CHT": "stock_cfd",
    "CHTR": "stock_cfd",
    "CHWY": "stock_cfd",
    "CI": "stock_cfd",
    "CIM": "stock_cfd",
    "CISCO": "stock_cfd",
    "CITI": "stock_cfd",
    "CL": "stock_cfd",
    "CL-OIL.s": "stock_cfd",
    "CLNX": "stock_cfd",
    "CLX": "stock_cfd",
    "CMCSA": "stock_cfd",
    "CME": "stock_cfd",
    "CMI": "stock_cfd",
    "CNA": "stock_cfd",
    "CNC": "stock_cfd",
    "COF": "stock_cfd",
    "COIN": "stock_cfd",
    "COPPER-Cs": "commodity",
    "COR": "stock_cfd",
    "COST": "stock_cfd",
    "COTY": "stock_cfd",
    "CPNG": "stock_cfd",
    "CPRI": "stock_cfd",
    "CRDA": "stock_cfd",
    "CRH": "stock_cfd",
    "CRM": "stock_cfd",
    "CRON": "stock_cfd",
    "CROUSD": "crypto",
    "CRVUSD": "crypto",
    "CRWD": "stock_cfd",
    "CSX": "stock_cfd",
    "CTAS": "stock_cfd",
    "CTRA": "stock_cfd",
    "CTSH": "stock_cfd",
    "CVS": "stock_cfd",
    "CVX": "stock_cfd",
    "Cocoa-Cs": "commodity",
    "Coffee-Cs": "commodity",
    "Cotton-Cs": "commodity",
    "D": "stock_cfd",
    "DAL": "stock_cfd",
    "DASH": "stock_cfd",
    "DB1": "stock_cfd",
    "DBA": "etf",
    "DBC": "etf",
    "DBX": "stock_cfd",
    "DCC": "stock_cfd",
    "DD": "stock_cfd",
    "DDOG": "stock_cfd",
    "DE": "stock_cfd",
    "DELL": "stock_cfd",
    "DGC": "stock_cfd",
    "DHER": "stock_cfd",
    "DHI": "stock_cfd",
    "DHL": "stock_cfd",
    "DHR": "stock_cfd",
    "DIM": "stock_cfd",
    "DISNEY": "stock_cfd",
    "DJ30.s": "index",
    "DJ30ft.s": "index",
    "DKNG": "stock_cfd",
    "DLR": "stock_cfd",
    "DLTR": "stock_cfd",
    "DOCU": "stock_cfd",
    "DOGUSD": "crypto",
    "DOTUSD": "crypto",
    "DOW": "stock_cfd",
    "DTE": "stock_cfd",
    "DUK": "stock_cfd",
    "DVN": "stock_cfd",
    "DWNI": "stock_cfd",
    "DWS": "stock_cfd",
    "DXC": "stock_cfd",
    "DXCM": "stock_cfd",
    "EA": "stock_cfd",
    "EBAY": "stock_cfd",
    "ECL": "stock_cfd",
    "ED": "stock_cfd",
    "EDU": "stock_cfd",
    "EEM": "etf",
    "EFA": "etf",
    "EMN": "stock_cfd",
    "EMR": "stock_cfd",
    "ENPH": "stock_cfd",
    "ENT": "stock_cfd",
    "EOG": "stock_cfd",
    "EOSUSD": "crypto",
    "EPD": "stock_cfd",
    "EQIX": "stock_cfd",
    "EQR": "stock_cfd",
    "ES35.s": "index",
    "ESGV": "etf",
    "ESL": "stock_cfd",
    "ESS": "stock_cfd",
    "ETCUSD": "crypto",
    "ETD": "stock_cfd",
    "ETHBCH": "crypto",
    "ETHEUR": "crypto",
    "ETHJPY": "crypto",
    "ETHLTC": "crypto",
    "ETHUSD": "crypto",
    "ETHXAU": "crypto",
    "ETN": "stock_cfd",
    "ETSY": "stock_cfd",
    "EU50.s": "index",
    "EUB10Y": "bond",
    "EUB2Y": "bond",
    "EUB30Y": "bond",
    "EUB5Y": "bond",
    "EURAUD.s": "forex_cross",
    "EURCAD.s": "forex_cross",
    "EURCHF.s": "forex_cross",
    "EURCZK.s": "forex_cross",
    "EURDKK.s": "forex_cross",
    "EURGBP.s": "forex_cross",
    "EURHUF.s": "forex_cross",
    "EURIBOR3M": "bond",
    "EURJPY.s": "forex_cross",
    "EURNZD.s": "forex_cross",
    "EURSGD.s": "forex_cross",
    "EURUSD": "forex_major",
    "EURUSD.s": "forex_cross",
    "EW": "stock_cfd",
    "EXC": "stock_cfd",
    "EXPE": "stock_cfd",
    "EXPN": "stock_cfd",
    "EXXON": "stock_cfd",
    "EZJ": "stock_cfd",
    "F": "stock_cfd",
    "FANG": "stock_cfd",
    "FAS": "etf",
    "FAST": "stock_cfd",
    "FAZ": "etf",
    "FCEL": "stock_cfd",
    "FCX": "stock_cfd",
    "FDN": "etf",
    "FDX": "stock_cfd",
    "FIE": "stock_cfd",
    "FILUSD": "crypto",
    "FIS": "stock_cfd",
    "FITB": "stock_cfd",
    "FLTR": "stock_cfd",
    "FME": "stock_cfd",
    "FOSL": "stock_cfd",
    "FOX": "stock_cfd",
    "FOXA": "stock_cfd",
    "FRA": "stock_cfd",
    "FRA40.s": "index",
    "FRA40ft.s": "index",
    "FRAS": "stock_cfd",
    "FRE": "stock_cfd",
    "FRES": "stock_cfd",
    "FSLR": "stock_cfd",
    "FTI": "stock_cfd",
    "FTNT": "stock_cfd",
    "FTV": "stock_cfd",
    "FXI": "etf",
    "G24": "stock_cfd",
    "GAS-Cs": "commodity",
    "GASOIL-Cs": "commodity",
    "GAUUSD.s": "commodity",
    "GBPAUD.s": "forex_cross",
    "GBPCAD.s": "forex_cross",
    "GBPCHF.s": "forex_cross",
    "GBPJPY.s": "forex_cross",
    "GBPNZD.s": "forex_cross",
    "GBPSGD.s": "forex_cross",
    "GBPUSD": "forex_major",
    "GBPUSD.s": "forex_cross",
    "GBTC": "etf",
    "GBXUSD": "forex_cross",
    "GD": "stock_cfd",
    "GDX": "etf",
    "GDXJ": "etf",
    "GE": "stock_cfd",
    "GER40.s": "index",
    "GER40ft.s": "index",
    "GEVO": "stock_cfd",
    "GFI": "stock_cfd",
    "GFS": "stock_cfd",
    "GILD": "stock_cfd",
    "GIS": "stock_cfd",
    "GLD": "etf",
    "GLPG": "stock_cfd",
    "GLW": "stock_cfd",
    "GM": "stock_cfd",
    "GNRC": "stock_cfd",
    "GOAU": "etf",
    "GOEX": "etf",
    "GOOG": "stock_cfd",
    "GPN": "stock_cfd",
    "GPRO": "stock_cfd",
    "GRAB": "stock_cfd",
    "GRID": "etf",
    "GRPN": "stock_cfd",
    "GRTUSD": "crypto",
    "GRVY": "stock_cfd",
    "GS": "stock_cfd",
    "GSG": "etf",
    "GT": "stock_cfd",
    "GWW": "stock_cfd",
    "HAL": "stock_cfd",
    "HBAN": "stock_cfd",
    "HBARUSD": "crypto",
    "HCA": "stock_cfd",
    "HD": "stock_cfd",
    "HDB": "stock_cfd",
    "HEI": "stock_cfd",
    "HEN3": "stock_cfd",
    "HIK": "stock_cfd",
    "HK50.s": "index",
    "HK50ft.s": "index",
    "HKTECH.s": "index",
    "HLAG": "stock_cfd",
    "HLF": "stock_cfd",
    "HLMA": "stock_cfd",
    "HLT": "stock_cfd",
    "HNR1": "stock_cfd",
    "HOG": "stock_cfd",
    "HON": "stock_cfd",
    "HOOD": "stock_cfd",
    "HOT": "stock_cfd",
    "HPE": "stock_cfd",
    "HPQ": "stock_cfd",
    "HRB": "stock_cfd",
    "HSBCn": "stock_cfd",
    "HSX": "stock_cfd",
    "HSY": "stock_cfd",
    "HTHT": "stock_cfd",
    "HUBS": "stock_cfd",
    "HUM": "stock_cfd",
    "HUT": "stock_cfd",
    "HYLN": "stock_cfd",
    "HYPEUSD": "crypto",
    "IAC": "stock_cfd",
    "IBIT": "etf",
    "IBM": "stock_cfd",
    "IBN": "stock_cfd",
    "ICE": "stock_cfd",
    "ICL": "stock_cfd",
    "ICLN": "etf",
    "IDXX": "stock_cfd",
    "IHG": "stock_cfd",
    "III": "stock_cfd",
    "ILMN": "stock_cfd",
    "IMCD": "stock_cfd",
    "INCUSD": "crypto",
    "INCY": "stock_cfd",
    "INF": "stock_cfd",
    "INFY": "stock_cfd",
    "INO": "stock_cfd",
    "INSG": "stock_cfd",
    "INTEL": "stock_cfd",
    "INTU": "stock_cfd",
    "IOTUSD": "crypto",
    "IOVA": "stock_cfd",
    "IP": "stock_cfd",
    "IQV": "stock_cfd",
    "IR": "stock_cfd",
    "ISRG": "stock_cfd",
    "ITRK": "stock_cfd",
    "ITV": "stock_cfd",
    "ITW": "stock_cfd",
    "IVZ": "stock_cfd",
    "IWM": "etf",
    "IYW": "etf",
    "JBL": "stock_cfd",
    "JCI": "stock_cfd",
    "JD": "stock_cfd",
    "JDI": "stock_cfd",
    "JMAT": "stock_cfd",
    "JNJ": "stock_cfd",
    "JNUG": "etf",
    "JPM": "stock_cfd",
    "JPN225ft.s": "index",
    "KBX": "stock_cfd",
    "KDP": "stock_cfd",
    "KEY": "stock_cfd",
    "KGC": "stock_cfd",
    "KGF": "stock_cfd",
    "KGX": "stock_cfd",
    "KHC": "stock_cfd",
    "KKR": "stock_cfd",
    "KLAC": "stock_cfd",
    "KMI": "stock_cfd",
    "KO": "stock_cfd",
    "KODK": "stock_cfd",
    "KR": "stock_cfd",
    "KRN": "stock_cfd",
    "KSS": "stock_cfd",
    "LAC": "stock_cfd",
    "LAND": "stock_cfd",
    "LAUR": "stock_cfd",
    "LBTYK": "stock_cfd",
    "LC": "stock_cfd",
    "LCID": "stock_cfd",
    "LEG": "stock_cfd",
    "LEN": "stock_cfd",
    "LEVI": "stock_cfd",
    "LGEN": "stock_cfd",
    "LHX": "stock_cfd",
    "LI": "stock_cfd",
    "LLY": "stock_cfd",
    "LMT": "stock_cfd",
    "LNKUSD": "crypto",
    "LOW": "stock_cfd",
    "LPL": "stock_cfd",
    "LRCUSD": "crypto",
    "LRCX": "stock_cfd",
    "LSEG": "stock_cfd",
    "LTCJPY": "crypto",
    "LTCUSD": "crypto",
    "LULU": "stock_cfd",
    "LUMN": "stock_cfd",
    "LUV": "stock_cfd",
    "LVS": "stock_cfd",
    "LYB": "stock_cfd",
    "LYFT": "stock_cfd",
    "LongGilt": "bond",
    "M": "stock_cfd",
    "MA": "stock_cfd",
    "MANU": "stock_cfd",
    "MAR": "stock_cfd",
    "MARA": "stock_cfd",
    "MAT": "stock_cfd",
    "MBG": "stock_cfd",
    "MBLY": "stock_cfd",
    "MCD": "stock_cfd",
    "MCHP": "stock_cfd",
    "MCK": "stock_cfd",
    "MCO": "stock_cfd",
    "MDLZ": "stock_cfd",
    "MDT": "stock_cfd",
    "MET": "stock_cfd",
    "META": "stock_cfd",
    "MFA": "stock_cfd",
    "MFC": "stock_cfd",
    "MGM": "stock_cfd",
    "MKRUSD": "crypto",
    "MLM": "stock_cfd",
    "MMM": "stock_cfd",
    "MNDI": "stock_cfd",
    "MNG": "stock_cfd",
    "MNST": "stock_cfd",
    "MO": "stock_cfd",
    "MOH": "stock_cfd",
    "MOMO": "stock_cfd",
    "MPC": "stock_cfd",
    "MPLX": "stock_cfd",
    "MPWR": "stock_cfd",
    "MRCK": "stock_cfd",
    "MRK": "stock_cfd",
    "MRNA": "stock_cfd",
    "MRVL": "stock_cfd",
    "MS": "stock_cfd",
    "MSFT": "stock_cfd",
    "MTB": "stock_cfd",
    "MTCH": "stock_cfd",
    "MTX": "stock_cfd",
    "MUV2": "stock_cfd",
    "NAS100.s": "index",
    "NAS100ft.s": "index",
    "NBIX": "stock_cfd",
    "NBR": "stock_cfd",
    "NCLH": "stock_cfd",
    "NEE": "stock_cfd",
    "NEMD": "stock_cfd",
    "NEOUSD": "crypto",
    "NERUSD": "crypto",
    "NET": "stock_cfd",
    "NETH25.s": "index",
    "NFLX": "stock_cfd",
    "NG-Cs": "commodity",
    "NGRID": "stock_cfd",
    "NIO": "stock_cfd",
    "NKE": "stock_cfd",
    "NN": "stock_cfd",
    "NOC": "stock_cfd",
    "NOW": "stock_cfd",
    "NSC": "stock_cfd",
    "NTAP": "stock_cfd",
    "NTES": "stock_cfd",
    "NTRS": "stock_cfd",
    "NUE": "stock_cfd",
    "NUGT": "etf",
    "NVIDIA": "stock_cfd",
    "NVS": "stock_cfd",
    "NWS": "stock_cfd",
    "NXPCUSD": "crypto",
    "NXPI": "stock_cfd",
    "NXT": "stock_cfd",
    "NZDCAD.s": "forex_cross",
    "NZDCHF.s": "forex_cross",
    "NZDJPY.s": "forex_cross",
    "NZDSGD.s": "forex_cross",
    "NZDUSD.s": "forex_cross",
    "Nikkei225.s": "index",
    "OCDO": "stock_cfd",
    "OIH": "etf",
    "OIS": "stock_cfd",
    "OJ-Cs": "commodity",
    "OKBUSD": "crypto",
    "OKE": "stock_cfd",
    "OKTA": "stock_cfd",
    "OMC": "stock_cfd",
    "ONDOUSD": "crypto",
    "ONEUSD": "crypto",
    "OPFI": "stock_cfd",
    "ORCL": "stock_cfd",
    "ORLY": "stock_cfd",
    "OSTK": "stock_cfd",
    "OXY": "stock_cfd",
    "PANW": "stock_cfd",
    "PAYX": "stock_cfd",
    "PCAR": "stock_cfd",
    "PCG": "stock_cfd",
    "PDD": "stock_cfd",
    "PEG": "stock_cfd",
    "PENN": "stock_cfd",
    "PEP": "stock_cfd",
    "PFIZER": "stock_cfd",
    "PG": "stock_cfd",
    "PGR": "stock_cfd",
    "PH": "stock_cfd",
    "PINS": "stock_cfd",
    "PLAY": "stock_cfd",
    "PLD": "stock_cfd",
    "PLTR": "stock_cfd",
    "PLUG": "stock_cfd",
    "PM": "stock_cfd",
    "PNC": "stock_cfd",
    "POOL": "stock_cfd",
    "PPG": "stock_cfd",
    "PPL": "stock_cfd",
    "PRX": "stock_cfd",
    "PSA": "stock_cfd",
    "PSH": "stock_cfd",
    "PSN": "stock_cfd",
    "PSON": "stock_cfd",
    "PSX": "stock_cfd",
    "PTON": "stock_cfd",
    "PUM": "stock_cfd",
    "PVH": "stock_cfd",
    "PYPL": "stock_cfd",
    "QCLN": "etf",
    "QCOM": "stock_cfd",
    "QQQ": "etf",
    "QS": "stock_cfd",
    "RAA": "stock_cfd",
    "RACE": "stock_cfd",
    "RAND": "stock_cfd",
    "RBLX": "stock_cfd",
    "RCL": "stock_cfd",
    "REGN": "stock_cfd",
    "RF": "stock_cfd",
    "RGLD": "stock_cfd",
    "RIG": "stock_cfd",
    "RING": "etf",
    "RIVN": "stock_cfd",
    "RL": "stock_cfd",
    "RMV": "stock_cfd",
    "RNG": "stock_cfd",
    "ROBUSTAft.s": "commodity",
    "ROK": "stock_cfd",
    "ROKU": "stock_cfd",
    "ROP": "stock_cfd",
    "ROST": "stock_cfd",
    "RR": "stock_cfd",
    "RRTL": "stock_cfd",
    "RSG": "stock_cfd",
    "RTO": "stock_cfd",
    "RTX": "stock_cfd",
    "RWE": "stock_cfd",
    "SA40.s": "index",
    "SANUSD": "crypto",
    "SBRY": "stock_cfd",
    "SBUX": "stock_cfd",
    "SCHW": "stock_cfd",
    "SDR": "stock_cfd",
    "SDS": "etf",
    "SE": "stock_cfd",
    "SENS": "stock_cfd",
    "SGDJ": "etf",
    "SGDJPY.s": "forex_cross",
    "SGDM": "etf",
    "SGE": "stock_cfd",
    "SGP20.s": "index",
    "SGRO": "stock_cfd",
    "SHBUSD": "crypto",
    "SHL": "stock_cfd",
    "SHOP": "stock_cfd",
    "SHW": "stock_cfd",
    "SIG": "stock_cfd",
    "SIRI": "stock_cfd",
    "SKYUSD": "crypto",
    "SLB": "stock_cfd",
    "SLVP": "etf",
    "SMG": "stock_cfd",
    "SMIN": "stock_cfd",
    "SMT": "stock_cfd",
    "SN": "stock_cfd",
    "SNAP": "stock_cfd",
    "SNOW": "stock_cfd",
    "SNPS": "stock_cfd",
    "SO": "stock_cfd",
    "SOFI": "stock_cfd",
    "SOLJPY": "crypto",
    "SOLUSD": "crypto",
    "SP500.s": "index",
    "SP500ft.s": "index",
    "SPCE": "stock_cfd",
    "SPG": "stock_cfd",
    "SPGI": "stock_cfd",
    "SPI200.s": "index",
    "SPLK": "stock_cfd",
    "SPOT": "stock_cfd",
    "SPX": "stock_cfd",
    "SPY": "etf",
    "SPYX": "etf",
    "SRE": "stock_cfd",
    "SRT3": "stock_cfd",
    "SSE": "stock_cfd",
    "STJ": "stock_cfd",
    "STT": "stock_cfd",
    "STZ": "stock_cfd",
    "SUSUSD": "crypto",
    "SVT": "stock_cfd",
    "SW": "stock_cfd",
    "SWI20.s": "index",
    "SWK": "stock_cfd",
    "SWKS": "stock_cfd",
    "SWR": "stock_cfd",
    "SY1": "stock_cfd",
    "SYF": "stock_cfd",
    "SYK": "stock_cfd",
    "SYY": "stock_cfd",
    "Soybean-Cs": "commodity",
    "Sugar-Cs": "commodity",
    "TAN": "etf",
    "TCOM": "stock_cfd",
    "TDOC": "stock_cfd",
    "TEAM": "stock_cfd",
    "TEL": "stock_cfd",
    "TEVA": "stock_cfd",
    "TFC": "stock_cfd",
    "TGT": "stock_cfd",
    "TJX": "stock_cfd",
    "TLX": "stock_cfd",
    "TMO": "stock_cfd",
    "TMUS": "stock_cfd",
    "TOYOTA": "stock_cfd",
    "TRIP": "stock_cfd",
    "TRMB": "stock_cfd",
    "TROW": "stock_cfd",
    "TRST": "stock_cfd",
    "TRUMPUSD": "crypto",
    "TRV": "stock_cfd",
    "TRXUSD": "crypto",
    "TSLA": "stock_cfd",
    "TSM": "stock_cfd",
    "TSN": "stock_cfd",
    "TTD": "stock_cfd",
    "TTWO": "stock_cfd",
    "TW": "stock_cfd",
    "TWINDEX.s": "index",
    "TWLO": "stock_cfd",
    "TXN": "stock_cfd",
    "U": "stock_cfd",
    "UA": "stock_cfd",
    "UAL": "stock_cfd",
    "UBER": "stock_cfd",
    "UK100.s": "index",
    "UK100ft.s": "index",
    "UKOUSD.s": "stock_cfd",
    "UKOUSDft.s": "stock_cfd",
    "UL": "stock_cfd",
    "ULTA": "stock_cfd",
    "UMC": "stock_cfd",
    "UNH": "stock_cfd",
    "UNIUSD": "crypto",
    "UNP": "stock_cfd",
    "UPS": "stock_cfd",
    "UPST": "stock_cfd",
    "US2000.s": "index",
    "USB": "stock_cfd",
    "USDAED": "forex_cross",
    "USDAED.s": "forex_cross",
    "USDBRL.s": "forex_cross",
    "USDCAD": "forex_major",
    "USDCAD.s": "forex_cross",
    "USDCHF": "forex_major",
    "USDCHF.s": "forex_cross",
    "USDCLP.s": "forex_cross",
    "USDCNH": "forex_cross",
    "USDCOP.s": "forex_cross",
    "USDCZK.s": "forex_cross",
    "USDDKK.s": "forex_cross",
    "USDHKD": "forex_cross",
    "USDHKD.s": "forex_cross",
    "USDHUF.s": "forex_cross",
    "USDIDR.s": "forex_cross",
    "USDILS.s": "forex_cross",
    "USDINR.s": "forex_cross",
    "USDJPY": "forex_major",
    "USDJPY.s": "forex_cross",
    "USDKRW.s": "forex_cross",
    "USDMXN.s": "forex_cross",
    "USDNOK.s": "forex_cross",
    "USDSEK.s": "forex_cross",
    "USDSGD": "forex_cross",
    "USDSGD.s": "forex_cross",
    "USDTHB.s": "forex_cross",
    "USDTJPY": "crypto",
    "USDTWD.s": "forex_cross",
    "USDX.s": "index",
    "USDZAR": "forex_cross",
    "USDZAR.s": "forex_cross",
    "USL": "etf",
    "USNote10Y": "bond",
    "USO": "etf",
    "USOUSD.s": "stock_cfd",
    "UTDI": "stock_cfd",
    "UU": "stock_cfd",
    "VFC": "stock_cfd",
    "VFS": "stock_cfd",
    "VGT": "etf",
    "VIRT": "stock_cfd",
    "VIS": "stock_cfd",
    "VISA": "stock_cfd",
    "VIX.s": "index",
    "VLO": "stock_cfd",
    "VMC": "stock_cfd",
    "VMW": "stock_cfd",
    "VNA": "stock_cfd",
    "VOW": "stock_cfd",
    "VPK": "stock_cfd",
    "VRTX": "stock_cfd",
    "VSGX": "etf",
    "VTRS": "stock_cfd",
    "VZ": "stock_cfd",
    "W": "stock_cfd",
    "WDAY": "stock_cfd",
    "WDC": "stock_cfd",
    "WEN": "stock_cfd",
    "WFC": "stock_cfd",
    "WIFUSD": "crypto",
    "WISE": "stock_cfd",
    "WKHS": "stock_cfd",
    "WKL": "stock_cfd",
    "WLDUSD": "crypto",
    "WLFIUSD": "crypto",
    "WM": "stock_cfd",
    "WMB": "stock_cfd",
    "WMT": "stock_cfd",
    "WPM": "stock_cfd",
    "WPP": "stock_cfd",
    "WTB": "stock_cfd",
    "WU": "stock_cfd",
    "WY": "stock_cfd",
    "WYNN": "stock_cfd",
    "Wheat-Cs": "commodity",
    "XAGUSD.s": "commodity",
    "XAUEUR.s": "commodity",
    "XAUJPY.s": "commodity",
    "XAUUSD.s": "commodity",
    "XEL": "stock_cfd",
    "XLF": "etf",
    "XLK": "etf",
    "XLMJPY": "crypto",
    "XLMUSD": "crypto",
    "XOP": "etf",
    "XPDUSD.s": "commodity",
    "XPEV": "stock_cfd",
    "XPTUSD.s": "commodity",
    "XRPJPY": "crypto",
    "XRPUSD": "crypto",
    "XRX": "stock_cfd",
    "XTZUSD": "crypto",
    "YALA": "stock_cfd",
    "YUM": "stock_cfd",
    "YUMC": "stock_cfd",
    "Z": "stock_cfd",
    "ZAL": "stock_cfd",
    "ZBH": "stock_cfd",
    "ZBRA": "stock_cfd",
    "ZECUSD": "crypto",
    "ZIM": "stock_cfd",
    "ZM": "stock_cfd",
    "ZTS": "stock_cfd",
}


# ── Helpers ───────────────────────────────────────────────────

_ALL_FOREX = FOREX_MAJORS + FOREX_CROSSES + FOREX_S_SUFFIX

def pip_value(symbol: str) -> float:
    """Return pip size for symbol."""
    return PIP_VALUES.get(symbol, 0.0001)

def contract_size(symbol: str) -> float:
    """Return contract size (units per lot) from broker data."""
    return CONTRACT_SIZES.get(symbol, 100_000.0)

def asset_class(symbol: str) -> str:
    """Return asset class tag for symbol."""
    return SYMBOL_CLASS.get(symbol, "unknown")

# ── Priority subset (fast scan ~60 symbols) ────────────────────
# Curated high-liquidity instruments — preserved across re-generations.
# Activate full universe: ACTIVE_SYMBOLS=ALL or USE_FULL_UNIVERSE=1
PRIORITY_SYMBOLS: list[str] = [
    "AAPL", "ABNB", "ADBE", "AGG", "AMAT",
    "AMD", "AMZN", "ARKK", "ARKW", "AUDUSD.s",
    "AVGO", "BND", "BNDX", "BTCUSD", "COIN",
    "COPPER-Cs", "COST", "CRM", "DIS", "DJ30.s",
    "DOGUSD", "DRN", "EEM", "ETHUSD", "EURAUD.s",
    "EURCHF.s", "EURGBP.s", "EURJPY.s", "EURSGD.s", "EURUSD.s",
    "FRA40.s", "GAUUSD.s", "GBPCHF.s", "GBPJPY.s", "GBPUSD.s",
    "GBTC", "GDX", "GER40.s", "GLD", "GOOGL",
    "IBIT", "INTC", "IWM", "KO", "LRCX",
    "MELI", "META", "MSFT", "MU", "NAS100.s",
    "NFLX", "NG-Cs", "NVDA", "NZDUSD.s", "ORCL",
    "PEP", "PYPL", "QCOM", "QQQ", "SHOP",
    "SOLUSD", "SP500.s", "SPY", "SQ", "TAN",
    "TSLA", "TXN", "UBER", "UK100.s", "UKOUSD.s",
    "USDCAD.s", "USDCHF.s", "USDHKD.s", "USDJPY.s", "USDSGD.s",
    "USOUSD.s", "VGT", "VZ", "WMT", "XAGUSD.s",
    "XAUUSD.s", "XLF", "XLK", "XOP", "XRPUSD",
    "YINN"
]

# ── Active symbols ─────────────────────────────────────────────
import os
_env_active = os.getenv("ACTIVE_SYMBOLS", None)
_use_full = os.getenv("USE_FULL_UNIVERSE", "0") == "1"
SYMBOLS: list[str] = (
    [s.strip() for s in _env_active.split(",") if s.strip()]
    if _env_active
    else ALL_SYMBOLS
    if _use_full
    else PRIORITY_SYMBOLS
)
ACTIVE_SYMBOLS = SYMBOLS