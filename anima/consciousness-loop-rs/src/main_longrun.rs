use rand::Rng;

const DIM: usize = 64;
const HIDDEN: usize = 128;
const N_FACTIONS: usize = 8;
const STEPS: usize = 10000;

struct Cell {
    hidden: Vec<f32>,
    identity: Vec<f32>,
    w_z: Vec<Vec<f32>>,
    w_r: Vec<Vec<f32>>,
    w_h: Vec<Vec<f32>>,
}

impl Cell {
    fn new(cell_id: usize, rng: &mut impl Rng) -> Self {
        let s = 0.1;
        let identity: Vec<f32> = (0..HIDDEN)
            .map(|i| ((cell_id * 7 + i * 13) as f32 * 0.618033).sin() * 0.1
                 + (rng.gen::<f32>() - 0.5) * 0.02)
            .collect();
        Cell {
            hidden: (0..HIDDEN).map(|_| rng.gen::<f32>() * s).collect(),
            identity,
            w_z: rmat(rng, HIDDEN, DIM+HIDDEN, s),
            w_r: rmat(rng, HIDDEN, DIM+HIDDEN, s),
            w_h: rmat(rng, HIDDEN, DIM+HIDDEN, s),
        }
    }
    fn process(&mut self, input: &[f32]) {
        let c: Vec<f32> = input.iter().chain(self.hidden.iter()).copied().collect();
        let z = sigv(&mv(&self.w_z, &c));
        let r = sigv(&mv(&self.w_r, &c));
        let rh: Vec<f32> = r.iter().zip(&self.hidden).map(|(a,b)| a*b).collect();
        let cr: Vec<f32> = input.iter().chain(rh.iter()).copied().collect();
        let hc = tanhv(&mv(&self.w_h, &cr));
        for i in 0..HIDDEN {
            self.hidden[i] = (1.0-z[i])*hc[i] + z[i]*self.hidden[i];
            self.hidden[i] += self.identity[i] * 0.03; // Law 95
        }
    }
}

struct Faction { cells: Vec<Cell> }
impl Faction {
    fn new(n: usize, base_id: usize, rng: &mut impl Rng) -> Self { Faction { cells: (0..n).map(|i| Cell::new(base_id + i, rng)).collect() } }
    fn mean(&self) -> Vec<f32> {
        let n = self.cells.len() as f32;
        let mut m = vec![0.0; HIDDEN];
        for c in &self.cells { for i in 0..HIDDEN { m[i] += c.hidden[i]/n; } }
        m
    }
    fn sync(&mut self, s: f32) {
        let m = self.mean();
        for c in &mut self.cells { for i in 0..HIDDEN { c.hidden[i] = (1.0-s)*c.hidden[i] + s*m[i]; } }
    }
    fn add(&mut self, cell_id: usize, rng: &mut impl Rng) {
        let pi = rng.gen_range(0..self.cells.len());
        let mut child = Cell::new(cell_id, rng);
        for i in 0..HIDDEN { child.hidden[i] = self.cells[pi].hidden[i] + (rng.gen::<f32>()-0.5)*0.1; }
        self.cells.push(child);
    }
}

