// Korean Jamo decomposition - Hangul syllable U+AC00..U+D7A3 -> 3 jamo indices
// Pure algorithmic (modular arithmetic), no Python, suitable for circulus korean_cleaners proxy
#include <stdio.h>
#include <string.h>
#include <stdint.h>

// 19 choseong (initial): ㄱㄲㄴㄷㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎ (U+1100..U+1112)
static const char* CHO[19] = {"ㄱ","ㄲ","ㄴ","ㄷ","ㄸ","ㄹ","ㅁ","ㅂ","ㅃ","ㅅ","ㅆ","ㅇ","ㅈ","ㅉ","ㅊ","ㅋ","ㅌ","ㅍ","ㅎ"};
// 21 jungseong (medial): U+1161..U+1175
static const char* JUNG[21] = {"ㅏ","ㅐ","ㅑ","ㅒ","ㅓ","ㅔ","ㅕ","ㅖ","ㅗ","ㅘ","ㅙ","ㅚ","ㅛ","ㅜ","ㅝ","ㅞ","ㅟ","ㅠ","ㅡ","ㅢ","ㅣ"};
// 28 jongseong (final, 0=none): U+11A7 for none, then U+11A8..U+11C2
static const char* JONG[28] = {"","ㄱ","ㄲ","ㄳ","ㄴ","ㄵ","ㄶ","ㄷ","ㄹ","ㄺ","ㄻ","ㄼ","ㄽ","ㄾ","ㄿ","ㅀ","ㅁ","ㅂ","ㅄ","ㅅ","ㅆ","ㅇ","ㅈ","ㅊ","ㅋ","ㅌ","ㅍ","ㅎ"};

// Decode UTF-8, return codepoint + byte count
int utf8_decode(const unsigned char* p, uint32_t* cp) {
    if (p[0] < 0x80) { *cp = p[0]; return 1; }
    if ((p[0] & 0xE0) == 0xC0) { *cp = ((p[0] & 0x1F) << 6) | (p[1] & 0x3F); return 2; }
    if ((p[0] & 0xF0) == 0xE0) { *cp = ((p[0] & 0x0F) << 12) | ((p[1] & 0x3F) << 6) | (p[2] & 0x3F); return 3; }
    if ((p[0] & 0xF8) == 0xF0) { *cp = ((p[0] & 0x07) << 18) | ((p[1] & 0x3F) << 12) | ((p[2] & 0x3F) << 6) | (p[3] & 0x3F); return 4; }
    *cp = 0; return 1;
}

int main(int argc, char** argv) {
    const char* text = (argc > 1) ? argv[1] : "안녕하세요";
    printf("Input: %s\n", text);
    printf("Jamo decomposition (cho|jung|jong):\n");
    const unsigned char* p = (unsigned char*)text;
    while (*p) {
        uint32_t cp;
        int nb = utf8_decode(p, &cp);
        if (cp >= 0xAC00 && cp <= 0xD7A3) {
            uint32_t off = cp - 0xAC00;
            int cho = off / (21 * 28);
            int jung = (off / 28) % 21;
            int jong = off % 28;
            printf("  %.*s U+%04X -> cho=%2d(%s) jung=%2d(%s) jong=%2d(%s)\n",
                   nb, p, cp, cho, CHO[cho], jung, JUNG[jung], jong, JONG[jong]);
        } else if (cp == ' ') {
            printf("  (space)\n");
        } else {
            printf("  %.*s U+%04X (non-Hangul)\n", nb, p, cp);
        }
        p += nb;
    }
    return 0;
}
