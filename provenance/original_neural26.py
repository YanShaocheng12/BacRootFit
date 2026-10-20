from common26 import *
import torch
from torch import nn
from sklearn.preprocessing import normalize

_FIXED={};_STORES={}
def runtime_settings():
    path=OUT/'execution_resource_addendum.json'
    return load(path) if path.exists() else dict(residue_layout='padded',microbatch_residue_budget=8192)

def fixed_features(encoder,representation):
    key=(encoder,representation)
    if key not in _FIXED:
        folder=FEATURES/encoder;mean=np.load(folder/'mean.npy',mmap_mode='r')
        value=np.concatenate([mean,np.load(folder/'std.npy',mmap_mode='r')],axis=1) if representation=='mean_std' else mean
        _FIXED[key]=normalize(value).astype(np.float32)
    return _FIXED[key]

def fragment_ranges(length,scale,stride):
    result=[]
    for offset in range(0,length,1022):
        size=min(1022,length-offset)
        starts=[0] if size<scale else sorted(set(list(range(0,size-scale+1,stride))+[size-scale]))
        result.extend((offset+s,offset+min(size,s+scale)) for s in starts)
    return result

class ResidueStore:
    def __init__(self,encoder):
        folder=FEATURES/encoder;self.info=load(folder/'complete.json');self.raw=np.load(folder/'residues.npy',mmap_mode='r')
        idx=read(OUT/'feature_index.tsv');self.lengths=np.array([int(r['length']) for r in idx]);self.offsets=np.array([int(r['residue_offset']) for r in idx]);self.dim=DIMS[encoder];self.range_cache={}
    def batch(self,ids,global_features,device):
        lengths=self.lengths[ids];maximum=int(max(lengths));native=np.zeros((len(ids),maximum,self.dim),dtype=self.raw.dtype)
        for j,i in enumerate(ids):
            offset=int(self.offsets[i]);native[j,:lengths[j]]=self.raw[offset:offset+int(lengths[j])]
        t=torch.from_numpy(native).to(device)
        t=t.view(torch.bfloat16).float() if self.info['storage']=='bfloat16_bits' else t.float()
        lengths_tensor=torch.tensor(lengths,dtype=torch.long,device=device);mask=torch.arange(maximum,device=device)[None,:]<lengths_tensor[:,None]
        return dict(residues=t,mask=mask,global_mean=torch.from_numpy(global_features[ids]).to(device),lengths=lengths.tolist())
    def packed_batch(self,ids,global_features,device):
        lengths=self.lengths[ids];offsets=np.r_[0,np.cumsum(lengths)[:-1]]
        native=np.concatenate([self.raw[int(self.offsets[i]):int(self.offsets[i]+self.lengths[i])] for i in ids],axis=0)
        t=torch.from_numpy(native).to(device);t=t.view(torch.bfloat16).float() if self.info['storage']=='bfloat16_bits' else t.float()
        fragments={}
        for scale,stride in [(16,8),(64,32)]:
            ranges=[];counts=[]
            for i,off in zip(ids,offsets):
                key=(i,scale)
                if key not in self.range_cache:self.range_cache[key]=np.asarray(fragment_ranges(int(self.lengths[i]),scale,stride),np.int64)
                r=self.range_cache[key];ranges.append(r+off);counts.append(len(r))
            rr=np.concatenate(ranges,axis=0)
            fragments[scale]=dict(starts=torch.from_numpy(rr[:,0].copy()).to(device),ends=torch.from_numpy(rr[:,1].copy()).to(device),counts=torch.tensor(counts,dtype=torch.long,device=device))
        return dict(packed=True,residues=t,global_mean=torch.from_numpy(global_features[ids]).to(device),lengths=lengths.tolist(),
            segment_lengths=torch.tensor(lengths,dtype=torch.long,device=device),fragments=fragments)

def residue_store(encoder):
    if encoder not in _STORES:_STORES[encoder]=ResidueStore(encoder)
    return _STORES[encoder]

def microbatches(ids,encoder,budget=8192):
    lengths=residue_store(encoder).lengths;batch=[];maximum=0
    for i in ids:
        nextmax=max(maximum,int(lengths[i]))
        if batch and nextmax*(len(batch)+1)>budget:
            yield batch;batch=[];maximum=0;nextmax=int(lengths[i])
        batch.append(int(i));maximum=nextmax
    if batch:yield batch

def packed_microbatches(ids,encoder,budget=65536):
    lengths=residue_store(encoder).lengths;batch=[];total=0
    for i in ids:
        length=int(lengths[i])
        if batch and total+length>budget:yield batch;batch=[];total=0
        batch.append(int(i));total+=length
    if batch:yield batch

class Head(nn.Module):
    def __init__(self,dim,widths,dropout=.3):
        super().__init__();layers=[]
        for width in widths:layers.extend([nn.Linear(dim,width),nn.LayerNorm(width),nn.GELU(),nn.Dropout(dropout)]);dim=width
        self.hidden=nn.Sequential(*layers);self.output=nn.Linear(dim,1)
    def forward(self,x):return self.output(self.hidden(x)).squeeze(1)

