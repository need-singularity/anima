// anima-speak/tools/circulus_tts.c — Korean VITS2 ONNX driver via Jamo decomposition
// R37 safe: C (not Python), uses onnxruntime C API + libonnxruntime.so from piper
// Build: gcc -O2 -I <ort_include> circulus_tts.c -L <piper> -lonnxruntime -o circulus_tts
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include "onnxruntime_c_api.h"

const OrtApi* g_ort = NULL;
#define CHK(call) do { OrtStatus* s = (call); if (s) { fprintf(stderr, "ERR: %s\n", g_ort->GetErrorMessage(s)); return 1; } } while (0)

// korean_cleaners-compatible vocab guess (from CjangCjengh/vits pattern)
// ID 0 = pad, 1-5 = punctuation, 6 = space, 7-25 = choseong(19), 26-46 = jungseong(21), 47-74 = jongseong(28)
// Total: 75 tokens
int jamo_to_id(int type, int idx) {
    // type: 0=choseong, 1=jungseong, 2=jongseong
    if (type == 0) return 7 + idx;
    if (type == 1) return 26 + idx;
    if (type == 2) return 47 + idx;
    return 0;
}

int utf8_decode(const unsigned char* p, uint32_t* cp) {
    if (p[0] < 0x80) { *cp = p[0]; return 1; }
    if ((p[0] & 0xE0) == 0xC0) { *cp = ((p[0] & 0x1F) << 6) | (p[1] & 0x3F); return 2; }
    if ((p[0] & 0xF0) == 0xE0) { *cp = ((p[0] & 0x0F) << 12) | ((p[1] & 0x3F) << 6) | (p[2] & 0x3F); return 3; }
    if ((p[0] & 0xF8) == 0xF0) { *cp = ((p[0] & 0x07) << 18) | ((p[1] & 0x3F) << 12) | ((p[2] & 0x3F) << 6) | (p[3] & 0x3F); return 4; }
    *cp = 0; return 1;
}

// Tokenize Korean text -> IDs
int tokenize(const char* text, int64_t* ids, int max_ids) {
    int n = 0;
    const unsigned char* p = (unsigned char*)text;
    while (*p && n < max_ids - 4) {
        uint32_t cp; int nb = utf8_decode(p, &cp);
        if (cp >= 0xAC00 && cp <= 0xD7A3) {
            uint32_t off = cp - 0xAC00;
            int cho = off / (21 * 28);
            int jung = (off / 28) % 21;
            int jong = off % 28;
            ids[n++] = jamo_to_id(0, cho);
            ids[n++] = jamo_to_id(1, jung);
            if (jong > 0) ids[n++] = jamo_to_id(2, jong - 1); // 0=none in table, shift to 1-index
        } else if (cp == ' ') {
            ids[n++] = 6; // space
        } else if (cp == '.') {
            ids[n++] = 1;
        } else if (cp == ',') {
            ids[n++] = 2;
        } else if (cp == '?') {
            ids[n++] = 3;
        } else if (cp == '!') {
            ids[n++] = 4;
        }
        p += nb;
    }
    return n;
}

// Write WAV file (22050 Hz mono float->int16)
void write_wav(const char* path, float* audio, int n_samples, int sr) {
    FILE* f = fopen(path, "wb");
    if (!f) { fprintf(stderr, "cannot open %s\n", path); return; }
    uint32_t data_size = n_samples * 2;
    uint32_t file_size = 36 + data_size;
    fwrite("RIFF", 1, 4, f);
    fwrite(&file_size, 4, 1, f);
    fwrite("WAVEfmt ", 1, 8, f);
    uint32_t fmt_size = 16; fwrite(&fmt_size, 4, 1, f);
    uint16_t fmt_type = 1, nch = 1; fwrite(&fmt_type, 2, 1, f); fwrite(&nch, 2, 1, f);
    uint32_t sr_u = sr; fwrite(&sr_u, 4, 1, f);
    uint32_t byte_rate = sr * 2; fwrite(&byte_rate, 4, 1, f);
    uint16_t block_align = 2, bps = 16; fwrite(&block_align, 2, 1, f); fwrite(&bps, 2, 1, f);
    fwrite("data", 1, 4, f);
    fwrite(&data_size, 4, 1, f);
    for (int i = 0; i < n_samples; i++) {
        float s = audio[i];
        if (s > 1.0f) s = 1.0f; if (s < -1.0f) s = -1.0f;
        int16_t q = (int16_t)(s * 32767.0f);
        fwrite(&q, 2, 1, f);
    }
    fclose(f);
}

