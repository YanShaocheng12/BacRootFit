(() => {
  'use strict';
  const $ = (id) => document.getElementById(id);
  const escape = (s) => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const safeUrl = (s) => /^https?:\/\//i.test(String(s || '')) ? String(s) : '';
  let records=[], studies=[], filtered=[], page=0; const size=12;
  const displayStudy = (id) => studies.find(s=>s.id===id)?.display || id;
  function render() {
    const query=$('search').value.trim().toLowerCase(), group=$('group').value, study=$('study').value;
    filtered=records.filter(r=>(!group||r.group===group)&&(!study||r.studies.includes(study))&&(!query||[r.id,r.organism,r.source_id,r.protein_name,r.gene,...r.studies].join(' ').toLowerCase().includes(query)));
    const max=Math.max(0,Math.ceil(filtered.length/size)-1);page=Math.min(page,max);
    $('result-count').textContent=`${filtered.length.toLocaleString()} records`;
    $('rows').innerHTML=filtered.slice(page*size,(page+1)*size).map(r=>`<tr><td><button class="row-link" data-id="${escape(r.id)}">${escape(r.protein_name||r.source_id.split('|').pop()||r.id)}</button><small>${escape(r.id)}</small></td><td>${escape(r.organism||'Not recorded')}</td><td><span class="badge ${r.group==='Experimental positive'?'positive':'background'}">${escape(r.group)}</span></td><td>${escape(r.studies.map(displayStudy).join('; ')||'UniProtKB / Swiss-Prot')}</td><td><button class="view" data-id="${escape(r.id)}">Details ↗</button></td></tr>`).join('')||'<tr><td colspan="5">No matching records. Try a broader search.</td></tr>';
    $('page-info').textContent=filtered.length?`Showing ${page*size+1}–${Math.min((page+1)*size,filtered.length)} of ${filtered.length}`:'No records';$('previous').disabled=page===0;$('next').disabled=page>=max;
  }
  function detail(id){const r=records.find(x=>x.id===id);if(!r)return; $('detail-title').textContent=r.protein_name||r.source_id.split('|').pop()||r.id;$('detail-id').textContent=r.id;
    const row=(k,v)=>`<div class="detail-row"><b>${escape(k)}</b><span>${v}</span></div>`;
    let sources=r.studies.map(id=>{const s=studies.find(x=>x.id===id);if(!s)return escape(id);const url=safeUrl(s.url);return url?`<a href="${escape(url)}" target="_blank" rel="noreferrer">${escape(s.display)}</a>`:escape(s.display)}).join('<br>');
    if(!sources&&r.accession)sources=`<a href="https://www.uniprot.org/uniprotkb/${encodeURIComponent(r.accession)}" target="_blank" rel="noreferrer">UniProtKB ${escape(r.accession)}</a>`;
    const number=(x)=>x!==''&&Number.isFinite(Number(x))?Number(x).toPrecision(4):String(x||'');
    const observation=(o)=>{const details=[o.plant&&`Host: ${escape(o.plant)}`,o.condition&&`Condition: ${escape(o.condition.replaceAll('_',' '))}`,o.effect&&`Effect: ${escape(number(o.effect))}${o.effect_type?' ('+escape(o.effect_type.replaceAll('_',' '))+')':''}`,o.p_value&&`P: ${escape(number(o.p_value))}`,o.q_value&&`q: ${escape(number(o.q_value))}`,o.replicates&&`Replicates: ${escape(o.replicates)}`,o.source_file&&`Source file: ${escape(o.source_file)}`,o.source_sheet&&`Sheet: ${escape(o.source_sheet)}`,o.source_row&&`Row: ${escape(o.source_row)}`].filter(Boolean).join(' · ');return `<div class="evidence-item"><strong>${escape(displayStudy(o.study))}</strong><p>${details||'See the original source for experimental details.'}</p></div>`};
    $('detail-content').innerHTML=row('Record type',escape(r.group))+row('Organism / strain',escape(r.organism||'Not recorded'))+row('Source identifiers',escape(r.source_id))+row('Protein length',escape(r.length)+' aa')+(r.gene?row('Gene',escape(r.gene)):'')+(r.function?row('Functional category',escape(r.function.replaceAll('_',' '))):'')+row('Evidence source',sources||'Not recorded')+(r.observations?.length?`<h3 class="evidence-heading">Experimental observations <small>(${r.observations.length})</small></h3>${r.observations.map(observation).join('')}`:'')+`<div class="detail-note">${r.group==='Experimental positive'?'Evidence is study-specific; follow the source link for the original experiment and its conditions.':'This is an annotation-screened background protein; a lack of known evidence does not establish an experimental negative.'} Protein sequences are not hosted by this interface.</div>`;
    $('detail').showModal();
  }
  async function init(){try{const res=await fetch('data/records.json');if(!res.ok)throw new Error('HTTP '+res.status);const data=await res.json();records=data.records;studies=data.studies;
    $('study').innerHTML+=[...studies].sort((a,b)=>a.display.localeCompare(b.display)).map(s=>`<option value="${escape(s.id)}">${escape(s.display)}</option>`).join('');
    const publicationType={'preprint':'Preprint','doctoral_thesis':'Doctoral thesis','journal_article':'Journal article'};
    $('study-cards').innerHTML=studies.map(s=>`<article class="study-card"><div><div class="study-code">${escape(publicationType[s.publication_type]||'Source')}</div><h3>${escape(s.display)}</h3><p>${escape(s.title||s.strains||'Study source')}</p></div>${safeUrl(s.url)?`<a href="${escape(s.url)}" target="_blank" rel="noreferrer">Original source ↗</a>`:'<span class="study-code">Source link unavailable</span>'}</article>`).join('');render();
  }catch(e){$('result-count').textContent='Could not load records. Please refresh the page.';console.error(e)}}
  for(const id of ['search','group','study'])$(id).addEventListener('input',()=>{page=0;render()});$('reset').addEventListener('click',()=>{$('search').value='';$('group').value='';$('study').value='';page=0;render()});$('previous').addEventListener('click',()=>{page--;render()});$('next').addEventListener('click',()=>{page++;render()});$('rows').addEventListener('click',e=>{const b=e.target.closest('button[data-id]');if(b)detail(b.dataset.id)});$('close-detail').addEventListener('click',()=>$('detail').close());init();
})();
