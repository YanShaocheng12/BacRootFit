import os
os.environ.setdefault('CUBLAS_WORKSPACE_CONFIG',':4096:8')
from common26 import *
from neural26 import *
import time,random,warnings,joblib
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC
from sklearn.exceptions import ConvergenceWarning
from threadpoolctl import threadpool_limits

def fit_job(task):
    folder=Path(task['folder']);folder.mkdir(parents=True,exist_ok=True);spec=task['spec'];seed=task.get('seed',37)
    info=load(OUT/f"features/{spec['encoder']}/complete.json")
    identity=dict(spec=spec,train=task['train'],monitor=task['monitor'],validation=task['validation'],fixed_epochs=task.get('fixed_epochs'),seed=seed,
        protocol_sha256=sha(OUT/'protocol.json'),feature_bank_sha256=sha(OUT/f"features/{spec['encoder']}/complete.json"),
        code={name:sha(HERE/name) for name in ['fit26.py','neural26.py','common26.py']})
    if (folder/'complete.json').exists():
        assert load(folder/'fit_identity.json')==identity
        for name,digest in load(folder/'complete.json')['files'].items():assert sha(folder/name)==digest
        return dict(folder=str(folder),reused=True,seconds=0.)
    if (folder/'fit_identity.json').exists():assert load(folder/'fit_identity.json')==identity
    save(folder/'fit_identity.json',identity);started=time.time()
    rows=read(DATA/'tables/samples.tsv');y=np.array([int(r['label']) for r in rows]);tr=np.asarray(task['train'],int);mo=np.asarray(task['monitor'],int);va=np.asarray(task['validation'],int)
    assert set(y[tr])=={0,1}
    random.seed(seed);np.random.seed(seed);torch.manual_seed(seed);torch.set_num_threads(1)
    x=fixed_features(spec['encoder'],spec['representation']);scaler=StandardScaler().fit(x[tr]);joblib.dump(scaler,folder/'scaler.joblib')
    z=scaler.transform(x).astype(np.float32);weights=np.ones(len(tr),np.float32)
    if spec['weight']=='balanced':
        for c in [0,1]:weights[y[tr]==c]=len(tr)/(2*np.sum(y[tr]==c))
    np.save(folder/'sample_weights.npy',weights);allwarnings=[];attempts=[];best_epoch=1;epochs_run=1;gamma=None;parameters=None
    with threadpool_limits(limits=1):
        if spec['learner']=='lr':
            for limit in spec['max_iter_attempts']:
                model=LogisticRegression(C=spec['C'],solver='lbfgs',penalty='l2',tol=spec['tol'],max_iter=limit,random_state=seed)
                with warnings.catch_warnings(record=True) as caught:
                    warnings.simplefilter('always');model.fit(z[tr],y[tr],sample_weight=weights)
                converged=not any(issubclass(v.category,ConvergenceWarning) for v in caught);allwarnings.extend(str(v.message) for v in caught)
                attempts.append(dict(max_iter=limit,n_iter=model.n_iter_.tolist(),converged=converged))
                if converged:break
            assert converged,'Unresolved LR convergence; no candidate is dropped.'
            joblib.dump(model,folder/'model.joblib');ms=model.decision_function(z[mo]) if len(mo) else np.empty(0);vs=model.decision_function(z[va]) if len(va) else np.empty(0)
        elif spec['learner']=='svm':
            variance=z[tr].astype(np.float64).var();gamma=(1/(z.shape[1]*variance) if variance else 1.)*spec['gamma_multiplier']
            model=SVC(C=spec['C'],kernel='rbf',gamma=gamma,tol=spec['tol'],max_iter=-1,cache_size=512,probability=False)
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter('always');model.fit(z[tr],y[tr],sample_weight=weights)
            allwarnings.extend(str(v.message) for v in caught);assert model.fit_status_==0
            joblib.dump(model,folder/'model.joblib');ms=model.decision_function(z[mo]) if len(mo) else np.empty(0);vs=model.decision_function(z[va]) if len(va) else np.empty(0)
        else:
            torch.cuda.manual_seed_all(seed);torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False;torch.backends.cudnn.benchmark=False;torch.use_deterministic_algorithms(True)
            device='cuda';model=make_model(spec).cuda();parameters=sum(p.numel() for p in model.parameters() if p.requires_grad)
            optimizer=torch.optim.AdamW(model.parameters(),lr=.001,weight_decay=spec['weight_decay']);rng=np.random.default_rng(seed)
            target=torch.tensor(y,dtype=torch.float32,device=device);global_weights=np.zeros(len(y),np.float32);global_weights[tr]=weights;gw=torch.from_numpy(global_weights).cuda()
            best=(-np.inf,-np.inf);state=None;history=[];maximum=task.get('fixed_epochs') or 100
            for epoch in range(1,maximum+1):
                model.train();order=tr[rng.permutation(len(tr))].tolist();total=0.;effective_batches=0;micro_count=0
                for start in range(0,len(order),128):
                    effective=order[start:start+128];optimizer.zero_grad(set_to_none=True)
                    for micro,logits in forward_parts(model,spec,effective,z,device):
                        loss=(nn.functional.binary_cross_entropy_with_logits(logits,target[micro],reduction='none')*gw[micro]).sum()/len(effective)
                        assert torch.isfinite(loss);loss.backward();total+=float(loss.detach())*len(effective);micro_count+=1
                    nn.utils.clip_grad_norm_(model.parameters(),1.);optimizer.step();effective_batches+=1
                if len(mo):
                    ms=predict(model,spec,mo.tolist(),z,device);auc=float(roc_auc_score(y[mo],ms));bce=float(np.mean(np.logaddexp(0,ms)-y[mo]*ms));key=(auc,-bce)
                    if key>best:best=key;best_epoch=epoch;state={k:v.detach().cpu().clone() for k,v in model.state_dict().items()}
                else:auc='';bce='';best_epoch=epoch
                history.append(dict(epoch=epoch,training_objective=total/len(tr),monitor_AUC=auc,monitor_UNWEIGHTED_BCE=bce,best_epoch=best_epoch,effective_batches=effective_batches,microbatches=micro_count))
                if len(mo) and epoch-best_epoch>=10:break
            epochs_run=epoch
            if len(mo):model.load_state_dict(state)
            else:state={k:v.detach().cpu().clone() for k,v in model.state_dict().items()}
            ms=predict(model,spec,mo.tolist(),z,device);vs=predict(model,spec,va.tolist(),z,device)
            torch.save(dict(spec=spec,state=state,input_dimension=z.shape[1],best_epoch=best_epoch,seed=seed,trainable_parameters=parameters),folder/'model.pt')
            write(folder/'history.tsv',history)
            del model,optimizer,target,gw;torch.cuda.empty_cache()
    assert np.isfinite(ms).all() and np.isfinite(vs).all();np.save(folder/'monitor_scores.npy',np.asarray(ms,np.float64));np.save(folder/'validation_scores.npy',np.asarray(vs,np.float64))
    save(folder/'warnings.json',allwarnings);save(folder/'optimizer_attempts.json',attempts)
    done=dict(status='complete',best_epoch=best_epoch,epochs_run=epochs_run,converged=True,trainable_parameters=parameters,effective_gamma=gamma,
        train_n=len(tr),monitor_n=len(mo),validation_n=len(va),seed=seed,from_random_initialization=True,seconds=time.time()-started)
    done['files']={p.name:sha(p) for p in folder.iterdir() if p.is_file() and p.name!='complete.json' and not p.name.endswith('.partial')}
    save(folder/'complete.json',done)
    return dict(folder=str(folder),reused=False,seconds=done['seconds'])

def infer(folder,ids,device='cpu'):
    folder=Path(folder);identity=load(folder/'fit_identity.json');spec=identity['spec'];scaler=joblib.load(folder/'scaler.joblib')
    x=fixed_features(spec['encoder'],spec['representation']);z=scaler.transform(x).astype(np.float32)
    if spec['learner']!='mlp':return joblib.load(folder/'model.joblib').decision_function(z[ids]).astype(np.float64)
    record=torch.load(folder/'model.pt',map_location='cpu',weights_only=False);model=make_model(spec).to(device);model.load_state_dict(record['state'])
    values=predict(model,spec,list(ids),z,device);del model
    if device=='cuda':torch.cuda.empty_cache()
    return values
