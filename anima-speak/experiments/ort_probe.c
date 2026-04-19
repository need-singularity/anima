// Minimal ORT probe — prints input/output names and types for a .onnx model
#include <stdio.h>
#include <string.h>
#include "onnxruntime_c_api.h"

const OrtApi* g_ort = NULL;
#define CHECK(call) do { OrtStatus* s = (call); if (s) { fprintf(stderr, "ERR: %s\n", g_ort->GetErrorMessage(s)); g_ort->ReleaseStatus(s); return 1; } } while (0)

int main(int argc, char** argv) {
    if (argc < 2) { fprintf(stderr, "usage: %s <model.onnx>\n", argv[0]); return 1; }
    g_ort = OrtGetApiBase()->GetApi(ORT_API_VERSION);
    OrtEnv* env; CHECK(g_ort->CreateEnv(ORT_LOGGING_LEVEL_WARNING, "probe", &env));
    OrtSessionOptions* so; CHECK(g_ort->CreateSessionOptions(&so));
    OrtSession* sess; CHECK(g_ort->CreateSession(env, argv[1], so, &sess));
    OrtAllocator* alloc; CHECK(g_ort->GetAllocatorWithDefaultOptions(&alloc));

    size_t n_in; CHECK(g_ort->SessionGetInputCount(sess, &n_in));
    printf("INPUTS (%zu):\n", n_in);
    for (size_t i = 0; i < n_in; i++) {
        char* name; CHECK(g_ort->SessionGetInputName(sess, i, alloc, &name));
        OrtTypeInfo* ti; CHECK(g_ort->SessionGetInputTypeInfo(sess, i, &ti));
        const OrtTensorTypeAndShapeInfo* tsi; CHECK(g_ort->CastTypeInfoToTensorInfo(ti, &tsi));
        ONNXTensorElementDataType dt; CHECK(g_ort->GetTensorElementType(tsi, &dt));
        size_t nd; CHECK(g_ort->GetDimensionsCount(tsi, &nd));
        int64_t dims[8] = {0}; CHECK(g_ort->GetDimensions(tsi, dims, nd));
        printf("  [%zu] %s dtype=%d ndim=%zu dims=[", i, name, (int)dt, nd);
        for (size_t j = 0; j < nd; j++) printf("%s%ld", j?",":"", dims[j]);
        printf("]\n");
        g_ort->ReleaseTypeInfo(ti);
        g_ort->AllocatorFree(alloc, name);
    }

    size_t n_out; CHECK(g_ort->SessionGetOutputCount(sess, &n_out));
    printf("OUTPUTS (%zu):\n", n_out);
    for (size_t i = 0; i < n_out; i++) {
        char* name; CHECK(g_ort->SessionGetOutputName(sess, i, alloc, &name));
        OrtTypeInfo* ti; CHECK(g_ort->SessionGetOutputTypeInfo(sess, i, &ti));
        const OrtTensorTypeAndShapeInfo* tsi; CHECK(g_ort->CastTypeInfoToTensorInfo(ti, &tsi));
        ONNXTensorElementDataType dt; CHECK(g_ort->GetTensorElementType(tsi, &dt));
        size_t nd; CHECK(g_ort->GetDimensionsCount(tsi, &nd));
        int64_t dims[8] = {0}; CHECK(g_ort->GetDimensions(tsi, dims, nd));
        printf("  [%zu] %s dtype=%d ndim=%zu dims=[", i, name, (int)dt, nd);
        for (size_t j = 0; j < nd; j++) printf("%s%ld", j?",":"", dims[j]);
        printf("]\n");
        g_ort->ReleaseTypeInfo(ti);
        g_ort->AllocatorFree(alloc, name);
    }

    g_ort->ReleaseSession(sess);
    g_ort->ReleaseSessionOptions(so);
    g_ort->ReleaseEnv(env);
    return 0;
}
