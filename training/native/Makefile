# Makefile — libtrain_step.so for hexa FIX-TRAIN-STEP-FFI
#
# Three build modes:
#
#   make stub    — mac/htz CPU build with CUDA stubs (type-check only)
#   make cuda    — H100 pod build with nvcc + cuBLAS + cudart
#   make test    — run the self-test binary
#
# Default = stub (portable). On H100 pods run `make cuda`.

UNAME := $(shell uname -s)
TARGET_STUB := libtrain_step_stub.so
TARGET_CUDA := libtrain_step.so
TEST_BIN := train_step_test

CFLAGS_COMMON := -Wall -O3 -std=c11 -fPIC
SRC := train_step.c
HDR := train_step.h

.PHONY: all stub cuda test clean

all: stub

stub: $(TARGET_STUB)

$(TARGET_STUB): $(SRC) $(HDR)
	cc $(CFLAGS_COMMON) -shared -o $@ $<
	@echo "[stub] $@ built (CPU stubs, no CUDA required)"

cuda: $(TARGET_CUDA)

$(TARGET_CUDA): $(SRC) $(HDR)
	nvcc -O3 -shared -Xcompiler -fPIC -x cu -lcublas -lcudart -o $@ $<
	@echo "[cuda] $@ built (linked against cuBLAS + cudart)"

test: $(TEST_BIN)
	@./$(TEST_BIN)

$(TEST_BIN): $(SRC) $(HDR)
	cc $(CFLAGS_COMMON) -DTRAIN_STEP_MAIN -o $@ $<

clean:
	rm -f $(TARGET_STUB) $(TARGET_CUDA) $(TEST_BIN) *.o
