import os
import struct

_FONTDIR = os.path.join(os.path.dirname(__file__), 'fonts')

def decode_font_section(font_section: bytes) -> dict:
    data = struct.unpack(">4s8xHHL2xH", font_section)

    result = dict()
    result["magic"] = data[0].decode('utf-8')
    result["char_length"] = data[1]
    result["char_size"] = data[2]
    result["section_size"] = data[3]
    result["tex_height"] = data[4]

    return result

def decode_tex_section(tex_section: bytes) -> dict:
    data = struct.unpack(">3s5xHH8xL8x", tex_section)

    result = dict()
    result["magic"] = data[0].decode('utf-8')
    result["width"] = data[1]
    result["height"] = data[2]
    result["data_size"] = data[3]

    return result

def decode_character(character: bytes) -> dict:
    data = struct.unpack(">3xcHHBBBHHx", character)
    
    result = dict()
    try:
        result["char"] = data[0].decode('utf-8')
    except UnicodeDecodeError:
        result["char"] = "unknown"
    result["x"] = data[1]
    result["y"] = data[2]
    result["width"] = data[3]
    result["height"] = data[4]
    result["baseLine"] = data[5]
    result["spacingBefore"] = data[6]
    result["spacingAfter"] = data[7]

    return result

if __name__ == "__main__":
    files = [file for file in os.listdir(_FONTDIR) if (os.path.isfile(os.path.join(_FONTDIR, file)) and file.endswith('.font'))]
    
    for file in files:
        with open(os.path.join(_FONTDIR, file), 'rb') as f:
            font_section_decoded = decode_font_section(f.read(24))

            characters = []
            for index in range(font_section_decoded["char_length"]):
                char_data = f.read(font_section_decoded["char_size"])
                characters.append(decode_character(char_data))
            
            bytes_left = font_section_decoded["section_size"] - (font_section_decoded["char_length"] * font_section_decoded["char_size"])
            f.read(bytes_left // 2)

            tex_section_decoded = decode_tex_section(f.read(32))

            # TODO: Save the decoded data to a file