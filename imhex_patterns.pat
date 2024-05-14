#pragma endian big

#include <std/mem>

struct Font {
    // 192 bits - 24 bytes
    u32 fixed;  // FONT - string
    padding[8]; // unknown1
    u16 character_length;
    u16 character_size;
    u32 section_size;
    padding[2]; // unknown2
    u16 tex_height;
    padding[2]; // unknown3
};

struct Tex {
    // 256 bits - 32 bytes
    u24  fixed; // TEX - string
    padding[5]; // unknown1
    u16 width;
    u16 height;
    padding[8]; // unknown2
    u32 data_size;
    padding[8]; // unknown3
    
};

struct Character {
    // 128 bits - 16 bytes
    padding[3]; // unknown1
    char character;
    u16 x;
    u16 y;
    u8 w;
    u8 h;
    u8 base_line;
    u16 spacing_before;
    u16 spacing_after;
    padding[1]; // padding
};

Font font @ 0x00;
Character characters[font.character_length] @ 0x00000018;
Tex tex @ font.section_size;