def format_as_hex(data: bytes) -> str:
    hex_data = data.hex().upper()
    return ' '.join(hex_data[i:i+2]for i in range(0, len(hex_data), 2))