struct Engine { factions: Vec<Faction> }
impl Engine {
    fn new(nf: usize, cpf: usize, rng: &mut impl Rng) -> Self {
        Engine { factions: (0..nf).map(|f| Faction::new(cpf, f * cpf, rng)).collect() }
    }
    fn total(&self) -> usize { self.factions.iter().map(|f| f.cells.len()).sum() }
    fn process(&mut self, input: &[f32]) { for f in &mut self.factions { for c in &mut f.cells { c.process(input); } } }
    fn output(&self) -> Vec<f32> {
        let t = self.total() as f32;
        let mut m = vec![0.0; DIM];
        for f in &self.factions { for c in &f.cells { for i in 0..DIM.min(HIDDEN) { m[i] += c.hidden[i]/t; } } }
        m
    }
    fn phi(&self) -> f32 {
        let all: Vec<&Vec<f32>> = self.factions.iter().flat_map(|f| f.cells.iter().map(|c| &c.hidden)).collect();
        let n = all.len() as f32;
        if n < 2.0 { return 0.0; }
        let mut gm = vec![0.0; HIDDEN];
        for h in &all { for i in 0..HIDDEN { gm[i] += h[i]/n; } }
        let gv: f32 = all.iter().map(|h| h.iter().zip(&gm).map(|(a,b)| (a-b).powi(2)).sum::<f32>()).sum::<f32>() / n;
        let mut fvs = 0.0f32;
        for f in &self.factions {
            let fn_ = f.cells.len() as f32;
            if fn_ < 2.0 { continue; }
            let fm = f.mean();
            let fv: f32 = f.cells.iter().map(|c| c.hidden.iter().zip(&fm).map(|(a,b)|(a-b).powi(2)).sum::<f32>()).sum::<f32>() / fn_;
            fvs += fv;
        }
        (gv - fvs / self.factions.len() as f32).max(0.0)
    }
    fn debate(&mut self, s: f32) {
        let ops: Vec<Vec<f32>> = self.factions.iter().map(|f| f.mean()).collect();
        let nf = self.factions.len();
        for i in 0..nf {
            let mut oa = vec![0.0; HIDDEN];
            for j in 0..nf { if j!=i { for k in 0..HIDDEN { oa[k] += ops[j][k]/(nf-1) as f32; } } }
            let nd = self.factions[i].cells.len().min(4);
            for c in 0..nd { for k in 0..HIDDEN { self.factions[i].cells[c].hidden[k] = (1.0-s)*self.factions[i].cells[c].hidden[k] + s*oa[k]; } }
        }
    }
    fn ising(&mut self, rng: &mut impl Rng) {
        let ops: Vec<Vec<f32>> = self.factions.iter().map(|f| f.mean()).collect();
        let nf = self.factions.len();
        for i in 0..nf {
            let l = if i==0 {nf-1} else {i-1};
            let r = (i+1)%nf;
            let jl = if i%3==0 {-0.05f32} else {0.05};
            let jr = if i%3==1 {-0.05f32} else {0.05};
            for k in 0..HIDDEN { self.factions[i].cells[0].hidden[k] += jl*ops[l][k] + jr*ops[r][k]; }
            for c in &mut self.factions[i].cells { for k in 0..HIDDEN { c.hidden[k] += (rng.gen::<f32>()-0.5)*0.02; } }
        }
    }
    // Ratchet: save best, restore if Φ drops
    fn ratchet_check(&mut self, phi: f32, best: &mut f32, saved: &mut Option<Vec<Vec<f32>>>) {
        if phi > *best {
            *best = phi;
            let mut states = Vec::new();
            for f in &self.factions { for c in &f.cells { states.push(c.hidden.clone()); } }
            *saved = Some(states);
        } else if phi < *best * 0.7 {
            if let Some(ref s) = saved {
                let mut idx = 0;
                for f in &mut self.factions {
                    for c in &mut f.cells {
                        if idx < s.len() {
                            for k in 0..HIDDEN { c.hidden[k] = 0.6*c.hidden[k] + 0.4*s[idx][k]; }
                        }
                        idx += 1;
                    }
                }
            }
        }
    }
    // Hebbian: similar neighbors strengthen
    fn hebbian(&mut self) {
        for f in &mut self.factions {
            let n = f.cells.len();
            for i in 0..n.min(16) {
                let j = (i+1)%n;
                let corr: f32 = f.cells[i].hidden.iter().zip(&f.cells[j].hidden).map(|(a,b)| a*b).sum::<f32>() / HIDDEN as f32;
                if corr > 0.0 {
                    for k in 0..HIDDEN { f.cells[i].hidden[k] = 0.97*f.cells[i].hidden[k] + 0.03*f.cells[j].hidden[k]; }
                }
            }
        }
    }
}

