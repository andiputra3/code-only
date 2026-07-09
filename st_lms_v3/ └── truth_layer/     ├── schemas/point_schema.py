class SupertrendPoint:
    point_id: str       # Contoh: "P2607081920" (Prefix + YYMMDDHHmm)
    price: float        # Contoh: 61526.8
    type: str           # Enum: "SUPPORT" | "RESISTANCE"
    color: str          # Enum: "GREEN" | "RED"
    time_wib: str       # Contoh: "2026-07-08 19:20:00"