class Attention(nn.Module):
    def __init__(self):
        super().__init__();self.hidden=nn.Linear(128,64);self.score=nn.Linear(64,1,bias=False)
    def forward(self,x,mask):
        logits=self.score(torch.tanh(self.hidden(x))).squeeze(-1).masked_fill(~mask,-torch.inf)
        weights=torch.softmax(logits,dim=1);return torch.sum(x*weights[:,:,None],dim=1)
    def forward_packed(self,x,lengths):
        logits=self.score(torch.tanh(self.hidden(x))).squeeze(-1)
        maxima=torch.segment_reduce(logits.detach(),'max',lengths=lengths)
        values=torch.exp(logits-torch.repeat_interleave(maxima,lengths,output_size=len(logits)))
        denominator=torch.segment_reduce(values,'sum',lengths=lengths)
        weights=values/torch.repeat_interleave(denominator,lengths,output_size=len(logits))
        return torch.segment_reduce(x*weights[:,None],'sum',lengths=lengths)

class LearnedPooling(nn.Module):
    def __init__(self,spec):
        super().__init__();dim=DIMS[spec['encoder']];kind=spec['representation'];self.kind=kind
        self.residue_norm=nn.LayerNorm(dim);self.residue_projection=nn.Linear(dim,128)
        self.global_projection=None if kind=='dual_no_global' else nn.Linear(dim,128)
        if kind=='residue_attention':self.residue_attention=Attention();branches=2
        else:
            self.scales=[(16,8)] if kind=='dual_short' else [(64,32)] if kind=='dual_long' else [(16,8),(64,32)]
            self.fragment_attention=nn.ModuleList([Attention() for _ in self.scales]);branches=len(self.scales)+(self.global_projection is not None)
        self.fusion=nn.Sequential(nn.Linear(128*branches,128),nn.LayerNorm(128),nn.GELU())
        self.head=Head(128,spec['widths'])
    def forward(self,batch):
        h=nn.functional.gelu(self.residue_projection(self.residue_norm(batch['residues'])))
        components=[]
        if self.global_projection is not None:components.append(self.global_projection(batch['global_mean']))
        if batch.get('packed',False):
            if self.kind=='residue_attention':components.append(self.residue_attention.forward_packed(h,batch['segment_lengths']))
            else:
                prefix=torch.cat([torch.zeros((1,128),dtype=torch.float64,device=h.device),torch.cumsum(h,dim=0,dtype=torch.float64)],dim=0)
                for (scale,stride),attention in zip(self.scales,self.fragment_attention):
                    f=batch['fragments'][scale];fragments=((prefix[f['ends']]-prefix[f['starts']])/(f['ends']-f['starts'])[:,None]).float()
                    components.append(attention.forward_packed(fragments,f['counts']))
            return self.head(self.fusion(torch.cat(components,dim=1)))
        if self.kind=='residue_attention':components.append(self.residue_attention(h,batch['mask']))
        else:
            prefix=torch.cat([torch.zeros((len(h),1,128),dtype=torch.float64,device=h.device),torch.cumsum(h,dim=1,dtype=torch.float64)],dim=1)
            for (scale,stride),attention in zip(self.scales,self.fragment_attention):
                ranges=[fragment_ranges(int(length),scale,stride) for length in batch['lengths']];maximum=max(map(len,ranges))
                starts=np.zeros((len(h),maximum),np.int64);ends=np.ones((len(h),maximum),np.int64);mask=np.zeros((len(h),maximum),bool)
                for i,rr in enumerate(ranges):
                    starts[i,:len(rr)]=[a for a,b in rr];ends[i,:len(rr)]=[b for a,b in rr];mask[i,:len(rr)]=True
                a=torch.from_numpy(starts).to(h.device);b=torch.from_numpy(ends).to(h.device);m=torch.from_numpy(mask).to(h.device)
                fragments=((prefix.gather(1,b[:,:,None].expand(-1,-1,128))-prefix.gather(1,a[:,:,None].expand(-1,-1,128)))/(b-a)[:,:,None]).float()
                components.append(attention(fragments,m))
        return self.head(self.fusion(torch.cat(components,dim=1)))

def learned(spec):return spec['representation'] not in ['mean','mean_std']
def make_model(spec):
    dim=DIMS[spec['encoder']]*(2 if spec['representation']=='mean_std' else 1)
    return LearnedPooling(spec) if learned(spec) else Head(dim,spec['widths'])

def parameter_count(spec):return sum(p.numel() for p in make_model(spec).parameters() if p.requires_grad)

def forward_parts(model,spec,ids,z,device):
    if learned(spec):
        store=residue_store(spec['encoder'])
        settings=runtime_settings()
        if settings['residue_layout']=='packed':
            for micro in packed_microbatches(ids,spec['encoder'],settings['microbatch_residue_budget']):yield micro,model(store.packed_batch(micro,z,device))
        else:
            for micro in microbatches(ids,spec['encoder'],settings['microbatch_residue_budget']):yield micro,model(store.batch(micro,z,device))
    else:
        for start in range(0,len(ids),1024):
            micro=ids[start:start+1024];yield micro,model(torch.from_numpy(z[micro]).to(device))

def predict(model,spec,ids,z,device):
    model.eval();values=[]
    with torch.inference_mode():
        for micro,scores in forward_parts(model,spec,ids,z,device):values.append(scores.detach().cpu().numpy())
    return np.concatenate(values).astype(np.float64) if values else np.empty(0,np.float64)
