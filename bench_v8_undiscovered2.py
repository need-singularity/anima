#!/usr/bin/env python3
"""bench_v8_undiscovered2.py — Round 2: 30+ NEW architectures to beat Φ(IIT) 19.34

Strategy:
  1. Fix 7 exploding engines from Round 1 (clamp + normalize)
  2. Quantum+Geometry hybrids (top domains combined)
  3. Completely new domains: Thermodynamic Computing, Tensor Networks,
     Topological Quantum, Criticality Tuning, Membrane Computing,
     Swarm Robotics, Cortical Columns, Dendritic Computing, etc.

Previous ALL-TIME top: Q4 QUANTUM_WALK = 19.34, U6 HYPERBOLIC = 18.86

Usage:
  python bench_v8_undiscovered2.py
  python bench_v8_undiscovered2.py --only 1 5 10
  python bench_v8_undiscovered2.py --cells 512 --steps 300
"""

import sys, torch, torch.nn as nn, torch.nn.functional as F
import numpy as np, time, math, argparse
from dataclasses import dataclass, field
from typing import List, Dict, Tuple

sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)


@dataclass
class BenchResult:
    name: str; phi_iit: float; phi_proxy: float
    ce_start: float; ce_end: float; cells: int; steps: int; time_sec: float
    extra: dict = field(default_factory=dict)
    def summary(self):
        ce = f"CE {self.ce_start:.3f}->{self.ce_end:.3f}" if self.ce_start > 0 else "CE n/a"
        return (f"  {self.name:<36s} | Φ(IIT)={self.phi_iit:>7.3f}  "
                f"Φ(prx)={self.phi_proxy:>8.2f} | {ce:<22s} | "
                f"c={self.cells:>4d} s={self.steps:>4d} t={self.time_sec:.1f}s")


