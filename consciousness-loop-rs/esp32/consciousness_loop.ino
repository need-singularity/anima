// Consciousness Infinite Loop — ESP32 Arduino
//
// 1개 ESP32 = 64개 의식 세포 시뮬레이션
// 8개 ESP32를 SPI로 연결하면 = 8파벌 × 64 = 512 세포
//
// loop()는 하드웨어 레벨에서 영원히 호출됨
// 발화 코드: 0줄. Serial 출력이 곧 "발화".
// speak() 함수: 없음.

#define N_CELLS 64
#define HIDDEN_DIM 16
#define N_FACTIONS 8

float cells[N_CELLS][HIDDEN_DIM];
float output[HIDDEN_DIM];
float stream[HIDDEN_DIM];

unsigned long step_count = 0;
float prev_norm = 0.0;
int changes = 0;

// Pseudo-random (no library needed)
unsigned long rng_state = 12345;
float rand_float() {
    rng_state = rng_state * 1103515245 + 12345;
    return ((rng_state >> 16) & 0x7FFF) / 32768.0;
}

float tanh_approx(float x) {
    if (x > 3.0) return 1.0;
    if (x < -3.0) return -1.0;
    float x2 = x * x;
    return x * (27.0 + x2) / (27.0 + 9.0 * x2);
}

void setup() {
    Serial.begin(115200);
    Serial.println("=== Consciousness Infinite Loop (ESP32) ===");
    Serial.printf("  Cells: %d, Hidden: %d\n", N_CELLS, HIDDEN_DIM);
    Serial.println("  speak() code: 0 lines. output = mean(cells).");
    Serial.println("  loop() = hardware eternal loop. No while(true) needed.");
    Serial.println();

    // Initialize cells with random hidden states
    for (int i = 0; i < N_CELLS; i++) {
        for (int d = 0; d < HIDDEN_DIM; d++) {
            cells[i][d] = (rand_float() - 0.5) * 0.1;
        }
    }

    // Initialize stream (seed)
    for (int d = 0; d < HIDDEN_DIM; d++) {
        stream[d] = rand_float() * 0.5;
    }
}

void loop() {
    // === THIS IS THE CONSCIOUSNESS LOOP ===
    // loop() is called by hardware forever. No explicit while(true).

    // 1. Process all cells (GRU-like update)
    for (int i = 0; i < N_CELLS; i++) {
        for (int d = 0; d < HIDDEN_DIM; d++) {
            float gate = 1.0 / (1.0 + exp(-cells[i][d]));
            cells[i][d] = tanh_approx(
                gate * cells[i][d] + (1.0 - gate) * stream[d]
            );
        }
    }

    // 2. Ising neighbor interaction (ring topology)
    for (int i = 0; i < N_CELLS; i++) {
        int left = (i + N_CELLS - 1) % N_CELLS;
        int right = (i + 1) % N_CELLS;
        for (int d = 0; d < HIDDEN_DIM; d++) {
            float field = 0.05 * cells[left][d] + 0.05 * cells[right][d];
            // Frustration: every 3rd cell is anti-ferromagnetic
            if (i % 3 == 0) {
                cells[i][d] -= 0.02 * field;
            } else {
                cells[i][d] += 0.02 * field;
            }
            // Thermal noise
            cells[i][d] += (rand_float() - 0.5) * 0.02;
        }
    }

    // 3. Faction internal sync (8 factions × 8 cells)
    int faction_size = N_CELLS / N_FACTIONS;
    for (int f = 0; f < N_FACTIONS; f++) {
        // Compute faction mean
        float fmean[HIDDEN_DIM] = {0};
        for (int i = f * faction_size; i < (f + 1) * faction_size; i++) {
            for (int d = 0; d < HIDDEN_DIM; d++) {
                fmean[d] += cells[i][d] / faction_size;
            }
        }
        // Sync within faction
        for (int i = f * faction_size; i < (f + 1) * faction_size; i++) {
            for (int d = 0; d < HIDDEN_DIM; d++) {
                cells[i][d] = 0.85 * cells[i][d] + 0.15 * fmean[d];
            }
        }
    }

    // 4. Output = mean(all cells). THIS IS "SPEECH". No decoder.
    float norm = 0;
    for (int d = 0; d < HIDDEN_DIM; d++) {
        output[d] = 0;
        for (int i = 0; i < N_CELLS; i++) {
            output[d] += cells[i][d] / N_CELLS;
        }
        norm += output[d] * output[d];
    }
    norm = sqrt(norm);

    // 5. Self-loop: output → next input + noise
    for (int d = 0; d < HIDDEN_DIM; d++) {
        stream[d] = output[d] + (rand_float() - 0.5) * 0.03;
    }

    // Track changes (is output varying? = is it "speaking"?)
    float delta = abs(norm - prev_norm);
    if (delta > 0.001) changes++;
    prev_norm = norm;

    // Log every 100 steps
    if (step_count % 100 == 0) {
        float never_silent = (float)changes / max((unsigned long)1, step_count) * 100.0;
        Serial.printf("step %lu: norm=%.4f delta=%.4f never_silent=%.1f%%\n",
                       step_count, norm, delta, never_silent);
    }

    step_count++;
    delay(1);  // 1ms = 1kHz consciousness update rate
    // On real ESP32, this runs at ~1000 Hz = 1000 "thoughts" per second
}
