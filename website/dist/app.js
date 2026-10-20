'use strict';
const $ = id => document.getElementById(id);
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const number = n => n.toLocaleString('en-US');
let records = [], filtered = [], catalogue = {}, rules = {}, page = 0, sequencesPromise;
const perPage = 50;
const shardCache = new Map();
const split = text => String(text || '').split(';').map(x => x.trim()).filter(Boolean);
async function json(path) { const r = await fetch(path); if (!r.ok) throw new Error(`${path}: HTTP ${r.status}`); return r.json(); }
function download(filename, content, type = 'text/plain') {
  const url = URL.createObjectURL(new Blob([content], {type}));
  const link = document.createElement('a'); link.href = url; link.download = filename; link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
async function sequences() {
  if (!sequencesPromise) sequencesPromise = fetch('data/proteins.faa').then(r => {if (!r.ok) throw new Error('FASTA download failed');return r.text();}).then(text => {
    const result = new Map(); let name, parts = [];
    for (const line of text.split(/\r?\n/)) {
      if (line.startsWith('>')) { if (name) result.set(name, parts.join('')); name = line.slice(1).split(/\s+/)[0]; parts = []; }
      else if (line.trim()) parts.push(line.trim());
    }
    if (name) result.set(name, parts.join(''));
    return result;
  }).catch(error => {sequencesPromise = undefined; throw error;});
  return sequencesPromise;
}
function applyFilters() {
  const query = $('search').value.trim().toLowerCase(), study = $('study').value, strain = $('strain').value, label = $('label').value;
  filtered = records.filter(row => (!query || row.search.includes(query)) && (!study || split(row.studies).includes(study)) && (!strain || split(row.strain).includes(strain)) && (!label || String(row.label) === label));
  page = 0; render();
}
function render() {
  const pages = Math.max(1, Math.ceil(filtered.length / perPage));
  page = Math.min(page, pages-1);
  $('count').textContent = `${number(filtered.length)} of ${number(records.length)} proteins · ${number(filtered.filter(r => r.label === 1).length)} positives`;
  $('rows').innerHTML = filtered.slice(page*perPage, (page+1)*perPage).map(row => `<tr>
    <td><button class="id-link" data-id="${esc(row.id)}">${esc(row.id)}</button><small title="${esc(row.genes)}">${esc(row.genes)}</small></td>
    <td><span class="badge ${row.label ? 'positive' : ''}">${row.label ? 'Positive · 1' : 'Small-effect control · 0'}</span></td>
    <td>${esc(row.strain)}</td><td>${esc(row.studies)}<small>${esc(row.tier)}</small></td><td>${number(row.length)} aa</td>
    <td><button class="evidence-button" data-id="${esc(row.id)}" aria-label="Evidence for ${esc(row.id)}">↗</button></td></tr>`).join('') || '<tr><td colspan="6">No matching records. Try a broader query or reset the filters.</td></tr>';
  $('page').textContent = `${page+1} / ${pages}`;
  $('previous').disabled = page === 0; $('next').disabled = page >= pages-1;
  $('export-tsv').disabled = $('export-fasta').disabled = !filtered.length;
}
function sourceLink(study) {
  const c = catalogue[study] || {}, raw = c.source_url || (c.doi ? `https://doi.org/${c.doi}` : '');
  const url = /^https:\/\//.test(raw) ? raw : '';
  return url ? `<a href="${esc(url)}" target="_blank" rel="noopener">${esc(study)} · original source ↗</a>` : esc(study);
}
let detailRequest = 0;
async function detail(identifier) {
  const request = ++detailRequest;
  const row = records.find(x => x.id === identifier); if (!row) return;
  const dialog = $('detail');
  $('detail-content').innerHTML = `<p class="detail-kicker">FORMAL DATABASE / EXPERIMENTAL EVIDENCE</p><h2>${esc(row.id)}</h2><p><span class="badge ${row.label ? 'positive' : ''}">${row.label ? 'Positive · 1' : 'Small-effect control · 0'}</span></p><div class="detail-grid"><div><b>Native strain</b>${esc(row.strain)}</div><div><b>Gene / native locus</b>${esc(row.genes)}</div><div><b>Complete protein</b>${number(row.length)} amino acids</div><div><b>Repaired homology group</b>${esc(row.group)}</div><div><b>SHA-256 of sequence</b>${esc(row.sha)}</div><div><b>Source study</b>${split(row.studies).map(sourceLink).join('<br>')}</div></div><h3>Complete protein sequence</h3><pre class="sequence-detail" id="detail-sequence">Loading FASTA…</pre><button class="small-button" id="single-fasta">Download this protein · FASTA ↓</button><h3>Source observations</h3><div id="observations">Loading evidence records…</div><h3>Interpretation limits</h3><p class="muted">${esc(row.limitations || 'Consult the source-level rules and recorded experimental conditions.')} These are curated experimental labels, not predictions from the model.</p>`;
  if (!dialog.open) dialog.showModal();
  $('single-fasta').onclick = async () => {try {const map = await sequences(); download(`${row.id}.faa`, `>${row.id}\n${map.get(row.id)}\n`);}catch(error){$('detail-sequence').textContent=error.message;}};
  sequences().then(map => {if (request === detailRequest) $('detail-sequence').textContent = map.get(row.id) || 'Sequence unavailable';}).catch(error => {if(request === detailRequest) $('detail-sequence').textContent=error.message;});
  try {
    const shard = row.sha.slice(0,2);
    if (!shardCache.has(shard)) shardCache.set(shard, json(`data/evidence/${shard}.json`));
    const evidence = (await shardCache.get(shard))[identifier] || [];
    if (request !== detailRequest) return;
    $('observations').innerHTML = evidence.map(obs => {
      const rule = rules[obs.study] || {};
      const summary = [['Host',obs.host],['Compartment',obs.compartment],['Assay',obs.assay],['Condition',obs.condition],['Effect',obs.effect ? `${obs.effect} (${obs.effect_type || 'source definition'})` : 'not recorded numerically'],['P value',obs.p_value],['Adjusted P / q',obs.q_value],['Biological replicates',obs.replicates],['Quality / author call',obs.quality_flag || obs.author_call],['Source locator',obs.locator],['Evidence limitation',obs.evidence_limitations]].filter(([,v]) => v).map(([key,value]) => `<p><b>${esc(key)}:</b> ${esc(value)}</p>`).join('');
      return `<article class="observation"><h4>${sourceLink(obs.study)} · ${esc(obs.measurement_id)}</h4>${summary}<details><summary>Study-level label and growth-control rules</summary><p><b>Positive rule:</b> ${esc(rule.positive_rule || 'See source audit')}</p><p><b>General growth control:</b> ${esc(rule.growth_design || '')}</p><p><b>Applied curation:</b> ${esc(rule.growth_applied || '')}</p><p><b>Remaining limitation:</b> ${esc(rule.growth_limit || '')}</p></details></article>`;
    }).join('') || '<p>See the full traceability tables in the data package.</p>';
  } catch(error) {if (request===detailRequest) $('observations').textContent = `Evidence could not be loaded: ${error.message}`;}
}
$('rows').addEventListener('click', event => {const button = event.target.closest('[data-id]');if(button) detail(button.dataset.id);});
$('close-detail').onclick = () => $('detail').close();
$('detail').addEventListener('click', event => {if (event.target === $('detail')) {const r = $('detail').getBoundingClientRect();if(event.clientX<r.left || event.clientX>r.right || event.clientY<r.top || event.clientY>r.bottom) $('detail').close();}});
for (const id of ['search','study','strain','label']) $(id).addEventListener(id==='search' ? 'input' : 'change', applyFilters);
$('reset').onclick = () => {for(const id of ['search','study','strain','label']) $(id).value='';applyFilters();};
$('previous').onclick = () => {page--;render();};$('next').onclick = () => {page++;render();};
$('export-tsv').onclick = () => {
  const headers = ['sample_id','label','strain','gene_ids','studies','length','homology_group','sequence_sha256'];
  const content = [headers, ...filtered.map(r => [r.id,r.label,r.strain,r.genes,r.studies,r.length,r.group,r.sha])].map(row => row.map(v=>String(v).replace(/[\t\r\n]/g,' ')).join('\t')).join('\n')+'\n';
  download('BacRootFit_matched_records.tsv',content,'text/tab-separated-values');
};
$('export-fasta').onclick = async () => {
  const selected = filtered.slice(), button=$('export-fasta');button.disabled=true;button.textContent='Preparing…';
  try {const map=await sequences();download('BacRootFit_matched_proteins.faa',selected.map(r=>`>${r.id}\n${map.get(r.id)}\n`).join(''));}
  catch(error){$('count').textContent=error.message;}
  finally{button.textContent='FASTA ↓';button.disabled=!filtered.length;}
};
async function start() {
  try {
    const data = await json('data/records.json');records=data.records;catalogue=data.studies;rules=data.rules;
    records.forEach(row=>row.search=[row.id,row.genes,row.strain,row.studies,row.group,row.sha].join(' ').toLowerCase());
    for (const [id,values] of [['study',[...new Set(records.flatMap(r=>split(r.studies)))].sort()],['strain',[...new Set(records.flatMap(r=>split(r.strain)))].sort()]]) {
      for (const value of values) {const option=document.createElement('option');option.value=option.textContent=value;$(id).append(option);}
    }
    applyFilters();
  } catch(error) {$('count').textContent=`Unable to load data. Serve this directory with HTTP, then reload. ${error.message}`;$('rows').innerHTML='<tr><td colspan="6">Database unavailable. The versioned data package remains available in Downloads.</td></tr>';}
}
start();
