use criterion::{black_box, criterion_group, criterion_main, Criterion};
use telescope_rs::{consciousness, topology, causal, mi};

fn bench_mi(c: &mut Criterion) {
    let a: Vec<f64> = (0..128).map(|i| (i as f64 * 0.1).sin()).collect();
    let b: Vec<f64> = (0..128).map(|i| (i as f64 * 0.07).cos()).collect();
    c.bench_function("mi_128d", |bencher| {
        bencher.iter(|| mi::mutual_info(black_box(&a), black_box(&b), 16))
    });
}

fn bench_pairwise_mi(c: &mut Criterion) {
    let data: Vec<f64> = (0..64 * 128).map(|i| (i as f64 * 0.03).sin()).collect();
    c.bench_function("pairwise_mi_64x128", |bencher| {
        bencher.iter(|| mi::pairwise_mi(black_box(&data), 64, 128, 16, 200))
    });
}

fn bench_consciousness_scan(c: &mut Criterion) {
    let data: Vec<f64> = (0..64 * 128).map(|i| (i as f64 * 0.03).sin()).collect();
    c.bench_function("consciousness_64c_50steps", |bencher| {
        bencher.iter(|| {
            let mut lens = consciousness::ConsciousnessLens::new(64, 128, 12, 50, 0.014);
            lens.scan(black_box(&data), 64, 128)
        })
    });
}

fn bench_topology_scan(c: &mut Criterion) {
    let data: Vec<f64> = (0..64 * 32).map(|i| (i as f64 * 0.05).sin()).collect();
    c.bench_function("topology_64pts_32d", |bencher| {
        bencher.iter(|| topology::scan(black_box(&data), 64, 32, 50, 0.014))
    });
}

fn bench_causal_scan(c: &mut Criterion) {
    let n = 100;
    let d = 10;
    let data: Vec<f64> = (0..n * d).map(|i| (i as f64 * 0.07).sin()).collect();
    c.bench_function("causal_100x10", |bencher| {
        bencher.iter(|| causal::scan(black_box(&data), n, d, 3, 16, 0.1))
    });
}

criterion_group!(benches, bench_mi, bench_pairwise_mi, bench_consciousness_scan, bench_topology_scan, bench_causal_scan);
criterion_main!(benches);
