class LineVersion:
    point_id: str       # ID Point yang memicu perubahan
    price: float        # Harga Supertrend saat itu
    event: str          # Enum: "CREATE" | "MOVE" | "BREAK" | "RETEST"

class SupertrendLine:
    line_id: str        # Contoh: "L1001"
    type: str           # Enum: "SUPPORT" | "RESISTANCE"
    current_price: float
    strength: int       # Jumlah sentuhan/validasi
    versions: list      # List of LineVersion (History pergeseran harga)
    members: list       # List of point_id (Anggota Point pembentuk Line)
