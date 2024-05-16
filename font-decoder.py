import os
import struct
import logging
import potrace
import argparse
import numpy as np
from PIL import Image

_FONTDIR = os.path.join(os.path.dirname(__file__), 'fonts')
_RESULTDIR = os.path.join(os.path.dirname(__file__), 'result')

def decode_font_section(font_section: bytes) -> dict:
    """Decodes the first 24 bytes of the font file."""
    data = struct.unpack(">4sB7xHHL2xH", font_section)
    logger.debug(f"Font section: {font_section}")
    logger.debug(f"Data: {data}")

    result = dict()
    result["magic"] = data[0].decode('utf-8')
    result["version"] = data[1]
    result["char_length"] = data[2]
    result["char_size"] = data[3]
    result["section_size"] = data[4]
    result["tex_height"] = data[5]

    return result

def decode_tex_section(tex_section: bytes) -> dict:
    data = struct.unpack(">3s5xHH8xL8x", tex_section)
    logger.debug(f"Tex section: {tex_section}")
    logger.debug(f"Data: {data}")

    result = dict()
    result["magic"] = data[0].decode('utf-8')
    result["width"] = data[1]
    result["height"] = data[2]
    result["data_size"] = data[3]

    return result

def decode_character(character: bytes) -> dict:
    data = struct.unpack(">3xcHHBBBHHx", character)
    
    result = dict()
    result["ord"] = data[0]
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

def read_bmp_data(file, width, height) -> list[bytes]:
    binary_data = []

    for y in range(height):
        line = file.read(width)
        binary_data.extend([line[i:i+1] for i in range(0, len(line))])

    return binary_data

def convert_to_image(binary_data, width, height) -> Image:
    image = Image.new('L', (width, height))
    
    pixels = [(0xFF if byte == b'\xff' else 0x00) for byte in binary_data]

    image.putdata(pixels)

    return image

def decode_font(file: str) -> tuple[list[bytes], dict, dict, list[dict]]:
    with open(os.path.join(_FONTDIR, file), 'rb') as f:
        # 192 bits - 24 bytes
        font_section_decoded = decode_font_section(f.read(24))

        if font_section_decoded["version"] != 1:
            logger.warn(f"Unsupported version: {font_section_decoded['version']}")
        
        # each character -> 128 bits - 16 bytes
        characters = []
        for index in range(font_section_decoded["char_length"]):
            char_data = f.read(font_section_decoded["char_size"])
            characters.append(decode_character(char_data))
        
        bytes_left = font_section_decoded["section_size"] - (font_section_decoded["char_length"] * font_section_decoded["char_size"]) - 24
        f.read(bytes_left)

        # 256 bits - 32 bytes
        tex_section_decoded = decode_tex_section(f.read(32))

        return read_bmp_data(f, tex_section_decoded["width"], tex_section_decoded["height"]), font_section_decoded, tex_section_decoded, characters

def get_char_from_font(font_image: Image, char: dict) -> Image:
    """Extracts the character image from the font image."""
    return font_image.crop((
        char["x"], 
        char["y"],
        char["x"] + char["width"], 
        char["y"] + char["height"],
    ))

def svg_convert(image, width, height) -> str:
    svg_image = ""
    svg_image += f'<svg version="1.1" width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">'

    for x in range(width):
        for y in range(height):
            if image[y][x] == 0:
                continue
            svg_image += f'<rect x="{x}" y="{y}" width="1" height="1" style="fill:rgb(255,255,255); stroke:none;" />\n'
            
    svg_image += """</svg>\n"""

    return svg_image

def export_font(file: str) -> None:
    import PIL.ImageOps # used to invert the image

    with open(os.path.join(_FONTDIR, file), 'rb') as f:
        decoded_font = decode_font(file)
    
    width, height = decoded_font[2]["width"], decoded_font[2]["height"]
    font_image = convert_to_image(decoded_font[0], width, height)
    
    font_dir = result_path = os.path.join(_RESULTDIR, file[:-5])
    if not os.path.exists(font_dir):
        os.makedirs(font_dir)

    # create an .svg image for each character in the 'result/fontname' directory
    for char in decoded_font[3]:
        char_width, char_height = char["width"], char["height"]
        if char_width == 0 or char_height == 0: # skip empty characters
            continue
        if char["char"] == "unknown": # skip unknown characters
            logger.warn(f"Skipping unknown character: (ord: {char['ord']})")
            continue
        result_path = os.path.join(font_dir, str(ord(char["char"])))

        pil_image = get_char_from_font(font_image, char)
        pil_image = PIL.ImageOps.invert(pil_image)
        array_image = np.array(pil_image)
        result_image = svg_convert(array_image, char_width, char_height)

        del pil_image, array_image # free memory

        with open(f"{result_path}.svg", "w") as f:
            f.write(result_image)

    # TODO: create a .tff file from the .svg files

    return

if __name__ == "__main__":
    # check arguments passed
    parser = argparse.ArgumentParser(description='Select which features to run.')
    parser.add_argument('--debug', help='Run in debug mode.', nargs='*')
    parser.add_argument('-d', '--decode', help="Decode the font into a single .bmp file", nargs='*')
    parser.add_argument('-e', '--export', help="Export the font as a .tff file", nargs='*')
    args = parser.parse_args()

    # logging config
    logger = logging.getLogger(__name__)
    logging.basicConfig(level=logging.DEBUG if args.debug else logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    files = [file for file in os.listdir(_FONTDIR) if (os.path.isfile(os.path.join(_FONTDIR, file)) and file.endswith('.font'))]
    
    for file in files:
        no_args = args.decode is None and args.export is None

        if args.decode is not None or no_args:
            logger.info(f"Decoding file: {file}")
            decoded_font = decode_font(file)

            image = convert_to_image(decoded_font[0], decoded_font[2]["width"], decoded_font[2]["height"])
            image.save(os.path.join(_RESULTDIR, f"{file[:-5]}_output.bmp"), "BMP")
        
        if args.export is not None:
            logger.info(f"Exporting file: {file} ")
            export_font(file)
        
        logger.info(f"Done.")