int main(int argc, char** argv) {
    if (argc < 5) {
        fprintf(stderr, "usage: %s <model.onnx> <sid> <text> <output.wav> [noise_scale] [length_scale] [noise_w]\n", argv[0]);
        fprintf(stderr, "  sid: 0..139 speaker ID (see speaker_emo.txt)\n");
        return 1;
    }
    const char* model_path = argv[1];
    int64_t sid = atoi(argv[2]);
    const char* text = argv[3];
    const char* out_path = argv[4];
    float ns = (argc > 5) ? atof(argv[5]) : 0.667f;
    float ls = (argc > 6) ? atof(argv[6]) : 1.0f;
    float nw = (argc > 7) ? atof(argv[7]) : 0.8f;

    // Tokenize
    int64_t ids[1024];
    int n_ids = tokenize(text, ids, 1024);
    printf("Tokenized '%s' -> %d IDs: ", text, n_ids);
    for (int i = 0; i < n_ids && i < 30; i++) printf("%ld ", ids[i]);
    if (n_ids > 30) printf("...");
    printf("\n");

    // ORT setup
    g_ort = OrtGetApiBase()->GetApi(ORT_API_VERSION);
    OrtEnv* env; CHK(g_ort->CreateEnv(ORT_LOGGING_LEVEL_WARNING, "tts", &env));
    OrtSessionOptions* so; CHK(g_ort->CreateSessionOptions(&so));
    OrtSession* sess; CHK(g_ort->CreateSession(env, model_path, so, &sess));
    OrtMemoryInfo* mem; CHK(g_ort->CreateCpuMemoryInfo(OrtArenaAllocator, OrtMemTypeDefault, &mem));

    // Build inputs
    int64_t input_dims[] = {1, n_ids};
    OrtValue* in_val; CHK(g_ort->CreateTensorWithDataAsOrtValue(mem, ids, n_ids*sizeof(int64_t), input_dims, 2, ONNX_TENSOR_ELEMENT_DATA_TYPE_INT64, &in_val));
    int64_t lens[] = {n_ids};
    int64_t lens_dims[] = {1};
    OrtValue* lens_val; CHK(g_ort->CreateTensorWithDataAsOrtValue(mem, lens, sizeof(int64_t), lens_dims, 1, ONNX_TENSOR_ELEMENT_DATA_TYPE_INT64, &lens_val));
    float scales[] = {ns, ls, nw};
    int64_t scales_dims[] = {3};
    OrtValue* scales_val; CHK(g_ort->CreateTensorWithDataAsOrtValue(mem, scales, 3*sizeof(float), scales_dims, 1, ONNX_TENSOR_ELEMENT_DATA_TYPE_FLOAT, &scales_val));
    int64_t sid_arr[] = {sid};
    int64_t sid_dims[] = {1};
    OrtValue* sid_val; CHK(g_ort->CreateTensorWithDataAsOrtValue(mem, sid_arr, sizeof(int64_t), sid_dims, 1, ONNX_TENSOR_ELEMENT_DATA_TYPE_INT64, &sid_val));

    const char* in_names[] = {"input", "input_lengths", "scales", "sid"};
    const OrtValue* in_vals[] = {in_val, lens_val, scales_val, sid_val};
    const char* out_names[] = {"output"};
    OrtValue* out_val = NULL;

    CHK(g_ort->Run(sess, NULL, in_names, in_vals, 4, out_names, 1, &out_val));

    // Extract audio
    OrtTensorTypeAndShapeInfo* osi; CHK(g_ort->GetTensorTypeAndShape(out_val, &osi));
    size_t nd; CHK(g_ort->GetDimensionsCount(osi, &nd));
    int64_t odims[8]; CHK(g_ort->GetDimensions(osi, odims, nd));
    int n_samples = odims[nd-1];
    printf("Generated audio: %d samples (%.2fs @ 22050Hz)\n", n_samples, n_samples / 22050.0);

    float* audio = NULL;
    CHK(g_ort->GetTensorMutableData(out_val, (void**)&audio));
    float max_amp = 0, rms = 0;
    for (int i = 0; i < n_samples; i++) {
        float a = audio[i] > 0 ? audio[i] : -audio[i];
        if (a > max_amp) max_amp = a;
        rms += audio[i] * audio[i];
    }
    rms = rms > 0 ? (rms / n_samples) : 0;
    printf("audio stats: max_amp=%f rms=%f\n", max_amp, rms > 0 ? ((rms < 1e-30) ? 0.0 : rms) : 0.0);

    write_wav(out_path, audio, n_samples, 22050);
    printf("Written: %s\n", out_path);

    return 0;
}