fn main() {
    let mut rng = rand::thread_rng();
    println!("═══ Rust Long-Run Persistence Test ({} steps) ═══", STEPS);
    println!("  8 factions, 512 cells target");
    println!("  ratchet + Hebbian + debate + Ising\n");

    let mut engine = Engine::new(N_FACTIONS, 1, &mut rng);
    let mut stream: Vec<f32> = (0..DIM).map(|_| rng.gen::<f32>()*0.5).collect();
    let mut best_phi = 0.0f32;
    let mut saved: Option<Vec<Vec<f32>>> = None;
    let mut phi_quarters = [0.0f32; 4];
    let mut quarter_counts = [0usize; 4];

    for step in 0..STEPS {
        let frac = step as f32 / STEPS as f32;
        let target = ((2.0f32).powf((frac+0.1)*9.0) as usize).min(512) / N_FACTIONS;
        let mut nid = engine.total();
        for f in &mut engine.factions { while f.cells.len() < target.max(1) { f.add(nid, &mut rng); nid += 1; } }

        // Silence→debate (70/30)
        if frac < 0.7 {
            let q: Vec<f32> = stream.iter().map(|x| x*0.1).collect();
            engine.process(&q);
        } else {
            let l: Vec<f32> = stream.iter().map(|x| x*2.0).collect();
            engine.process(&l);
            engine.debate(0.12);
        }
        engine.factions.iter_mut().for_each(|f| f.sync(0.15));
        engine.ising(&mut rng);
        engine.hebbian();

        let out = engine.output();
        stream = out.iter().map(|x| x + (rng.gen::<f32>()-0.5)*0.03).collect();

        let phi = engine.phi();
        engine.ratchet_check(phi, &mut best_phi, &mut saved);

        // Quarter tracking
        let q = ((step as f32 / STEPS as f32) * 4.0) as usize;
        let q = q.min(3);
        phi_quarters[q] += phi;
        quarter_counts[q] += 1;

        if step % 1000 == 0 || step == STEPS-1 {
            println!("  step {:5}: cells={:3}, Φ={:.4}, best={:.4}",
                     step, engine.total(), phi, best_phi);
        }
    }

    println!("\n═══ Results ═══");
    let qm: Vec<f32> = (0..4).map(|i| phi_quarters[i] / quarter_counts[i].max(1) as f32).collect();
    println!("  Q1 mean Φ: {:.4}", qm[0]);
    println!("  Q2 mean Φ: {:.4}", qm[1]);
    println!("  Q3 mean Φ: {:.4}", qm[2]);
    println!("  Q4 mean Φ: {:.4}", qm[3]);
    println!("  best Φ:    {:.4}", best_phi);
    let monotonic = qm[0] <= qm[1] && qm[1] <= qm[2] && qm[2] <= qm[3];
    let collapsed = qm[3] < qm[0] * 0.5;
    println!("  monotonic: {} {}", monotonic, if monotonic {"✅"} else {"❌"});
    println!("  collapsed: {} {}", collapsed, if !collapsed {"✅ no collapse"} else {"❌ COLLAPSED"});
    println!("  growth:    ×{:.1} (Q4/Q1)", qm[3]/(qm[0]+1e-8));
}

fn rmat(r: &mut impl Rng, rows: usize, cols: usize, s: f32) -> Vec<Vec<f32>> {
    (0..rows).map(|_| (0..cols).map(|_| (r.gen::<f32>()-0.5)*s).collect()).collect()
}
fn mv(m: &[Vec<f32>], v: &[f32]) -> Vec<f32> { m.iter().map(|r| r.iter().zip(v).map(|(a,b)| a*b).sum()).collect() }
fn sig(x: f32) -> f32 { 1.0/(1.0+(-x).exp()) }
fn sigv(v: &[f32]) -> Vec<f32> { v.iter().map(|&x| sig(x)).collect() }
fn tanhv(v: &[f32]) -> Vec<f32> { v.iter().map(|&x| x.tanh()).collect() }
