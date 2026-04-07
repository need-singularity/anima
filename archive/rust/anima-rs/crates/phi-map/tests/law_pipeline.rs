use anima_phi_map::{LawTerrain, PhiTerrain, TerrainPoint, AsciiHeatmap};

#[test]
fn test_law_terrain_from_json() {
    let json = include_str!("law_terrain_test.json");
    let terrain = LawTerrain::from_json(json).expect("Failed to parse law terrain JSON");

    assert!((terrain.baseline_phi - 1.2345).abs() < 1e-4);
    assert_eq!(terrain.laws.len(), 2);
    assert_eq!(terrain.interactions.len(), 1);
    assert!((terrain.integrated_phi - 1.3).abs() < 1e-4);
}

#[test]
fn test_law_terrain_render_all() {
    let json = include_str!("law_terrain_test.json");
    let terrain = LawTerrain::from_json(json).unwrap();
    let output = terrain.render_all();

    // Should contain section headers
    assert!(output.contains("Law Single Effects"));
    assert!(output.contains("Synergy Matrix"));
    assert!(output.contains("Integrated Analysis"));
    // Should contain law keys
    assert!(output.contains("T_EQ"));
    assert!(output.contains("SYM"));
}

#[test]
fn test_law_terrain_roundtrip() {
    let json = include_str!("law_terrain_test.json");
    let terrain = LawTerrain::from_json(json).unwrap();
    let re_json = terrain.to_json();
    let terrain2 = LawTerrain::from_json(&re_json).unwrap();

    assert!((terrain.baseline_phi - terrain2.baseline_phi).abs() < 1e-10);
    assert_eq!(terrain.laws.len(), terrain2.laws.len());
}

#[test]
fn test_phi_terrain_basic() {
    let modules = vec!["ModA".to_string(), "ModB".to_string()];
    let scales = vec![32, 64];
    let mut terrain = PhiTerrain::new(modules, scales);

    terrain.add_point(TerrainPoint {
        modules: vec![],
        n_modules: 0,
        cells: 32,
        phi_iit: 1.0,
        phi_proxy: 10.0,
        ce: 2.5,
        stable: true,
        delta_pct: 0.0,
    });

    terrain.add_point(TerrainPoint {
        modules: vec!["ModA".to_string()],
        n_modules: 1,
        cells: 32,
        phi_iit: 1.5,
        phi_proxy: 15.0,
        ce: 2.0,
        stable: true,
        delta_pct: 50.0,
    });

    let heatmap = AsciiHeatmap::render(&terrain);
    assert!(!heatmap.is_empty());

    let peak = terrain.peak();
    assert!(peak.is_some());
    assert!((peak.unwrap().phi_iit - 1.5).abs() < 1e-4);
}