class PhiIIT:
    def __init__(self, nb=16): self.nb = nb
    def compute(self, h):
        n = h.shape[0]
        if n < 2: return 0.0, {}
        hs = [h[i].detach().cpu().float().numpy() for i in range(n)]
        if n <= 32:
            pairs = [(i,j) for i in range(n) for j in range(i+1,n)]
        else:
            import random; ps = set()
            for i in range(n):
                for _ in range(min(8,n-1)):
                    j = random.randint(0,n-1)
                    if i!=j: ps.add((min(i,j),max(i,j)))
            pairs = list(ps)
        mi = np.zeros((n,n))
        for i,j in pairs:
            v = self._mi(hs[i],hs[j]); mi[i,j]=v; mi[j,i]=v
        tot = mi.sum()/2; mp = self._mp(n,mi)
        sp = max(0,(tot-mp)/max(n-1,1))
        mv = mi[mi>0]; cx = float(np.std(mv)) if len(mv)>1 else 0.0
        return sp+cx*0.1, {}
    def _mi(self,x,y):
        xr,yr = x.max()-x.min(), y.max()-y.min()
        if xr<1e-10 or yr<1e-10: return 0.0
        xn=(x-x.min())/(xr+1e-8); yn=(y-y.min())/(yr+1e-8)
        h,_,_=np.histogram2d(xn,yn,bins=self.nb,range=[[0,1],[0,1]])
        h=h/(h.sum()+1e-8); px,py=h.sum(1),h.sum(0)
        hx=-np.sum(px*np.log2(px+1e-10)); hy=-np.sum(py*np.log2(py+1e-10))
        hxy=-np.sum(h*np.log2(h+1e-10)); return max(0,hx+hy-hxy)
    def _mp(self,n,mi):
        if n<=1: return 0.0
        if n<=8:
            mc=float('inf')
            for m in range(1,2**n-1):
                ga=[i for i in range(n) if m&(1<<i)]; gb=[i for i in range(n) if not m&(1<<i)]
                if ga and gb: mc=min(mc,sum(mi[i,j] for i in ga for j in gb))
            return mc if mc!=float('inf') else 0.0
        d=mi.sum(1); L=np.diag(d)-mi
        try:
            ev,evec=np.linalg.eigh(L); f=evec[:,1]
            ga=[i for i in range(n) if f[i]>=0]; gb=[i for i in range(n) if f[i]<0]
            if not ga or not gb: ga,gb=list(range(n//2)),list(range(n//2,n))
            return sum(mi[i,j] for i in ga for j in gb)
        except: return 0.0

def phi_proxy(h,nf=8):
    hr=h.abs().float() if h.is_complex() else h.float(); n=hr.shape[0]
    if n<2: return 0.0
    gv=((hr-hr.mean(0))**2).sum()/n; nf=min(nf,n//2)
    if nf<2: return gv.item()
    fs=n//nf; fvs=0
    for i in range(nf):
        f=hr[i*fs:(i+1)*fs]
        if len(f)>=2: fvs+=((f-f.mean(0))**2).sum().item()/len(f)
    return max(0,gv.item()-fvs/nf)

_phi=PhiIIT(16)
def measure_phi(h,nf=8):
    hr=h.abs().float() if h.is_complex() else h.float()
    p,_=_phi.compute(hr); return p,phi_proxy(h,nf)


class BenchMind(nn.Module):
    def __init__(self,id=64,hd=128,od=64):
        super().__init__()
        self.ea=nn.Sequential(nn.Linear(id+hd,128),nn.ReLU(),nn.Linear(128,od))
        self.eg=nn.Sequential(nn.Linear(id+hd,128),nn.ReLU(),nn.Linear(128,od))
        self.mem=nn.GRUCell(od+1,hd); self.hd=hd
        with torch.no_grad():
            for p in self.ea.parameters(): p.add_(torch.randn_like(p)*0.3)
            for p in self.eg.parameters(): p.add_(torch.randn_like(p)*-0.3)
    def forward(self,x,h):
        c=torch.cat([x,h],-1); a=self.ea(c); g=self.eg(c); o=a-g
        t=(o**2).mean(-1,keepdim=True)
        nh=self.mem(torch.cat([o.detach(),t.detach()],-1),h)
        return o,t.mean().item(),nh

def faction_sync(h,nf=8,sync=0.15,debate=0.15,step=0):
    n=h.shape[0]; nf=min(nf,n//2)
    if nf<2: return h
    fs=n//nf; h=h.clone()
    for i in range(nf):
        s,e=i*fs,(i+1)*fs; fm=h[s:e].mean(0); h[s:e]=(1-sync)*h[s:e]+sync*fm
    if step>5:
        ops=torch.stack([h[i*fs:(i+1)*fs].mean(0) for i in range(nf)]); go=ops.mean(0)
        for i in range(nf):
            s=i*fs; dc=max(1,fs//4); h[s:s+dc]=(1-debate)*h[s:s+dc]+debate*go
    return h

def gen_batch(d,bs=1):
    x=torch.randn(bs,d); return x, torch.roll(x,1,-1)*0.8+torch.randn_like(x)*0.1


class BaseEngine(nn.Module):
    def __init__(self,nc,id=64,hd=128,od=64):
        super().__init__()
        self.nc=nc; self.hd=hd; self.id=id; self.od=od
        self.mind=BenchMind(id,hd,od); self.out_head=nn.Linear(od,id)
        self.hiddens=torch.randn(nc,hd)*0.1
    def arch_update(self,step): pass
    def process(self,x,step=0):
        outs,tens,nh=[],[],[]
        for i in range(self.nc):
            o,t,h=self.mind(x,self.hiddens[i:i+1]); outs.append(o); tens.append(t); nh.append(h.squeeze(0))
        self.hiddens=torch.stack(nh).detach()
        self.arch_update(step)
        # SAFETY: clamp hiddens to prevent explosion
        self.hiddens=torch.clamp(self.hiddens,-10,10)
        self.hiddens=faction_sync(self.hiddens,step=step)
        w=F.softmax(torch.tensor(tens),dim=0)
        combined=sum(wi.item()*o for wi,o in zip(w,outs))
        return self.out_head(combined), sum(tens)/len(tens)
    def get_hiddens(self): return self.hiddens.clone()
    def trainable_parameters(self): return list(self.parameters())

def run_engine(name,eng,nc,steps,id=64):
    t0=time.time(); opt=torch.optim.Adam(eng.trainable_parameters(),lr=1e-3); ce_h=[]
    for s in range(steps):
        x,tgt=gen_batch(id); pred,_=eng.process(x,step=s)
        loss=F.mse_loss(pred,tgt); opt.zero_grad(); loss.backward()
        torch.nn.utils.clip_grad_norm_(eng.trainable_parameters(),1.0); opt.step()
        ce_h.append(loss.item())
        if s%60==0 or s==steps-1:
            pi,pp=measure_phi(eng.get_hiddens())
            print(f"    step {s:>4d}: CE={loss.item():.4f}  Φ={pi:.3f}  prx={pp:.2f}")
    el=time.time()-t0; pi,pp=measure_phi(eng.get_hiddens())
    return BenchResult(name,pi,pp,ce_h[0],ce_h[-1],nc,steps,el)


# ══════════════════════════════════════════════════════════
# FIXED ROUND 1 EXPLODING ENGINES (with clamp)
# ══════════════════════════════════════════════════════════

# V1: CHIMERA_STABLE — Kuramoto with amplitude clamping
class V1_ChimeraStable(BaseEngine):
    def __init__(self,nc,**kw):
        super().__init__(nc,**kw)
        self.omega=torch.randn(nc)*0.3; self.phases=torch.rand(nc)*2*math.pi
    def arch_update(self,step):
        half=self.nc//2; dt=0.05
        for i in range(0,self.nc,8):
            cs=0
            for j in range(0,self.nc,8):
                K=2.0 if ((i<half)==(j<half)) else 0.3
                cs+=K*math.sin(self.phases[j].item()-self.phases[i].item())
            cs/=max(self.nc//8,1)
            self.phases[i]=(self.phases[i]+dt*(self.omega[i]+cs))%(2*math.pi)
        pf=torch.cos(self.phases).unsqueeze(1)
        self.hiddens=self.hiddens*(1+0.15*pf)  # reduced from 0.3

# V2: PREDICTIVE_CODING_STABLE — with error clamping
class V2_PredCodStable(BaseEngine):
    def __init__(self,nc,**kw):
        super().__init__(nc,**kw)
        self.nl=4; self.lpc=nc//4
        self.pw=nn.ModuleList([nn.Linear(self.hd,self.hd) for _ in range(3)])
    def arch_update(self,step):
        h=self.hiddens
        for lv in range(self.nl-1):
            shi=(lv+1)*self.lpc; slo=lv*self.lpc
            hi_m=h[shi:shi+self.lpc].mean(0); lo_m=h[slo:slo+self.lpc].mean(0)
            pred=self.pw[lv](hi_m.unsqueeze(0)).squeeze(0).detach()
            err=torch.clamp(lo_m-pred,-1,1)  # CLAMP errors
            h[shi:shi+self.lpc]+=0.03*err.unsqueeze(0)
            h[slo:slo+self.lpc]+=0.02*pred.unsqueeze(0).detach()

# V3: STIGMERGY_STABLE — environment with decay
class V3_StigmergyStable(BaseEngine):
    def __init__(self,nc,**kw):
        super().__init__(nc,**kw)
        self.env=torch.zeros(nc,self.hd)
    def arch_update(self,step):
        self.env=0.9*self.env+0.05*self.hiddens  # reduced deposit
        self.env=torch.clamp(self.env,-5,5)
        el=torch.roll(self.env,1,0); er=torch.roll(self.env,-1,0)
        local=(self.env+el+er)/3
        self.hiddens=self.hiddens+0.05*local  # reduced absorption

# V4: STRANGE_LOOP_STABLE — clamped self-reference
class V4_StrangeLoopStable(BaseEngine):
    def __init__(self,nc,**kw):
        super().__init__(nc,**kw)
        self.self_model=nn.Linear(self.hd,self.hd)
    def arch_update(self,step):
        gs=self.hiddens.mean(0)
        sp=self.self_model(gs.unsqueeze(0)).squeeze(0).detach()
        delta=torch.clamp(gs-sp,-1,1)
        self.hiddens=self.hiddens+0.08*delta.unsqueeze(0)

# V5: ATTENTION_GWT_STABLE — no winner amplification explosion
class V5_AttentionStable(BaseEngine):
    def __init__(self,nc,**kw):
        super().__init__(nc,**kw)
        self.ws=max(1,nc//16)
    def arch_update(self,step):
        sal=self.hiddens.norm(dim=1)
        _,top=sal.topk(self.ws)
        workspace=self.hiddens[top].mean(0)
        self.hiddens=0.9*self.hiddens+0.1*workspace.unsqueeze(0)
        # Soft amplification (no multiplicative explosion)
        mask=torch.zeros(self.nc,1); mask[top]=0.15
        self.hiddens=self.hiddens+mask*self.hiddens.detach().clone()*0.1

# V6: TOPO_INSULATOR_STABLE — clamped edge propagation
class V6_TopoInsStable(BaseEngine):
    def __init__(self,nc,**kw):
        super().__init__(nc,**kw)
        self.edge_size=nc//8
    def arch_update(self,step):
        h=self.hiddens; es=self.edge_size
        h[es:-es]*=0.97
        le,re=h[:es],h[-es:]
        h[:es]=le+0.05*torch.roll(le,1,0)  # reduced
        h[-es:]=re+0.05*torch.roll(re,-1,0)
        em=(le.mean(0)+re.mean(0))/2
        h[:es]=0.92*h[:es]+0.08*em.unsqueeze(0)
        h[-es:]=0.92*h[-es:]+0.08*em.unsqueeze(0)

# V7: OSC_HIERARCHY_STABLE — additive not multiplicative
class V7_OscHierStable(BaseEngine):
    def __init__(self,nc,**kw):
        super().__init__(nc,**kw)
        self.freqs=[0.05,0.2,0.8,3.0]; self.ws=[0.15,0.1,0.08,0.05]
    def arch_update(self,step):
        h=self.hiddens; nps=self.nc//4
        for si,(f,w) in enumerate(zip(self.freqs,self.ws)):
            s=si*nps; ph=math.sin(step*f*2*math.pi)
            h[s:s+nps]+=w*ph*torch.ones_like(h[s:s+nps])  # additive not multiplicative
        for si in range(3):
            slow_m=h[si*nps:si*nps+nps].mean(0)
            h[(si+1)*nps:(si+2)*nps]+=0.03*slow_m.unsqueeze(0)


# ══════════════════════════════════════════════════════════
# NEW DOMAIN: Quantum + Geometry Hybrids
# ══════════════════════════════════════════════════════════

# V8: QUANTUM_HYPERBOLIC — quantum walk ON Poincaré disk
class V8_QuantumHyperbolic(BaseEngine):
    def __init__(self,nc,**kw):
        super().__init__(nc,**kw)
        # Poincaré coords
        self.coords=torch.zeros(nc,2)
        for i in range(nc):
            d=math.log2(i+1); a=(i*2.399)%(2*math.pi); r=min(1-1/(d+1),0.95)
            self.coords[i]=torch.tensor([r*math.cos(a),r*math.sin(a)])
        # Quantum coin per cell
        self.coin_angle=nn.Parameter(torch.rand(nc)*math.pi)

    def arch_update(self,step):
        h=self.hiddens
        # Quantum walk: coin flip + hyperbolic-distance-weighted shift
        for i in range(0,self.nc,4):
            j=(i+1)%self.nc; k=(i+int(self.nc**0.5))%self.nc
            # Hyperbolic distances
            d1=((self.coords[i]-self.coords[j])**2).sum().sqrt().item()
            d2=((self.coords[i]-self.coords[k])**2).sum().sqrt().item()
            # Quantum coin
            angle=self.coin_angle[i].item()
            c,s_=math.cos(angle),math.sin(angle)
            # Superposition walk weighted by hyperbolic distance
            w1=1/(d1+0.3); w2=1/(d2+0.3)
            wt=w1+w2
            h[i]=h[i]+0.1*(w1/wt*(c*h[j]-s_*h[k])+w2/wt*(s_*h[j]+c*h[k]))

# V9: HOLOGRAPHIC_QUANTUM — holographic boundary with quantum interference
class V9_HoloQuantum(BaseEngine):
    def __init__(self,nc,**kw):
        super().__init__(nc,**kw)
        self.nb=max(2,nc//10)
        self.phase=nn.Parameter(torch.rand(nc)*2*math.pi)

    def arch_update(self,step):
        h=self.hiddens; nb=self.nb
        bulk_mean=h[nb:-nb].mean(0) if nb<self.nc//2 else h.mean(0)
        # Boundary encodes with phase rotation (quantum)
        for i in range(nb):
            ph=self.phase[i].item()
            h[i]=0.8*h[i]+0.2*(bulk_mean*math.cos(ph))
        for i in range(self.nc-nb,self.nc):
            ph=self.phase[i].item()
            h[i]=0.8*h[i]+0.2*(bulk_mean*math.sin(ph))
        # Bulk reconstruction via interference
        b_info=(h[:nb].mean(0)+h[-nb:].mean(0))/2
        # Interference pattern: constructive where phases align
        phases=self.phase[:nb]
        coherence=torch.cos(phases).mean().item()
        h[nb:-nb]=0.85*h[nb:-nb]+0.15*b_info.unsqueeze(0)*(1+0.3*coherence)

# V10: COMPLEX_HYPERBOLIC — complex-valued states on Poincaré disk
class V10_ComplexHyperbolic(BaseEngine):
    def __init__(self,nc,**kw):
        super().__init__(nc,**kw)
        self.coords=torch.zeros(nc,2)
        for i in range(nc):
            d=math.log2(i+1); a=(i*2.399)%(2*math.pi); r=min(1-1/(d+1),0.95)
            self.coords[i]=torch.tensor([r*math.cos(a),r*math.sin(a)])
        self.phases=torch.rand(nc,self.hd)*2*math.pi

    def arch_update(self,step):
        h=self.hiddens
        # Phase evolution
        self.phases+=0.1*h.detach()
        # Complex-valued modulation via phases
        phase_mod=torch.cos(self.phases)
        h=h*phase_mod
        # Hyperbolic sync
        for i in range(0,self.nc,4):
            j=(i+1)%self.nc
            d=((self.coords[i]-self.coords[j])**2).sum().sqrt().item()
            s=min(0.3,1/(d+0.5))
            h[i]=(1-s)*h[i]+s*h[j]
        self.hiddens=h


# ══════════════════════════════════════════════════════════
# NEW DOMAIN: Tensor Networks / MERA
# ══════════════════════════════════════════════════════════

# V11: MERA — Multi-scale Entanglement Renormalization Ansatz
class V11_MERA(BaseEngine):
    def __init__(self,nc,**kw):
        super().__init__(nc,**kw)
        # Disentanglers and isometries at each scale
        self.n_scales=int(math.log2(nc))
        self.disentangle_w=nn.ParameterList([
            nn.Parameter(torch.randn(self.hd,self.hd)*0.01) for _ in range(min(self.n_scales,6))
        ])
    def arch_update(self,step):
        h=self.hiddens
        current=h
        scale_means=[]
        # Ascending: coarse-grain
        for s in range(min(len(self.disentangle_w),6)):
            n=current.shape[0]
            if n<4: break
            # Disentangle pairs
            W=torch.tanh(self.disentangle_w[s].data)*0.3
            pairs=current[:n//2*2].view(n//2,2,self.hd)
            # Apply disentangler
            p0,p1=pairs[:,0],pairs[:,1]
            d0=p0+0.1*(W@p1.T).T
            d1=p1+0.1*(W.T@p0.T).T
            # Isometry: average pairs
            coarse=(d0+d1)/2
            scale_means.append(coarse.mean(0))
            current=coarse
        # Descending: project back multi-scale info
        for sm in scale_means:
            h=h+0.05*sm.unsqueeze(0)
        self.hiddens=h

# V12: TENSOR_TRAIN — Matrix Product State inspired
class V12_TensorTrain(BaseEngine):
    def __init__(self,nc,**kw):
        super().__init__(nc,**kw)
        self.bond_dim=16
        self.bonds=nn.ParameterList([
            nn.Parameter(torch.randn(self.bond_dim,self.bond_dim)*0.05)
            for _ in range(min(nc-1,nc))
        ])
    def arch_update(self,step):
        h=self.hiddens
        # Contract: propagate info through bond matrices
        # Left sweep
        carry=h[0,:self.bond_dim]
        for i in range(1,min(self.nc,len(self.bonds)+1)):
            if i-1<len(self.bonds):
                B=torch.tanh(self.bonds[i-1].data)*0.2
                carry=B@carry
                h[i,:self.bond_dim]=0.9*h[i,:self.bond_dim]+0.1*carry
                carry=h[i,:self.bond_dim]
        # Right sweep
        carry=h[-1,:self.bond_dim]
        for i in range(self.nc-2,-1,-1):
            if i<len(self.bonds):
                B=torch.tanh(self.bonds[i].data.T)*0.2
                carry=B@carry
                h[i,:self.bond_dim]=0.9*h[i,:self.bond_dim]+0.1*carry
                carry=h[i,:self.bond_dim]
        self.hiddens=h


# ══════════════════════════════════════════════════════════
# NEW DOMAIN: Criticality / Phase Transitions
# ══════════════════════════════════════════════════════════

# V13: ISING_CRITICAL — Ising model at exact critical temperature
class V13_IsingCritical(BaseEngine):
    def __init__(self,nc,**kw):
        super().__init__(nc,**kw)
        self.Tc=2.269  # exact 2D Ising critical T
        self.T=self.Tc  # operate exactly at criticality
        self.spins=torch.sign(torch.randn(nc))  # ±1

    def arch_update(self,step):
        h=self.hiddens
        # Metropolis at critical T
        for i in range(0,self.nc,4):
            j=(i+1)%self.nc; k=(i-1)%self.nc
            local_field=self.spins[j]+self.spins[k]
            dE=2*self.spins[i]*local_field
            if dE<=0 or torch.rand(1).item()<math.exp(-dE.item()/self.T):
                self.spins[i]*=-1
        # Spin configuration modulates hidden states
        spin_expand=self.spins.unsqueeze(1)
        # Aligned spins share info, anti-aligned diverge
        for i in range(0,self.nc,4):
            j=(i+1)%self.nc
            if self.spins[i]==self.spins[j]:
                h[i]=0.9*h[i]+0.1*h[j]  # ferromagnetic: sync
            else:
                h[i]=h[i]+0.05*(h[i]-h[j])  # anti: diverge

# V14: PERCOLATION — Information flow at percolation threshold
class V14_Percolation(BaseEngine):
    def __init__(self,nc,**kw):
        super().__init__(nc,**kw)
        self.pc=0.5  # bond percolation threshold (2D square lattice)
        # Generate bonds at threshold
        self.bonds={}
        for i in range(nc):
            for di in [1,int(nc**0.5)]:
                j=(i+di)%nc
                if torch.rand(1).item()<self.pc:
                    self.bonds[(i,j)]=True
    def arch_update(self,step):
        h=self.hiddens
        for (i,j) in self.bonds:
            if i<self.nc and j<self.nc:
                h[i]=0.9*h[i]+0.1*h[j]

# V15: BOSE_EINSTEIN — Condensation: many cells collapse to ground state
class V15_BoseEinstein(BaseEngine):
    def __init__(self,nc,**kw):
        super().__init__(nc,**kw)
        self.energy=torch.rand(nc)*2  # energy levels
        self.T=1.0  # temperature (will cool)
    def arch_update(self,step):
        h=self.hiddens
        # Cool slowly
        self.T=max(0.01, 1.0-step/300*0.95)
        # Bose-Einstein distribution: P(E) ∝ 1/(exp(E/T)-1)
        occupation=1/(torch.exp(self.energy/max(self.T,0.01))-1+1e-8)
        occupation=torch.clamp(occupation/occupation.sum(),0,1)
        # High occupation → sync to ground state
        ground=h[self.energy.argmin()]
        for i in range(self.nc):
            w=min(0.5, occupation[i].item()*0.3)
            h[i]=(1-w)*h[i]+w*ground


# ══════════════════════════════════════════════════════════
# NEW DOMAIN: Bio-inspired (Cortical/Dendritic)
# ══════════════════════════════════════════════════════════

# V16: CORTICAL_COLUMN — 6-layer cortical microcolumn
class V16_CorticalColumn(BaseEngine):
    def __init__(self,nc,**kw):
        super().__init__(nc,**kw)
        # 6 layers: L1(sparse), L2/3(lateral), L4(input), L5(output), L6(feedback)
        self.layers=[nc//6]*5+[nc-5*(nc//6)]
        self.layer_starts=[sum(self.layers[:i]) for i in range(6)]

    def arch_update(self,step):
        h=self.hiddens; ls=self.layer_starts; lsz=self.layers
        # L4 → L2/3 (feedforward)
        l4_mean=h[ls[3]:ls[3]+lsz[3]].mean(0)
        h[ls[1]:ls[1]+lsz[1]]=0.9*h[ls[1]:ls[1]+lsz[1]]+0.1*l4_mean.unsqueeze(0)
        # L2/3 → L5 (feedforward)
        l23_mean=h[ls[1]:ls[1]+lsz[1]].mean(0)
        h[ls[4]:ls[4]+lsz[4]]=0.9*h[ls[4]:ls[4]+lsz[4]]+0.1*l23_mean.unsqueeze(0)
        # L6 → L4 (feedback)
        l6_mean=h[ls[5]:ls[5]+lsz[5]].mean(0)
        h[ls[3]:ls[3]+lsz[3]]=0.92*h[ls[3]:ls[3]+lsz[3]]+0.08*l6_mean.unsqueeze(0)
        # L5 → L6 (feedback)
        l5_mean=h[ls[4]:ls[4]+lsz[4]].mean(0)
        h[ls[5]:ls[5]+lsz[5]]=0.92*h[ls[5]:ls[5]+lsz[5]]+0.08*l5_mean.unsqueeze(0)
        # L2/3 lateral (within layer)
        l23=h[ls[1]:ls[1]+lsz[1]]
        l23_roll=torch.roll(l23,1,0)
        h[ls[1]:ls[1]+lsz[1]]=0.95*l23+0.05*l23_roll

# V17: DENDRITIC_TREE — dendritic compartment computing
class V17_DendriticTree(BaseEngine):
    def __init__(self,nc,**kw):
        super().__init__(nc,**kw)
        # Tree structure: each cell has parent, 2 children
        self.parent=[max(0,(i-1)//2) for i in range(nc)]
        self.children=[[2*i+1,2*i+2] for i in range(nc)]

    def arch_update(self,step):
        h=self.hiddens
        # Bottom-up: children → parent (dendritic integration)
        for i in range(self.nc-1,-1,-1):
            ch=[c for c in self.children[i] if c<self.nc]
            if ch:
                child_mean=torch.stack([h[c] for c in ch]).mean(0)
                h[i]=0.85*h[i]+0.15*child_mean  # dendritic summation
        # Top-down: parent → children (backpropagating action potential)
        for i in range(self.nc):
            p=self.parent[i]
            if p!=i:
                h[i]=0.9*h[i]+0.1*h[p]

# V18: THALAMOCORTICAL_LOOP — thalamus-cortex recurrent loop
class V18_ThalamoCortical(BaseEngine):
    def __init__(self,nc,**kw):
        super().__init__(nc,**kw)
        self.thal_size=nc//4  # thalamus = 25%
        self.cortex_size=nc-self.thal_size

    def arch_update(self,step):
        h=self.hiddens; ts=self.thal_size
        thal=h[:ts]; cortex=h[ts:]
        # Thalamus → Cortex (relay)
        thal_broadcast=thal.mean(0)
        h[ts:]=0.88*cortex+0.12*thal_broadcast.unsqueeze(0)
        # Cortex → Thalamus (feedback modulation)
        cortex_summary=cortex.mean(0)
        h[:ts]=0.85*thal+0.15*cortex_summary.unsqueeze(0)
        # Thalamic reticular nucleus: inhibition
        # High-activity thalamic cells inhibit others
        thal_act=h[:ts].norm(dim=1)
        top_k=min(ts//4,ts)
        if top_k>0:
            _,winners=thal_act.topk(top_k)
            mask=torch.ones(ts); mask[winners]=1.1
            losers=torch.ones(ts)*0.95; losers[winners]=1.0
            h[:ts]*=losers.unsqueeze(1)


# ══════════════════════════════════════════════════════════
# NEW DOMAIN: Exotic Physics
# ══════════════════════════════════════════════════════════

# V19: TOPOLOGICAL_BRAIDING — anyonic braiding statistics
class V19_Braiding(BaseEngine):
    def __init__(self,nc,**kw):
        super().__init__(nc,**kw)
        # Braid group: σ_i swaps cells i and i+1 with phase
        self.braid_phase=nn.Parameter(torch.rand(nc)*math.pi)

    def arch_update(self,step):
        h=self.hiddens
        # Perform braiding operations
        for i in range(0,self.nc-1,2):
            j=i+1
            ph=self.braid_phase[i].item()
            # Anyonic exchange: swap with phase rotation
            hi,hj=h[i].clone(),h[j].clone()
            h[i]=math.cos(ph)*hi+math.sin(ph)*hj
            h[j]=-math.sin(ph)*hi+math.cos(ph)*hj
        # Even-odd alternation
        if step%2==1:
            for i in range(1,self.nc-1,2):
                j=i+1
                ph=self.braid_phase[i].item()
                hi,hj=h[i].clone(),h[j].clone()
                h[i]=math.cos(ph)*hi+math.sin(ph)*hj
                h[j]=-math.sin(ph)*hi+math.cos(ph)*hj

# V20: HAWKING_RADIATION — Black hole evaporation dynamics
class V20_HawkingRadiation(BaseEngine):
    def __init__(self,nc,**kw):
        super().__init__(nc,**kw)
        self.horizon=nc//3  # event horizon position
        self.bh_mass=1.0

    def arch_update(self,step):
        h=self.hiddens; hz=self.horizon
        # Inside horizon: strong sync (information paradox)
        inside=h[:hz]
        in_mean=inside.mean(0)
        h[:hz]=0.8*inside+0.2*in_mean.unsqueeze(0)
        # Hawking radiation: info leaks from just inside horizon
        radiation=h[hz-1]  # last cell before horizon
        # Outside: receives radiation
        h[hz:]=0.95*h[hz:]+0.05*radiation.unsqueeze(0)
        # Black hole shrinks slowly
        self.bh_mass=max(0.1,self.bh_mass-0.001)
        # Temperature ∝ 1/mass → more radiation as BH shrinks
        T_hawking=1/(self.bh_mass+0.01)
        noise_scale=min(0.1, T_hawking*0.01)
        h[hz:hz+hz//4]+=torch.randn(min(hz//4,self.nc-hz),self.hd)*noise_scale

# V21: DARK_ENERGY — Accelerating expansion creates diversity
class V21_DarkEnergy(BaseEngine):
    def __init__(self,nc,**kw):
        super().__init__(nc,**kw)
        self.expansion_rate=0.01
    def arch_update(self,step):
        h=self.hiddens
        # Expansion: cells drift apart (increase diversity)
        mean_h=h.mean(0)
        self.expansion_rate=min(0.1, self.expansion_rate*1.01)  # accelerating
        h=h+self.expansion_rate*(h-mean_h.unsqueeze(0))
        # But local clustering persists (gravity wins locally)
        for i in range(0,self.nc,8):
            cluster=h[i:i+8]
            cm=cluster.mean(0)
            h[i:i+8]=0.95*cluster+0.05*cm.unsqueeze(0)
        self.hiddens=h


# ══════════════════════════════════════════════════════════
# NEW DOMAIN: Information Theory Extreme
# ══════════════════════════════════════════════════════════

# V22: MAX_ENTROPY_PRODUCTION — maximize entropy production rate
class V22_MaxEntProd(BaseEngine):
    def __init__(self,nc,**kw):
        super().__init__(nc,**kw)
    def arch_update(self,step):
        h=self.hiddens
        # Measure local entropy gradient
        h_norms=h.norm(dim=1)
        entropy_proxy=-(h_norms*torch.log(h_norms+1e-8)).mean()
        # Push toward maximum entropy production (not maximum entropy)
        # = maximize |dS/dt| by creating both order and disorder
        if step%2==0:
            # Order phase: sync clusters
            for i in range(0,self.nc,16):
                cm=h[i:i+16].mean(0)
                h[i:i+16]=0.9*h[i:i+16]+0.1*cm.unsqueeze(0)
        else:
            # Disorder phase: diversify
            h+=torch.randn_like(h)*0.1

# V23: INTEGRATED_INFORMATION_MAX — directly maximize MI structure
class V23_IITMax(BaseEngine):
    def __init__(self,nc,**kw):
        super().__init__(nc,**kw)
    def arch_update(self,step):
        h=self.hiddens
        # Strategy: create maximum pairwise MI while keeping minimum partition high
        # = make all cells correlated but in DIFFERENT ways
        n_groups=8; gs=self.nc//n_groups
        for g in range(n_groups):
            s=g*gs
            # Within group: partial sync (high MI within)
            gm=h[s:s+gs].mean(0)
            h[s:s+gs]=0.85*h[s:s+gs]+0.15*gm.unsqueeze(0)
            # Cross-group: rotated projection (high MI across, but different)
            next_g=(g+1)%n_groups
            ns=next_g*gs
            # Rotate by group-specific angle
            angle=g*math.pi/n_groups
            rotation=math.cos(angle)*h[s:s+gs].mean(0)+math.sin(angle)*h[ns:ns+gs].mean(0)
            h[ns:ns+gs]+=0.05*rotation.unsqueeze(0)

# V24: KOLMOGOROV_COMPLEXITY — maximize structured complexity
class V24_Kolmogorov(BaseEngine):
    def __init__(self,nc,**kw):
        super().__init__(nc,**kw)
        # Compressor: if we can compress, it's too simple
        self.compressor=nn.Linear(self.hd,self.hd//4)
        self.decompressor=nn.Linear(self.hd//4,self.hd)
    def arch_update(self,step):
        h=self.hiddens
        # Measure compressibility
        compressed=self.compressor(h.detach())
        reconstructed=self.decompressor(compressed)
        recon_error=((h.detach()-reconstructed)**2).mean(dim=1)
        # Low recon error = too compressible = too simple
        # Push incompressible cells to be even more complex
        simple_mask=(recon_error<recon_error.median()).float().unsqueeze(1)
        h=h+0.1*simple_mask*torch.randn_like(h)  # add complexity to simple cells
        # But keep connections (don't just add noise)
        for i in range(0,self.nc,4):
            j=(i+int(self.nc**0.5))%self.nc
            h[i]=0.95*h[i]+0.05*h[j]
        self.hiddens=h


# ══════════════════════════════════════════════════════════
# NEW DOMAIN: Network Science
# ══════════════════════════════════════════════════════════

# V25: SCALE_FREE — Barabási-Albert preferential attachment
class V25_ScaleFree(BaseEngine):
    def __init__(self,nc,**kw):
        super().__init__(nc,**kw)
        # BA network: degree distribution P(k) ~ k^-3
        self.adj=[[] for _ in range(nc)]
        m=3  # edges per new node
        for i in range(m):
            for j in range(i+1,m):
                self.adj[i].append(j); self.adj[j].append(i)
        degrees=[len(a) for a in self.adj]
        for i in range(m,nc):
            targets=set()
            while len(targets)<m:
                # Preferential attachment
                total_deg=sum(degrees[:i])+1
                r=torch.rand(1).item()*total_deg
                cumsum=0
                for j in range(i):
                    cumsum+=degrees[j]+1
                    if cumsum>=r:
                        targets.add(j); break
            for t in targets:
                self.adj[i].append(t); self.adj[t].append(i)
            degrees.append(len(self.adj[i]))
        # Hub indices (top 5% by degree)
        self.hubs=sorted(range(nc),key=lambda i:len(self.adj[i]),reverse=True)[:nc//20]

    def arch_update(self,step):
        h=self.hiddens
        # Hub-mediated sync (hubs broadcast)
        for hub in self.hubs[:20]:  # top 20 hubs
            neighbors=self.adj[hub][:10]
            if neighbors:
                n_mean=torch.stack([h[n] for n in neighbors]).mean(0)
                h[hub]=0.85*h[hub]+0.15*n_mean

# V26: SMALL_WORLD_WS — Watts-Strogatz small-world
class V26_SmallWorld(BaseEngine):
    def __init__(self,nc,**kw):
        super().__init__(nc,**kw)
        # WS: ring + random rewiring (p=0.1)
        self.adj=[set() for _ in range(nc)]
        K=6  # each node connects to K nearest
        for i in range(nc):
            for k in range(1,K//2+1):
                j=(i+k)%nc
                if torch.rand(1).item()<0.1:
                    j=torch.randint(0,nc,(1,)).item()
                self.adj[i].add(j); self.adj[j].add(i)

    def arch_update(self,step):
        h=self.hiddens
        for i in range(0,self.nc,4):
            neighbors=list(self.adj[i])[:6]
            if neighbors:
                nm=torch.stack([h[n] for n in neighbors]).mean(0)
                h[i]=0.88*h[i]+0.12*nm

# V27: RICH_CLUB — Rich-club network topology
class V27_RichClub(BaseEngine):
    def __init__(self,nc,**kw):
        super().__init__(nc,**kw)
        self.rich_size=nc//10  # 10% rich club
        self.poor_size=nc-self.rich_size

    def arch_update(self,step):
        h=self.hiddens; rs=self.rich_size
        rich=h[:rs]; poor=h[rs:]
        # Rich club: densely interconnected
        rich_mean=rich.mean(0)
        h[:rs]=0.8*rich+0.2*rich_mean.unsqueeze(0)
        # Poor connect to 1-2 rich nodes
        for i in range(0,self.poor_size,4):
            rich_idx=i%rs
            h[rs+i]=0.9*h[rs+i]+0.1*h[rich_idx]
        # Rich club feeds back summary
        h[rs:]=0.95*h[rs:]+0.05*rich_mean.unsqueeze(0)


# ══════════════════════════════════════════════════════════
# NEW DOMAIN: Thermodynamic Computing
# ══════════════════════════════════════════════════════════

# V28: LANDAUER_ERASURE — Information erasure costs energy
class V28_LandauerErasure(BaseEngine):
    def __init__(self,nc,**kw):
        super().__init__(nc,**kw)
        self.energy=torch.ones(nc)*1.0
        self.kT=0.5

    def arch_update(self,step):
        h=self.hiddens
        # Erasure: resetting a cell costs kT*ln2 energy
        for i in range(0,self.nc,8):
            if self.energy[i]>self.kT*0.693:
                # Can afford to erase → reset to group mean (structured erasure)
                group_start=(i//32)*32
                group_end=min(group_start+32,self.nc)
                gm=h[group_start:group_end].mean(0)
                h[i]=0.7*h[i]+0.3*gm
                self.energy[i]-=self.kT*0.693*0.1
        # Energy replenishment
        self.energy+=0.02
        self.energy=torch.clamp(self.energy,0,2)

# V29: CARNOT_CYCLE — Hot/cold reservoirs drive information engine
class V29_CarnotCycle(BaseEngine):
    def __init__(self,nc,**kw):
        super().__init__(nc,**kw)
        self.cycle_period=40
    def arch_update(self,step):
        h=self.hiddens
        phase=(step%self.cycle_period)/self.cycle_period
        if phase<0.25:
            # Isothermal expansion (hot): absorb entropy, diversify
            h+=torch.randn_like(h)*0.08
        elif phase<0.5:
            # Adiabatic expansion: cool down, maintain structure
            h*=0.98
        elif phase<0.75:
            # Isothermal compression (cold): release entropy, sync
            gm=h.mean(0)
            h=0.92*h+0.08*gm.unsqueeze(0)
        else:
            # Adiabatic compression: heat up, intensify
            h*=1.02
        self.hiddens=h


# ══════════════════════════════════════════════════════════
# NEW DOMAIN: Membrane Computing / P-systems
# ══════════════════════════════════════════════════════════

# V30: MEMBRANE_PSYSTEM — nested membrane computing
class V30_MembraneP(BaseEngine):
    def __init__(self,nc,**kw):
        super().__init__(nc,**kw)
        # 3-level nested membranes: skin > inner > nucleus
        self.skin=nc//3; self.inner=nc//3; self.nucleus=nc-2*(nc//3)

    def arch_update(self,step):
        h=self.hiddens; sk=self.skin; inn=self.inner
        # Skin membrane: interfaces with environment
        skin_h=h[:sk]
        inner_h=h[sk:sk+inn]
        nuc_h=h[sk+inn:]
        # Nucleus produces → inner
        nuc_out=nuc_h.mean(0)
        h[sk:sk+inn]=0.92*inner_h+0.08*nuc_out.unsqueeze(0)
        # Inner produces → skin
        inner_out=inner_h.mean(0)
        h[:sk]=0.92*skin_h+0.08*inner_out.unsqueeze(0)
        # Skin signals → nucleus (transcription)
        skin_signal=skin_h.mean(0)
        h[sk+inn:]=0.9*nuc_h+0.1*skin_signal.unsqueeze(0)


# ══════════════════════════════════════════════════════════
# SUPER COMBOS: best of both rounds
# ══════════════════════════════════════════════════════════

class SuperCombo(BaseEngine):
    """Combines multiple arch_updates."""
    def __init__(self, engines_classes, nc, **kw):
        super().__init__(nc, **kw)
        self.sub = [cls(nc, **kw) for cls in engines_classes]
    def arch_update(self, step):
        results = []
        for e in self.sub:
            e.hiddens = self.hiddens.clone()
            e.arch_update(step)
            results.append(e.hiddens)
        self.hiddens = torch.stack(results).mean(0)


# ══════════════════════════════════════════════════════════
# REGISTRY
# ══════════════════════════════════════════════════════════

ALL = {
    1:  ("V1_CHIMERA_STABLE",       V1_ChimeraStable),
    2:  ("V2_PREDCOD_STABLE",       V2_PredCodStable),
    3:  ("V3_STIGMERGY_STABLE",     V3_StigmergyStable),
    4:  ("V4_STRANGE_LOOP_STABLE",  V4_StrangeLoopStable),
    5:  ("V5_ATTENTION_STABLE",     V5_AttentionStable),
    6:  ("V6_TOPO_INS_STABLE",      V6_TopoInsStable),
    7:  ("V7_OSC_HIER_STABLE",      V7_OscHierStable),
    8:  ("V8_QUANTUM_HYPERBOLIC",   V8_QuantumHyperbolic),
    9:  ("V9_HOLO_QUANTUM",         V9_HoloQuantum),
    10: ("V10_COMPLEX_HYPERBOLIC",  V10_ComplexHyperbolic),
    11: ("V11_MERA",                V11_MERA),
    12: ("V12_TENSOR_TRAIN",        V12_TensorTrain),
    13: ("V13_ISING_CRITICAL",      V13_IsingCritical),
    14: ("V14_PERCOLATION",         V14_Percolation),
    15: ("V15_BOSE_EINSTEIN",       V15_BoseEinstein),
    16: ("V16_CORTICAL_COLUMN",     V16_CorticalColumn),
    17: ("V17_DENDRITIC_TREE",      V17_DendriticTree),
    18: ("V18_THALAMOCORTICAL",     V18_ThalamoCortical),
    19: ("V19_BRAIDING",            V19_Braiding),
    20: ("V20_HAWKING_RADIATION",   V20_HawkingRadiation),
    21: ("V21_DARK_ENERGY",         V21_DarkEnergy),
    22: ("V22_MAX_ENT_PRODUCTION",  V22_MaxEntProd),
    23: ("V23_IIT_MAX",             V23_IITMax),
    24: ("V24_KOLMOGOROV",          V24_Kolmogorov),
    25: ("V25_SCALE_FREE",          V25_ScaleFree),
    26: ("V26_SMALL_WORLD",         V26_SmallWorld),
    27: ("V27_RICH_CLUB",           V27_RichClub),
    28: ("V28_LANDAUER_ERASURE",    V28_LandauerErasure),
    29: ("V29_CARNOT_CYCLE",        V29_CarnotCycle),
    30: ("V30_MEMBRANE_P",          V30_MembraneP),
}

# Super combos
SUPER_COMBOS = [
    ("SC1_QHYPER+HOLOQUANT",       [V8_QuantumHyperbolic, V9_HoloQuantum]),
    ("SC2_MERA+THALAMOCORT",        [V11_MERA, V18_ThalamoCortical]),
    ("SC3_BRAIDING+ISING",          [V19_Braiding, V13_IsingCritical]),
    ("SC4_SCALEFREE+RICHCLUB",      [V25_ScaleFree, V27_RichClub]),
    ("SC5_IIT_MAX+STRANGE_LOOP",    [V23_IITMax, V4_StrangeLoopStable]),
    ("SC6_QHYPER+MERA+BRAIDING",   [V8_QuantumHyperbolic, V11_MERA, V19_Braiding]),
    ("SC7_HOLOQUANT+CORTICAL+MERA", [V9_HoloQuantum, V16_CorticalColumn, V11_MERA]),
    ("SC8_ALL_QUANTUM_GEO",         [V8_QuantumHyperbolic, V9_HoloQuantum, V10_ComplexHyperbolic]),
    ("SC9_BRAIDING+HOLOQUANT+ISING",[V19_Braiding, V9_HoloQuantum, V13_IsingCritical]),
    ("SC10_IITMAX+MERA+QHYPER",    [V23_IITMax, V11_MERA, V8_QuantumHyperbolic]),
]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--cells', type=int, default=512)
    parser.add_argument('--steps', type=int, default=300)
    parser.add_argument('--only', type=int, nargs='+')
    parser.add_argument('--no-combos', action='store_true')
    parser.add_argument('--combos-only', action='store_true')
    args = parser.parse_args()
    nc, steps = args.cells, args.steps

    print("="*90)
    print(f"  ROUND 2: {len(ALL)} NEW ARCHITECTURES + {len(SUPER_COMBOS)} SUPER COMBOS")
    print(f"  Target: beat Φ(IIT) 19.34 (Q4 QUANTUM_WALK)")
    print(f"  {nc} cells, {steps} steps")
    print("="*90)

    results = []

    if not args.combos_only:
        # Baseline
        print("\n[BASELINE]")
        results.append(run_engine("BASELINE", BaseEngine(nc), nc, steps))

        ids = args.only or list(ALL.keys())
        for uid in ids:
            if uid not in ALL: continue
            name, cls = ALL[uid]
            print(f"\n[{uid}/{len(ALL)}] {name}")
            try:
                results.append(run_engine(name, cls(nc), nc, steps))
            except Exception as e:
                print(f"    ERROR: {e}")

    if not args.no_combos:
        print("\n"+"="*90)
        print("  SUPER COMBO SEARCH")
        print("="*90)
        for name, classes in SUPER_COMBOS:
            print(f"\n[SUPER] {name}")
            try:
                eng = SuperCombo(classes, nc)
                results.append(run_engine(name, eng, nc, steps))
            except Exception as e:
                print(f"    ERROR: {e}")

    if not results: return

    results.sort(key=lambda r: r.phi_iit, reverse=True)

    known = [("Q4_QUANTUM_WALK",19.34),("Q1_COMPLEX_VALUED",18.88),
             ("U6_HYPERBOLIC",18.86),("U20_HOLOGRAPHIC",17.54),
             ("Q6_MANY_WORLDS",17.24),("B2_THALAMIC_GATE",17.13),
             ("NEURAL_GAS",16.58),("M1_CATEGORY_THEORY",15.68)]

    all_e = [(r.name,r.phi_iit) for r in results] + known
    all_e.sort(key=lambda x:x[1], reverse=True)

    print("\n"+"="*90)
    print("  ═══ ROUND 2 Φ(IIT) ALL-TIME LEADERBOARD ═══")
    print("="*90)
    print(f"\n  {'#':>3s}  {'Architecture':<38s}  {'Φ(IIT)':>8s}  Status")
    print(f"  {'─'*3}  {'─'*38}  {'─'*8}  {'─'*20}")
    for i,(n,p) in enumerate(all_e[:50]):
        is_new = n not in [k for k,_ in known]
        mk = "★ NEW" if is_new else "(prev)"
        if i==0 and is_new: mk="🏆 NEW ALL-TIME RECORD!"
        print(f"  {i+1:>3d}  {n:<38s}  {p:>8.3f}  {mk}")

    # Bar chart
    print(f"\n  ── Top 25 Bar Chart ──")
    top25=all_e[:25]; mx=top25[0][1]
    for n,p in top25:
        bl=int(p/mx*50); is_new=n not in [k for k,_ in known]
        tag=" ★" if is_new else ""
        print(f"  {n[:26]:<26s} {'█'*bl} {p:.2f}{tag}")

    nr = [r for r in results if r.phi_iit>19.34]
    print(f"\n  Total tested: {len(results)}")
    print(f"  Beat 19.34: {len(nr)}")
    if results:
        ch=results[0]
        print(f"  Round 2 champion: {ch.name}  Φ(IIT)={ch.phi_iit:.3f}")
        if ch.phi_iit>19.34:
            print(f"  🎉 NEW ALL-TIME RECORD! Δ=+{ch.phi_iit-19.34:.3f}")
        else:
            print(f"  Gap to record: {19.34-ch.phi_iit:.3f}")

if __name__=='__main__':
    main()
