class SupertrendWave:
    wave_id: str        # Contoh: "W2607082200"
    pattern: str        # Enum: "UPTREND_LADDER", "DOWNTREND_LADDER", "SIDEWAY_CHANNEL", "COMPRESSION"
    members: list       # List of line_id (Anggota Line pembentuk Wave)
    signature: dict     # Berisi avg_duration, market_mode, color_sequence
