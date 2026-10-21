'use strict';
const $ = id => document.getElementById(id);
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const number = n => n.toLocaleString('en-US');
let records = [], filtered = [], catalogue = {}, rules = {}, display = {labels:{},studies:{}}, page = 0, sequencesPromise;
const perPage = 50;
const shardCache = new Map();
const sequenceShardCache = new Map();
const split = text => String(text || '').split(';').map(x => x.trim()).filter(Boolean);
const readable = value => split(value).map(v => display.labels[v] || v.replace(/_/g, ' ')).join(' ');
const studyName = study => display.studies[study] || study.replace(/_/g, ' ');
const nativeLocus = row => split(row.genes).map(v => v.split('|').pop()).join('; ') || row.id;
function numeric(value) {
  if (value === '' || value === null || value === undefined) return '';
  const n = Number(value); if (!Number.isFinite(n)) return readable(value);
  return n && (Math.abs(n)<.001 || Math.abs(n)>=10000) ? n.toExponential(2) : String(Number(n.toPrecision(4)));
}
function conditionName(obs) {
  if (/_[a-f0-9]{10}$/.test(obs.condition || '')) return 'Source-defined condition (see source locator)';
  return readable(obs.condition);
}
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
async function proteinSequence(row) {
  const shard = row.sha.slice(0, 2);
  if (!sequenceShardCache.has(shard)) {
    const promise = (async () => {
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 15000);
      try {
        const response = await fetch(`data/sequences/${shard}.json`, {signal:controller.signal});
        if (!response.ok) throw new Error(`Sequence request: HTTP ${response.status}`);
        return await response.json();
      } finally { clearTimeout(timeout); }
    })();
    sequenceShardCache.set(shard, promise);
    promise.catch(() => {if (sequenceShardCache.get(shard) === promise) sequenceShardCache.delete(shard);});
  }
  const values = await sequenceShardCache.get(shard);
  if (!values || typeof values !== 'object' || Array.isArray(values)) {
    sequenceShardCache.delete(shard);
    throw new Error('Invalid sequence response');
  }
  const sequence = values[row.id];
  if (typeof sequence !== 'string' || sequence.length !== row.length || !/^[ACDEFGHIKLMNPQRSTVWY]+$/.test(sequence)) {
    sequenceShardCache.delete(shard);
    throw new Error('Sequence record unavailable or incomplete');
  }
  if (globalThis.crypto?.subtle) {
    const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(sequence));
    const actual = Array.from(new Uint8Array(digest), b => b.toString(16).padStart(2, '0')).join('');
    if (actual !== row.sha) {
      sequenceShardCache.delete(shard);
      throw new Error('Sequence identity check failed');
    }
  }
  return sequence;
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
    <td><button class="id-link" data-id="${esc(row.id)}" title="${esc(row.genes)}">${esc(nativeLocus(row))}</button><small>Database ID: ${esc(row.id)}</small></td>
    <td><span class="badge ${row.label ? 'positive' : ''}">${row.label ? 'Positive · 1' : 'Small-effect control · 0'}</span></td>
    <td>${esc(row.strain)}</td><td>${split(row.studies).map(s=>esc(studyName(s))).join('; ')}<small>${esc(readable(row.tier))}</small></td><td>${number(row.length)} aa</td>
    <td><button class="evidence-button" data-id="${esc(row.id)}" aria-label="Evidence for ${esc(row.id)}">↗</button></td></tr>`).join('') || '<tr><td colspan="6">No matching records. Try a broader query or reset the filters.</td></tr>';
  $('page').textContent = `${page+1} / ${pages}`;
  $('previous').disabled = page === 0; $('next').disabled = page >= pages-1;
  $('export-tsv').disabled = $('export-fasta').disabled = !filtered.length;
}
function sourceLink(study) {
  const c = catalogue[study] || {}, raw = c.source_url || (c.doi ? `https://doi.org/${c.doi}` : '');
  const url = /^https:\/\//.test(raw) ? raw : '';
  return url ? `<a href="${esc(url)}" target="_blank" rel="noopener">${esc(studyName(study))} · original source ↗</a>` : esc(studyName(study));
}
let detailRequest = 0;
async function detail(identifier) {
  const request = ++detailRequest;
  const row = records.find(x => x.id === identifier); if (!row) return;
  const dialog = $('detail');
  $('detail-content').innerHTML = `<p class="detail-kicker">EXPERIMENTAL EVIDENCE</p><h2>${esc(nativeLocus(row))}</h2><p class="muted">Database ID: ${esc(row.id)}</p><p><span class="badge ${row.label ? 'positive' : ''}">${row.label ? 'Positive · 1' : 'Small-effect control · 0'}</span></p><div class="detail-grid"><div><b>Native strain</b>${esc(row.strain)}</div><div><b>Gene / native locus</b>${esc(row.genes)}</div><div><b>Complete protein</b>${number(row.length)} amino acids</div><div><b>Homology group</b>${esc(row.group)}</div><div><b>SHA-256 of sequence</b>${esc(row.sha)}</div><div><b>Source study</b>${split(row.studies).map(sourceLink).join('<br>')}</div></div><h3>Complete protein sequence</h3><pre class="sequence-detail" id="detail-sequence" role="status" aria-live="polite" aria-busy="true">Loading protein sequence…</pre><button class="small-button" id="single-fasta" disabled>Download this protein · FASTA ↓</button><button class="small-button" id="retry-sequence" hidden>Retry sequence loading</button><h3>Source observations</h3><div id="observations">Loading evidence records…</div><h3>Interpretation limits</h3><p class="muted">${esc(readable(row.limitations) || 'Consult the source-level rules and recorded experimental conditions.')} These are curated experimental labels, not predictions from the model.</p>`;
  if (!dialog.open) dialog.showModal();
  const sequenceElement = $('detail-sequence'), sequenceButton = $('single-fasta'), retryButton = $('retry-sequence');
  const current = () => request === detailRequest && dialog.open && sequenceElement.isConnected;
  let loadedSequence;
  sequenceButton.onclick = () => {if (current() && loadedSequence) download(`${row.id}.faa`, `>${row.id}\n${loadedSequence}\n`);};
  async function loadSequence() {
    if (!current()) return;
    loadedSequence = undefined;
    sequenceButton.disabled = true;
    retryButton.hidden = true;
    sequenceElement.classList.remove('error');
    sequenceElement.setAttribute('aria-busy', 'true');
    sequenceElement.textContent = 'Loading protein sequence…';
    try {
      const sequence = await proteinSequence(row);
      if (!current()) return;
      loadedSequence = sequence;
      sequenceElement.textContent = sequence;
      sequenceElement.setAttribute('aria-busy', 'false');
      sequenceButton.disabled = false;
    } catch(error) {
      if (!current()) return;
      sequenceElement.textContent = error.name === 'AbortError' ? 'Sequence loading timed out. Please retry.' : 'The protein sequence could not be loaded. Please retry.';
      sequenceElement.setAttribute('aria-busy', 'false');
      sequenceElement.classList.add('error');
      retryButton.hidden = false;
    }
  }
  retryButton.onclick = loadSequence;
  void loadSequence();
  try {
    const shard = row.sha.slice(0,2);
    if (!shardCache.has(shard)) shardCache.set(shard, json(`data/evidence/${shard}.json`));
    const evidence = (await shardCache.get(shard))[identifier] || [];
    if (request !== detailRequest) return;
    $('observations').innerHTML = evidence.map(obs => {
      const rule = rules[obs.study] || {};
      const summary = [['Host',obs.host],['Compartment',obs.compartment],['Assay',readable(obs.assay)],['Condition',conditionName(obs)],['Effect',obs.effect ? `${numeric(obs.effect)} (${readable(obs.effect_type) || 'source definition'})` : 'not recorded numerically'],['P value',numeric(obs.p_value)],['Adjusted P / q',numeric(obs.q_value)],['Biological replicates',readable(obs.replicates)],['Quality / author call',readable(obs.quality_flag || obs.author_call)],['Source locator',obs.public_locator || 'See the source reference and released evidence table'],['Evidence limitation',readable(obs.evidence_limitations)]].filter(([,v]) => v).map(([key,value]) => `<p><b>${esc(key)}:</b> ${esc(value)}</p>`).join('');
      return `<article class="observation"><h4>${sourceLink(obs.study)}</h4>${summary}<details class="record-identifiers"><summary>Record identifiers</summary><p><b>Study ID:</b> ${esc(obs.study)}</p><p><b>Measurement ID:</b> ${esc(obs.measurement_id)}</p><p><b>Condition ID:</b> ${esc(obs.condition)}</p></details><details><summary>Study-level label and growth-control rules</summary><p><b>Positive rule:</b> ${esc(rule.positive_rule || 'See source audit')}</p><p><b>General growth control:</b> ${esc(rule.growth_design || '')}</p><p><b>Applied curation:</b> ${esc(rule.growth_applied || '')}</p><p><b>Remaining limitation:</b> ${esc(rule.growth_limit || '')}</p></details></article>`;
    }).join('') || '<p>See the full traceability tables in the data package.</p>';
  } catch(error) {if (request===detailRequest) $('observations').textContent = `Evidence could not be loaded: ${error.message}`;}
}
$('rows').addEventListener('click', event => {const button = event.target.closest('[data-id]');if(button) detail(button.dataset.id);});
$('close-detail').onclick = () => $('detail').close();
$('detail').addEventListener('close', () => {if (!$('detail').open) detailRequest++;});
$('detail').addEventListener('click', event => {if (event.target === $('detail')) {const r = $('detail').getBoundingClientRect();if(event.clientX<r.left || event.clientX>r.right || event.clientY<r.top || event.clientY>r.bottom) $('detail').close();}});
for (const id of ['search','study','strain','label']) $(id).addEventListener(id==='search' ? 'input' : 'change', applyFilters);
$('reset').onclick = () => {for(const id of ['search','study','strain','label']) $(id).value='';applyFilters();};
$('previous').onclick = () => {page--;render();};$('next').onclick = () => {page++;render();};
$('export-tsv').onclick = () => {
  const headers = ['sample_id','label','strain','gene_ids','studies','study_names','source_dois','length','homology_group','sequence_sha256'];
  const content = [headers, ...filtered.map(r => [r.id,r.label,r.strain,r.genes,r.studies,split(r.studies).map(studyName).join('; '),split(r.studies).map(s=>catalogue[s]?.doi || '').join('; '),r.length,r.group,r.sha])].map(row => row.map(v=>String(v).replace(/[\t\r\n]/g,' ')).join('\t')).join('\n')+'\n';
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
    const [data, presentation] = await Promise.all([json('data/records.json'),json('data/display_labels.json')]);records=data.records;catalogue=data.studies;rules=data.rules;display=presentation;
    records.forEach(row=>row.search=[row.id,row.genes,row.strain,row.studies,split(row.studies).map(studyName).join(' '),row.group,row.sha].join(' ').toLowerCase());
    for (const [id,values] of [['study',[...new Set(records.flatMap(r=>split(r.studies)))].sort()],['strain',[...new Set(records.flatMap(r=>split(r.strain)))].sort()]]) {
      for (const value of values) {const option=document.createElement('option');option.value=value;option.textContent=id==='study' ? studyName(value) : value;$(id).append(option);}
    }
    applyFilters();
  } catch(error) {$('count').textContent=`The database could not be loaded. Please reload or use the data download. ${error.message}`;$('rows').innerHTML='<tr><td colspan="6">Database unavailable. The versioned data package remains available in Downloads.</td></tr>';}
}
start();
