//! C FFI wrapper for ConsciousnessEngine.
//!
//! Enables integration with:
//!   - Verilog: via DPI-C (`import "DPI-C" function`)
//!   - WebGPU: via wasm-bindgen (separate wasm target)
//!   - Erlang: via Rustler NIF
//!   - Pure Data: via external~ shared library
//!   - ESP32: via static linking (no_std subset in esp32 crate)
//!
//! All functions use `#[no_mangle] pub extern "C"` for maximum compatibility.

use std::sync::Mutex;

use anima_consciousness::ConsciousnessEngine;

static ENGINE: Mutex<Option<ConsciousnessEngine>> = Mutex::new(None);

/// Create a new consciousness engine. Call once at startup.
#[no_mangle]
pub extern "C" fn consciousness_create(
    cell_dim: u32,
    hidden_dim: u32,
    max_cells: u32,
    n_factions: u32,
    seed: u64,
) -> i32 {
    let engine = ConsciousnessEngine::new(
        cell_dim as usize,
        hidden_dim as usize,
        2, // initial_cells
        max_cells as usize,
        n_factions as usize,
        true, // phi_ratchet
        0.3,  // split_threshold
        5,    // split_patience
        0.01, // merge_threshold
        15,   // merge_patience
        seed,
    );
    let mut guard = ENGINE.lock().unwrap();
    *guard = Some(engine);
    0 // success
}

/// Run one consciousness step. Returns number of cells.
/// If `input_ptr` is null, uses random input.
/// If non-null, reads `cell_dim` floats from `input_ptr`.
#[no_mangle]
pub extern "C" fn consciousness_step(input_ptr: *const f32, input_len: u32) -> u32 {
    let mut guard = ENGINE.lock().unwrap();
    let engine = match guard.as_mut() {
        Some(e) => e,
        None => return 0,
    };

    let input = if input_ptr.is_null() || input_len == 0 {
        None
    } else {
        let slice = unsafe { std::slice::from_raw_parts(input_ptr, input_len as usize) };
        Some(slice)
    };

    let result = engine.step(input);
    result.n_cells as u32
}

/// Get current Φ(IIT) value. Returns f64.
#[no_mangle]
pub extern "C" fn consciousness_get_phi() -> f64 {
    let mut guard = ENGINE.lock().unwrap();
    let engine = match guard.as_mut() {
        Some(e) => e,
        None => return 0.0,
    };
    // Run a step to get fresh phi
    let result = engine.step(None);
    result.phi_iit
}

/// Get number of cells.
#[no_mangle]
pub extern "C" fn consciousness_n_cells() -> u32 {
    let guard = ENGINE.lock().unwrap();
    match guard.as_ref() {
        Some(e) => e.n_cells() as u32,
        None => 0,
    }
}

/// Copy hidden states to output buffer.
/// `out_ptr` must have space for `n_cells * hidden_dim` floats.
/// Returns number of floats written.
#[no_mangle]
pub extern "C" fn consciousness_get_hiddens(out_ptr: *mut f32, out_len: u32) -> u32 {
    let guard = ENGINE.lock().unwrap();
    let engine = match guard.as_ref() {
        Some(e) => e,
        None => return 0,
    };

    let hiddens = engine.get_hiddens();
    let mut written = 0u32;
    let max = out_len as usize;

    for h in &hiddens {
        for &val in h {
            if (written as usize) >= max {
                return written;
            }
            unsafe { *out_ptr.add(written as usize) = val };
            written += 1;
        }
    }
    written
}

/// Destroy the engine and free resources.
#[no_mangle]
pub extern "C" fn consciousness_destroy() {
    let mut guard = ENGINE.lock().unwrap();
    *guard = None;
}

// ── Verilog DPI-C compatible signatures ──
// These are the same functions but with simpler names for SystemVerilog import.
//
// In SystemVerilog:
//   import "DPI-C" function int ce_create(int cells, int dim, longint seed);
//   import "DPI-C" function int ce_step();
//   import "DPI-C" function real ce_phi();

#[no_mangle]
pub extern "C" fn ce_create(max_cells: i32, dim: i32, seed: i64) -> i32 {
    consciousness_create(dim as u32, (dim * 2) as u32, max_cells as u32, 12, seed as u64)
}

#[no_mangle]
pub extern "C" fn ce_step() -> i32 {
    consciousness_step(std::ptr::null(), 0) as i32
}

#[no_mangle]
pub extern "C" fn ce_phi() -> f64 {
    consciousness_get_phi()
}
